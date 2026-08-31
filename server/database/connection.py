import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE = ROOT / "cinefolio.sqlite3"
SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def get_connection(database_path=DEFAULT_DATABASE):
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(database_path=DEFAULT_DATABASE):
    with get_connection(database_path) as connection:
        connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
