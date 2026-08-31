"""Testes unitários para o serviço de integração com a API da TMDB."""

import json
import unittest
from unittest.mock import Mock
from urllib.error import URLError

from server.services.tmdb_service import TmdbService


class MockHttpResponse:
    """Mock de resposta HTTP compatível com o gerenciador de contexto `with`."""

    def __init__(self, data: dict):
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return None

    def read(self) -> bytes:
        return json.dumps(self.data).encode("utf-8")


class TmdbServiceTests(unittest.TestCase):
    """Testes de validação e normalização do serviço TMDB."""

    def test_search_normalizes_catalog_result(self):
        """Valida que a resposta da TMDB é normalizada com os tipos e campos esperados."""
        sample_response = {
            "results": [
                {
                    "id": 550,
                    "title": "Fight Club",
                    "original_title": "Fight Club",
                    "release_date": "1999-10-15",
                    "poster_path": "/poster.jpg",
                    "backdrop_path": "/backdrop.jpg",
                    "overview": "An insomniac office worker...",
                }
            ]
        }

        mock_opener = Mock(return_value=MockHttpResponse(sample_response))
        service = TmdbService("dummy_secret_token", opener=mock_opener)

        results = service.search("Fight Club")
        self.assertEqual(len(results), 1)

        first = results[0]
        self.assertEqual(first["tmdb_id"], 550)
        self.assertEqual(first["title"], "Fight Club")
        self.assertEqual(first["release_year"], 1999)
        self.assertEqual(first["poster_path"], "/poster.jpg")

        # Verifica cabeçalho de autenticação enviado
        request_obj = mock_opener.call_args[0][0]
        self.assertIn("Bearer dummy_secret_token", request_obj.headers["Authorization"])

    def test_rejects_empty_search_and_invalid_id(self):
        """Valida se buscas em branco ou IDs inválidos geram ValueError."""
        service = TmdbService("dummy_secret", opener=Mock())

        with self.assertRaises(ValueError):
            service.search("   ")

        with self.assertRaises(ValueError):
            service.details("identificador_invalido")

        with self.assertRaises(ValueError):
            service.details(-1)

    def test_hides_external_error_details(self):
        """Garante que exceções de rede externas não vazam tokens ou dados crus."""
        mock_opener = Mock(side_effect=URLError("Falha de conexão com a rede"))
        service = TmdbService("token-privado", opener=mock_opener)

        with self.assertRaisesRegex(ValueError, "Não foi possível consultar o catálogo"):
            service.popular()

    def test_requires_server_token(self):
        """Garante que erro descritivo é levantado caso o token não tenha sido configurado."""
        service = TmdbService("", opener=Mock())

        with self.assertRaisesRegex(ValueError, "não está configurada"):
            service.popular()


if __name__ == "__main__":
    unittest.main()
