"""Repositório de acesso a dados para relações usuário-filme (avaliações, status e favoritos)."""

from typing import Optional
from server.repositories.user_repository import now_iso


class UserMovieRepository:
    """Camada de persistência para a tabela associativa `user_movies`."""

    def __init__(self, connection):
        self.connection = connection

    def upsert(
        self,
        user_id: int,
        movie_id: int,
        status: str,
        rating: Optional[float] = None,
        review: Optional[str] = None,
        favorite: bool = False,
        watched_at: Optional[str] = None,
    ):
        """Insere ou atualiza o status/avaliação de um filme no perfil do usuário."""
        # Mesmo timestamp usado em created_at (se for um insert novo) e
        # updated_at, para manter os dois valores sincronizados na criação
        timestamp = now_iso()
        self.connection.execute(
            """
            INSERT INTO user_movies (
                user_id,
                movie_id,
                status,
                rating,
                review,
                favorite,
                watched_at,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, movie_id) DO UPDATE SET
                status = excluded.status,
                rating = excluded.rating,
                review = excluded.review,
                favorite = excluded.favorite,
                watched_at = excluded.watched_at,
                updated_at = excluded.updated_at
            """,
            # No conflito (usuário já tinha registro para esse filme),
            # "created_at" NÃO é sobrescrito — só updated_at avança.
            (
                user_id,
                movie_id,
                status,
                rating,
                review,
                int(bool(favorite)),    # SQLite não tem tipo boolean nativo: vira 0 ou 1
                watched_at,
                timestamp,
                timestamp,
            ),
        )
        self.connection.commit()

    def remove(self, user_id: int, movie_id: int) -> bool:
        """Remove a associação entre o usuário e o filme."""
        cursor = self.connection.execute(
            "DELETE FROM user_movies WHERE user_id = ? AND movie_id = ?",
            (user_id, movie_id),
        )
        self.connection.commit()
        # rowcount > 0 confirma se algo realmente foi apagado (permite ao
        # service, por exemplo, retornar 404 se nada existia para remover)
        return cursor.rowcount > 0

    def get_by_user_and_movie(self, user_id: int, movie_id: int):
        """Retorna o registro específico de um filme salvo por um usuário."""
        # JOIN junta os dados do filme (tabela movies) com os dados da
        # relação usuário-filme (status, nota, review) em uma única linha
        return self.connection.execute(
            """
            SELECT movies.*,
                   user_movies.status,
                   user_movies.rating,
                   user_movies.review,
                   user_movies.favorite,
                   user_movies.watched_at
            FROM user_movies
            JOIN movies ON movies.id = user_movies.movie_id
            WHERE user_movies.user_id = ? AND user_movies.movie_id = ?
            """,
            (user_id, movie_id),
        ).fetchone()

    def list_for_profile(
        self,
        user_id: int,
        status: Optional[str] = None,
        favorite: Optional[bool] = None,
        limit: Optional[int] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
    ):
        """Lista os filmes do usuário com filtros opcionais de status, favorito ou data.

        `since` e `until` (formato `AAAA-MM-DD`) restringem o resultado a uma janela
        de datas, comparando a data efetiva de cada registro — a data em que o filme
        foi assistido (`watched_at`) ou, na sua ausência, a data da última alteração
        (`updated_at`). São limites inclusivos, o que permite excluir tanto registros
        antigos quanto datas inválidas no futuro.
        """
        query = """
            SELECT movies.*,
                   user_movies.status,
                   user_movies.rating,
                   user_movies.review,
                   user_movies.favorite,
                   user_movies.watched_at
            FROM user_movies
            JOIN movies ON movies.id = user_movies.movie_id
            WHERE user_movies.user_id = ?
        """
        parameters = [user_id]

        # A query é construída dinamicamente: cada filtro só é adicionado
        # ao SQL se o parâmetro correspondente foi de fato informado.
        # Isso evita ter que escrever uma consulta separada para cada
        # combinação possível de filtros (status, favorito, ambos, nenhum).
        if status:
            query += " AND user_movies.status = ?"
            parameters.append(status)

        if favorite is not None:
            query += " AND user_movies.favorite = ?"
            parameters.append(int(bool(favorite)))

        # Compara apenas a parte de data para lidar com `watched_at` (AAAA-MM-DD)
        # e `updated_at` (timestamp ISO completo) no mesmo critério.
        effective_date = "substr(COALESCE(user_movies.watched_at, user_movies.updated_at), 1, 10)"

        if since:
            query += f" AND {effective_date} >= ?"
            parameters.append(since)

        if until:
            query += f" AND {effective_date} <= ?"
            parameters.append(until)

        query += " ORDER BY COALESCE(user_movies.watched_at, user_movies.updated_at) DESC"

        if limit:
            query += " LIMIT ?"
            parameters.append(limit)

        return self.connection.execute(query, parameters).fetchall()

    def statistics(self, user_id: int):
        """Calcula estatísticas agregadas (filmes assistidos, média de avaliação, reviews)."""
        # FILTER (WHERE ...) é uma extensão SQL que permite aplicar um filtro
        # dentro de uma função agregada específica — assim COUNT(*), por
        # exemplo, conta só as linhas que batem com a condição do FILTER,
        # tudo em uma única consulta (sem precisar de 3 SELECTs separados)
        return self.connection.execute(
            """
            SELECT
                COUNT(*) FILTER (WHERE status = 'WATCHED') AS watched_count,
                ROUND(AVG(rating), 1) AS average_rating,
                COUNT(*) FILTER (WHERE review IS NOT NULL AND TRIM(review) != '') AS review_count
            FROM user_movies
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()
