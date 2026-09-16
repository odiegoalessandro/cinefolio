"""Serviço de autenticação, hashing de senhas e gerenciamento de sessões."""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone


# Número de iterações do algoritmo PBKDF2. Quanto maior, mais lento e mais
# caro fica tentar "quebrar" o hash por força bruta (é o valor recomendado
# atualmente pela OWASP para PBKDF2-HMAC-SHA256).
ITERATIONS = 310_000


def now_iso() -> str:
    """Retorna o timestamp atual em UTC formatado em ISO 8601."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def hash_password(password: str) -> str:
    """Gera um hash PBKDF2-HMAC-SHA256 seguro com salt individual de 16 bytes."""
    # O "salt" é um valor aleatório único por senha: garante que duas pessoas
    # com a mesma senha gerem hashes diferentes, e impede ataques com
    # tabelas pré-computadas (rainbow tables).
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    # O hash final guarda tudo que é preciso para verificar depois:
    # algoritmo, número de iterações, salt e o resultado — assim, mesmo que
    # o valor de ITERATIONS mude no futuro, senhas antigas continuam
    # verificáveis corretamente.
    return f"pbkdf2_sha256${ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verifica se a senha fornecida corresponde ao hash armazenado."""
    try:
        algorithm, iterations, salt_hex, expected_hex = stored_hash.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        # Recalcula o hash usando a MESMA senha informada agora, mas com o
        # salt e o número de iterações que foram salvos no cadastro
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iterations),
        )
        # hmac.compare_digest faz uma comparação em "tempo constante":
        # evita vazar informação sobre a senha através do tempo que a
        # comparação leva (proteção contra timing attack), diferente de um "=="
        return hmac.compare_digest(actual.hex(), expected_hex)
    except (ValueError, TypeError):
        # Hash salvo em formato corrompido/inesperado -> trata como senha inválida
        return False


class AuthService:
    """Camada de serviço para registro, login e gerenciamento de sessão de usuários."""

    def __init__(self, user_repository):
        self.users = user_repository

    def register(self, username: str, display_name: str, password: str):
        """Valida e cadastra um novo usuário no sistema."""
        # Normaliza username (minúsculo, sem espaço nas pontas) para evitar
        # duplicidade tipo "Joao" e "joao" sendo tratados como usuários diferentes
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

        # A senha em texto puro só existe até esta linha: a partir daqui,
        # só o hash é armazenado/manipulado
        return self.users.create(username, display_name, hash_password(password))

    def login(self, username: str, password: str):
        """Autentica o usuário e gera um token de sessão válido por 7 dias."""
        username = (username or "").strip().lower()
        password = password or ""

        user = self.users.get_by_username(username)
        if not user or not verify_password(password, user["password_hash"]):
            # Mensagem de erro genérica de propósito: não revela se foi o
            # username que não existe ou a senha que está errada, evitando
            # que um atacante descubra quais usernames são válidos
            raise ValueError("Usuário ou senha inválidos.")

        # secrets.token_urlsafe gera um token aleatório criptograficamente seguro
        token = secrets.token_urlsafe(32)
        # Só o HASH do token é salvo no banco (nunca o token em si) — assim,
        # mesmo que o banco vaze, ninguém consegue reconstruir os tokens
        # válidos e se passar pelos usuários logados
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        expires_at = (datetime.now(timezone.utc) + timedelta(days=7)).replace(microsecond=0).isoformat()

        self.users.create_session(user["id"], token_hash, expires_at)
        # O token "puro" é retornado só aqui, uma única vez, para virar o
        # cookie enviado ao navegador do cliente
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
