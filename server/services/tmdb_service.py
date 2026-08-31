"""Serviço de integração com a API da The Movie Database (TMDB)."""

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

TMDB_API_BASE = "https://api.themoviedb.org/3"


class TmdbService:
    """Cliente para consulta do catálogo externo da TMDB sem expor chaves ao cliente."""

    def __init__(self, token: str = None, opener=urlopen):
        self.token = token if token is not None else os.environ.get("TMDB_BEARER_TOKEN", "")
        self.opener = opener

    def _request(self, path: str, params: dict = None) -> dict:
        """Executa uma requisição HTTP autenticada à API da TMDB."""
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
                content = response.read().decode("utf-8")
                return json.loads(content)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
            raise ValueError("Não foi possível consultar o catálogo de filmes no momento.") from error

    @staticmethod
    def normalize_movie(movie: dict) -> dict:
        """Padroniza a estrutura de dados de filme retornada pela TMDB."""
        release_date = movie.get("release_date") or ""
        year_str = release_date[:4]
        release_year = int(year_str) if year_str.isdigit() else None

        return {
            "tmdb_id": movie["id"],
            "title": movie.get("title") or movie.get("name") or "Sem título",
            "original_title": movie.get("original_title") or "",
            "release_year": release_year,
            "poster_path": movie.get("poster_path") or "",
            "backdrop_path": movie.get("backdrop_path") or "",
            "overview": movie.get("overview") or "",
            "genres": movie.get("genres", []),
        }

    def search(self, query: str) -> list:
        """Busca filmes por título no catálogo da TMDB."""
        query = (query or "").strip()
        if not 1 <= len(query) <= 100:
            raise ValueError("A busca deve ter entre 1 e 100 caracteres.")

        data = self._request("/search/movie", {"query": query, "language": "pt-BR"})
        results = data.get("results", [])
        return [self.normalize_movie(movie) for movie in results]

    def popular(self) -> list:
        """Obtém os filmes atualmente em destaque / populares."""
        data = self._request("/movie/popular", {"language": "pt-BR"})
        results = data.get("results", [])
        return [self.normalize_movie(movie) for movie in results]

    def details(self, tmdb_id: int) -> dict:
        """Obtém detalhes completos de um filme específico pelo seu ID da TMDB."""
        if not str(tmdb_id).isdigit() or int(tmdb_id) <= 0:
            raise ValueError("Identificador de filme inválido.")

        data = self._request(f"/movie/{int(tmdb_id)}", {"language": "pt-BR"})
        return self.normalize_movie(data)
