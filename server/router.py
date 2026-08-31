import json
from http import HTTPStatus
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from server.repositories.movie_repository import MovieRepository
from server.repositories.user_movie_repository import UserMovieRepository
from server.repositories.user_repository import UserRepository
from server.services.auth_service import AuthService
from server.services.profile_service import ProfileService
from server.services.tmdb_service import TmdbService


def json_response(handler, status, body, headers=None):
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(payload)))
    for name, value in (headers or {}).items(): handler.send_header(name, value)
    handler.end_headers(); handler.wfile.write(payload)


def read_json(handler):
    size = int(handler.headers.get("Content-Length", "0"))
    if size > 20_000:
        raise ValueError("Payload muito grande.")
    try:
        payload = json.loads(handler.rfile.read(size).decode("utf-8")) if size else {}
    except json.JSONDecodeError as error:
        raise ValueError("JSON inválido.") from error
    if not isinstance(payload, dict):
        raise ValueError("JSON deve ser um objeto.")
    return payload


def profile_payload(data):
    values = {key: data.get(key, "") for key in ("display_name", "bio", "avatar_url", "banner_url")}
    if not all(isinstance(value, str) for value in values.values()):
        raise ValueError("Dados de perfil inválidos.")
    display_name = values["display_name"].strip()
    bio = values["bio"].strip()
    avatar_url = values["avatar_url"].strip()
    banner_url = values["banner_url"].strip()
    if not 1 <= len(display_name) <= 80:
        raise ValueError("Nome de exibição inválido.")
    if len(bio) > 500:
        raise ValueError("Bio deve ter no máximo 500 caracteres.")
    return display_name, bio, avatar_url, banner_url


def movie_profile_payload(data):
    allowed = {"status", "rating", "review", "favorite", "watched_at"}
    if set(data) - allowed or "status" not in data:
        raise ValueError("Dados de filme inválidos.")
    return {key: data.get(key) for key in allowed if key in data}

class Router:
    def __init__(self, connection):
        users = UserRepository(connection)
        self.auth, self.movies, self.user_movies = AuthService(users), MovieRepository(connection), UserMovieRepository(connection)
        self.profiles, self.tmdb = ProfileService(users, self.user_movies), TmdbService()

    def _user(self, handler):
        cookie = handler.headers.get("Cookie", "")
        token = next((part.strip()[8:] for part in cookie.split(";") if part.strip().startswith("session=")), None)
        return self.auth.current_user(token), token

    def dispatch(self, handler):
        parsed = urlparse(handler.path); path = parsed.path; query = parse_qs(parsed.query)
        try:
            user, token = self._user(handler)
            if path == "/api/auth/register" and handler.command == "POST":
                created = self.auth.register(**read_json(handler)); return json_response(handler, 201, {"user": self.safe_user(created)})
            if path == "/api/auth/login" and handler.command == "POST":
                logged, token = self.auth.login(**read_json(handler)); return json_response(handler, 200, {"user": self.safe_user(logged)}, {"Set-Cookie": f"session={token}; HttpOnly; SameSite=Lax; Path=/; Max-Age=604800"})
            if path == "/api/auth/logout" and handler.command == "POST":
                self.auth.logout(token); return json_response(handler, 200, {"ok": True}, {"Set-Cookie": "session=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0"})
            if path == "/api/auth/me" and handler.command == "GET":
                if not user: return json_response(handler, 401, {"error":"Autenticação necessária."})
                return json_response(handler, 200, {"user":self.safe_user(user)})
            if path == "/api/movies/search" and handler.command == "GET": return json_response(handler, 200, {"results":self.tmdb.search(query.get("q", [""])[0])})
            if path == "/api/movies/popular" and handler.command == "GET": return json_response(handler, 200, {"results":self.tmdb.popular()})
            if path.startswith("/api/movies/"):
                parts=path.split("/"); tmdb_id=parts[3]
                if len(parts)==4 and handler.command=="GET": return json_response(handler,200,{"movie":self.tmdb.details(tmdb_id)})
                if len(parts)==5 and parts[4]=="profile":
                    if not user: return json_response(handler,401,{"error":"Autenticação necessária."})
                    movie=self.movies.upsert(self.tmdb.details(tmdb_id))
                    if handler.command=="DELETE": return json_response(handler,200,{"removed":self.user_movies.remove(user["id"],movie["id"])})
                    payload=movie_profile_payload(read_json(handler)); self.user_movies.upsert(user["id"],movie["id"],**payload); return json_response(handler,200,{"ok":True})
            if path.startswith("/api/profiles/") and handler.command == "GET":
                profile=self.profiles.public_profile(path.rsplit("/",1)[1]); return json_response(handler,200,{"profile":profile}) if profile else json_response(handler,404,{"error":"Perfil não encontrado."})
            if path == "/api/profile" and handler.command == "PUT":
                if not user:return json_response(handler,401,{"error":"Autenticação necessária."})
                data=read_json(handler); updated=self.profiles.users.update_profile(user["id"], *profile_payload(data)); return json_response(handler,200,{"user":self.safe_user(updated)})
            if path == "/api/account" and handler.command == "DELETE":
                if not user:return json_response(handler,401,{"error":"Autenticação necessária."})
                self.profiles.users.delete(user["id"]); return json_response(handler,200,{"ok":True},{"Set-Cookie":"session=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0"})
            return json_response(handler,404,{"error":"Rota não encontrada."})
        except ValueError as error: return json_response(handler,400,{"error":str(error)})
        except Exception: return json_response(handler,500,{"error":"Erro interno do servidor."})

    @staticmethod
    def safe_user(user):
        return {key:user[key] for key in ("id","username","display_name","bio","avatar_url","banner_url","created_at")}
