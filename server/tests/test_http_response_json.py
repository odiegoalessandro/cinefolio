"""Testes da escrita de respostas JSON na fronteira HTTP."""

import io
import json
import unittest
from http import HTTPStatus

from server.http.response_json import json_response


class ResponseHandler:
    """Handler mínimo para observar uma resposta HTTP gerada."""

    def __init__(self):
        self.status = None
        self.headers = []
        self.ended = False
        self.wfile = io.BytesIO()

    def send_response(self, status):
        self.status = status

    def send_header(self, name, value):
        self.headers.append((name, value))

    def end_headers(self):
        self.ended = True


class ResponseJsonTests(unittest.TestCase):
    def test_json_response_writes_utf8_payload_and_extra_headers(self):
        """Falha se respostas JSON perderem corpo, charset ou headers adicionais."""
        handler = ResponseHandler()

        json_response(
            handler,
            HTTPStatus.CREATED,
            {"message": "Olá"},
            {"X-Request-Id": "request-123"},
        )

        headers = dict(handler.headers)
        self.assertEqual(handler.status, HTTPStatus.CREATED)
        self.assertTrue(handler.ended)
        self.assertEqual(headers["Content-Type"], "application/json; charset=utf-8")
        self.assertEqual(headers["X-Request-Id"], "request-123")
        self.assertEqual(
            int(headers["Content-Length"]),
            len(handler.wfile.getvalue()),
        )
        self.assertEqual(
            json.loads(handler.wfile.getvalue().decode("utf-8")),
            {"message": "Olá"},
        )


if __name__ == "__main__":
    unittest.main()
