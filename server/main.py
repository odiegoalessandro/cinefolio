"""Ponto de entrada do servidor HTTP do Cinefolio.

Inicia o servidor HTTP multithread nativo do Python na porta configurada,
carrega as variáveis de ambiente do arquivo .env e serve arquivos estáticos
da pasta `public/` juntamente com a API REST em `/api/*`.
"""

import mimetypes
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent


def load_environment():
    """Lê o arquivo .env da raiz do projeto e carrega as variáveis de ambiente."""
    env_file = ROOT_DIR.parent / ".env"
    if not env_file.exists():
        return

    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        key, separator, value = line.partition("=")
        if separator and key:
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


# Inicializa as variáveis de ambiente antes de carregar os módulos da aplicação
load_environment()

# Adiciona a raiz do projeto ao sys.path
sys.path.insert(0, str(ROOT_DIR.parent))

from server.database.connection import (
    DEFAULT_DATABASE,
    get_connection,
    initialize_database,
)
from server.router import Router

PUBLIC_DIR = ROOT_DIR.parent / "public"


class AppHandler(SimpleHTTPRequestHandler):
    """Manipulador de requisições HTTP para arquivos estáticos e endpoints de API."""

    def __init__(self, *args, database_path=DEFAULT_DATABASE, **kwargs):
        self.database_path = database_path
        super().__init__(*args, directory=str(PUBLIC_DIR), **kwargs)

    def dispatch_api(self):
        """Abre uma conexão isolada com o banco de dados e despacha a requisição para o Router."""
        connection = get_connection(self.database_path)
        try:
            router = Router(connection)
            router.dispatch(self)
        finally:
            connection.close()

    def do_GET(self):
        """Processa requisições HTTP GET."""
        if self.path.startswith("/api/"):
            self.dispatch_api()
        else:
            super().do_GET()

    def do_POST(self):
        """Processa requisições HTTP POST."""
        self.dispatch_api()

    def do_PUT(self):
        """Processa requisições HTTP PUT."""
        self.dispatch_api()

    def do_DELETE(self):
        """Processa requisições HTTP DELETE."""
        self.dispatch_api()

    def log_message(self, format, *args):
        """Silencia logs padrão para manter a saída do console limpa."""
        pass


def main():
    """Função principal de inicialização do servidor Cinefolio."""
    initialize_database()

    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))

    handler_factory = lambda *args, **kwargs: AppHandler(
        *args, database_path=DEFAULT_DATABASE, **kwargs
    )

    server = ThreadingHTTPServer((host, port), handler_factory)

    print("=" * 60)
    print("🎬 Cinefolio - Servidor Iniciado com Sucesso")
    print(f"📍 Endereço: http://{host}:{port}")
    print(f"📁 Diretório estático: {PUBLIC_DIR}")
    print(f"💾 Banco de dados: {DEFAULT_DATABASE}")
    print("=" * 60)
    print("Pressione Ctrl+C para encerrar o servidor.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrando servidor Cinefolio...")
        server.server_close()


if __name__ == "__main__":
    main()
