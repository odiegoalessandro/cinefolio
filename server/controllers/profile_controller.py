"""Controlador responsável pela visualização de perfis públicos e manutenção da conta."""

from server.controllers.auth_controller import sanitize_user


def validate_profile_payload(data: dict) -> dict:
    """Valida os dados recebidos para atualização cadastral do perfil."""
    fields = ("display_name", "bio", "avatar_url", "banner_url")
    values = {key: data.get(key, "") for key in fields}

    if not all(isinstance(val, str) for val in values.values()):
        raise ValueError("Dados de perfil inválidos.")

    display_name = values["display_name"].strip()
    bio = values["bio"].strip()
    avatar_url = values["avatar_url"].strip()
    banner_url = values["banner_url"].strip()

    if not 1 <= len(display_name) <= 80:
        raise ValueError("O nome de exibição deve ter entre 1 e 80 caracteres.")

    if len(bio) > 500:
        raise ValueError("A biografia deve ter no máximo 500 caracteres.")

    return {
        "display_name": display_name,
        "bio": bio,
        "avatar_url": avatar_url,
        "banner_url": banner_url,
    }


class ProfileController:
    """Controlador para operações de perfil e conta."""

    def __init__(self, profile_service, user_repository):
        self.profile_service = profile_service
        self.user_repository = user_repository

    def get_public_profile(self, username: str) -> dict:
        """Obtém o perfil público formatado do usuário especificado."""
        profile = self.profile_service.public_profile(username)
        if not profile:
            raise KeyError("Perfil não encontrado.")
        return {"profile": profile}

    def update_profile(self, current_user: dict, payload: dict) -> dict:
        """Atualiza os dados de perfil do usuário autenticado."""
        if not current_user:
            raise PermissionError("Autenticação necessária.")

        validated = validate_profile_payload(payload)
        updated_user = self.user_repository.update_profile(
            user_id=current_user["id"],
            **validated,
        )
        return {"user": sanitize_user(updated_user)}

    def delete_account(self, current_user: dict) -> dict:
        """Exclui a conta do usuário e todos os registros relacionados."""
        if not current_user:
            raise PermissionError("Autenticação necessária.")

        self.user_repository.delete(current_user["id"])
        return {"ok": True, "message": "Conta excluída com sucesso."}
