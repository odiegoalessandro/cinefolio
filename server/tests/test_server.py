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
    """Sobe o servidor real numa thread separada, em segundo plano, para os
    testes fazerem requisições HTTP de verdade contra ele."""
    # daemon=True garante que essa thread não impeça o processo de teste de
    # encerrar, mesmo se algo der errado e o shutdown não for chamado
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        # devolve a PORTA escolhida (porta 0 = o sistema operacional escolhe
        # uma porta livre automaticamente), para o teste montar a URL certa
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)      # espera a thread terminar, no máximo 2s


class ServerBootstrapTests(unittest.TestCase):
    def test_main_reports_successful_env_load(self):
        """Falha se a inicialização não confirmar a leitura do arquivo .env."""
        class InterruptingServer:
            """Servidor falso que já "encerra" a si mesmo imediatamente,
            simulando um Ctrl+C, para o teste não ficar preso rodando
            serve_forever() de verdade."""
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

        # Substitui (patch) três pontos da função main() para isolar
        # exatamente o que está sendo testado (a mensagem impressa),
        # sem depender de arquivo .env real nem de banco de dados real
        with (
            patch.object(server_main.ServerConfig, "load", return_value=config),
            patch.object(server_main, "initialize_database"),
            patch.object(server_main, "create_server", return_value=InterruptingServer()),
            redirect_stdout(output),     # captura tudo que seria print()ado no console
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

            # Troca a classe TmdbService real (usada dentro de
            # application.py) pela versão falsa, só durante este teste
            with patch("server.application.TmdbService", FakeTmdbService):
                server = server_main.create_server(config, database_path=database_path)
                with running_server(server) as port:
                    # Faz uma requisição HTTP real contra o servidor de teste
                    with urlopen(
                        f"http://127.0.0.1:{port}/api/movies/search?q=teste",
                        timeout=2,
                    ) as response:
                        body = json.loads(response.read().decode("utf-8"))

        self.assertEqual(body, {"results": []})
        # Confirma que o token configurado (config.tmdb_bearer_token)
        # realmente "flui" até chegar na construção do TmdbService
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
            # Confirma que "/" devolve o index.html real (contém a tag <title>)
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
                # urlopen lança HTTPError para respostas com status de erro
                # (como 404) em vez de simplesmente devolvê-las
                with self.assertRaises(HTTPError) as raised:
                    urlopen(f"http://127.0.0.1:{port}/api/unknown", timeout=2)

                response = raised.exception
                body = json.loads(response.read().decode("utf-8"))

        self.assertEqual(response.code, 404)
        # Confirma que o 404 de uma rota de API é JSON (e não uma página
        # HTML de "não encontrado" genérica do SimpleHTTPRequestHandler)
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

            # Confirma que o diretório de upload customizado realmente
            # chega até a "fábrica" do handler (functools.partial em main.py),
            # sem precisar subir o servidor para verificar isso
            self.assertEqual(server.RequestHandlerClass.keywords["avatar_upload_directory"], upload_directory)
            server.server_close()


if __name__ == "__main__":
    unittest.main()
