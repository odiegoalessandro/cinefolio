"""Testes unitários dos repositórios, serviços e regras de negócio centrais."""

import gc
import os
import tempfile
import unittest

from server.database.connection import get_connection, initialize_database
from server.repositories.movie_repository import MovieRepository
from server.repositories.user_movie_repository import UserMovieRepository
from server.repositories.user_repository import UserRepository
from server.router import movie_profile_payload, profile_payload
from server.services.auth_service import AuthService, hash_password, verify_password
from server.services.profile_service import ProfileService


class DatabaseTestCase(unittest.TestCase):
    """Caso base de teste com banco de dados temporário isolado por teste."""

    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        self.temp_file.close()
        self.db_path = self.temp_file.name

        initialize_database(self.db_path)
        self.connection = get_connection(self.db_path)
        self.users = UserRepository(self.connection)
        self.movies = MovieRepository(self.connection)
        self.user_movies = UserMovieRepository(self.connection)

    def tearDown(self):
        self.connection.close()
        del self.connection
        del self.users
        del self.movies
        del self.user_movies
        gc.collect()
        try:
            if os.path.exists(self.db_path):
                os.unlink(self.db_path)
        except OSError:
            pass

    def create_test_user(self, username="diego"):
        """Cria um usuário padrão para os testes."""
        return self.users.create(
            username=username,
            display_name="Diego Alessandro",
            password_hash=hash_password("senhasegura123"),
        )

    def create_test_movie(self, tmdb_id=550):
        """Cria um filme padrão para os testes."""
        return self.movies.upsert(
            {
                "tmdb_id": tmdb_id,
                "title": "Clube da Luta",
                "original_title": "Fight Club",
                "release_year": 1999,
                "poster_path": "/bptfVGEQuv6vDTIMVCHjJ9Dz8PX.jpg",
                "backdrop_path": "/hZkgoQYus5vegHoetLkCJzb17zJ.jpg",
            }
        )

    def test_schema_enforces_unique_and_foreign_keys(self):
        """Valida se o schema bloqueia usernames duplicados e registros sem chave estrangeira."""
        self.create_test_user("usuario_unico")

        # Tentativa de duplicar username
        with self.assertRaises(Exception):
            self.create_test_user("usuario_unico")

        # Tentativa de associar filme inexistente
        with self.assertRaises(Exception):
            self.connection.execute(
                """
                INSERT INTO user_movies (user_id, movie_id, status, created_at, updated_at)
                VALUES (999, 999, 'WATCHED', '2026-01-01', '2026-01-01')
                """
            )

    def test_movie_crud_and_statistics(self):
        """Valida o ciclo completo de Create, Read, Update e Delete de filmes no perfil."""
        user = self.create_test_user("cinefilo_1")
        movie = self.create_test_movie(101)

        # Create
        self.user_movies.upsert(
            user_id=user["id"],
            movie_id=movie["id"],
            status="WATCHED",
            rating=9.5,
            review="Obra-prima do cinema moderno.",
            favorite=True,
            watched_at="2026-05-10",
        )

        # Read
        saved_list = self.user_movies.list_for_profile(user["id"], favorite=True)
        self.assertEqual(len(saved_list), 1)
        self.assertEqual(saved_list[0]["title"], "Clube da Luta")
        self.assertEqual(saved_list[0]["rating"], 9.5)
        self.assertEqual(saved_list[0]["favorite"], 1)

        # Statistics
        stats = self.user_movies.statistics(user["id"])
        self.assertEqual(stats["watched_count"], 1)
        self.assertEqual(stats["average_rating"], 9.5)
        self.assertEqual(stats["review_count"], 1)

        # Delete
        self.assertTrue(self.user_movies.remove(user["id"], movie["id"]))
        self.assertFalse(self.user_movies.remove(user["id"], movie["id"]))

    def test_invalid_status_rejected(self):
        """Valida se valores fora do CHECK (status) são rejeitados."""
        user = self.create_test_user("cinefilo_2")
        movie = self.create_test_movie(102)

        with self.assertRaises(Exception):
            self.user_movies.upsert(
                user_id=user["id"],
                movie_id=movie["id"],
                status="STATUS_INVALIDO",
            )

    def test_profile_groups_movies(self):
        """Valida o agrupamento correto das seções no perfil público."""
        user = self.create_test_user("marcos")
        movie1 = self.create_test_movie(201)
        movie2 = self.create_test_movie(202)

        self.user_movies.upsert(
            user_id=user["id"],
            movie_id=movie1["id"],
            status="WATCHED",
            rating=10.0,
            review="Excelente!",
            favorite=True,
            watched_at="2026-06-01",
        )
        self.user_movies.upsert(
            user_id=user["id"],
            movie_id=movie2["id"],
            status="WATCHING",
        )

        profile_service = ProfileService(self.users, self.user_movies)
        profile_data = profile_service.public_profile("marcos")

        self.assertIsNotNone(profile_data)
        self.assertEqual(len(profile_data["sections"]["favorites"]), 1)
        self.assertEqual(len(profile_data["sections"]["watching"]), 1)
        self.assertEqual(len(profile_data["sections"]["watched"]), 1)
        self.assertNotIn("password_hash", profile_data)


