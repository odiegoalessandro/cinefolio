"""Testes das operações de avatar do usuário autenticado."""

import os
import tempfile
import threading
import unittest
from pathlib import Path

from server.controllers.profile_controller import ProfileController
from server.database.connection import get_connection, initialize_database
from server.http.multipart import UploadedFile
from server.repositories.user_movie_repository import UserMovieRepository
from server.repositories.user_repository import UserRepository
from server.services.avatar_storage import AvatarStorage
from server.services.avatar_mutation_coordinator import AvatarMutationCoordinator
from server.services.auth_service import hash_password
from server.services.profile_service import ProfileService


PNG_BYTES = b"\x89PNG\r\n\x1a\nprofile-image"


class ProfileAvatarTests(unittest.TestCase):
    """Garante que operações de avatar alterem somente a sessão atual."""

    def setUp(self):
        database_file = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        database_file.close()
        self.database_path = database_file.name
        initialize_database(self.database_path)
        self.connection = get_connection(self.database_path)
        self.users = UserRepository(self.connection)
        self.user_movies = UserMovieRepository(self.connection)
        self.temp_directory = tempfile.TemporaryDirectory()
        self.upload_directory = Path(self.temp_directory.name) / "avatars"
        self.storage = AvatarStorage(self.upload_directory)
        self.profile_service = ProfileService(self.users, self.user_movies)
        self.controller = ProfileController(
            self.profile_service,
            self.users,
            self.storage,
        )

    def tearDown(self):
        self.temp_directory.cleanup()
        self.connection.close()
        os.unlink(self.database_path)

    def create_test_user(self, username: str):
        """Cria um usuário real para testar a autorização pelo identificador da sessão."""
        return self.users.create(
            username=username,
            display_name=username.title(),
            password_hash=hash_password("senhasegura123"),
        )

    def test_replace_avatar_changes_only_the_authenticated_user(self):
        """Falha se o avatar enviado na sessão do dono puder alterar outro registro."""
        owner = self.create_test_user("owner")
        other = self.create_test_user("other")

        result = self.controller.replace_avatar(
            dict(owner),
            UploadedFile(content=PNG_BYTES, content_type="image/png"),
        )

        self.assertRegex(result["user"]["avatar_url"], r"^/uploads/avatars/.+\.png$")
        self.assertEqual(self.users.get_by_id(other["id"])["avatar_url"], "")

    def test_replace_avatar_removes_the_previous_local_file_after_persisting_the_new_one(self):
        """Falha se substituir uma foto deixar o arquivo anterior acessível no disco."""
        owner = self.create_test_user("owner")
        first = self.controller.replace_avatar(
            dict(owner),
            UploadedFile(content=PNG_BYTES, content_type="image/png"),
        )

        second = self.controller.replace_avatar(
            dict(owner),
            UploadedFile(content=PNG_BYTES, content_type="image/png"),
        )

        self.assertNotEqual(first["user"]["avatar_url"], second["user"]["avatar_url"])
        self.assertEqual(len(list(self.upload_directory.iterdir())), 1)

    def test_remove_avatar_clears_the_database_value_and_removes_the_local_file(self):
        """Falha se remover a foto não restaurar o avatar padrão do usuário."""
        owner = self.create_test_user("owner")
        self.controller.replace_avatar(
            dict(owner),
            UploadedFile(content=PNG_BYTES, content_type="image/png"),
        )

        result = self.controller.remove_avatar(dict(owner))

        self.assertEqual(result["user"]["avatar_url"], "")
        self.assertEqual(self.users.get_by_id(owner["id"])["avatar_url"], "")
        self.assertEqual(list(self.upload_directory.iterdir()), [])

    def test_update_profile_keeps_the_avatar_when_the_payload_omits_its_url(self):
        """Falha se atualizar textos apagar uma foto enviada pelo novo fluxo."""
        owner = self.create_test_user("owner")
        with_avatar = self.controller.replace_avatar(
            dict(owner),
            UploadedFile(content=PNG_BYTES, content_type="image/png"),
        )

        result = self.controller.update_profile(
            dict(owner),
            {
                "display_name": "Novo nome",
                "bio": "Nova biografia",
                "banner_url": "",
            },
        )

        self.assertEqual(result["user"]["avatar_url"], with_avatar["user"]["avatar_url"])

    def test_delete_account_removes_its_local_avatar_before_deleting_the_user(self):
        """Falha se excluir a conta deixar uma foto local órfã no armazenamento."""
        owner = self.create_test_user("owner")
        self.controller.replace_avatar(
            dict(owner),
            UploadedFile(content=PNG_BYTES, content_type="image/png"),
        )

        result = self.controller.delete_account(dict(owner))

        self.assertEqual(result["ok"], True)
        self.assertIsNone(self.users.get_by_id(owner["id"]))
        self.assertEqual(list(self.upload_directory.iterdir()), [])

    def test_delete_account_restores_the_avatar_when_database_deletion_fails(self):
        """Falha se a conta mantiver referência para uma foto removida após erro no banco."""
        owner = self.create_test_user("owner")
        uploaded = self.controller.replace_avatar(
            dict(owner),
            UploadedFile(content=PNG_BYTES, content_type="image/png"),
        )
        avatar_path = self.upload_directory / uploaded["user"]["avatar_url"].rsplit("/", 1)[1]
        original_delete = self.users.delete

        def fail_delete(_user_id):
            raise RuntimeError("Banco indisponível.")

        self.users.delete = fail_delete
        try:
            with self.assertRaisesRegex(RuntimeError, "Banco indisponível"):
                self.controller.delete_account(dict(owner))
        finally:
            self.users.delete = original_delete

        self.assertIsNotNone(self.users.get_by_id(owner["id"]))
        self.assertTrue(avatar_path.exists())

    def test_same_user_avatar_mutations_are_serialized(self):
        """Falha se remover durante upload deixar a resposta final fora da ordem das ações."""
        owner = self.create_test_user("owner")
        storage = BlockingAvatarStorage(self.storage)
        coordinator = AvatarMutationCoordinator()
        errors = []

        def create_thread_controller():
            connection = get_connection(self.database_path)
            users = UserRepository(connection)
            user_movies = UserMovieRepository(connection)
            controller = ProfileController(
                ProfileService(users, user_movies),
                users,
                storage,
                coordinator,
            )
            return controller, connection

        def upload_avatar():
            controller, connection = create_thread_controller()
            try:
                controller.replace_avatar(
                    dict(owner),
                    UploadedFile(content=PNG_BYTES, content_type="image/png"),
                )
            except Exception as error:
                errors.append(error)
            finally:
                connection.close()

        def remove_avatar():
            controller, connection = create_thread_controller()
            try:
                controller.remove_avatar(dict(owner))
            except Exception as error:
                errors.append(error)
            finally:
                connection.close()

        upload_thread = threading.Thread(target=upload_avatar)
        upload_thread.start()
        self.assertTrue(storage.save_started.wait(timeout=1), errors)

        remove_thread = threading.Thread(target=remove_avatar)
        remove_thread.start()
        self.assertFalse(storage.stage_started.wait(timeout=0.1))

        storage.release_save.set()
        upload_thread.join(timeout=1)
        remove_thread.join(timeout=1)

        self.assertEqual(errors, [])
        self.assertEqual(self.users.get_by_id(owner["id"])["avatar_url"], "")
        self.assertEqual(list(self.upload_directory.iterdir()), [])


class BlockingAvatarStorage:
    """Controla a gravação real para expor a corrida entre duas mutações."""

    def __init__(self, storage):
        self.storage = storage
        self.save_started = threading.Event()
        self.release_save = threading.Event()
        self.stage_started = threading.Event()

    def save(self, content, content_type):
        self.save_started.set()
        self.release_save.wait(timeout=1)
        return self.storage.save(content, content_type)

    def stage_removal(self, avatar_url):
        self.stage_started.set()
        return self.storage.stage_removal(avatar_url)

    def remove(self, avatar_url):
        return self.storage.remove(avatar_url)

    def restore(self, staged_avatar):
        return self.storage.restore(staged_avatar)

    def discard(self, staged_avatar):
        return self.storage.discard(staged_avatar)


if __name__ == "__main__":
    unittest.main()
