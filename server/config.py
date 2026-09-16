"""Configuração de inicialização do servidor Cinefolio."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from server.environment import load_environment

# Diretório raiz do projeto (duas pastas acima deste arquivo: server/config.py -> server/ -> raiz)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
# Caminho padrão esperado para o arquivo .env, na raiz do projeto
DEFAULT_ENV_FILE = PROJECT_ROOT / ".env"


@dataclass(frozen=True)
class ServerConfig:
    """Configuração imutável carregada do ambiente local.

    "frozen=True" torna os atributos somente leitura depois de criados,
    evitando que a configuração seja alterada por engano em outro lugar do código.
    """

    host: str   # endereço onde o servidor vai escutar (ex: 127.0.0.1)
    port: int   # porta do servidor (ex: 8000)
    tmdb_bearer_token: str = field(default="", repr=False)
        # token de autenticação da API do TMDB (The Movie Database).
        # repr=False evita que o token apareça se alguém der print() no objeto,
        # protegendo o segredo contra vazamento acidental em logs.
    env_file_loaded: bool = False   # indica se um arquivo .env foi encontrado e lido

    @classmethod
    def load(cls, env_file: Path = DEFAULT_ENV_FILE) -> "ServerConfig":
        """Monta a configuração final combinando o .env com as variáveis do sistema."""
        # Primeiro carrega o .env (se existir) para dentro das variáveis de ambiente do processo
        result = load_environment(env_file)
        # Depois lê cada valor final de os.environ, já com .env e sistema combinados,
        # aplicando valores padrão (fallback) quando a variável não estiver definida
        return cls(
            host=os.environ.get("HOST", "127.0.0.1"),
            port=int(os.environ.get("PORT", "8000")),
            tmdb_bearer_token=os.environ.get("TMDB_BEARER_TOKEN", ""),
            env_file_loaded=result.file_loaded,
        )
