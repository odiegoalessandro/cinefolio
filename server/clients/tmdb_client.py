"""Transporte HTTP para a API da The Movie Database (TMDB)."""

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


TMDB_API_BASE = "https://api.themoviedb.org/3"


class TmdbClient:
    """Executa chamadas autenticadas à API externa da TMDB.

    Esta é a camada "mais baixa" que fala diretamente com a internet.
    Diferente do TmdbService, ela não conhece regra de negócio — só sabe
    montar a URL, autenticar e fazer a requisição HTTP.
    """

    def __init__(self, token: str = None, opener=urlopen):
        # Se nenhum token for passado explicitamente, tenta ler da variável
        # de ambiente (isso permite reaproveitar a mesma classe em contextos
        # diferentes: produção lê do ambiente, testes passam um token fake)
        self.token = token if token is not None else os.environ.get("TMDB_BEARER_TOKEN", "")
        # Se nenhum token for passado explicitamente, tenta ler da variável
        # de ambiente (isso permite reaproveitar a mesma classe em contextos
        # diferentes: produção lê do ambiente, testes passam um token fake)
        self.opener = opener

    def get(self, path: str, params: dict = None) -> dict:
        """Obtém e decodifica um recurso JSON da TMDB."""
        if not self.token:
            raise ValueError("A chave da TMDB não está configurada no servidor (.env).")

        # urlencode transforma um dict em querystring (ex: {"query": "matrix"}
        # vira "query=matrix"), já tratando o escape de caracteres especiais
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
            # timeout=10 evita que o servidor Cinefolio fique travado
            # indefinidamente esperando uma resposta lenta da TMDB
            with self.opener(request, timeout=10) as response:
                return json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
            raise ValueError("Não foi possível consultar o catálogo de filmes no momento.") from error
