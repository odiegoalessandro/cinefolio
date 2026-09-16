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
        """Insere ou atualiza os metadados do filme no catálogo local.

        "upsert" = UPDATE + INSERT: tenta inserir um filme novo; se já existir
        um filme com o mesmo tmdb_id (ver UNIQUE no schema.sql), atualiza os
        dados existentes em vez de gerar um erro de duplicidade.
        Isso mantém o "cache" local de filmes sempre atualizado com os
        dados mais recentes vindos da API do TMDB.
        """
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
            # "excluded" é uma palavra-chave especial do SQLite: refere-se aos
            # valores que TENTARAM ser inseridos (o novo registro), usados
            # aqui para atualizar o registro já existente em caso de conflito.
            # Note que "created_at" não é atualizado no ON CONFLICT — a data
            # de criação original do filme é preservada.
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