class AuthTestCase(DatabaseTestCase):
    """Testes de segurança, hashing e sessões de autenticação."""

    def test_hash_uses_salt_and_verifies(self):
        """Valida que dois hashes da mesma senha usam salts diferentes e podem ser validados."""
        first_hash = hash_password("minhasenhaforte")
        second_hash = hash_password("minhasenhaforte")

        self.assertNotEqual(first_hash, second_hash)
        self.assertTrue(verify_password("minhasenhaforte", first_hash))
        self.assertTrue(verify_password("minhasenhaforte", second_hash))
        self.assertFalse(verify_password("senhaerrada", first_hash))

    def test_register_login_and_session(self):
        """Valida fluxo de criação de conta, login com geração de sessão e logout."""
        auth_service = AuthService(self.users)
        user = auth_service.register(
            username="lucas_cine",
            display_name="Lucas Silva",
            password="senhasegura123",
        )

        self.assertEqual(user["username"], "lucas_cine")

        logged_user, token = auth_service.login("lucas_cine", "senhasegura123")
        self.assertEqual(logged_user["id"], user["id"])
        self.assertTrue(bool(token))

        active_user = auth_service.current_user(token)
        self.assertIsNotNone(active_user)
        self.assertEqual(active_user["id"], user["id"])

        auth_service.logout(token)
        self.assertIsNone(auth_service.current_user(token))

    def test_auth_rejects_invalid_input(self):
        """Valida a rejeição de nomes de usuário ou senhas curtas/inválidas."""
        auth_service = AuthService(self.users)

        # Username muito curto
        with self.assertRaises(ValueError):
            auth_service.register("ab", "Nome", "senha1234")

        # Senha muito curta
        with self.assertRaises(ValueError):
            auth_service.register("usuario_valido", "Nome", "123")

        # Login inexistente
        with self.assertRaises(ValueError):
            auth_service.login("usuario_inexistente", "qualquersenha")


class RouterValidationTests(unittest.TestCase):
    """Testes para as funções de validação de payload."""

    def test_profile_payload_rejects_invalid_values(self):
        """Valida restrições do payload de atualização de perfil."""
        with self.assertRaises(ValueError):
            profile_payload({"display_name": "", "bio": ""})

        with self.assertRaises(ValueError):
            profile_payload({"display_name": "Nome", "bio": "x" * 501})

        with self.assertRaises(ValueError):
            profile_payload({"display_name": ["Tipo", "Invalido"]})

    def test_movie_payload_requires_status_and_known_fields(self):
        """Valida restrições do payload de classificação de filme."""
        with self.assertRaises(ValueError):
            movie_profile_payload({"rating": 8})

        with self.assertRaises(ValueError):
            movie_profile_payload({"status": "WATCHED", "campo_desconhecido": True})

        validated = movie_profile_payload({"status": "WATCHED", "favorite": True})
        self.assertEqual(validated["status"], "WATCHED")
        self.assertTrue(validated["favorite"])


if __name__ == "__main__":
    unittest.main()
