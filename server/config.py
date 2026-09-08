"""Configuração de inicialização do servidor Cinefolio."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from server.environment import load_environment


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ENV_FILE = PROJECT_ROOT / ".env"


@dataclass(frozen=True)
class ServerConfig:
    """Configuração imutável carregada do ambiente local."""

    host: str
    port: int
    tmdb_bearer_token: str = field(default="", repr=False)
    env_file_loaded: bool = False

    @classmethod
    def load(cls, env_file: Path = DEFAULT_ENV_FILE) -> "ServerConfig":
        result = load_environment(env_file)
        return cls(
            host=os.environ.get("HOST", "127.0.0.1"),
            port=int(os.environ.get("PORT", "8000")),
            tmdb_bearer_token=os.environ.get("TMDB_BEARER_TOKEN", ""),
            env_file_loaded=result.file_loaded,
        )
