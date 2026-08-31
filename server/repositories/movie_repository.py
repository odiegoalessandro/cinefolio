"""Repositório de acesso a dados para filmes catalogados."""

from server.repositories.user_repository import now_iso


class MovieRepository:
    """Camada de persistência para a tabela `movies`."""

    def __init__(self, connection):
        self.connection = connection

    def get_by_tmdb_id(self, tmdb_id: int):
        """Busca um filme pelo identificador único da TMDB."""
        return self.connection.execute(
            "SELECT * FROM movies WHERE tmdb_id = ?",
            (tmdb_id,),
        ).fetchone()

    def upsert(self, movie: dict):
        """Insere ou atualiza os metadados do filme no catálogo local."""
        self.connection.execute(
            """
            INSERT INTO movies (
                tmdb_id,
                title,
                original_title,
                release_year,
                poster_path,
                backdrop_path,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(tmdb_id) DO UPDATE SET
                title = excluded.title,
                original_title = excluded.original_title,
                release_year = excluded.release_year,
                poster_path = excluded.poster_path,
                backdrop_path = excluded.backdrop_path
            """,
            (
                movie["tmdb_id"],
                movie["title"],
                movie.get("original_title", ""),
                movie.get("release_year"),
                movie.get("poster_path", ""),
                movie.get("backdrop_path", ""),
                now_iso(),
            ),
        )
        self.connection.commit()
        return self.get_by_tmdb_id(movie["tmdb_id"])
