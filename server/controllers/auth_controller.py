"""Controlador responsável pelos fluxos de autenticação e sessão do usuário."""

from server.serializers.user import sanitize_user


class AuthController:
    """Controlador de autenticação."""

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
        return {"user": sanitize_user(created_user)}

    def login(self, payload: dict) -> tuple[dict, str]:
        """Processa a solicitação de autenticação (login)."""
        username = payload.get("username", "")
        password = payload.get("password", "")

        user, token = self.auth_service.login(username=username, password=password)
        return {"user": sanitize_user(user)}, token

    def logout(self, token: str) -> dict:
        """Processa a solicitação de encerramento de sessão (logout)."""
        self.auth_service.logout(token)
        return {"ok": True}

    def me(self, current_user: dict) -> dict:
        """Retorna os dados do usuário atualmente autenticado."""
        if not current_user:
            raise PermissionError("Autenticação necessária.")
        return {"user": sanitize_user(current_user)}
