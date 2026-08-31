"""Serviço de autenticação, hashing de senhas e gerenciamento de sessões."""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

ITERATIONS = 310_000


def now_iso() -> str:
    """Retorna o timestamp atual em UTC formatado em ISO 8601."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def hash_password(password: str) -> str:
    """Gera um hash PBKDF2-HMAC-SHA256 seguro com salt individual de 16 bytes."""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verifica se a senha fornecida corresponde ao hash armazenado."""
    try:
        algorithm, iterations, salt_hex, expected_hex = stored_hash.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iterations),
        )
        return hmac.compare_digest(actual.hex(), expected_hex)
    except (ValueError, TypeError):
        return False


class AuthService:
    """Camada de serviço para registro, login e gerenciamento de sessão de usuários."""

    def __init__(self, user_repository):
        self.users = user_repository

    def register(self, username: str, display_name: str, password: str):
        """Valida e cadastra um novo usuário no sistema."""
        username = (username or "").strip().lower()
        display_name = (display_name or "").strip()
        password = password or ""

        if not 3 <= len(username) <= 30 or not username.replace("_", "").isalnum():
            raise ValueError("Username deve ter entre 3 e 30 caracteres alfanuméricos ou sublinhado (_).")

        if not 1 <= len(display_name) <= 80:
            raise ValueError("Nome de exibição deve ter entre 1 e 80 caracteres.")

        if not 8 <= len(password) <= 128:
            raise ValueError("Senha deve ter entre 8 e 128 caracteres.")

        if self.users.get_by_username(username):
            raise ValueError("Este nome de usuário já está em uso.")

        return self.users.create(username, display_name, hash_password(password))

    def login(self, username: str, password: str):
        """Autentica o usuário e gera um token de sessão válido por 7 dias."""
        username = (username or "").strip().lower()
        password = password or ""

        user = self.users.get_by_username(username)
        if not user or not verify_password(password, user["password_hash"]):
            raise ValueError("Usuário ou senha inválidos.")

        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        expires_at = (datetime.now(timezone.utc) + timedelta(days=7)).replace(microsecond=0).isoformat()

        self.users.create_session(user["id"], token_hash, expires_at)
        return user, token

    def current_user(self, token: str):
        """Obtém os dados do usuário a partir do token de sessão ativo."""
        if not token:
            return None
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        return self.users.get_session_user(token_hash, now_iso())

    def logout(self, token: str):
        """Invalida a sessão correspondente ao token."""
        if token:
            token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
            self.users.delete_session(token_hash)
