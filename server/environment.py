"""Leitura segura do arquivo .env para o processo do servidor."""

import os
import re
from collections.abc import MutableMapping
from dataclasses import dataclass
from pathlib import Path

# Regex que valida nomes de variável de ambiente: precisa começar com
# letra ou "_", seguido de letras, números ou "_" (padrão POSIX).
ENVIRONMENT_VARIABLE_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*$")

# Regex para detectar e remover o prefixo "export " no início da linha,
# comum em arquivos .env que também podem ser "sourceados" no shell (bash).
EXPORT_PREFIX = re.compile(r"export\s+")



@dataclass(frozen=True)
class EnvironmentLoadResult:
    """Resultado da leitura do arquivo de ambiente, sem expor valores sensíveis.

    Guarda só METADADOS (se carregou, quais chaves) e não os valores em si,
    porque esses valores podem conter segredos (ex: token de API) que não
    devem aparecer em logs por engano.
    """
    file_loaded: bool   # True se o arquivo .env foi encontrado e lido
    loaded_keys: tuple[str, ...]    # nomes das variáveis que foram carregadas


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
        # Não é um erro: o .env é opcional (ex: em produção as variáveis já
        # podem vir configuradas diretamente no sistema operacional).
        return EnvironmentLoadResult(file_loaded=False, loaded_keys=())

    # Permite injetar um dicionário de ambiente customizado (útil em testes),
    # senão usa o ambiente real do processo (os.environ).
    target_environment = os.environ if environ is None else environ
    loaded_keys: list[str] = []

    # "utf-8-sig" remove automaticamente o BOM (marca de início de arquivo)
    # que alguns editores (como o Bloco de Notas do Windows) inserem.
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8-sig").splitlines(),
        start=1,
    ):
        assignment = _parse_assignment(raw_line, line_number)
        if assignment is None:
            # Linha em branco, comentário, ou algo ignorável: pula para a próxima.
            continue

        key, value = assignment
        if target_environment.get(key):
            # Já existe um valor não-vazio definido (ex: passado na linha de
            # comando). Esse valor "de fora" tem prioridade sobre o .env.
            continue

        target_environment[key] = value
        loaded_keys.append(key)

    return EnvironmentLoadResult(
        file_loaded=True,
        loaded_keys=tuple(loaded_keys),
    )


def _parse_assignment(raw_line: str, line_number: int) -> tuple[str, str] | None:
    """Interpreta uma linha do .env no formato CHAVE=valor.

    Retorna None se a linha deve ser ignorada (vazia ou comentário).
    Levanta ValueError se a linha estiver em um formato inválido.
    """
    line = raw_line.strip()
    if not line or line.startswith("#"):
        return None

    # Remove um possível "export " no começo (ex: `export PORT=8000`)
    export_prefix = EXPORT_PREFIX.match(line)
    if export_prefix:
        line = line[export_prefix.end() :]

    # Divide a linha em CHAVE e VALOR pelo primeiro "="
    key, separator, raw_value = line.partition("=")
    key = key.strip()
    if not separator or not ENVIRONMENT_VARIABLE_NAME.fullmatch(key):
        # Sem "=" na linha, ou nome de variável em formato inválido
        raise ValueError(f"Formato inválido no arquivo .env na linha {line_number}.")

    return key, _parse_value(raw_value.strip(), line_number)


def _parse_value(raw_value: str, line_number: int) -> str:
    if not raw_value or raw_value[0] not in {"\"", "'"}:
        # Valor sem aspas: corta fora um comentário inline (ex: `PORT=8000 # porta`)
        # e remove espaços em branco à direita.
        return re.split(r"\s+#", raw_value, maxsplit=1)[0].rstrip()

    # Valor entre aspas (simples ou duplas): preserva o conteúdo literal,
    # incluindo espaços, permitindo valores como "meu valor com espaço"
    quote = raw_value[0]
    closing_quote = raw_value.rfind(quote)
    if closing_quote == 0:
        # Só achou a aspa de abertura, não uma de fechamento
        raise ValueError(f"Aspas não fechadas no arquivo .env na linha {line_number}.")

    # Depois da aspa de fechamento só pode vir espaço em branco ou comentário
    trailing_content = raw_value[closing_quote + 1 :].strip()
    if trailing_content and not trailing_content.startswith("#"):
        raise ValueError(f"Valor inválido no arquivo .env na linha {line_number}.")

    return raw_value[1:closing_quote]   # conteúdo entre as aspas, sem elas
