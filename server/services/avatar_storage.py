"""Armazenamento local e seguro das fotos de perfil."""

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4


MAX_AVATAR_BYTES = 2 * 1024 * 1024  # limite de 2 MiB por foto
AVATAR_URL_PREFIX = "/uploads/avatars/" # prefixo de URL usado para servir os avatares

# "Assinatura de arquivo" (magic bytes): os primeiros bytes de um arquivo
# identificam seu formato real, independente da extensão ou do header
# Content-Type informado (que podem ser falsificados pelo cliente).
# Cada entrada mapeia: content-type esperado -> (extensão, função que
# confirma se os bytes batem com aquele formato de imagem)
IMAGE_TYPES = {
    "image/jpeg": (".jpg", lambda content: content.startswith(b"\xff\xd8\xff")),
    "image/png": (".png", lambda content: content.startswith(b"\x89PNG\r\n\x1a\n")),
    "image/webp": (
        ".webp",
        lambda content: len(content) >= 12
        and content[:4] == b"RIFF"
        and content[8:12] == b"WEBP",
    ),
}


@dataclass(frozen=True)
class StagedAvatar:
    """Arquivo movido temporariamente enquanto a alteração no banco é confirmada.

    Guarda tanto o caminho original quanto o caminho temporário, para que
    seja possível restaurar o arquivo de volta ao lugar original se algo
    der errado depois (ex: falha ao salvar no banco de dados).
    """

    original_path: Path
    staged_path: Path


class AvatarStorage:
    """Persiste apenas imagens verificadas no diretório local configurado."""

    def __init__(self, upload_directory: Path):
        self.upload_directory = Path(upload_directory)

    def save(self, content: bytes, content_type: str) -> str:
        """Valida a imagem e retorna sua URL relativa após a escrita atômica."""
        extension, is_matching_image = IMAGE_TYPES.get(content_type, (None, None))
        if not extension or not is_matching_image(content):
            # Rejeita se o tipo não é suportado OU se os bytes reais do
            # arquivo não batem com o Content-Type que o cliente alegou
            # (proteção contra upload de arquivo malicioso disfarçado de imagem)
            raise ValueError("O tipo da foto não corresponde ao arquivo enviado.")
        if len(content) > MAX_AVATAR_BYTES:
            raise ValueError("A foto deve ter no máximo 2 MiB.")

        # Nome de arquivo aleatório (UUID) evita: colisão de nomes, um
        # usuário "adivinhar" o nome do arquivo de outro, e problemas com
        # caracteres especiais que o nome original pudesse ter
        filename = f"{uuid4()}{extension}"
        self.upload_directory.mkdir(parents=True, exist_ok=True)
        self._write_atomically(self.upload_directory / filename, content)
        return f"{AVATAR_URL_PREFIX}{filename}"

    def remove(self, avatar_url: str) -> None:
        """Remove somente um avatar pertencente a este armazenamento local."""
        target = self._local_path(avatar_url)
        if target is None:
            return

        target.unlink(missing_ok=True)  # missing_ok evita erro se o arquivo já não existir

    def stage_removal(self, avatar_url: str) -> StagedAvatar | None:
        """Move o avatar para um nome interno antes de uma mudança no banco.

        Em vez de apagar o arquivo antigo direto, ele é RENOMEADO para um
        nome "escondido" (prefixo "."). Isso implementa um padrão de
        "transação": se a atualização no banco falhar depois, dá pra
        restaurar o arquivo original (ver o método restore).
        """
        target = self._local_path(avatar_url)
        if target is None or not target.exists():
            return None

        staged_path = target.with_name(f".removing-{uuid4()}{target.suffix}")
        os.replace(target, staged_path) # rename atômico no sistema de arquivos
        return StagedAvatar(original_path=target, staged_path=staged_path)

    @staticmethod
    def restore(staged_avatar: StagedAvatar | None) -> None:
        """Restaura o arquivo movido quando a persistência no banco falha."""
        if staged_avatar is not None and staged_avatar.staged_path.exists():
            os.replace(staged_avatar.staged_path, staged_avatar.original_path)

    @staticmethod
    def discard(staged_avatar: StagedAvatar | None) -> None:
        """Descarta o arquivo já desvinculado após a persistência ser confirmada."""
        if staged_avatar is None:
            return

        try:
            staged_avatar.staged_path.unlink(missing_ok=True)
        except OSError:
            # Falha ao apagar o arquivo temporário não deve quebrar a
            # operação principal (o banco já foi atualizado com sucesso);
            # na pior hipótese, sobra um arquivo órfão no disco
            pass

    def _local_filename(self, avatar_url: str) -> str | None:
        """Extrai um nome simples de arquivo de uma URL local de avatar."""
        if not isinstance(avatar_url, str) or not avatar_url.startswith(AVATAR_URL_PREFIX):
            return None

        filename = avatar_url.removeprefix(AVATAR_URL_PREFIX)
        # Path(filename).name != filename detecta tentativas de "path
        # traversal" (ex: filename = "../../etc/passwd"), pois nesse caso
        # o ".name" retornaria só "passwd", diferente do filename completo
        if not filename or Path(filename).name != filename:
            return None
        return filename

    def _local_path(self, avatar_url: str) -> Path | None:
        """Resolve uma URL local para um arquivo sem permitir saída do diretório."""
        filename = self._local_filename(avatar_url)
        if filename is None:
            return None

        # .resolve() converte para caminho absoluto, eliminando "..", links
        # simbólicos etc. Depois confirma que o resultado realmente está
        # DENTRO do diretório de uploads — uma segunda camada de proteção
        # contra escrever/apagar arquivos fora da pasta permitida
        target = (self.upload_directory / filename).resolve()
        root = self.upload_directory.resolve()
        return target if target.parent == root else None

    def _write_atomically(self, target: Path, content: bytes) -> None:
        """Grava em arquivo temporário e só então o publica no destino final.

        Escrever direto no arquivo final poderia deixar um arquivo
        corrompido/incompleto visível caso o processo caia no meio da
        escrita. Por isso: escreve tudo num arquivo temporário primeiro,
        garante que foi gravado em disco (fsync) e só então RENOMEIA
        (operação atômica no sistema de arquivos) para o nome final.
        """
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=self.upload_directory,  # mesmo diretório do destino: renomear entre diretórios diferentes não seria atômico
                prefix=".avatar-",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                temporary_file.write(content)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())   # força a escrita física no disco

            os.replace(temporary_path, target)
        finally:
            # Se algo falhar antes do os.replace, garante que o arquivo
            # temporário não fica esquecido ocupando espaço em disco
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
