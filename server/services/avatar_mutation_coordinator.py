"""Coordenação de mutações concorrentes de avatar no processo do servidor."""

from contextlib import contextmanager
from dataclasses import dataclass
from threading import Lock


@dataclass
class _LockEntry:
    """Lock de um usuário e número de operações que ainda o referenciam."""

    lock: Lock
    references: int = 0


class AvatarMutationCoordinator:
    """Serializa upload, remoção e exclusão de avatar por usuário."""

    def __init__(self):
        self._registry_lock = Lock()
        self._entries: dict[int, _LockEntry] = {}

    @contextmanager
    def hold(self, user_id: int):
        """Mantém exclusividade para todas as mutações do avatar de um usuário."""
        entry = self._acquire_entry(user_id)
        entry.lock.acquire()
        try:
            yield
        finally:
            entry.lock.release()
            self._release_entry(user_id, entry)

    def _acquire_entry(self, user_id: int) -> _LockEntry:
        """Obtém a entrada estável para o usuário enquanto há operações pendentes."""
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
                self._entries.pop(user_id, None)
