"""Testes da composição das dependências da aplicação HTTP."""

import os
import tempfile
import unittest
from pathlib import Path

from server.application import create_router
from server.controllers.account_controller import AccountController
from server.controllers.avatar_controller import AvatarController
from server.controllers.profile_controller import ProfileController
from server.database.connection import get_connection, initialize_database
from server.router import Router
from server.services.avatar_mutation_coordinator import AvatarMutationCoordinator


class ApplicationTests(unittest.TestCase):
    """Garante que o roteador receba dependências já compostas."""

    def setUp(self):
        database_file = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        database_file.close()
        self.database_path = database_file.name
        initialize_database(self.database_path)
        self.connection = get_connection(self.database_path)
        self.temp_directory = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.connection.close()
        self.temp_directory.cleanup()
        os.unlink(self.database_path)

    def test_create_router_composes_domain_controllers(self):
        """Falha se o Router voltar a construir repositories, services ou controllers."""
        router = create_router(
            self.connection,
            avatar_upload_directory=Path(self.temp_directory.name) / "avatars",
            avatar_mutation_coordinator=AvatarMutationCoordinator(),
            tmdb_token="token",
        )

        self.assertIsInstance(router, Router)
        self.assertIsInstance(router.profile_controller, ProfileController)
        self.assertIsInstance(router.avatar_controller, AvatarController)
        self.assertIsInstance(router.account_controller, AccountController)


if __name__ == "__main__":
    unittest.main()
