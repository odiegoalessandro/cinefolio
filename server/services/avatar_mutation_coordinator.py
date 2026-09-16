"""Coordenação de mutações concorrentes de avatar no processo do servidor."""

from contextlib import contextmanager
from dataclasses import dataclass
from threading import Lock


@dataclass
class _LockEntry:
    """Lock de um usuário e número de operações que ainda o referenciam."""

    lock: Lock
    references: int = 0 # quantas operações (threads) estão usando/esperando este lock agora



class AvatarMutationCoordinator:
    """Serializa upload, remoção e exclusão de avatar por usuário.

    Como o servidor pode atender várias requisições ao mesmo tempo (em
    threads diferentes), sem esse controle duas requisições simultâneas
    trocando o avatar do MESMO usuário poderiam se sobrepor de forma
    inconsistente (ex: uma apaga o arquivo que a outra estava usando).
    Esta classe garante que só uma operação de avatar por usuário roda
    por vez, sem travar operações de OUTROS usuários (cada um tem seu
    próprio lock, criado sob demanda).
    """

    def __init__(self):
        self._registry_lock = Lock()    # protege o dicionário abaixo
        self._entries: dict[int, _LockEntry] = {}   # um Lock por user_id

    @contextmanager
    def hold(self, user_id: int):
        """Mantém exclusividade para todas as mutações do avatar de um usuário.

        Uso: `with coordinator.hold(user_id): ...` — o bloco "with" só
        executa depois de conseguir o lock, e libera automaticamente ao sair
        (mesmo se uma exceção acontecer no meio do bloco).
        """
        entry = self._acquire_entry(user_id)
        entry.lock.acquire()
        try:
            yield
        finally:
            entry.lock.release()
            self._release_entry(user_id, entry)

    def _acquire_entry(self, user_id: int) -> _LockEntry:
        """Obtém a entrada estável para o usuário enquanto há operações pendentes."""
        # registry_lock evita que duas threads criem, ao mesmo tempo, dois
        # locks DIFERENTES para o mesmo user_id (o que quebraria a exclusão mútua)
        with self._registry_lock:
            entry = self._entries.get(user_id)
            if entry is None:
                entry = _LockEntry(lock=Lock())
                self._entries[user_id] = entry
            entry.references += 1
            return entry

    def _release_entry(self, user_id: int, entry: _LockEntry) -> None:
        """Libera a entrada quando não há mais operações ativas ou aguardando."""
        with self._registry_lock:
            entry.references -= 1
            if entry.references == 0:
                # Remove do dicionário para não acumular memória
                # indefinidamente com entradas de usuários que não estão
                # mais alterando o avatar
                self._entries.pop(user_id, None)
