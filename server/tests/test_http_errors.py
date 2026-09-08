"""Testes do mapeamento de erros de domínio para HTTP."""

import io
import json
import unittest
from http import HTTPStatus

from server.http.errors import write_exception_response


class ErrorResponseHandler:
    """Handler mínimo para observar erros HTTP serializados."""

    def __init__(self):
        self.status = None
        self.headers = []
        self.wfile = io.BytesIO()

    def send_response(self, status):
        self.status = status

    def send_header(self, name, value):
        self.headers.append((name, value))

    def end_headers(self):
        return None


class HttpErrorTests(unittest.TestCase):
    def test_write_exception_response_preserves_error_mapping(self):
        """Falha se uma exceção passar a responder com status ou payload incorreto."""
        cases = (
            (
                ValueError("Dados inválidos."),
                HTTPStatus.BAD_REQUEST,
                "Dados inválidos.",
            ),
            (
                PermissionError("Autenticação necessária."),
                HTTPStatus.UNAUTHORIZED,
                "Autenticação necessária.",
            ),
            (
                KeyError("Perfil não encontrado."),
                HTTPStatus.NOT_FOUND,
                "Perfil não encontrado.",
            ),
            (
                RuntimeError("erro interno"),
                HTTPStatus.INTERNAL_SERVER_ERROR,
                "Ocorreu um erro interno no servidor.",
            ),
        )

        for error, status, message in cases:
            with self.subTest(error=type(error).__name__):
                handler = ErrorResponseHandler()

                write_exception_response(handler, error)

                self.assertEqual(handler.status, status)
                self.assertEqual(
                    json.loads(handler.wfile.getvalue().decode("utf-8")),
                    {"error": message},
                )


if __name__ == "__main__":
    unittest.main()
