"""Testes de integração da inicialização HTTP do Cinefolio."""

import io
import json
import tempfile
import threading
import unittest
from contextlib import contextmanager, redirect_stdout
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen
from unittest.mock import patch

from server import main as server_main
from server.config import ServerConfig
from server.database.connection import initialize_database


@contextmanager
def running_server(server):
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


class ServerBootstrapTests(unittest.TestCase):
    def test_main_reports_successful_env_load(self):
        """Falha se a inicialização não confirmar a leitura do arquivo .env."""
        class InterruptingServer:
            server_address = ("127.0.0.1", 8000)

            def serve_forever(self):
                raise KeyboardInterrupt

            def server_close(self):
                return None

        output = io.StringIO()
        config = ServerConfig(
            host="127.0.0.1",
            port=8000,
            env_file_loaded=True,
        )

        with (
            patch.object(server_main.ServerConfig, "load", return_value=config),
            patch.object(server_main, "initialize_database"),
            patch.object(server_main, "create_server", return_value=InterruptingServer()),
            redirect_stdout(output),
        ):
            server_main.main()

        self.assertIn(
            "Arquivo .env carregado com sucesso.",
            output.getvalue(),
        )

    def test_create_server_passes_tmdb_token_to_api_requests(self):
        """Falha se o token configurado não alcançar a integração de catálogo."""
        class FakeTmdbService:
            received_token = None

            def __init__(self, token=None):
                type(self).received_token = token

            def search(self, query):
                return []

        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "cinefolio.sqlite3"
            initialize_database(database_path)
            config = ServerConfig(
                host="127.0.0.1",
                port=0,
                tmdb_bearer_token="token-da-configuracao",
            )

            with patch("server.router.TmdbService", FakeTmdbService):
                server = server_main.create_server(config, database_path=database_path)
                with running_server(server) as port:
                    with urlopen(
                        f"http://127.0.0.1:{port}/api/movies/search?q=teste",
                        timeout=2,
                    ) as response:
                        body = json.loads(response.read().decode("utf-8"))

        self.assertEqual(body, {"results": []})
        self.assertEqual(FakeTmdbService.received_token, "token-da-configuracao")

    def test_create_server_serves_public_index(self):
        """Falha se a composição do servidor deixar de expor o frontend."""
        create_server = getattr(server_main, "create_server", None)
        self.assertIsNotNone(
            create_server,
            "server.main precisa fornecer create_server",
        )

        server = create_server(ServerConfig(host="127.0.0.1", port=0))
        with running_server(server) as port:
            with urlopen(f"http://127.0.0.1:{port}/", timeout=2) as response:
                body = response.read().decode("utf-8")

            self.assertEqual(response.status, 200)
            self.assertIn("<title>Cinefolio", body)

    def test_create_server_dispatches_api_requests_as_json(self):
        """Falha se uma rota de API for tratada como arquivo estático."""
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "cinefolio.sqlite3"
            initialize_database(database_path)
            server = server_main.create_server(
                ServerConfig(host="127.0.0.1", port=0),
                database_path=database_path,
            )

            with running_server(server) as port:
                with self.assertRaises(HTTPError) as raised:
                    urlopen(f"http://127.0.0.1:{port}/api/unknown", timeout=2)

                response = raised.exception
                body = json.loads(response.read().decode("utf-8"))

        self.assertEqual(response.code, 404)
        self.assertEqual(
            response.headers.get_content_type(),
            "application/json",
        )
        self.assertEqual(body, {"error": "Rota não encontrada."})

    def test_create_server_accepts_an_isolated_avatar_upload_directory(self):
        """Falha se testes de upload precisarem escrever em public/uploads do repositório."""
        with tempfile.TemporaryDirectory() as temp_dir:
            upload_directory = Path(temp_dir) / "avatars"
            server = server_main.create_server(
                ServerConfig(host="127.0.0.1", port=0),
                avatar_upload_directory=upload_directory,
            )

            self.assertEqual(server.RequestHandlerClass.keywords["avatar_upload_directory"], upload_directory)
            server.server_close()


if __name__ == "__main__":
    unittest.main()
