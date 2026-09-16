"""Regras de catálogo construídas sobre a API da The Movie Database (TMDB)."""

from urllib.request import urlopen

from server.clients.tmdb_client import TmdbClient


class TmdbService:
    """Valida e normaliza dados de catálogo obtidos da TMDB.

    Esta camada fica entre os controllers e o TmdbClient (que só sabe
    fazer requisições HTTP puras): aqui entram validação de entrada e a
    padronização do formato de dados, para o resto do sistema não
    precisar conhecer os detalhes de como a API externa responde.
    """

    def __init__(self, token: str = None, opener=urlopen):
        # "opener" pode ser substituído em testes (ao invés de urlopen real)
        # para simular respostas da API sem fazer requisições de verdade
        self.client = TmdbClient(token=token, opener=opener)

    @staticmethod
    def normalize_movie(movie: dict) -> dict:
        """Padroniza a estrutura de dados de filme retornada pela TMDB."""
        release_date = movie.get("release_date") or ""
        year_str = release_date[:4] # os 4 primeiros caracteres de "AAAA-MM-DD" = o ano
        release_year = int(year_str) if year_str.isdigit() else None

        return {
            "tmdb_id": movie["id"],
            # alguns endpoints da TMDB usam "title" (filmes) e outros "name"
            # (séries); aqui cobre os dois casos com um valor de fallback
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

        data = self.client.get("/search/movie", {"query": query, "language": "pt-BR"})
        results = data.get("results", [])
        return [self.normalize_movie(movie) for movie in results]

    def popular(self) -> list:
        """Obtém os filmes atualmente em destaque / populares."""
        data = self.client.get("/movie/popular", {"language": "pt-BR"})
        results = data.get("results", [])
        return [self.normalize_movie(movie) for movie in results]

    def details(self, tmdb_id: int) -> dict:
        """Obtém detalhes completos de um filme específico pelo seu ID da TMDB."""
        if not str(tmdb_id).isdigit() or int(tmdb_id) <= 0:
            raise ValueError("Identificador de filme inválido.")

        data = self.client.get(f"/movie/{int(tmdb_id)}", {"language": "pt-BR"})
        return self.normalize_movie(data)
