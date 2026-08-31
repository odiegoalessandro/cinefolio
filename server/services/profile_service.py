"""Serviço de agregação de perfil público e estatísticas de filmes."""

STATUSES = ("WATCHING", "WATCHED", "PLAN_TO_WATCH", "DROPPED")


def row_to_dict(row):
    """Converte um objeto sqlite3.Row em dicionário Python padrão."""
    return dict(row) if row else None


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

        # Agrupamentos de filmes
        sections = {
            "favorites": self.user_movies.list_for_profile(user_id, favorite=True, limit=6),
            "recently_watched": self.user_movies.list_for_profile(user_id, status="WATCHED", limit=6),
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
