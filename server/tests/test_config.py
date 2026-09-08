"""Testes da configuração de inicialização do servidor."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from server.config import ServerConfig
from server.environment import load_environment


class EnvironmentLoaderTests(unittest.TestCase):
    def test_load_environment_keeps_nonempty_process_variable(self):
        """Falha se o .env sobrescrever um segredo fornecido pelo processo."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_file = Path(temp_dir) / ".env"
            env_file.write_text(
                "TMDB_BEARER_TOKEN=token-do-arquivo\n",
                encoding="utf-8",
            )

            with patch.dict(
                os.environ,
                {"TMDB_BEARER_TOKEN": "token-do-processo"},
                clear=True,
            ):
                load_environment(env_file)

                self.assertEqual(
                    os.environ["TMDB_BEARER_TOKEN"],
                    "token-do-processo",
                )

    def test_load_environment_fills_empty_process_variable(self):
        """Falha se uma variável vazia impedir o valor definido no .env."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_file = Path(temp_dir) / ".env"
            env_file.write_text(
                "TMDB_BEARER_TOKEN=token-do-arquivo\n",
                encoding="utf-8",
            )

            with patch.dict(
                os.environ,
                {"TMDB_BEARER_TOKEN": ""},
                clear=True,
            ):
                load_environment(env_file)

                self.assertEqual(
                    os.environ["TMDB_BEARER_TOKEN"],
                    "token-do-arquivo",
                )

    def test_load_environment_ignores_inline_comment_outside_value(self):
        """Falha se comentários ao fim da linha virarem parte da variável."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_file = Path(temp_dir) / ".env"
            env_file.write_text(
                "PORT=8123 # porta local\n",
                encoding="utf-8",
            )

            with patch.dict(os.environ, {}, clear=True):
                load_environment(env_file)

                self.assertEqual(os.environ["PORT"], "8123")

    def test_load_environment_publishes_exported_token_from_env_file(self):
        """Falha se o token do .env não chegar ao ambiente do processo."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_file = Path(temp_dir) / ".env"
            env_file.write_text(
                '\ufeffexport\tTMDB_BEARER_TOKEN="token-do-arquivo"\n',
                encoding="utf-8",
            )

            with patch.dict(os.environ, {}, clear=True):
                result = load_environment(env_file)

                self.assertTrue(result.file_loaded)
                self.assertEqual(
                    os.environ["TMDB_BEARER_TOKEN"],
                    "token-do-arquivo",
                )


class ServerConfigTests(unittest.TestCase):
    def test_load_exposes_tmdb_token_and_env_file_status(self):
        """Falha se o bootstrap não tornar o token do .env explícito."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_file = Path(temp_dir) / ".env"
            env_file.write_text(
                "TMDB_BEARER_TOKEN=token-do-arquivo\n",
                encoding="utf-8",
            )

            with patch.dict(os.environ, {}, clear=True):
                config = ServerConfig.load(env_file)

        self.assertTrue(config.env_file_loaded)
        self.assertEqual(config.tmdb_bearer_token, "token-do-arquivo")

    def test_load_reads_host_and_port_from_env_file(self):
        """Falha se o arquivo .env deixar de alimentar a configuração do servidor."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_file = Path(temp_dir) / ".env"
            env_file.write_text(
                "HOST=0.0.0.0\nPORT=9123\n",
                encoding="utf-8",
            )

            with patch.dict(os.environ, {}, clear=True):
                config = ServerConfig.load(env_file)

        self.assertEqual(config.host, "0.0.0.0")
        self.assertEqual(config.port, 9123)


if __name__ == "__main__":
    unittest.main()
