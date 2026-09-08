"""Testes de cookies de sessão na fronteira HTTP."""

import unittest

from server.http.session_cookies import (
    create_session_cookie,
    expire_session_cookie,
    read_session_token,
)


class SessionCookieTests(unittest.TestCase):
    def test_session_cookie_headers_preserve_security_attributes(self):
        """Falha se login ou logout alterarem o contrato do cookie de sessão."""
        self.assertEqual(
            create_session_cookie("token-seguro"),
            "session=token-seguro; HttpOnly; SameSite=Lax; Path=/; Max-Age=604800",
        )
        self.assertEqual(
            expire_session_cookie(),
            "session=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0",
        )

    def test_read_session_token_finds_session_among_other_cookies(self):
        """Falha se o token de sessão não for extraído do header Cookie."""
        cookie_header = "theme=dark; session=token-seguro; preference=compact"

        self.assertEqual(read_session_token(cookie_header), "token-seguro")


if __name__ == "__main__":
    unittest.main()
