"""Módulo de conexão e inicialização do banco de dados SQLite."""

import sqlite3
from pathlib import Path

# Diretórios base
ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE = ROOT_DIR / "cinefolio.sqlite3"
SCHEMA_PATH = ROOT_DIR / "server" / "schema.sql"


def get_connection(database_path=DEFAULT_DATABASE):
    """Cria e retorna uma conexão SQLite configurada."""
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    return connection


def initialize_database(database_path=DEFAULT_DATABASE):
    """Executa o script DDL para criar tabelas e índices caso não existam."""
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    connection = get_connection(database_path)
    try:
        connection.executescript(schema_sql)
    finally:
        connection.close()
