"""Controlador das mutações de foto do usuário autenticado."""

from server.serializers.user import sanitize_user


class AvatarController:
    """Expõe upload, troca e remoção da foto de perfil."""

    def __init__(self, avatar_service):
        self.avatar_service = avatar_service

    def replace_avatar(self, current_user: dict, uploaded) -> dict:
        """Substitui a foto do usuário autenticado pelo arquivo validado."""
        self._require_current_user(current_user)
        updated_user = self.avatar_service.replace(current_user["id"], uploaded)
        return {"user": sanitize_user(updated_user)}

    def remove_avatar(self, current_user: dict) -> dict:
        """Remove a foto local do usuário autenticado e restaura o padrão."""
        self._require_current_user(current_user)
        updated_user = self.avatar_service.remove(current_user["id"])
        return {"user": sanitize_user(updated_user)}

    @staticmethod
    def _require_current_user(current_user: dict) -> None:
        if not current_user:
            raise PermissionError("Autenticação necessária.")
