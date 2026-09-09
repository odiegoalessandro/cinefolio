"""Casos de uso para a foto de perfil e seu ciclo de vida local."""


class AvatarService:
    """Coordena persistência do usuário e arquivos de avatar de forma atômica."""

    def __init__(self, user_repository, avatar_storage, avatar_mutation_coordinator):
        self.user_repository = user_repository
        self.avatar_storage = avatar_storage
        self.avatar_mutation_coordinator = avatar_mutation_coordinator

    def replace(self, user_id: int, uploaded):
        """Substitui o avatar do usuário e descarta a foto anterior quando aplicável."""
        with self.avatar_mutation_coordinator.hold(user_id):
            previous_user = self.user_repository.get_by_id(user_id)
            new_avatar_url = self.avatar_storage.save(
                uploaded.content,
                uploaded.content_type,
            )
            try:
                staged_avatar = self._stage_exclusive_removal(
                    user_id,
                    previous_user["avatar_url"],
                )
            except Exception:
                self.avatar_storage.remove(new_avatar_url)
                raise

            try:
                updated_user = self.user_repository.update_avatar_url(user_id, new_avatar_url)
            except Exception:
                self.avatar_storage.remove(new_avatar_url)
                self.avatar_storage.restore(staged_avatar)
                raise

            self.avatar_storage.discard(staged_avatar)
            return updated_user

    def remove(self, user_id: int):
        """Restaura o avatar padrão do usuário e remove a foto local exclusiva."""
        with self.avatar_mutation_coordinator.hold(user_id):
            previous_user = self.user_repository.get_by_id(user_id)
            staged_avatar = self._stage_exclusive_removal(
                user_id,
                previous_user["avatar_url"],
            )
            try:
                updated_user = self.user_repository.update_avatar_url(user_id, "")
            except Exception:
                self.avatar_storage.restore(staged_avatar)
                raise

            self.avatar_storage.discard(staged_avatar)
            return updated_user

    def delete_user(self, user_id: int) -> None:
        """Exclui o usuário e remove a foto local somente após confirmar o banco."""
        with self.avatar_mutation_coordinator.hold(user_id):
            previous_user = self.user_repository.get_by_id(user_id)
            staged_avatar = self._stage_exclusive_removal(
                user_id,
                previous_user["avatar_url"],
            )
            try:
                self.user_repository.delete(user_id)
            except Exception:
                self.avatar_storage.restore(staged_avatar)
                raise

            self.avatar_storage.discard(staged_avatar)

    def _stage_exclusive_removal(self, user_id: int, avatar_url: str):
        """Estagia apenas um arquivo local que não seja referenciado por outro usuário."""
        if not self.user_repository.avatar_url_is_exclusive_to_user(user_id, avatar_url):
            return None
        return self.avatar_storage.stage_removal(avatar_url)
