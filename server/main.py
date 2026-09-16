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
    # Um único coordinator é compartilhado entre TODAS as requisições/threads
    # do servidor (por isso é criado aqui, fora do handler, e passado adiante) —
    # ele é o que garante exclusão mútua nas mutações de avatar (ver
    # avatar_mutation_coordinator.py)
    avatar_mutation_coordinator = AvatarMutationCoordinator()
    # functools.partial "pré-configura" a classe AppHandler com esses
    # argumentos extras, porque o ThreadingHTTPServer, internamente, cria
    # uma instância de handler por conta própria a cada conexão,
    # chamando-a só com os argumentos padrão de socket
    handler_factory = partial(
        AppHandler,
        database_path=database_path,
        tmdb_token=config.tmdb_bearer_token,
        avatar_upload_directory=avatar_upload_directory,
        avatar_mutation_coordinator=avatar_mutation_coordinator,
    )
    # ThreadingHTTPServer atende cada requisição em uma thread separada,
    # permitindo múltiplos usuários simultâneos sem bloquear uns aos outros
    return ThreadingHTTPServer((config.host, config.port), handler_factory)


def main():
    """Carrega a configuração e mantém o servidor ativo até a interrupção."""
    config = ServerConfig.load()
    if config.env_file_loaded:
        print("Arquivo .env carregado com sucesso.")

    initialize_database()# garante que as tabelas existem antes de aceitar requisições
    server = create_server(config)
    host, port = server.server_address[:2]

    print(f"Cinefolio disponível em http://{host}:{port}")
    print("Pressione Ctrl+C para encerrar o servidor.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        # Ctrl+C gera essa exceção: é tratada aqui para encerrar de forma
        # limpa em vez de mostrar um traceback de erro assustador ao usuário
        print("\nEncerrando servidor Cinefolio...")
    finally:
        server.server_close()   # libera a porta do sistema operacional


if __name__ == "__main__":
    main()
