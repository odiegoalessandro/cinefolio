"""Testes do transporte HTTP para a API da The Movie Database (TMDB)."""

import json
import unittest

from server.clients.tmdb_client import TmdbClient


class JsonHttpResponse:
    """Resposta HTTP mínima para exercitar o cliente sem acessar a rede."""

    def __init__(self, data: dict):
        self._body = json.dumps(data).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return None

    def read(self) -> bytes:
        return self._body


class CapturingOpener:
    """Substitui apenas a fronteira de rede e registra a requisição recebida."""

    def __init__(self, response: JsonHttpResponse):
        self._response = response
        self.request = None
        self.timeout = None

    def __call__(self, request, timeout: int):
        self.request = request
        self.timeout = timeout
        return self._response


class TmdbClientTests(unittest.TestCase):
    """Contratos do cliente que conversa com o catálogo externo."""

    def test_get_sends_authenticated_request_and_decodes_json_response(self):
        """Falha se o cliente não montar ou interpretar corretamente a chamada à TMDB."""
        opener = CapturingOpener(JsonHttpResponse({"results": [{"id": 550}]}))
        client = TmdbClient("token-de-teste", opener=opener)

        data = client.get("/search/movie", {"query": "Fight Club", "language": "pt-BR"})

        self.assertEqual(data, {"results": [{"id": 550}]})
        self.assertEqual(
            opener.request.full_url,
            "https://api.themoviedb.org/3/search/movie?query=Fight+Club&language=pt-BR",
        )
        self.assertEqual(opener.request.headers["Authorization"], "Bearer token-de-teste")
        self.assertEqual(opener.timeout, 10)


if __name__ == "__main__":
    unittest.main()
