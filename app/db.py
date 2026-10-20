import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "db" / "hanzi_trainer.db"
SCHEMA_PATH = PROJECT_ROOT / "db" / "schema.sql"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    """Ajustes a tablas ya existentes que 'CREATE TABLE IF NOT EXISTS' no cubre."""
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(characters)")}
    if "familiarity" not in columns:
        conn.execute("ALTER TABLE characters ADD COLUMN familiarity INTEGER NOT NULL DEFAULT 0")
    if "explanation" not in columns:
        conn.execute("ALTER TABLE characters ADD COLUMN explanation TEXT")
    if "mnemonic" not in columns:
        conn.execute("ALTER TABLE characters ADD COLUMN mnemonic TEXT")


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection()
    try:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        _migrate(conn)
        conn.commit()
    finally:
        conn.close()
