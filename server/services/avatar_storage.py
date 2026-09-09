"""Armazenamento local e seguro das fotos de perfil."""

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4


MAX_AVATAR_BYTES = 2 * 1024 * 1024
AVATAR_URL_PREFIX = "/uploads/avatars/"
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
    """Arquivo movido temporariamente enquanto a alteração no banco é confirmada."""

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
            raise ValueError("O tipo da foto não corresponde ao arquivo enviado.")
        if len(content) > MAX_AVATAR_BYTES:
            raise ValueError("A foto deve ter no máximo 2 MiB.")

        filename = f"{uuid4()}{extension}"
        self.upload_directory.mkdir(parents=True, exist_ok=True)
        self._write_atomically(self.upload_directory / filename, content)
        return f"{AVATAR_URL_PREFIX}{filename}"

    def remove(self, avatar_url: str) -> None:
        """Remove somente um avatar pertencente a este armazenamento local."""
        target = self._local_path(avatar_url)
        if target is None:
            return

        target.unlink(missing_ok=True)

    def stage_removal(self, avatar_url: str) -> StagedAvatar | None:
        """Move o avatar para um nome interno antes de uma mudança no banco."""
        target = self._local_path(avatar_url)
        if target is None or not target.exists():
            return None

        staged_path = target.with_name(f".removing-{uuid4()}{target.suffix}")
        os.replace(target, staged_path)
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
            pass

    def _local_filename(self, avatar_url: str) -> str | None:
        """Extrai um nome simples de arquivo de uma URL local de avatar."""
        if not isinstance(avatar_url, str) or not avatar_url.startswith(AVATAR_URL_PREFIX):
            return None

        filename = avatar_url.removeprefix(AVATAR_URL_PREFIX)
        if not filename or Path(filename).name != filename:
            return None
        return filename

    def _local_path(self, avatar_url: str) -> Path | None:
        """Resolve uma URL local para um arquivo sem permitir saída do diretório."""
        filename = self._local_filename(avatar_url)
        if filename is None:
            return None

        target = (self.upload_directory / filename).resolve()
        root = self.upload_directory.resolve()
        return target if target.parent == root else None

    def _write_atomically(self, target: Path, content: bytes) -> None:
        """Grava em arquivo temporário e só então o publica no destino final."""
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=self.upload_directory,
                prefix=".avatar-",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                temporary_file.write(content)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())

            os.replace(temporary_path, target)
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
