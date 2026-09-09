"""Composição das dependências usadas pela aplicação HTTP."""

from pathlib import Path

from server.controllers.account_controller import AccountController
from server.controllers.auth_controller import AuthController
from server.controllers.avatar_controller import AvatarController
from server.controllers.movie_controller import MovieController
from server.controllers.profile_controller import ProfileController
from server.repositories.movie_repository import MovieRepository
from server.repositories.user_movie_repository import UserMovieRepository
from server.repositories.user_repository import UserRepository
from server.router import Router
from server.services.auth_service import AuthService
from server.services.avatar_service import AvatarService
from server.services.avatar_storage import AvatarStorage
from server.services.profile_service import ProfileService
from server.services.tmdb_service import TmdbService


def create_router(
    connection,
    avatar_upload_directory: Path,
    avatar_mutation_coordinator,
    tmdb_token: str | None = None,
) -> Router:
    """Monta o grafo de dependências e devolve um roteador pronto para despachar."""
    user_repository = UserRepository(connection)
    movie_repository = MovieRepository(connection)
    user_movie_repository = UserMovieRepository(connection)

    auth_service = AuthService(user_repository)
    profile_service = ProfileService(user_repository, user_movie_repository)
    tmdb_service = TmdbService(token=tmdb_token)
    avatar_service = AvatarService(
        user_repository,
        AvatarStorage(avatar_upload_directory),
        avatar_mutation_coordinator,
    )

    return Router(
        auth_controller=AuthController(auth_service),
        movie_controller=MovieController(
            tmdb_service,
            movie_repository,
            user_movie_repository,
        ),
        profile_controller=ProfileController(profile_service, user_repository),
        avatar_controller=AvatarController(avatar_service),
        account_controller=AccountController(avatar_service),
        current_user_resolver=auth_service.current_user,
    )
