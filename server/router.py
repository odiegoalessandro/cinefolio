"""Roteador HTTP nativo da aplicação Cinefolio.

Mapeia as requisições para os controladores correspondentes.
"""

from http import HTTPStatus
from urllib.parse import parse_qs, urlparse

from server.controllers.movie_controller import validate_movie_payload
from server.controllers.profile_controller import validate_profile_payload
from server.http.errors import write_exception_response
from server.http.multipart import read_multipart_file
from server.http.request_json import read_json
from server.http.response_json import json_response
from server.http.session_cookies import (
    create_session_cookie,
    expire_session_cookie,
    read_session_token,
)
from server.serializers.user import sanitize_user

# Exporta funções de validação para compatibilidade com a suíte de testes
# (alguns testes importam essas funções com estes nomes antigos)
movie_profile_payload = validate_movie_payload
profile_payload = validate_profile_payload


class Router:
    """Roteador responsável por despachar as requisições da API.

    Faz o papel de um "roteador manual": como o projeto não usa nenhum
    framework web (Flask, Django etc), é aqui que cada combinação de
    caminho (path) + método HTTP é associada manualmente ao controller certo.
    """

    def __init__(
        self,
        auth_controller,
        movie_controller,
        profile_controller,
        avatar_controller,
        account_controller,
        current_user_resolver,
    ):
        self.auth_controller = auth_controller
        self.movie_controller = movie_controller
        self.profile_controller = profile_controller
        self.avatar_controller = avatar_controller
        self.account_controller = account_controller
        self.current_user_resolver = current_user_resolver

    def _extract_user(self, handler) -> tuple[dict, str]:
        """Extrai o usuário autenticado e o token da requisição a partir dos cookies."""
        token = read_session_token(handler.headers.get("Cookie", ""))
        current_user = self.current_user_resolver(token)
        return current_user, token

    def dispatch(self, handler):
        """Analisa a rota e o método HTTP da requisição e executa o controlador correspondente."""
        # urlparse separa a URL em partes: aqui interessa o "path" (ex:
        # "/api/movies/search") e a "query" (ex: "q=matrix")
        parsed_url = urlparse(handler.path)
        path = parsed_url.path
        method = handler.command
        query_params = parse_qs(parsed_url.query)

        try:
            # A identidade do usuário é resolvida UMA vez no início e
            # reaproveitada em todas as rotas abaixo, em vez de cada rota
            # ler o cookie de novo
            current_user, token = self._extract_user(handler)

            # -----------------------------------------------------------------
            # Rotas de Autenticação (/api/auth/*)
            # -----------------------------------------------------------------
            if path == "/api/auth/register" and method == "POST":
                payload = read_json(handler)
                result = self.auth_controller.register(payload)
                return json_response(handler, HTTPStatus.CREATED, result)

            if path == "/api/auth/login" and method == "POST":
                payload = read_json(handler)
                result, new_token = self.auth_controller.login(payload)
                # No login, além do corpo JSON, um header Set-Cookie é
                # enviado para o navegador guardar o token de sessão
                return json_response(
                    handler,
                    HTTPStatus.OK,
                    result,
                    {"Set-Cookie": create_session_cookie(new_token)},
                )

            if path == "/api/auth/logout" and method == "POST":
                result = self.auth_controller.logout(token)
                # No logout, o Set-Cookie manda o navegador APAGAR o cookie
                return json_response(
                    handler,
                    HTTPStatus.OK,
                    result,
                    {"Set-Cookie": expire_session_cookie()},
                )

            if path == "/api/auth/me" and method == "GET":
                result = self.auth_controller.me(current_user)
                return json_response(handler, HTTPStatus.OK, result)

            # -----------------------------------------------------------------
            # Rotas de Catálogo de Filmes (/api/movies/*)
            # -----------------------------------------------------------------
            if path == "/api/movies/search" and method == "GET":
                # query_params.get("q", [""])[0]: parse_qs sempre devolve
                # listas (pois uma query string pode repetir a mesma chave),
                # então pega o primeiro valor, com "" como padrão se ausente
                search_query = query_params.get("q", [""])[0]
                result = self.movie_controller.search(search_query)
                return json_response(handler, HTTPStatus.OK, result)

            if path == "/api/movies/popular" and method == "GET":
                result = self.movie_controller.popular()
                return json_response(handler, HTTPStatus.OK, result)

            if path.startswith("/api/movies/"):
                # Rotas com um ID de filme na URL (ex: /api/movies/603) não
                # dá pra comparar path inteiro com "==", então o caminho é
                # quebrado em "segmentos" para examinar cada parte
                segments = path.strip("/").split("/")
                # ex: "/api/movies/603" -> ["api", "movies", "603"]
                # ex: "/api/movies/603/profile" -> ["api", "movies", "603", "profile"]



                # Rota: GET /api/movies/{tmdb_id}
                if len(segments) == 3 and method == "GET":
                    tmdb_id = segments[2]
                    result = self.movie_controller.details(tmdb_id, current_user)
                    return json_response(handler, HTTPStatus.OK, result)

                # Rota: /api/movies/{tmdb_id}/profile
                if len(segments) == 4 and segments[3] == "profile":
                    tmdb_id = segments[2]

                    if method == "PUT":
                        payload = read_json(handler)
                        result = self.movie_controller.save_to_profile(
                            tmdb_id,
                            current_user,
                            payload,
                        )
                        return json_response(handler, HTTPStatus.OK, result)

                    if method == "DELETE":
                        result = self.movie_controller.remove_from_profile(
                            tmdb_id,
                            current_user,
                        )
                        return json_response(handler, HTTPStatus.OK, result)

            # -----------------------------------------------------------------
            # Rotas de Perfis e Conta (/api/profiles/*, /api/profile, /api/account)
            # -----------------------------------------------------------------
            if path.startswith("/api/profiles/") and method == "GET":
                username = path[len("/api/profiles/") :]
                result = self.profile_controller.get_public_profile(username)
                return json_response(handler, HTTPStatus.OK, result)

            if path == "/api/profile/avatar" and method == "PUT":
                if not current_user:
                    raise PermissionError("Autenticação necessária.")
                # A leitura do multipart só é feita DEPOIS de confirmar que
                # o usuário está logado, evitando processar um upload de
                # arquivo grande à toa quando a requisição já vai ser rejeitada
                uploaded = read_multipart_file(handler)
                result = self.avatar_controller.replace_avatar(current_user, uploaded)
                return json_response(handler, HTTPStatus.OK, result)

            if path == "/api/profile/avatar" and method == "DELETE":
                result = self.avatar_controller.remove_avatar(current_user)
                return json_response(handler, HTTPStatus.OK, result)

            if path == "/api/profile" and method == "PUT":
                payload = read_json(handler)
                result = self.profile_controller.update_profile(current_user, payload)
                return json_response(handler, HTTPStatus.OK, result)

            if path == "/api/account" and method == "DELETE":
                result = self.account_controller.delete_account(current_user)
                return json_response(
                    handler,
                    HTTPStatus.OK,
                    result,
                    # Ao excluir a conta, também desloga o navegador expirando o cookie
                    {"Set-Cookie": expire_session_cookie()},
                )

            # Caso a rota não corresponda a nenhum endpoint
            return json_response(
                handler,
                HTTPStatus.NOT_FOUND,
                {"error": "Rota não encontrada."},
            )

        except Exception as error:
            # Ponto único de tratamento de erros: qualquer exceção lançada
            # em qualquer controller/service/repository cai aqui e é
            # convertida numa resposta HTTP apropriada (ver http/errors.py)
            return write_exception_response(handler, error)

    @staticmethod
    def safe_user(user: dict) -> dict:
        """Método utilitário para sanitização de usuário."""
        return sanitize_user(user)
