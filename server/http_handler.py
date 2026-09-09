"""Handler HTTP responsável por separar arquivos estáticos da API."""

from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from re import compile as compile_pattern
from urllib.parse import unquote, urlsplit

from server.database.connection import DEFAULT_DATABASE, get_connection
from server.router import Router
from server.services.avatar_mutation_coordinator import AvatarMutationCoordinator


PUBLIC_DIR = Path(__file__).resolve().parent.parent / "public"
DEFAULT_AVATAR_UPLOAD_DIRECTORY = PUBLIC_DIR / "uploads" / "avatars"
AVATAR_FILENAME = compile_pattern(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    r"\.(?:jpg|png|webp)"
)


class AppHandler(SimpleHTTPRequestHandler):
    """Atende o frontend e encaminha requisições de API ao roteador."""

    def __init__(
        self,
        *args,
        database_path=DEFAULT_DATABASE,
        tmdb_token: str | None = None,
        avatar_upload_directory: Path | None = None,
        avatar_mutation_coordinator: AvatarMutationCoordinator | None = None,
        **kwargs,
    ):
        self.database_path = database_path
        self.tmdb_token = tmdb_token
        self.avatar_upload_directory = Path(
            avatar_upload_directory or DEFAULT_AVATAR_UPLOAD_DIRECTORY
        )
        self.avatar_mutation_coordinator = (
            avatar_mutation_coordinator or AvatarMutationCoordinator()
        )
        super().__init__(*args, directory=str(PUBLIC_DIR), **kwargs)

    def dispatch_api(self) -> None:
        connection = get_connection(self.database_path)
        try:
            Router(
                connection,
                tmdb_token=self.tmdb_token,
                avatar_upload_directory=self.avatar_upload_directory,
                avatar_mutation_coordinator=self.avatar_mutation_coordinator,
            ).dispatch(self)
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

    def translate_path(self, path: str) -> str:
        """Expõe uploads injetados nos testes sem ampliar o diretório estático."""
        request_path = unquote(urlsplit(path).path)
        prefix = "/uploads/avatars/"
        if not request_path.startswith(prefix):
            return super().translate_path(path)

        root = self.avatar_upload_directory.resolve()
        filename = request_path.removeprefix(prefix)
        if not AVATAR_FILENAME.fullmatch(filename):
            return str(root / "__not_found__")
        return str(root / filename)

    def log_message(self, format, *args) -> None:
        pass
