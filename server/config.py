"""Configuração de inicialização do servidor Cinefolio."""

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ENV_FILE = PROJECT_ROOT / ".env"


@dataclass(frozen=True)
class ServerConfig:
    """Configuração imutável carregada do ambiente local."""

    host: str
    port: int

    @classmethod
    def load(cls, env_file: Path = DEFAULT_ENV_FILE) -> "ServerConfig":
        cls._load_environment(env_file)
        return cls(
            host=os.environ.get("HOST", "127.0.0.1"),
            port=int(os.environ.get("PORT", "8000")),
        )

    @staticmethod
    def _load_environment(env_file: Path) -> None:
        path = Path(env_file)
        if not path.exists():
            return

        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            key, separator, value = line.partition("=")
            key = key.strip()
            if separator and key:
                os.environ.setdefault(
                    key,
                    value.strip().strip('"').strip("'"),
                )
