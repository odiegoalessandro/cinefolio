"""Roteador HTTP nativo da aplicação Cinefolio.

Mapeia as requisições para os controladores correspondentes, gerencia
cookies de autenticação e padroniza respostas em formato JSON.
"""

import json
from http import HTTPStatus
from urllib.parse import parse_qs, urlparse

from server.controllers.auth_controller import AuthController, sanitize_user
from server.controllers.movie_controller import MovieController, validate_movie_payload
from server.controllers.profile_controller import ProfileController, validate_profile_payload
from server.repositories.movie_repository import MovieRepository
from server.repositories.user_movie_repository import UserMovieRepository
from server.repositories.user_repository import UserRepository
from server.services.auth_service import AuthService
from server.services.profile_service import ProfileService
from server.services.tmdb_service import TmdbService


def json_response(handler, status: int, body: dict, headers: dict = None):
    """Envia uma resposta HTTP formatada em JSON com os cabeçalhos apropriados."""
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(payload)))

    if headers:
        for name, value in headers.items():
            handler.send_header(name, value)

    handler.end_headers()
    handler.wfile.write(payload)


def read_json(handler) -> dict:
    """Lê e decodifica o corpo JSON da requisição HTTP com limite de tamanho."""
    content_length_header = handler.headers.get("Content-Length", "0")
    try:
        size = int(content_length_header)
    except ValueError:
        size = 0

    if size > 30_000:
        raise ValueError("O tamanho da requisição excede o limite permitido (30KB).")

    if size == 0:
        return {}

    try:
        raw_body = handler.rfile.read(size).decode("utf-8")
        payload = json.loads(raw_body)
    except json.JSONDecodeError as error:
        raise ValueError("Formato JSON inválido.") from error

    if not isinstance(payload, dict):
        raise ValueError("O corpo da requisição deve ser um objeto JSON.")

    return payload


# Exporta funções de validação para compatibilidade com a suíte de testes
movie_profile_payload = validate_movie_payload
profile_payload = validate_profile_payload


class Router:
    """Roteador responsável por despachar as requisições da API."""

    def __init__(self, connection):
        self.connection = connection

        # Inicialização dos repositórios
        self.user_repo = UserRepository(connection)
        self.movie_repo = MovieRepository(connection)
        self.user_movie_repo = UserMovieRepository(connection)

        # Inicialização dos serviços
        self.auth_service = AuthService(self.user_repo)
        self.profile_service = ProfileService(self.user_repo, self.user_movie_repo)
        self.tmdb_service = TmdbService()

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
        cookie_header = handler.headers.get("Cookie", "")
        token = None

        for cookie_part in cookie_header.split(";"):
            part = cookie_part.strip()
            if part.startswith("session="):
                token = part[len("session=") :]
                break

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
                cookie_header = (
                    f"session={new_token}; HttpOnly; SameSite=Lax; Path=/; Max-Age=604800"
                )
                return json_response(
                    handler,
                    HTTPStatus.OK,
                    result,
                    {"Set-Cookie": cookie_header},
                )

            if path == "/api/auth/logout" and method == "POST":
                result = self.auth_controller.logout(token)
                expire_cookie = "session=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0"
                return json_response(
                    handler,
                    HTTPStatus.OK,
                    result,
                    {"Set-Cookie": expire_cookie},
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
                expire_cookie = "session=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0"
                return json_response(
                    handler,
                    HTTPStatus.OK,
                    result,
                    {"Set-Cookie": expire_cookie},
                )

            # Caso a rota não corresponda a nenhum endpoint
            return json_response(
                handler,
                HTTPStatus.NOT_FOUND,
                {"error": "Rota não encontrada."},
            )

        except ValueError as error:
            return json_response(
                handler,
                HTTPStatus.BAD_REQUEST,
                {"error": str(error)},
            )
        except PermissionError as error:
            return json_response(
                handler,
                HTTPStatus.UNAUTHORIZED,
                {"error": str(error)},
            )
        except KeyError as error:
            message = error.args[0] if error.args else "Recurso não encontrado."
            return json_response(
                handler,
                HTTPStatus.NOT_FOUND,
                {"error": message},
            )
        except Exception:
            return json_response(
                handler,
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": "Ocorreu um erro interno no servidor."},
            )

    @staticmethod
    def safe_user(user: dict) -> dict:
        """Método utilitário para sanitização de usuário."""
        return sanitize_user(user)
