"""Cuentas de usuario, muy simples: usuario + contraseña (hash con bcrypt) y
sesión guardada en una cookie httponly. Sin librerías externas de auth ni
JWT — para el tamaño de esta app (tú + algún amigo puntual) una tabla
`sessions` en SQLite es más que suficiente y mucho más fácil de entender.
"""

import os
import secrets
import sqlite3
from datetime import datetime, timezone

import bcrypt
from fastapi import HTTPException, Request

SESSION_COOKIE = "session_token"


def check_invite_code(code: str) -> None:
    """Si hay un SIGNUP_INVITE_CODE configurado en el .env, exige que
    coincida para poder crear una cuenta nueva. Sin esa variable, cualquiera
    puede registrarse (cómodo en desarrollo local; se recomienda ponerla
    antes de compartir la app fuera de tu red)."""
    required_code = os.environ.get("SIGNUP_INVITE_CODE")
    if required_code and code != required_code:
        raise HTTPException(status_code=403, detail="Código de invitación incorrecto")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_session(conn: sqlite3.Connection, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    conn.execute(
        "INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)",
        (token, user_id, datetime.now(timezone.utc).isoformat()),
    )
    return token


def get_current_user_id(request: Request) -> int:
    return get_current_user(request)["id"]


def get_current_user(request: Request) -> sqlite3.Row:
    """Devuelve la fila completa de users (id, is_admin, contadores de uso...).
    Se usa en vez de get_current_user_id cuando un endpoint necesita
    comprobar límites de uso (ver NON_ADMIN_LIMITS en app/main.py)."""
    from app.db import get_connection  # import tardío para evitar import circular

    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="No has iniciado sesión")
    conn = get_connection()
    try:
        session_row = conn.execute("SELECT user_id FROM sessions WHERE token = ?", (token,)).fetchone()
        if session_row is None:
            raise HTTPException(status_code=401, detail="Sesión no válida, inicia sesión de nuevo")
        user_row = conn.execute("SELECT * FROM users WHERE id = ?", (session_row["user_id"],)).fetchone()
        if user_row is None:
            raise HTTPException(status_code=401, detail="Sesión no válida, inicia sesión de nuevo")
        return user_row
    finally:
        conn.close()
