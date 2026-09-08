"""Leitura e criação de cookies de sessão."""


SESSION_COOKIE_ATTRIBUTES = "HttpOnly; SameSite=Lax; Path=/"


def read_session_token(cookie_header: str) -> str | None:
    """Extrai o token da sessão a partir do header Cookie."""
    for cookie_part in (cookie_header or "").split(";"):
        part = cookie_part.strip()
        if part.startswith("session="):
            return part[len("session=") :]

    return None


def create_session_cookie(token: str) -> str:
    """Cria o header Set-Cookie para uma sessão válida por sete dias."""
    return f"session={token}; {SESSION_COOKIE_ATTRIBUTES}; Max-Age=604800"


def expire_session_cookie() -> str:
    """Cria o header Set-Cookie que invalida a sessão atual."""
    return f"session=; {SESSION_COOKIE_ATTRIBUTES}; Max-Age=0"
