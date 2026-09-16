"""Handler HTTP responsável por separar arquivos estáticos da API."""

from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from re import compile as compile_pattern
from urllib.parse import unquote, urlsplit

from server.application import create_router
from server.database.connection import DEFAULT_DATABASE, get_connection
from server.services.avatar_mutation_coordinator import AvatarMutationCoordinator


PUBLIC_DIR = Path(__file__).resolve().parent.parent / "public"
DEFAULT_AVATAR_UPLOAD_DIRECTORY = PUBLIC_DIR / "uploads" / "avatars"
# Regex que só aceita nomes de arquivo no formato exato gerado pelo
# AvatarStorage (UUID + extensão), ex: "3fa85f64-5717-4562-b3fc-2c963f66afa6.png"
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
        # Estes atributos são salvos ANTES do super().__init__, porque a
        # classe base já pode chamar métodos como do_GET durante sua
        # própria inicialização, e eles dependem desses atributos existirem
        self.database_path = database_path
        self.tmdb_token = tmdb_token
        self.avatar_upload_directory = Path(
            avatar_upload_directory or DEFAULT_AVATAR_UPLOAD_DIRECTORY
        )
        self.avatar_mutation_coordinator = (
            avatar_mutation_coordinator or AvatarMutationCoordinator()
        )
        # "directory=str(PUBLIC_DIR)" configura a pasta de onde os arquivos
        # estáticos (index.html, css, js) são servidos
        super().__init__(*args, directory=str(PUBLIC_DIR), **kwargs)

    def dispatch_api(self) -> None:
        # Uma conexão nova com o banco é aberta a CADA requisição de API
        # (e fechada no final) — simples e seguro para um servidor
        # threaded como este, evitando problemas de concorrência com uma
        # única conexão compartilhada entre threads
        connection = get_connection(self.database_path)
        try:
            create_router(
                connection,
                tmdb_token=self.tmdb_token,
                avatar_upload_directory=self.avatar_upload_directory,
                avatar_mutation_coordinator=self.avatar_mutation_coordinator,
            ).dispatch(self)
        finally:
            connection.close()

    def do_GET(self) -> None:
        # Convenção do http.server: do_GET/do_POST/do_PUT/do_DELETE são
        # chamados automaticamente conforme o método HTTP da requisição
        if self.path.startswith("/api/"):
            self.dispatch_api()
            return

        # Qualquer coisa que não seja /api/ é tratada como pedido de
        # arquivo estático (ex: /index.html, /js/app.js), delegado para a
        # implementação original da classe base
        super().do_GET()

    def do_POST(self) -> None:
        self.dispatch_api()

    def do_PUT(self) -> None:
        self.dispatch_api()

    def do_DELETE(self) -> None:
        self.dispatch_api()

    def translate_path(self, path: str) -> str:
        """Expõe uploads injetados nos testes sem ampliar o diretório estático."""
        # Sobrescreve o método da classe base que decide qual arquivo
        # físico corresponde a uma URL, para tratar "/uploads/avatars/..."
        # de forma especial (esses arquivos ficam fora da pasta "public"
        # padrão em alguns cenários de teste)
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
        # Silencia os logs padrão de cada requisição no console
        # (o SimpleHTTPRequestHandler por padrão imprime uma linha por request)
        pass
