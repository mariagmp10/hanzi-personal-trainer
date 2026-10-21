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
    user_columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)")}
    if "is_admin" not in user_columns:
        conn.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0")
        # La cuenta más antigua es la tuya (creada antes de que existieran
        # los límites de uso): se marca como administradora, exenta de ellos.
        conn.execute("UPDATE users SET is_admin = 1 WHERE id = (SELECT MIN(id) FROM users)")
    if "lookup_uses" not in user_columns:
        conn.execute("ALTER TABLE users ADD COLUMN lookup_uses INTEGER NOT NULL DEFAULT 0")
    if "photo_uses" not in user_columns:
        conn.execute("ALTER TABLE users ADD COLUMN photo_uses INTEGER NOT NULL DEFAULT 0")
    if "hsk_batch_uses" not in user_columns:
        conn.execute("ALTER TABLE users ADD COLUMN hsk_batch_uses INTEGER NOT NULL DEFAULT 0")
    if "sentence_uses" not in user_columns:
        conn.execute("ALTER TABLE users ADD COLUMN sentence_uses INTEGER NOT NULL DEFAULT 0")

    columns = {row["name"] for row in conn.execute("PRAGMA table_info(characters)")}
    if "familiarity" not in columns:
        conn.execute("ALTER TABLE characters ADD COLUMN familiarity INTEGER NOT NULL DEFAULT 0")
    if "explanation" not in columns:
        conn.execute("ALTER TABLE characters ADD COLUMN explanation TEXT")
    if "mnemonic" not in columns:
        conn.execute("ALTER TABLE characters ADD COLUMN mnemonic TEXT")
    if "user_id" not in columns:
        conn.execute("ALTER TABLE characters ADD COLUMN user_id INTEGER REFERENCES users(id)")

    settings_columns = {row["name"] for row in conn.execute("PRAGMA table_info(settings)")}
    if "user_id" not in settings_columns:
        conn.execute("ALTER TABLE settings ADD COLUMN user_id INTEGER REFERENCES users(id)")

    # La tabla settings original tenía "id INTEGER PRIMARY KEY CHECK (id = 1)"
    # (una sola fila global, de antes de que existieran las cuentas). Ahora
    # hace falta una fila por usuario, lo que choca con ese CHECK. SQLite no
    # permite quitar un CHECK con ALTER TABLE, así que si sigue ahí se
    # recrea la tabla entera, conservando los datos ya migrados a user_id.
    settings_sql = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'settings'"
    ).fetchone()["sql"]
    if settings_sql and "CHECK" in settings_sql:
        conn.execute("ALTER TABLE settings RENAME TO settings_old")
        conn.execute(
            "CREATE TABLE settings (user_id INTEGER PRIMARY KEY REFERENCES users(id), "
            "hsk_level INTEGER NOT NULL DEFAULT 3)"
        )
        conn.execute(
            "INSERT INTO settings (user_id, hsk_level) "
            "SELECT user_id, hsk_level FROM settings_old WHERE user_id IS NOT NULL"
        )
        conn.execute("DROP TABLE settings_old")


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection()
    try:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        _migrate(conn)
        conn.commit()
    finally:
        conn.close()
