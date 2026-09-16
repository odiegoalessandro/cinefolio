"""Testes das operações de avatar do usuário autenticado."""

import os
import tempfile
import threading
import unittest
from pathlib import Path

from server.controllers.account_controller import AccountController
from server.controllers.avatar_controller import AvatarController
from server.controllers.profile_controller import ProfileController
from server.database.connection import get_connection, initialize_database
from server.http.multipart import UploadedFile
from server.repositories.user_movie_repository import UserMovieRepository
from server.repositories.user_repository import UserRepository
from server.services.avatar_storage import AvatarStorage
from server.services.avatar_mutation_coordinator import AvatarMutationCoordinator
from server.services.auth_service import hash_password
from server.services.avatar_service import AvatarService
from server.services.profile_service import ProfileService


PNG_BYTES = b"\x89PNG\r\n\x1a\nprofile-image"


class ProfileAvatarTests(unittest.TestCase):
    """Garante que operações de avatar alterem somente a sessão atual.

    Diferente de test_avatar_routes.py (que testa via HTTP real), este
    arquivo testa a camada de CONTROLLERS diretamente — mais rápido, e
    permite testar cenários internos (como falhas simuladas no banco)
    difíceis de provocar só através de requisições HTTP.
    """

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
        self.avatar_service = AvatarService(
            self.users,
            self.storage,
            AvatarMutationCoordinator(),
        )
        self.avatar_controller = AvatarController(self.avatar_service)
        self.account_controller = AccountController(self.avatar_service)
        self.profile_controller = ProfileController(
            self.profile_service,
            self.users,
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

        # dict(owner) converte o sqlite3.Row num dict comum, simulando o
        # "current_user" que o Router normalmente passaria ao controller
        result = self.avatar_controller.replace_avatar(
            dict(owner),
            UploadedFile(content=PNG_BYTES, content_type="image/png"),
        )

        self.assertRegex(result["user"]["avatar_url"], r"^/uploads/avatars/.+\.png$")
        # Confirma que o segundo usuário ("other") continua sem avatar,
        # mesmo depois do "owner" fazer upload
        self.assertEqual(self.users.get_by_id(other["id"])["avatar_url"], "")

    def test_replace_avatar_removes_the_previous_local_file_after_persisting_the_new_one(self):
        """Falha se substituir uma foto deixar o arquivo anterior acessível no disco."""
        owner = self.create_test_user("owner")
        first = self.avatar_controller.replace_avatar(
            dict(owner),
            UploadedFile(content=PNG_BYTES, content_type="image/png"),
        )

        second = self.avatar_controller.replace_avatar(
            dict(owner),
            UploadedFile(content=PNG_BYTES, content_type="image/png"),
        )

        # Cada upload gera um nome de arquivo diferente (UUID aleatório)
        self.assertNotEqual(first["user"]["avatar_url"], second["user"]["avatar_url"])
        # Mas o disco deve ter só 1 arquivo no final: a segunda foto ficou,
        # a primeira foi descartada corretamente (sem deixar "lixo" no disco)
        self.assertEqual(len(list(self.upload_directory.iterdir())), 1)

    def test_remove_avatar_clears_the_database_value_and_removes_the_local_file(self):
        """Falha se remover a foto não restaurar o avatar padrão do usuário."""
        owner = self.create_test_user("owner")
        self.avatar_controller.replace_avatar(
            dict(owner),
            UploadedFile(content=PNG_BYTES, content_type="image/png"),
        )

        result = self.avatar_controller.remove_avatar(dict(owner))

        self.assertEqual(result["user"]["avatar_url"], "")
        self.assertEqual(self.users.get_by_id(owner["id"])["avatar_url"], "")
        self.assertEqual(list(self.upload_directory.iterdir()), [])

    def test_update_profile_keeps_the_avatar_when_the_payload_omits_its_url(self):
        """Falha se atualizar textos apagar uma foto enviada pelo novo fluxo."""
        owner = self.create_test_user("owner")
        with_avatar = self.avatar_controller.replace_avatar(
            dict(owner),
            UploadedFile(content=PNG_BYTES, content_type="image/png"),
        )

        # Atualiza SÓ os campos de texto do perfil (sem mencionar avatar)
        result = self.profile_controller.update_profile(
            dict(owner),
            {
                "display_name": "Novo nome",
                "bio": "Nova biografia",
                "banner_url": "",
            },
        )

        # Confirma que o avatar continua o MESMO de antes (a atualização de
        # texto não "zera" o avatar por acidente)
        self.assertEqual(result["user"]["avatar_url"], with_avatar["user"]["avatar_url"])

    def test_delete_account_removes_its_local_avatar_before_deleting_the_user(self):
        """Falha se excluir a conta deixar uma foto local órfã no armazenamento."""
        owner = self.create_test_user("owner")
        self.avatar_controller.replace_avatar(
            dict(owner),
            UploadedFile(content=PNG_BYTES, content_type="image/png"),
        )

        result = self.account_controller.delete_account(dict(owner))

        self.assertEqual(result["ok"], True)
        self.assertIsNone(self.users.get_by_id(owner["id"]))
        # O avatar do usuário excluído também some do disco (não fica órfão)
        self.assertEqual(list(self.upload_directory.iterdir()), [])

    def test_delete_account_restores_the_avatar_when_database_deletion_fails(self):
        """Falha se a conta mantiver referência para uma foto removida após erro no banco."""
        owner = self.create_test_user("owner")
        uploaded = self.avatar_controller.replace_avatar(
            dict(owner),
            UploadedFile(content=PNG_BYTES, content_type="image/png"),
        )
        avatar_path = self.upload_directory / uploaded["user"]["avatar_url"].rsplit("/", 1)[1]
        original_delete = self.users.delete

        # "Monkey patch": substitui temporariamente o método delete() do
        # repositório por uma versão que sempre falha, para simular um
        # banco de dados indisponível durante a exclusão
        def fail_delete(_user_id):
            raise RuntimeError("Banco indisponível.")

        self.users.delete = fail_delete
        try:
            with self.assertRaisesRegex(RuntimeError, "Banco indisponível"):
                self.account_controller.delete_account(dict(owner))
        finally:
            # Restaura o método original, mesmo se o teste falhar, para não
            # "vazar" esse comportamento quebrado para outros testes
            self.users.delete = original_delete

        # Como o banco "falhou", o usuário e o arquivo do avatar devem
        # continuar intactos — nada foi excluído pela metade (ver
        # avatar_service.py: o stage/restore garante essa atomicidade)
        self.assertIsNotNone(self.users.get_by_id(owner["id"]))
        self.assertTrue(avatar_path.exists())

    def test_same_user_avatar_mutations_are_serialized(self):
        """Falha se remover durante upload deixar a resposta final fora da ordem das ações."""
        # Este é um teste de CONCORRÊNCIA: simula duas requisições
        # simultâneas (upload e remoção) do MESMO usuário, para confirmar
        # que o AvatarMutationCoordinator realmente as executa uma de cada vez
        owner = self.create_test_user("owner")
        storage = BlockingAvatarStorage(self.storage)
        coordinator = AvatarMutationCoordinator()
        errors = []

        def create_thread_controller():
            # Cada thread precisa da sua PRÓPRIA conexão com o banco
            # (conexões SQLite não são seguras para compartilhar entre
            # threads livremente)
            connection = get_connection(self.database_path)
            users = UserRepository(connection)
            user_movies = UserMovieRepository(connection)
            avatar_service = AvatarService(
                users,
                storage,
                coordinator,
            )
            return AvatarController(avatar_service), connection

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

        # Inicia o upload primeiro e espera até ele "travar" dentro de
        # storage.save() (ver BlockingAvatarStorage abaixo) — ponto exato
        # em que o lock do coordinator já deveria estar sendo segurado
        upload_thread = threading.Thread(target=upload_avatar)
        upload_thread.start()
        self.assertTrue(storage.save_started.wait(timeout=1), errors)

        # Só então inicia a remoção: como ela usa o MESMO coordinator/lock,
        # ela deve ficar bloqueada esperando o upload terminar
        remove_thread = threading.Thread(target=remove_avatar)
        remove_thread.start()
        # Confirma que a remoção NÃO conseguiu avançar (stage_removal não
        # foi chamado) enquanto o upload ainda está "preso" em save()
        self.assertFalse(storage.stage_started.wait(timeout=0.1))

        # Libera o upload para terminar; só depois disso a remoção pode prosseguir
        storage.release_save.set()
        upload_thread.join(timeout=1)
        remove_thread.join(timeout=1)

        self.assertEqual(errors, [])
        # Resultado final esperado: como a remoção rodou DEPOIS do upload
        # (nessa ordem, garantida pelo lock), o avatar termina vazio
        self.assertEqual(self.users.get_by_id(owner["id"])["avatar_url"], "")
        self.assertEqual(list(self.upload_directory.iterdir()), [])


class BlockingAvatarStorage:
    """Controla a gravação real para expor a corrida entre duas mutações.

    "Decora" o AvatarStorage de verdade, mas insere pontos de
    sincronização controlados por threading.Event: permite ao teste
    "pausar" a execução de uma thread no meio de uma operação (dentro de
    save()), para forçar deliberadamente uma condição de corrida e
    verificar se ela é tratada corretamente.
    """

    def __init__(self, storage):
        self.storage = storage
        self.save_started = threading.Event()   # sinaliza: "save() começou"
        self.release_save = threading.Event()   # sinaliza: "pode continuar o save()"
        self.stage_started = threading.Event()  # sinaliza: "stage_removal() começou"

    def save(self, content, content_type):
        self.save_started.set()
        # Bloqueia aqui até o teste liberar (no máximo 1 segundo), criando
        # de propósito uma janela de tempo onde o lock deve estar sendo mantido
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
