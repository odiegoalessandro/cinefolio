"""Testes da escrita de respostas JSON na fronteira HTTP."""

import io
import json
import unittest
from http import HTTPStatus

from server.http.response_json import json_response


class ResponseHandler:
    """Handler mínimo para observar uma resposta HTTP gerada.

    Este é um "test double" (dublê de teste): simula só o comportamento
    mínimo do handler HTTP real (SimpleHTTPRequestHandler) que a função
    json_response precisa usar, sem precisar abrir um socket/servidor de
    verdade para testar — deixa o teste rápido e isolado.
    """

    def __init__(self):
        self.status = None
        self.headers = []
        self.ended = False
        self.wfile = io.BytesIO()    # simula o "arquivo" de saída onde a resposta é escrita

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
            {"message": "Olá"},     # inclui acento de propósito, para testar UTF-8
            {"X-Request-Id": "request-123"},    # header extra customizado
        )

        headers = dict(handler.headers)
        self.assertEqual(handler.status, HTTPStatus.CREATED)
        self.assertTrue(handler.ended)
        self.assertEqual(headers["Content-Type"], "application/json; charset=utf-8")
        self.assertEqual(headers["X-Request-Id"], "request-123")
        # Confirma que o Content-Length declarado bate exatamente com o
        # tamanho real dos bytes escritos (evita resposta truncada/cortada)
        self.assertEqual(
            int(headers["Content-Length"]),
            len(handler.wfile.getvalue()),
        )
        # Confirma que o corpo é um JSON válido e com o acento preservado
        # corretamente (prova que ensure_ascii=False funcionou)
        self.assertEqual(
            json.loads(handler.wfile.getvalue().decode("utf-8")),
            {"message": "Olá"},
        )


if __name__ == "__main__":
    unittest.main()
