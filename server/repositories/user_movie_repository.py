from server.repositories.user_repository import now_iso


class UserMovieRepository:
    def __init__(self, connection):
        self.connection = connection

    def upsert(self, user_id, movie_id, status, rating=None, review=None, favorite=False, watched_at=None):
        timestamp = now_iso()
        self.connection.execute(
            "INSERT INTO user_movies (user_id, movie_id, status, rating, review, favorite, watched_at, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(user_id, movie_id) DO UPDATE SET status = excluded.status, rating = excluded.rating, "
            "review = excluded.review, favorite = excluded.favorite, watched_at = excluded.watched_at, updated_at = excluded.updated_at",
            (user_id, movie_id, status, rating, review, int(bool(favorite)), watched_at, timestamp, timestamp),
        )
        self.connection.commit()

    def remove(self, user_id, movie_id):
        cursor = self.connection.execute("DELETE FROM user_movies WHERE user_id = ? AND movie_id = ?", (user_id, movie_id))
        self.connection.commit()
        return cursor.rowcount > 0

    def list_for_profile(self, user_id, status=None, favorite=None, limit=None):
        query = (
            "SELECT movies.*, user_movies.status, user_movies.rating, user_movies.review, user_movies.favorite, user_movies.watched_at "
            "FROM user_movies JOIN movies ON movies.id = user_movies.movie_id WHERE user_movies.user_id = ?"
        )
        parameters = [user_id]
        if status:
            query += " AND user_movies.status = ?"
            parameters.append(status)
        if favorite is not None:
            query += " AND user_movies.favorite = ?"
            parameters.append(int(bool(favorite)))
        query += " ORDER BY COALESCE(user_movies.watched_at, user_movies.updated_at) DESC"
        if limit:
            query += " LIMIT ?"
            parameters.append(limit)
        return self.connection.execute(query, parameters).fetchall()

    def statistics(self, user_id):
        return self.connection.execute(
            "SELECT COUNT(*) FILTER (WHERE status = 'WATCHED') AS watched_count, "
            "ROUND(AVG(rating), 1) AS average_rating, COUNT(*) FILTER (WHERE review IS NOT NULL AND review != '') AS review_count "
            "FROM user_movies WHERE user_id = ?", (user_id,)
        ).fetchone()
