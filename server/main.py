"""Ponto de entrada do servidor HTTP do Cinefolio."""

from functools import partial
from http.server import ThreadingHTTPServer

from server.config import ServerConfig
from server.database.connection import (
    DEFAULT_DATABASE,
    initialize_database,
)
from server.http_handler import AppHandler
from server.services.avatar_mutation_coordinator import AvatarMutationCoordinator


def create_server(
    config: ServerConfig,
    database_path=DEFAULT_DATABASE,
    avatar_upload_directory=None,
) -> ThreadingHTTPServer:
    """Cria o servidor HTTP com as dependências necessárias ao handler."""
    avatar_mutation_coordinator = AvatarMutationCoordinator()
    handler_factory = partial(
        AppHandler,
        database_path=database_path,
        tmdb_token=config.tmdb_bearer_token,
        avatar_upload_directory=avatar_upload_directory,
        avatar_mutation_coordinator=avatar_mutation_coordinator,
    )
    return ThreadingHTTPServer((config.host, config.port), handler_factory)


def main():
    """Carrega a configuração e mantém o servidor ativo até a interrupção."""
    config = ServerConfig.load()
    if config.env_file_loaded:
        print("Arquivo .env carregado com sucesso.")

    initialize_database()
    server = create_server(config)
    host, port = server.server_address[:2]

    print(f"Cinefolio disponível em http://{host}:{port}")
    print("Pressione Ctrl+C para encerrar o servidor.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrando servidor Cinefolio...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
