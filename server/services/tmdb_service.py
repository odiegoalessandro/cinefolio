import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://api.themoviedb.org/3"


class TmdbService:
    def __init__(self, token=None, opener=urlopen):
        self.token = token if token is not None else os.environ.get("TMDB_BEARER_TOKEN", "")
        self.opener = opener

    def _request(self, path, params=None):
        if not self.token:
            raise ValueError("TMDB não está configurada no servidor.")
        url = f"{BASE_URL}{path}" + (f"?{urlencode(params)}" if params else "")
        request = Request(url, headers={"Authorization": f"Bearer {self.token}", "Accept": "application/json"})
        try:
            with self.opener(request, timeout=10) as response:
                return json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
            raise ValueError("Não foi possível consultar o catálogo de filmes.") from error

    @staticmethod
    def normalize(movie):
        release_date = movie.get("release_date") or ""
        return {"tmdb_id": movie["id"], "title": movie.get("title") or "Sem título", "original_title": movie.get("original_title") or "", "release_year": int(release_date[:4]) if release_date[:4].isdigit() else None, "poster_path": movie.get("poster_path") or "", "backdrop_path": movie.get("backdrop_path") or "", "overview": movie.get("overview") or "", "genres": movie.get("genres", [])}

    def search(self, query):
        if not 1 <= len(query.strip()) <= 100:
            raise ValueError("Busca deve ter entre 1 e 100 caracteres.")
        return [self.normalize(movie) for movie in self._request("/search/movie", {"query": query.strip(), "language": "pt-BR"}).get("results", [])]

    def details(self, tmdb_id):
        if not str(tmdb_id).isdigit() or int(tmdb_id) <= 0:
            raise ValueError("Identificador de filme inválido.")
        return self.normalize(self._request(f"/movie/{int(tmdb_id)}", {"language": "pt-BR"}))

    def popular(self):
        return [self.normalize(movie) for movie in self._request("/movie/popular", {"language": "pt-BR"}).get("results", [])]
