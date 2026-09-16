"""Módulo de conexão e inicialização do banco de dados SQLite."""

import sqlite3
from pathlib import Path

# Diretórios base
# __file__ = .../server/database/connection.py
# parents[0] = server/database, parents[1] = server, parents[2] = raiz do projeto
ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE = ROOT_DIR / "cinefolio.sqlite3"   # arquivo físico do banco SQLite
SCHEMA_PATH = ROOT_DIR / "server" / "schema.sql"    # script DDL com CREATE TABLE etc.


def get_connection(database_path=DEFAULT_DATABASE):
    """Cria e retorna uma conexão SQLite configurada."""
    connection = sqlite3.connect(database_path)
    # row_factory = sqlite3.Row permite acessar as colunas do resultado
    # pelo nome (ex: linha["username"]) em vez de só por índice numérico,
    # deixando o código dos repositórios muito mais legível.
    connection.row_factory = sqlite3.Row
    # Cada nova conexão SQLite vem com FOREIGN KEY desligado por padrão,
    # então isso precisa ser reforçado aqui também (além do schema.sql),
    # senão o ON DELETE CASCADE das tabelas não funcionaria.
    connection.execute("PRAGMA foreign_keys = ON;")
    return connection


def initialize_database(database_path=DEFAULT_DATABASE):
    """Executa o script DDL para criar tabelas e índices caso não existam."""
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    connection = get_connection(database_path)
    try:
        # executescript roda várias instruções SQL de uma vez (separadas por ";"),
        # diferente de execute() que roda só uma instrução.
        # Como as tabelas usam "CREATE TABLE IF NOT EXISTS", é seguro chamar
        # essa função toda vez que o servidor iniciar.
        connection.executescript(schema_sql)
    finally:
        # Garante que a conexão é fechada mesmo se executescript falhar
        connection.close()
