"""Controlador responsável pelas operações de catálogo e gerenciamento de filmes no perfil."""


def validate_movie_payload(data: dict) -> dict:
    """Valida os dados recebidos para salvar ou atualizar um filme no perfil."""
    allowed_fields = {"status", "rating", "review", "favorite", "watched_at"}
    extra_fields = set(data.keys()) - allowed_fields

    if extra_fields or "status" not in data:
        raise ValueError("Dados de filme inválidos.")

    status = data.get("status")
    if status not in ("WATCHING", "WATCHED", "PLAN_TO_WATCH", "DROPPED"):
        raise ValueError("Status de filme inválido.")

    rating = data.get("rating")
    if rating is not None and rating != "":
        try:
            rating = float(rating)
            if not (0 <= rating <= 10):
                raise ValueError()
        except ValueError:
            raise ValueError("A nota deve ser um número entre 0 e 10.")
    else:
        rating = None

    review = data.get("review")
    if review is not None:
        review = str(review).strip()
        if len(review) > 5000:
            raise ValueError("A review não pode exceder 5000 caracteres.")
        if not review:
            review = None

    favorite = bool(data.get("favorite", False))
    watched_at = data.get("watched_at") or None

    return {
        "status": status,
        "rating": rating,
        "review": review,
        "favorite": favorite,
        "watched_at": watched_at,
    }


class MovieController:
    """Controlador para manipulação de filmes e catálogo."""

    def __init__(self, tmdb_service, movie_repository, user_movie_repository):
        self.tmdb_service = tmdb_service
        self.movie_repository = movie_repository
        self.user_movie_repository = user_movie_repository

    def search(self, query: str) -> dict:
        """Busca filmes por título no catálogo."""
        results = self.tmdb_service.search(query)
        return {"results": results}

    def popular(self) -> dict:
        """Retorna os filmes populares da semana."""
        results = self.tmdb_service.popular()
        return {"results": results}

    def details(self, tmdb_id: str, current_user: dict = None) -> dict:
        """Retorna os detalhes de um filme e, caso o usuário esteja logado, o status salvo."""
        movie_data = self.tmdb_service.details(tmdb_id)

        user_status = None
        if current_user:
            local_movie = self.movie_repository.get_by_tmdb_id(movie_data["tmdb_id"])
            if local_movie:
                saved = self.user_movie_repository.get_by_user_and_movie(
                    current_user["id"],
                    local_movie["id"],
                )
                if saved:
                    user_status = {
                        "status": saved["status"],
                        "rating": saved["rating"],
                        "review": saved["review"],
                        "favorite": bool(saved["favorite"]),
                        "watched_at": saved["watched_at"],
                    }

        movie_data["user_status"] = user_status
        return {"movie": movie_data}

    def save_to_profile(self, tmdb_id: str, current_user: dict, payload: dict) -> dict:
        """Associa ou atualiza um filme no perfil do usuário autenticado (Create/Update)."""
        if not current_user:
            raise PermissionError("Autenticação necessária.")

        # Obtém metadados da TMDB e garante inserção na tabela `movies`
        movie_details = self.tmdb_service.details(tmdb_id)
        local_movie = self.movie_repository.upsert(movie_details)

        # Valida os dados de avaliação
        validated = validate_movie_payload(payload)

        # Salva na tabela associativa `user_movies`
        self.user_movie_repository.upsert(
            user_id=current_user["id"],
            movie_id=local_movie["id"],
            **validated,
        )
        return {"ok": True, "message": "Filme salvo com sucesso no seu perfil."}

    def remove_from_profile(self, tmdb_id: str, current_user: dict) -> dict:
        """Remove a associação do filme com o perfil do usuário (Delete)."""
        if not current_user:
            raise PermissionError("Autenticação necessária.")

        local_movie = self.movie_repository.get_by_tmdb_id(int(tmdb_id))
        if not local_movie:
            return {"removed": False}

        removed = self.user_movie_repository.remove(
            user_id=current_user["id"],
            movie_id=local_movie["id"],
        )
        return {"removed": removed}
