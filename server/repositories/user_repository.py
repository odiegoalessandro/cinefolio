from datetime import datetime, timezone


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class UserRepository:
    def __init__(self, connection):
        self.connection = connection

    def create(self, username, display_name, password_hash):
        cursor = self.connection.execute(
            "INSERT INTO users (username, display_name, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (username, display_name, password_hash, now_iso()),
        )
        self.connection.commit()
        return self.get_by_id(cursor.lastrowid)

    def get_by_id(self, user_id):
        return self.connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

    def get_by_username(self, username):
        return self.connection.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()

    def update_profile(self, user_id, display_name, bio, avatar_url, banner_url):
        self.connection.execute(
            "UPDATE users SET display_name = ?, bio = ?, avatar_url = ?, banner_url = ? WHERE id = ?",
            (display_name, bio, avatar_url, banner_url, user_id),
        )
        self.connection.commit()
        return self.get_by_id(user_id)

    def delete(self, user_id):
        self.connection.execute("DELETE FROM users WHERE id = ?", (user_id,))
        self.connection.commit()

    def create_session(self, user_id, token_hash, expires_at):
        self.connection.execute(
            "INSERT INTO sessions (user_id, token_hash, expires_at, created_at) VALUES (?, ?, ?, ?)",
            (user_id, token_hash, expires_at, now_iso()),
        )
        self.connection.commit()

    def get_session_user(self, token_hash, current_time):
        return self.connection.execute(
            "SELECT users.* FROM sessions JOIN users ON users.id = sessions.user_id "
            "WHERE sessions.token_hash = ? AND sessions.expires_at > ?",
            (token_hash, current_time),
        ).fetchone()

    def delete_session(self, token_hash):
        self.connection.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))
        self.connection.commit()

    def delete_expired_sessions(self, current_time):
        self.connection.execute("DELETE FROM sessions WHERE expires_at <= ?", (current_time,))
        self.connection.commit()
