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
        # Testa se o cookie de LOGIN é montado com exatamente os atributos
        # de segurança esperados (HttpOnly, SameSite, etc) e o valor certo de Max-Age
        self.assertEqual(
            create_session_cookie("token-seguro"),
            "session=token-seguro; HttpOnly; SameSite=Lax; Path=/; Max-Age=604800",
        )
        # Testa se o cookie de LOGOUT expira corretamente (Max-Age=0, valor vazio)
        self.assertEqual(
            expire_session_cookie(),
            "session=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0",
        )

    def test_read_session_token_finds_session_among_other_cookies(self):
        """Falha se o token de sessão não for extraído do header Cookie."""
        # Simula um header Cookie real, onde vários cookies vêm juntos
        # separados por ";" — o teste garante que a função acha o certo
        # no meio dos outros, sem se confundir
        cookie_header = "theme=dark; session=token-seguro; preference=compact"

        self.assertEqual(read_session_token(cookie_header), "token-seguro")


if __name__ == "__main__":
    # Permite rodar este arquivo isoladamente com: python -m server.tests.test_http_session_cookies
    unittest.main()
