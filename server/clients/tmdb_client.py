"""Transporte HTTP para a API da The Movie Database (TMDB)."""

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


TMDB_API_BASE = "https://api.themoviedb.org/3"


class TmdbClient:
    """Executa chamadas autenticadas à API externa da TMDB."""

    def __init__(self, token: str = None, opener=urlopen):
        self.token = token if token is not None else os.environ.get("TMDB_BEARER_TOKEN", "")
        self.opener = opener

    def get(self, path: str, params: dict = None) -> dict:
        """Obtém e decodifica um recurso JSON da TMDB."""
        if not self.token:
            raise ValueError("A chave da TMDB não está configurada no servidor (.env).")

        query_string = f"?{urlencode(params)}" if params else ""
        url = f"{TMDB_API_BASE}{path}{query_string}"
        request = Request(
            url,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/json",
                "User-Agent": "Cinefolio/1.0",
            },
        )

        try:
            with self.opener(request, timeout=10) as response:
                return json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
            raise ValueError("Não foi possível consultar o catálogo de filmes no momento.") from error
