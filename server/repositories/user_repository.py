"""Repositório de acesso a dados para usuários e sessões."""

from datetime import datetime, timezone


def now_iso() -> str:
    """Retorna a data e hora UTC atual em formato ISO 8601 sem microssegundos."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class UserRepository:
    """Camada de persistência para as tabelas `users` e `sessions`."""

    def __init__(self, connection):
        self.connection = connection

    # -------------------------------------------------------------------------
    # Operações da entidade Users
    # -------------------------------------------------------------------------

    def create(self, username: str, display_name: str, password_hash: str):
        """Insere um novo usuário e retorna o registro criado."""
        cursor = self.connection.execute(
            """
            INSERT INTO users (username, display_name, password_hash, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (username, display_name, password_hash, now_iso()),
        )
        self.connection.commit()
        return self.get_by_id(cursor.lastrowid)

    def get_by_id(self, user_id: int):
        """Busca um usuário pelo identificador primário."""
        return self.connection.execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

    def get_by_username(self, username: str):
        """Busca um usuário pelo seu nome de usuário único."""
        return self.connection.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,),
        ).fetchone()

    def update_profile(
        self,
        user_id: int,
        display_name: str,
        bio: str,
        avatar_url: str,
        banner_url: str,
    ):
        """Atualiza os dados de perfil de um usuário existente."""
        self.connection.execute(
            """
            UPDATE users
            SET display_name = ?,
                bio = ?,
                avatar_url = ?,
                banner_url = ?
            WHERE id = ?
            """,
            (display_name, bio, avatar_url, banner_url, user_id),
        )
        self.connection.commit()
        return self.get_by_id(user_id)

    def delete(self, user_id: int):
        """Remove o usuário e todos os seus dados associados em cascata."""
        self.connection.execute("DELETE FROM users WHERE id = ?", (user_id,))
        self.connection.commit()

    # -------------------------------------------------------------------------
    # Operações da entidade Sessions
    # -------------------------------------------------------------------------

    def create_session(self, user_id: int, token_hash: str, expires_at: str):
        """Cria um registro de sessão ativa para o usuário."""
        self.connection.execute(
            """
            INSERT INTO sessions (user_id, token_hash, expires_at, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, token_hash, expires_at, now_iso()),
        )
        self.connection.commit()

    def get_session_user(self, token_hash: str, current_time: str):
        """Recupera o usuário associado a um token de sessão válido e não expirado."""
        return self.connection.execute(
            """
            SELECT users.*
            FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.token_hash = ?
              AND sessions.expires_at > ?
            """,
            (token_hash, current_time),
        ).fetchone()

    def delete_session(self, token_hash: str):
        """Invalida/remove uma sessão específica pelo hash do token."""
        self.connection.execute(
            "DELETE FROM sessions WHERE token_hash = ?",
            (token_hash,),
        )
        self.connection.commit()

    def delete_expired_sessions(self, current_time: str):
        """Remove todas as sessões cujo prazo de validade já expirou."""
        self.connection.execute(
            "DELETE FROM sessions WHERE expires_at <= ?",
            (current_time,),
        )
        self.connection.commit()
