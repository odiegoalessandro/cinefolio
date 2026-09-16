"""Repositório de acesso a dados para usuários e sessões."""

from datetime import datetime, timezone


def now_iso() -> str:
    """Retorna a data e hora UTC atual em formato ISO 8601 sem microssegundos."""
    # timezone.utc garante que o horário salvo no banco não depende do fuso
    # horário do servidor (evita bugs quando o servidor roda em outro país/fuso)
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class UserRepository:
    """Camada de persistência para as tabelas `users` e `sessions`.

    Um "Repository" é a camada responsável só por conversar com o banco
    (SQL puro). Ele não valida regras de negócio nem decide o que fazer
    com os dados — isso é papel da camada de "service", que fica acima dele.
    """

    def __init__(self, connection):
        self.connection = connection    # conexão SQLite recebida de fora (injeção de dependência)

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
            # "?" são placeholders: o driver do SQLite escapa os valores
            # automaticamente, evitando ataques de SQL Injection
            (username, display_name, password_hash, now_iso()),
        )
        self.connection.commit()
        # cursor.lastrowid = id gerado automaticamente (AUTOINCREMENT) pelo INSERT acima
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
        banner_url: str,
    ):
        """Atualiza os dados textuais de um usuário sem alterar seu avatar."""
        # O avatar é atualizado em um método separado (update_avatar_url)
        # porque o upload de foto segue um fluxo diferente do resto do perfil
        self.connection.execute(
            """
            UPDATE users
            SET display_name = ?,
                bio = ?,
                banner_url = ?
            WHERE id = ?
            """,
            (display_name, bio, banner_url, user_id),
        )
        self.connection.commit()
        return self.get_by_id(user_id)

    def update_avatar_url(self, user_id: int, avatar_url: str):
        """Atualiza somente a URL de avatar do usuário identificado pela sessão."""
        self.connection.execute(
            "UPDATE users SET avatar_url = ? WHERE id = ?",
            (avatar_url, user_id),
        )
        self.connection.commit()
        return self.get_by_id(user_id)

    def avatar_url_is_exclusive_to_user(self, user_id: int, avatar_url: str) -> bool:
        """Confirma que uma URL local pertence somente ao usuário que a remove.

        Isso é usado antes de apagar o arquivo físico de um avatar antigo:
        se por algum motivo outro usuário estivesse usando a MESMA url
        (situação rara, mas possível em edge cases), o arquivo não pode
        ser apagado do disco, senão quebraria o avatar de outra pessoa.
        """
        if not avatar_url:
            return False

        shared = self.connection.execute(
            "SELECT 1 FROM users WHERE avatar_url = ? AND id != ? LIMIT 1",
            (avatar_url, user_id),
        ).fetchone()
        return shared is None   # None = ninguém mais usa essa URL = é exclusiva

    def delete(self, user_id: int):
        """Remove o usuário e todos os seus dados associados em cascata."""
        # Graças ao "ON DELETE CASCADE" definido no schema.sql, apagar o
        # usuário também apaga automaticamente suas sessões e seus
        # registros em user_movies — não é preciso apagar cada um manualmente.
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
        # O JOIN busca o usuário dono do token em uma única consulta,
        # e a condição "expires_at > current_time" já filtra sessões vencidas
        # (então uma sessão expirada simplesmente não retorna nenhum usuário)   
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
        """Remove todas as sessões cujo prazo de validade já expirou.

        Serve como uma "limpeza" (garbage collection) da tabela de sessões,
        evitando que ela cresça indefinidamente com tokens já inválidos.
        """
        self.connection.execute(
            "DELETE FROM sessions WHERE expires_at <= ?",
            (current_time,),
        )
        self.connection.commit()
