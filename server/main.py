from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import mimetypes
import os
import sys

ROOT = Path(__file__).resolve().parent

def load_environment():
    env_file = ROOT.parent / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        key, separator, value = line.strip().partition("=")
        if separator and key and not key.startswith("#"):
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

load_environment()
sys.path.insert(0, str(ROOT.parent))
from server.database.connection import DEFAULT_DATABASE, get_connection, initialize_database
from server.router import Router

PUBLIC = ROOT.parent / "public"

class AppHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, database_path, **kwargs):
        self.database_path = database_path
        super().__init__(*args, directory=str(PUBLIC), **kwargs)

    def dispatch_api(self):
        connection = get_connection(self.database_path)
        try:
            Router(connection).dispatch(self)
        finally:
            connection.close()

    def do_GET(self):
        if self.path.startswith("/api/"): self.dispatch_api()
        else: super().do_GET()
    def do_POST(self): self.dispatch_api()
    def do_PUT(self): self.dispatch_api()
    def do_DELETE(self): self.dispatch_api()
    def log_message(self, format, *args): pass

def main():
    initialize_database()
    host, port = os.environ.get("HOST", "127.0.0.1"), int(os.environ.get("PORT", "8000"))
    handler = lambda *args, **kwargs: AppHandler(*args, database_path=DEFAULT_DATABASE, **kwargs)
    print(f"Cinefolio disponível em http://{host}:{port}")
    ThreadingHTTPServer((host, port), handler).serve_forever()

if __name__ == "__main__": main()
