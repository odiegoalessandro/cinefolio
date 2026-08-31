from server.repositories.user_movie_repository import UserMovieRepository

STATUSES = ("WATCHING", "WATCHED", "PLAN_TO_WATCH", "DROPPED")


def row_data(row):
    return dict(row) if row else None


class ProfileService:
    def __init__(self, users, user_movies):
        self.users = users
        self.user_movies = user_movies

    def public_profile(self, username):
        user = self.users.get_by_username(username)
        if not user:
            return None
        data = row_data(user)
        sections = {"favorites": self.user_movies.list_for_profile(user["id"], favorite=True, limit=6), "recently_watched": self.user_movies.list_for_profile(user["id"], status="WATCHED", limit=6)}
        for status in STATUSES:
            sections[status.lower()] = self.user_movies.list_for_profile(user["id"], status=status)
        data["stats"] = row_data(self.user_movies.statistics(user["id"])) or {}
        data["sections"] = {name: [row_data(movie) for movie in movies] for name, movies in sections.items()}
        data.pop("password_hash", None)
        return data
