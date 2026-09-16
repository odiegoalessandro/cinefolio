"""Testes do armazenamento local de avatares."""

import tempfile
import unittest
from pathlib import Path

from server.services.avatar_storage import AvatarStorage


PNG_BYTES = b"\x89PNG\r\n\x1a\nprofile-image"
JPEG_BYTES = b"\xff\xd8\xffprofile-image"
WEBP_BYTES = b"RIFF\x12\x00\x00\x00WEBPprofile-image"


class AvatarStorageTests(unittest.TestCase):
    """Garante persistência local somente para imagens verificadas."""

    def setUp(self):
        # setUp roda ANTES de cada teste desta classe: cria um diretório
        # temporário isolado, então os testes nunca escrevem no disco real
        # do projeto nem interferem uns nos outros
        self.temp_directory = tempfile.TemporaryDirectory()
        self.upload_directory = Path(self.temp_directory.name) / "avatars"
        self.storage = AvatarStorage(self.upload_directory)

    def tearDown(self):
        # tearDown roda DEPOIS de cada teste: apaga o diretório temporário
        self.temp_directory.cleanup()

    def test_save_returns_a_local_png_url_and_persists_the_verified_bytes(self):
        """Falha se um PNG válido não for gravado sob o diretório de avatar configurado."""
        avatar_url = self.storage.save(PNG_BYTES, "image/png")

        # Confirma o formato da URL gerada (prefixo + UUID + extensão)
        self.assertRegex(avatar_url, r"^/uploads/avatars/[0-9a-f-]+\.png$")
        filename = avatar_url.rsplit("/", 1)[1]
        # Confirma que o arquivo foi realmente escrito no disco com os
        # bytes corretos (não só que a URL "parece certa")
        self.assertEqual((self.upload_directory / filename).read_bytes(), PNG_BYTES)

    def test_save_accepts_each_supported_image_signature(self):
        """Falha se JPEG ou WebP válidos forem rejeitados pelo verificador binário."""
        # Envia bytes de PNG mas alega ser "image/jpeg": deve ser recusado
        cases = (
            (JPEG_BYTES, "image/jpeg", ".jpg"),
            (WEBP_BYTES, "image/webp", ".webp"),
        )

        # Confirma que a tentativa recusada nem chegou a criar o diretório
        # de uploads (nada é escrito em disco em caso de erro)
        for content, content_type, extension in cases:
            with self.subTest(content_type=content_type):
                avatar_url = self.storage.save(content, content_type)
                self.assertTrue(avatar_url.endswith(extension))

    def test_save_rejects_a_declared_type_that_does_not_match_the_signature(self):
        """Falha se o tipo informado pelo navegador puder divergir dos bytes enviados."""
        # Monta um PNG válido (passa na checagem de assinatura) mas maior
        # que o limite de 2 MiB, para testar exclusivamente a checagem de tamanho
        with self.assertRaisesRegex(ValueError, "tipo da foto"):
            self.storage.save(PNG_BYTES, "image/jpeg")

        self.assertFalse(self.upload_directory.exists())

    def test_save_rejects_content_larger_than_two_mebibytes(self):
        """Falha se a camada de armazenamento aceitar conteúdo além do limite da feature."""
        oversized_png = b"\x89PNG\r\n\x1a\n" + b"x" * (2 * 1024 * 1024 - 7)

        with self.assertRaisesRegex(ValueError, "no máximo 2 MiB"):
            self.storage.save(oversized_png, "image/png")

        self.assertFalse(self.upload_directory.exists())

    def test_remove_ignores_external_and_unsafe_urls(self):
        """Falha se uma URL que não pertence ao armazenamento local puder apagar um arquivo."""
        sentinel = self.upload_directory / "sentinel.txt"
        sentinel.parent.mkdir(parents=True, exist_ok=True)
        sentinel.write_text("preserve")

        # Tenta remover uma URL externa (de outro domínio) e uma tentativa
        # de "path traversal" (../) — nenhuma das duas deve apagar o arquivo sentinela
        self.storage.remove("https://images.example/avatar.png")
        self.storage.remove("/uploads/avatars/../sentinel.txt")

        self.assertTrue(sentinel.exists())

    def test_remove_deletes_only_a_previously_saved_local_avatar(self):
        """Falha se uma foto local removida permanecer acessível no disco."""
        avatar_url = self.storage.save(PNG_BYTES, "image/png")

        self.storage.remove(avatar_url)

        # O diretório deve ficar vazio depois da remoção (nenhum arquivo sobrando)
        self.assertEqual(list(self.upload_directory.iterdir()), [])

    def test_stage_removal_restores_the_avatar_after_a_failed_database_operation(self):
        """Falha se o arquivo não puder voltar ao local após a persistência falhar."""
        avatar_url = self.storage.save(PNG_BYTES, "image/png")
        filename = avatar_url.rsplit("/", 1)[1]

        # Simula o primeiro passo de uma troca de avatar: o arquivo antigo
        # é "estagiado" (renomeado, mas não apagado de verdade)
        staged_avatar = self.storage.stage_removal(avatar_url)
        self.assertFalse((self.upload_directory / filename).exists())

        # Simula uma falha depois (ex: erro ao salvar no banco): o arquivo
        # deve voltar exatamente para onde estava, com o conteúdo intacto
        self.storage.restore(staged_avatar)

        self.assertEqual((self.upload_directory / filename).read_bytes(), PNG_BYTES)


class AvatarStorageInitializationTests(unittest.TestCase):
    """Garante que a construção do armazenamento não acesse o volume de uploads."""

    def test_constructor_does_not_create_the_upload_directory(self):
        """Falha se uma requisição sem avatar precisar escrever no diretório de uploads."""
        with tempfile.TemporaryDirectory() as temp_dir:
            upload_directory = Path(temp_dir) / "avatars"

            AvatarStorage(upload_directory)

            # O construtor sozinho não deve criar a pasta — ela só é criada
            # de fato quando save() é chamado pela primeira vez (ver avatar_storage.py)
            self.assertFalse(upload_directory.exists())


if __name__ == "__main__":
    unittest.main()
