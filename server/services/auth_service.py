import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

ITERATIONS = 310_000


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def hash_password(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password, stored_hash):
    try:
        algorithm, iterations, salt_hex, expected_hex = stored_hash.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations))
        return hmac.compare_digest(actual.hex(), expected_hex)
    except (ValueError, TypeError):
        return False


class AuthService:
    def __init__(self, users):
        self.users = users

    def register(self, username, display_name, password):
        username = username.strip().lower()
        display_name = display_name.strip()
        if not 3 <= len(username) <= 30 or not username.replace("_", "").isalnum():
            raise ValueError("Username deve ter 3 a 30 caracteres alfanuméricos ou _.")
        if not display_name or len(display_name) > 80:
            raise ValueError("Nome de exibição inválido.")
        if len(password) < 8 or len(password) > 128:
            raise ValueError("Senha deve ter entre 8 e 128 caracteres.")
        if self.users.get_by_username(username):
            raise ValueError("Username já está em uso.")
        return self.users.create(username, display_name, hash_password(password))

    def login(self, username, password):
        user = self.users.get_by_username(username.strip().lower())
        if not user or not verify_password(password, user["password_hash"]):
            raise ValueError("Username ou senha inválidos.")
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        expires_at = (datetime.now(timezone.utc) + timedelta(days=7)).replace(microsecond=0).isoformat()
        self.users.create_session(user["id"], token_hash, expires_at)
        return user, token

    def current_user(self, token):
        if not token:
            return None
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        return self.users.get_session_user(token_hash, now_iso())

    def logout(self, token):
        if token:
            self.users.delete_session(hashlib.sha256(token.encode("utf-8")).hexdigest())
