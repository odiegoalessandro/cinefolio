"""Casos de uso para a foto de perfil e seu ciclo de vida local."""


class AvatarService:
    """Coordena persistência do usuário e arquivos de avatar de forma atômica.

    Esta classe existe porque trocar/remover um avatar envolve DUAS
    operações que precisam ficar sincronizadas: o registro no BANCO
    (campo avatar_url do usuário) e o ARQUIVO no disco. Se só uma das
    duas funcionar, o sistema fica num estado inconsistente (ex: banco
    aponta para um arquivo que não existe mais, ou um arquivo órfão fica
    ocupando espaço). Por isso, cada método aqui segue sempre o mesmo
    padrão de "transação manual": salva o novo, tenta confirmar no banco,
    e se der erro, desfaz (rollback) o que já tinha sido feito no disco.
    """

    def __init__(self, user_repository, avatar_storage, avatar_mutation_coordinator):
        self.user_repository = user_repository
        self.avatar_storage = avatar_storage
        # Garante que duas mutações de avatar do MESMO usuário nunca
        # rodem ao mesmo tempo (ver avatar_mutation_coordinator.py)
        self.avatar_mutation_coordinator = avatar_mutation_coordinator

    def replace(self, user_id: int, uploaded):
        """Substitui o avatar do usuário e descarta a foto anterior quando aplicável."""
        # "with ... hold(user_id)" trava a exclusividade para ESTE
        # usuário durante toda a operação, liberando automaticamente ao final
        with self.avatar_mutation_coordinator.hold(user_id):
            previous_user = self.user_repository.get_by_id(user_id)

            # Passo 1: salva o ARQUIVO NOVO primeiro (antes de mexer no
            # banco ou no arquivo antigo) — se isso falhar (ex: imagem
            # inválida), nada mais precisa ser desfeito ainda
            new_avatar_url = self.avatar_storage.save(
                uploaded.content,
                uploaded.content_type,
            )
            try:
                # Passo 2: "estagia" a remoção do avatar ANTIGO (renomeia,
                # mas não apaga de vez ainda) — só se ele for exclusivo
                # deste usuário (ver _stage_exclusive_removal)
                staged_avatar = self._stage_exclusive_removal(
                    user_id,
                    previous_user["avatar_url"],
                )
            except Exception:
                # Se estagiar o antigo falhar por algum motivo, desfaz o
                # arquivo NOVO que acabou de ser salvo (rollback), para
                # não deixar um arquivo órfão no disco
                self.avatar_storage.remove(new_avatar_url)
                raise

            try:
                # Passo 3: só agora tenta confirmar a mudança no BANCO
                updated_user = self.user_repository.update_avatar_url(user_id, new_avatar_url)
            except Exception:
                # Se o banco falhar, desfaz TUDO: remove o arquivo novo
                # que seria o avatar, e restaura o antigo de volta ao lugar
                self.avatar_storage.remove(new_avatar_url)
                self.avatar_storage.restore(staged_avatar)
                raise

            # Só quando o banco confirma com sucesso é que o arquivo
            # antigo "estagiado" é descartado de vez (apagado definitivamente)
            self.avatar_storage.discard(staged_avatar)
            return updated_user

    def remove(self, user_id: int):
        """Restaura o avatar padrão do usuário e remove a foto local exclusiva."""
        with self.avatar_mutation_coordinator.hold(user_id):
            previous_user = self.user_repository.get_by_id(user_id)
            # Mesmo padrão do replace(), mas aqui não há "arquivo novo"
            # para salvar — o avatar final é simplesmente uma string vazia
            staged_avatar = self._stage_exclusive_removal(
                user_id,
                previous_user["avatar_url"],
            )
            try:
                updated_user = self.user_repository.update_avatar_url(user_id, "")
            except Exception:
                # Falhou no banco: o arquivo antigo volta ao lugar dele
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
                # ON DELETE CASCADE no schema.sql já cuida de apagar as
                # sessões e os registros de user_movies deste usuário
                # automaticamente junto com o DELETE abaixo
                self.user_repository.delete(user_id)
            except Exception:
                # Se a exclusão no banco falhar, o avatar (e o usuário)
                # continuam intactos — nada é apagado pela metade
                self.avatar_storage.restore(staged_avatar)
                raise

            self.avatar_storage.discard(staged_avatar)

    def _stage_exclusive_removal(self, user_id: int, avatar_url: str):
        """Estagia apenas um arquivo local que não seja referenciado por outro usuário."""
        # Proteção contra um cenário raro/legado: se por algum motivo
        # OUTRO usuário estivesse usando essa MESMA URL de avatar,
        # apagar o arquivo quebraria o avatar dessa outra pessoa também.
        # Por isso, só estagia a remoção se a URL for EXCLUSIVA deste usuário.
        if not self.user_repository.avatar_url_is_exclusive_to_user(user_id, avatar_url):
            return None
        return self.avatar_storage.stage_removal(avatar_url)
