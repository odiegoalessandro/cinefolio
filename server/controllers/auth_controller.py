"""Controlador responsável pelos fluxos de autenticação e sessão do usuário."""

from server.serializers.user import sanitize_user


class AuthController:
    """Controlador de autenticação.

    Um "Controller" é a camada que recebe os dados já extraídos da
    requisição HTTP (payload, usuário atual, token) e decide o que fazer,
    delegando as regras de negócio para o Service. Ele não sabe nada sobre
    sockets/HTTP puro — isso fica no http_handler/router.
    """

    def __init__(self, auth_service):
        self.auth_service = auth_service

    def register(self, payload: dict) -> dict:
        """Processa a solicitação de cadastro de novo usuário."""
        username = payload.get("username", "")
        display_name = payload.get("display_name", "")
        password = payload.get("password", "")

        created_user = self.auth_service.register(
            username=username,
            display_name=display_name,
            password=password,
        )
        # sanitize_user remove o password_hash antes de devolver ao cliente
        return {"user": sanitize_user(created_user)}

    def login(self, payload: dict) -> tuple[dict, str]:
        """Processa a solicitação de autenticação (login)."""
        username = payload.get("username", "")
        password = payload.get("password", "")

        user, token = self.auth_service.login(username=username, password=password)
        # Retorna uma tupla (corpo da resposta, token) porque o token
        # precisa ser usado por quem chamou este método para montar o
        # cookie de sessão (Set-Cookie) — ele não faz parte do JSON de resposta
        return {"user": sanitize_user(user)}, token

    def logout(self, token: str) -> dict:
        """Processa a solicitação de encerramento de sessão (logout)."""
        self.auth_service.logout(token)
        return {"ok": True}

    def me(self, current_user: dict) -> dict:
        """Retorna os dados do usuário atualmente autenticado."""
        if not current_user:
            # PermissionError é convertido em HTTP 401 pelo errors.py
            raise PermissionError("Autenticação necessária.")
        return {"user": sanitize_user(current_user)}
