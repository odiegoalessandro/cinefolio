"""Controlador das operações destrutivas da conta autenticada."""


class AccountController:
    """Expõe a exclusão da conta e de seus recursos associados."""

    def __init__(self, avatar_service):
        # Usa o avatar_service (não o user_repository direto) porque
        # excluir a conta também precisa remover o arquivo de avatar do
        # disco de forma coordenada — essa lógica já mora no AvatarService
        self.avatar_service = avatar_service

    def delete_account(self, current_user: dict) -> dict:
        """Exclui a conta autenticada e todos os recursos vinculados."""
        if not current_user:
            raise PermissionError("Autenticação necessária.")

        self.avatar_service.delete_user(current_user["id"])
        return {"ok": True, "message": "Conta excluída com sucesso."}
