"""Handler HTTP responsável por separar arquivos estáticos da API."""

from http.server import SimpleHTTPRequestHandler
from pathlib import Path

from server.database.connection import DEFAULT_DATABASE, get_connection
from server.router import Router


PUBLIC_DIR = Path(__file__).resolve().parent.parent / "public"


class AppHandler(SimpleHTTPRequestHandler):
    """Atende o frontend e encaminha requisições de API ao roteador."""

    def __init__(
        self,
        *args,
        database_path=DEFAULT_DATABASE,
        tmdb_token: str | None = None,
        **kwargs,
    ):
        self.database_path = database_path
        self.tmdb_token = tmdb_token
        super().__init__(*args, directory=str(PUBLIC_DIR), **kwargs)

    def dispatch_api(self) -> None:
        connection = get_connection(self.database_path)
        try:
            Router(connection, tmdb_token=self.tmdb_token).dispatch(self)
        finally:
            connection.close()

    def do_GET(self) -> None:
        if self.path.startswith("/api/"):
            self.dispatch_api()
            return

        super().do_GET()

    def do_POST(self) -> None:
        self.dispatch_api()

    def do_PUT(self) -> None:
        self.dispatch_api()

    def do_DELETE(self) -> None:
        self.dispatch_api()

    def log_message(self, format, *args) -> None:
        pass
