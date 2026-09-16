"""Leitura e criação de cookies de sessão."""

# Atributos de segurança aplicados a todo cookie de sessão:
# - HttpOnly: impede que JavaScript no navegador leia o cookie (protege contra ataques XSS)
# - SameSite=Lax: bloqueia o envio do cookie em a maioria das requisições
#   vindas de outros sites (proteção básica contra CSRF)
# - Path=/: o cookie vale para todas as rotas do site
SESSION_COOKIE_ATTRIBUTES = "HttpOnly; SameSite=Lax; Path=/"


def read_session_token(cookie_header: str) -> str | None:
    """Extrai o token da sessão a partir do header Cookie."""
    # O header Cookie pode conter vários cookies separados por ";"
    # (ex: "session=abc123; outro=xyz"), então é preciso percorrer cada um
    for cookie_part in (cookie_header or "").split(";"):
        part = cookie_part.strip()
        if part.startswith("session="):
            return part[len("session=") :]      # retorna só o valor, sem o "session="

    return None     # nenhum cookie de sessão encontrado (usuário não logado)


def create_session_cookie(token: str) -> str:
    """Cria o header Set-Cookie para uma sessão válida por sete dias."""
    # Max-Age em segundos: 604800 = 7 dias * 24h * 60min * 60s
    return f"session={token}; {SESSION_COOKIE_ATTRIBUTES}; Max-Age=604800"


def expire_session_cookie() -> str:
    """Cria o header Set-Cookie que invalida a sessão atual."""
    # Max-Age=0 instrui o navegador a apagar o cookie imediatamente (usado no logout)
    return f"session=; {SESSION_COOKIE_ATTRIBUTES}; Max-Age=0"
