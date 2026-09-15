"""Serviço de agregação de perfil público e estatísticas de filmes."""

from datetime import datetime, timedelta, timezone

STATUSES = ("WATCHING", "WATCHED", "PLAN_TO_WATCH", "DROPPED")
RECENTLY_WATCHED_WINDOW_DAYS = 7


def row_to_dict(row):
    """Converte um objeto sqlite3.Row em dicionário Python padrão."""
    return dict(row) if row else None


def recently_watched_window() -> tuple:
    """Retorna os limites inclusivos (AAAA-MM-DD) da janela de assistidos recentemente.

    O limite superior é a data UTC de hoje: um filme marcado agora sem data
    informada recai em `updated_at`, que também é UTC, e portanto nunca é
    excluído pela borda.
    """
    today = datetime.now(timezone.utc).date()
    return (
        (today - timedelta(days=RECENTLY_WATCHED_WINDOW_DAYS)).isoformat(),
        today.isoformat(),
    )


class ProfileService:
    """Camada de serviço para consulta e composição dos perfis públicos."""

    def __init__(self, user_repository, user_movie_repository):
        self.users = user_repository
        self.user_movies = user_movie_repository

    def public_profile(self, username: str):
        """Retorna o perfil público completo do usuário com coleções e estatísticas."""
        user = self.users.get_by_username((username or "").strip().lower())
        if not user:
            return None

        data = row_to_dict(user)
        user_id = user["id"]

        # "Assistidos Recentemente" cobre apenas os últimos 7 dias; fora da
        # janela o filme continua em "Todos os Assistidos", mas não aqui.
        recently_watched_since, recently_watched_until = recently_watched_window()

        # Agrupamentos de filmes
        sections = {
            "favorites": self.user_movies.list_for_profile(user_id, favorite=True, limit=6),
            "recently_watched": self.user_movies.list_for_profile(
                user_id,
                status="WATCHED",
                limit=6,
                since=recently_watched_since,
                until=recently_watched_until,
            ),
        }

        for status in STATUSES:
            sections[status.lower()] = self.user_movies.list_for_profile(user_id, status=status)

        data["stats"] = row_to_dict(self.user_movies.statistics(user_id)) or {
            "watched_count": 0,
            "average_rating": None,
            "review_count": 0,
        }
        data["sections"] = {
            name: [row_to_dict(movie) for movie in movies]
            for name, movies in sections.items()
        }

        # Remove dados sensíveis
        data.pop("password_hash", None)
        return data
