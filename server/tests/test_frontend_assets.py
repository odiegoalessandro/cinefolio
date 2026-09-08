"""Testes dos assets ESM servidos e do acesso público ao perfil."""

import json
import tempfile
import threading
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import urlopen

from server.config import ServerConfig
from server.database.connection import get_connection, initialize_database
from server.main import create_server
from server.repositories.user_repository import UserRepository
from server.services.auth_service import hash_password


PAGE_ENTRYPOINTS = {
    "index.html": "js/search.js",
    "login.html": "js/auth.js",
    "register.html": "js/auth.js",
    "movie.html": "js/movie.js",
    "profile.html": "js/profile.js",
    "settings.html": "js/settings.js",
}


class LocalScriptParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts = []

    def handle_starttag(self, tag, attrs):
        if tag != "script":
            return

        attributes = dict(attrs)
        source = attributes.get("src", "")
        if source.startswith("js/"):
            self.scripts.append((source, attributes.get("type")))


class FrontendAssetsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(cls.temp_dir.name) / "cinefolio.sqlite3"
        initialize_database(database_path)

        connection = get_connection(database_path)
        try:
            UserRepository(connection).create(
                username="public_user",
                display_name="Perfil Público",
                password_hash=hash_password("senhasegura123"),
            )
        finally:
            connection.close()

        cls.server = create_server(
            ServerConfig(host="127.0.0.1", port=0),
            database_path=database_path,
        )
        cls.thread = threading.Thread(
            target=cls.server.serve_forever,
            daemon=True,
        )
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)
        cls.temp_dir.cleanup()

    def test_each_page_serves_guard_and_one_module_entrypoint(self):
        for page, entrypoint in PAGE_ENTRYPOINTS.items():
            with self.subTest(page=page):
                with urlopen(f"{self.base_url}/{page}", timeout=2) as response:
                    html = response.read().decode("utf-8")

                parser = LocalScriptParser()
                parser.feed(html)
                self.assertEqual(
                    parser.scripts,
                    [
                        ("js/file-protocol-guard.js", None),
                        (entrypoint, "module"),
                    ],
                )

                for source, _ in parser.scripts:
                    with urlopen(
                        f"{self.base_url}/{source}",
                        timeout=2,
                    ) as asset_response:
                        asset_response.read()
                        self.assertEqual(asset_response.status, 200)
                        self.assertIn(
                            asset_response.headers.get_content_type(),
                            {"text/javascript", "application/javascript"},
                        )

    def test_profile_data_is_public_without_session_cookie(self):
        with urlopen(
            f"{self.base_url}/api/profiles/public_user",
            timeout=2,
        ) as response:
            payload = json.loads(response.read().decode("utf-8"))
            self.assertEqual(response.status, 200)

        self.assertEqual(payload["profile"]["username"], "public_user")


if __name__ == "__main__":
    unittest.main()
