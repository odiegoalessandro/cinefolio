"""Roteador HTTP nativo da aplicação Cinefolio.

Mapeia as requisições para os controladores correspondentes.
"""

from http import HTTPStatus
from urllib.parse import parse_qs, urlparse

from server.controllers.auth_controller import AuthController, sanitize_user
from server.controllers.movie_controller import MovieController, validate_movie_payload
from server.controllers.profile_controller import ProfileController, validate_profile_payload
from server.http.errors import write_exception_response
from server.http.request_json import read_json
from server.http.response_json import json_response
from server.http.session_cookies import (
    create_session_cookie,
    expire_session_cookie,
    read_session_token,
)
from server.repositories.movie_repository import MovieRepository
from server.repositories.user_movie_repository import UserMovieRepository
from server.repositories.user_repository import UserRepository
from server.services.auth_service import AuthService
from server.services.profile_service import ProfileService
from server.services.tmdb_service import TmdbService


# Exporta funções de validação para compatibilidade com a suíte de testes
movie_profile_payload = validate_movie_payload
profile_payload = validate_profile_payload


class Router:
    """Roteador responsável por despachar as requisições da API."""

    def __init__(self, connection, tmdb_token: str | None = None):
        self.connection = connection

        # Inicialização dos repositórios
        self.user_repo = UserRepository(connection)
        self.movie_repo = MovieRepository(connection)
        self.user_movie_repo = UserMovieRepository(connection)

        # Inicialização dos serviços
        self.auth_service = AuthService(self.user_repo)
        self.profile_service = ProfileService(self.user_repo, self.user_movie_repo)
        self.tmdb_service = TmdbService(token=tmdb_token)

        # Inicialização dos controladores
        self.auth_controller = AuthController(self.auth_service)
        self.movie_controller = MovieController(
            self.tmdb_service,
            self.movie_repo,
            self.user_movie_repo,
        )
        self.profile_controller = ProfileController(
            self.profile_service,
            self.user_repo,
        )

    def _extract_user(self, handler) -> tuple[dict, str]:
        """Extrai o usuário autenticado e o token da requisição a partir dos cookies."""
        token = read_session_token(handler.headers.get("Cookie", ""))
        current_user = self.auth_service.current_user(token)
        return current_user, token

    def dispatch(self, handler):
        """Analisa a rota e o método HTTP da requisição e executa o controlador correspondente."""
        parsed_url = urlparse(handler.path)
        path = parsed_url.path
        method = handler.command
        query_params = parse_qs(parsed_url.query)

        try:
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
                return json_response(
                    handler,
                    HTTPStatus.OK,
                    result,
                    {"Set-Cookie": create_session_cookie(new_token)},
                )

            if path == "/api/auth/logout" and method == "POST":
                result = self.auth_controller.logout(token)
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
                search_query = query_params.get("q", [""])[0]
                result = self.movie_controller.search(search_query)
                return json_response(handler, HTTPStatus.OK, result)

            if path == "/api/movies/popular" and method == "GET":
                result = self.movie_controller.popular()
                return json_response(handler, HTTPStatus.OK, result)

            if path.startswith("/api/movies/"):
                segments = path.strip("/").split("/")

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

            if path == "/api/profile" and method == "PUT":
                payload = read_json(handler)
                result = self.profile_controller.update_profile(current_user, payload)
                return json_response(handler, HTTPStatus.OK, result)

            if path == "/api/account" and method == "DELETE":
                result = self.profile_controller.delete_account(current_user)
                return json_response(
                    handler,
                    HTTPStatus.OK,
                    result,
                    {"Set-Cookie": expire_session_cookie()},
                )

            # Caso a rota não corresponda a nenhum endpoint
            return json_response(
                handler,
                HTTPStatus.NOT_FOUND,
                {"error": "Rota não encontrada."},
            )

        except Exception as error:
            return write_exception_response(handler, error)

    @staticmethod
    def safe_user(user: dict) -> dict:
        """Método utilitário para sanitização de usuário."""
        return sanitize_user(user)
