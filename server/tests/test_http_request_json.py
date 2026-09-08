"""Testes da leitura de corpos JSON na fronteira HTTP."""

import io
import unittest

from server.http.request_json import read_json


class RequestHandler:
    """Handler mínimo para fornecer um body JSON ao parser."""

    def __init__(self, body: bytes):
        self.headers = {"Content-Length": str(len(body))}
        self.rfile = io.BytesIO(body)


class RequestJsonTests(unittest.TestCase):
    def test_read_json_decodes_utf8_object_body(self):
        """Falha se um body JSON válido deixar de chegar como dicionário."""
        handler = RequestHandler(b'{"display_name":"Diego"}')

        self.assertEqual(read_json(handler), {"display_name": "Diego"})

    def test_read_json_rejects_malformed_or_non_object_body(self):
        """Falha se bodies JSON inválidos deixarem de retornar erro de validação."""
        cases = (
            (b"[]", "O corpo da requisição deve ser um objeto JSON."),
            (b"{invalido", "Formato JSON inválido."),
        )

        for body, message in cases:
            with self.subTest(body=body):
                with self.assertRaisesRegex(ValueError, message):
                    read_json(RequestHandler(body))


if __name__ == "__main__":
    unittest.main()
