"""Testes de integração da inicialização HTTP do Cinefolio."""

import json
import tempfile
import threading
import unittest
from contextlib import contextmanager
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

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


if __name__ == "__main__":
    unittest.main()
