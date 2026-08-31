from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import mimetypes
import os
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
from server.database.connection import DEFAULT_DATABASE, get_connection, initialize_database
from server.router import Router

PUBLIC = ROOT.parent / "public"

class AppHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, router, **kwargs):
        self.router = router
        super().__init__(*args, directory=str(PUBLIC), **kwargs)

    def do_GET(self):
        if self.path.startswith("/api/"): self.router.dispatch(self)
        else: super().do_GET()
    def do_POST(self): self.router.dispatch(self)
    def do_PUT(self): self.router.dispatch(self)
    def do_DELETE(self): self.router.dispatch(self)
    def log_message(self, format, *args): pass

def main():
    initialize_database()
    connection = get_connection()
    router = Router(connection)
    host, port = os.environ.get("HOST", "127.0.0.1"), int(os.environ.get("PORT", "8000"))
    handler = lambda *args, **kwargs: AppHandler(*args, router=router, **kwargs)
    print(f"Cinefolio disponível em http://{host}:{port}")
    ThreadingHTTPServer((host, port), handler).serve_forever()

if __name__ == "__main__": main()
