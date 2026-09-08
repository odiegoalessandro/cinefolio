"""Leitura segura do arquivo .env para o processo do servidor."""

import os
import re
from collections.abc import MutableMapping
from dataclasses import dataclass
from pathlib import Path


ENVIRONMENT_VARIABLE_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*$")
EXPORT_PREFIX = re.compile(r"export\s+")


@dataclass(frozen=True)
class EnvironmentLoadResult:
    """Resultado da leitura do arquivo de ambiente, sem expor valores sensíveis."""

    file_loaded: bool
    loaded_keys: tuple[str, ...]


def load_environment(
    env_file: Path,
    environ: MutableMapping[str, str] | None = None,
) -> EnvironmentLoadResult:
    """Carrega variáveis de um .env no ambiente do processo.

    Variáveis não vazias já definidas no processo têm precedência sobre o
    arquivo. Valores vazios são preenchidos pelo .env para evitar que uma
    configuração vazia do ambiente impeça a inicialização local.
    """
    path = Path(env_file)
    if not path.exists():
        return EnvironmentLoadResult(file_loaded=False, loaded_keys=())

    target_environment = os.environ if environ is None else environ
    loaded_keys: list[str] = []

    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8-sig").splitlines(),
        start=1,
    ):
        assignment = _parse_assignment(raw_line, line_number)
        if assignment is None:
            continue

        key, value = assignment
        if target_environment.get(key):
            continue

        target_environment[key] = value
        loaded_keys.append(key)

    return EnvironmentLoadResult(
        file_loaded=True,
        loaded_keys=tuple(loaded_keys),
    )


def _parse_assignment(raw_line: str, line_number: int) -> tuple[str, str] | None:
    line = raw_line.strip()
    if not line or line.startswith("#"):
        return None

    export_prefix = EXPORT_PREFIX.match(line)
    if export_prefix:
        line = line[export_prefix.end() :]

    key, separator, raw_value = line.partition("=")
    key = key.strip()
    if not separator or not ENVIRONMENT_VARIABLE_NAME.fullmatch(key):
        raise ValueError(f"Formato inválido no arquivo .env na linha {line_number}.")

    return key, _parse_value(raw_value.strip(), line_number)


def _parse_value(raw_value: str, line_number: int) -> str:
    if not raw_value or raw_value[0] not in {"\"", "'"}:
        return re.split(r"\s+#", raw_value, maxsplit=1)[0].rstrip()

    quote = raw_value[0]
    closing_quote = raw_value.rfind(quote)
    if closing_quote == 0:
        raise ValueError(f"Aspas não fechadas no arquivo .env na linha {line_number}.")

    trailing_content = raw_value[closing_quote + 1 :].strip()
    if trailing_content and not trailing_content.startswith("#"):
        raise ValueError(f"Valor inválido no arquivo .env na linha {line_number}.")

    return raw_value[1:closing_quote]
