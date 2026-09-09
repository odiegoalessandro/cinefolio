"""Controlador responsável pela visualização de perfis públicos e manutenção da conta."""

from server.controllers.auth_controller import sanitize_user
from server.services.avatar_mutation_coordinator import AvatarMutationCoordinator


def validate_profile_payload(data: dict) -> dict:
    """Valida os dados recebidos para atualização cadastral do perfil."""
    if "avatar_url" in data:
        raise ValueError("Use o envio de foto para alterar o avatar.")

    fields = ("display_name", "bio", "banner_url")
    values = {key: data.get(key, "") for key in fields}

    if not all(isinstance(val, str) for val in values.values()):
        raise ValueError("Dados de perfil inválidos.")

    display_name = values["display_name"].strip()
    bio = values["bio"].strip()
    banner_url = values["banner_url"].strip()

    if not 1 <= len(display_name) <= 80:
        raise ValueError("O nome de exibição deve ter entre 1 e 80 caracteres.")

    if len(bio) > 500:
        raise ValueError("A biografia deve ter no máximo 500 caracteres.")

    return {
        "display_name": display_name,
        "bio": bio,
        "banner_url": banner_url,
    }


class ProfileController:
    """Controlador para operações de perfil e conta."""

    def __init__(
        self,
        profile_service,
        user_repository,
        avatar_storage,
        avatar_mutation_coordinator: AvatarMutationCoordinator | None = None,
    ):
        self.profile_service = profile_service
        self.user_repository = user_repository
        self.avatar_storage = avatar_storage
        self.avatar_mutation_coordinator = (
            avatar_mutation_coordinator or AvatarMutationCoordinator()
        )

    def get_public_profile(self, username: str) -> dict:
        """Obtém o perfil público formatado do usuário especificado."""
        profile = self.profile_service.public_profile(username)
        if not profile:
            raise KeyError("Perfil não encontrado.")
        return {"profile": profile}

    def update_profile(self, current_user: dict, payload: dict) -> dict:
        """Atualiza os dados de perfil do usuário autenticado."""
        self._require_current_user(current_user)

        validated = validate_profile_payload(payload)
        updated_user = self.user_repository.update_profile(
            user_id=current_user["id"],
            **validated,
        )
        return {"user": sanitize_user(updated_user)}

    def replace_avatar(self, current_user: dict, uploaded) -> dict:
        """Substitui a foto do usuário autenticado por um arquivo local validado."""
        self._require_current_user(current_user)
        with self.avatar_mutation_coordinator.hold(current_user["id"]):
            return self._replace_avatar(current_user, uploaded)

    def _replace_avatar(self, current_user: dict, uploaded) -> dict:
        """Executa uma troca de avatar já serializada para o usuário atual."""
        previous_user = self.user_repository.get_by_id(current_user["id"])
        new_avatar_url = self.avatar_storage.save(uploaded.content, uploaded.content_type)
        try:
            staged_avatar = self._stage_avatar_removal(
                current_user["id"],
                previous_user["avatar_url"],
            )
        except Exception:
            self.avatar_storage.remove(new_avatar_url)
            raise

        try:
            updated_user = self.user_repository.update_avatar_url(
                current_user["id"],
                new_avatar_url,
            )
        except Exception:
            self.avatar_storage.remove(new_avatar_url)
            self.avatar_storage.restore(staged_avatar)
            raise

        self.avatar_storage.discard(staged_avatar)
        return {"user": sanitize_user(updated_user)}

    def remove_avatar(self, current_user: dict) -> dict:
        """Remove a foto local e restaura o avatar padrão do usuário autenticado."""
        self._require_current_user(current_user)
        with self.avatar_mutation_coordinator.hold(current_user["id"]):
            return self._remove_avatar(current_user)

    def _remove_avatar(self, current_user: dict) -> dict:
        """Executa a remoção de avatar já serializada para o usuário atual."""
        previous_user = self.user_repository.get_by_id(current_user["id"])
        staged_avatar = self._stage_avatar_removal(
            current_user["id"],
            previous_user["avatar_url"],
        )
        try:
            updated_user = self.user_repository.update_avatar_url(current_user["id"], "")
        except Exception:
            self.avatar_storage.restore(staged_avatar)
            raise

        self.avatar_storage.discard(staged_avatar)
        return {"user": sanitize_user(updated_user)}

    def delete_account(self, current_user: dict) -> dict:
        """Exclui a conta do usuário e todos os registros relacionados."""
        self._require_current_user(current_user)
        with self.avatar_mutation_coordinator.hold(current_user["id"]):
            return self._delete_account(current_user)

    def _delete_account(self, current_user: dict) -> dict:
        """Executa a exclusão de conta já serializada para o usuário atual."""

        previous_user = self.user_repository.get_by_id(current_user["id"])
        staged_avatar = self._stage_avatar_removal(
            current_user["id"],
            previous_user["avatar_url"],
        )
        try:
            self.user_repository.delete(current_user["id"])
        except Exception:
            self.avatar_storage.restore(staged_avatar)
            raise

        self.avatar_storage.discard(staged_avatar)
        return {"ok": True, "message": "Conta excluída com sucesso."}

    @staticmethod
    def _require_current_user(current_user: dict) -> None:
        """Bloqueia qualquer mutação de perfil sem uma sessão válida."""
        if not current_user:
            raise PermissionError("Autenticação necessária.")

    def _stage_avatar_removal(self, user_id: int, avatar_url: str):
        """Estagia a remoção apenas para um avatar que não seja compartilhado."""
        if not self.user_repository.avatar_url_is_exclusive_to_user(user_id, avatar_url):
            return None
        return self.avatar_storage.stage_removal(avatar_url)
