import json
import random
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional

import anthropic
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, Response, UploadFile
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ai.vocab_ai import (
    AIResponseError,
    explain_character,
    extract_from_photo,
    generate_hsk_batch,
    generate_sentence,
    lookup_word,
)
from app.auth import SESSION_COOKIE, create_session, get_current_user_id, hash_password, verify_password
from app.db import get_connection, init_db
from app.radicals import radical_meaning
from app.util import pinyin_plain

load_dotenv()

STATIC_DIR = Path(__file__).resolve().parent / "static"
MAX_VOCAB_FOR_SENTENCE = 60  # cuántas palabras conocidas se le pasan como contexto a la IA
SESSION_MAX_AGE = 60 * 60 * 24 * 365  # 1 año

app = FastAPI(title="Hanzi Trainer")


@app.on_event("startup")
def on_startup() -> None:
    init_db()


class CharacterIn(BaseModel):
    hanzi: str
    pinyin: str
    meaningEs: str
    meaningEn: str = ""
    hskLevel: Optional[int] = None
    radicals: list[str] = []
    notes: str = ""
    source: str = "manual"


class LookupIn(BaseModel):
    query: str


class SentenceIn(BaseModel):
    characterId: Optional[int] = None


class SettingsIn(BaseModel):
    hskLevel: int


class HskBatchIn(BaseModel):
    level: int
    excludeHanzi: list[str] = []


class MarkIn(BaseModel):
    known: bool


class SignupIn(BaseModel):
    username: str
    password: str


class LoginIn(BaseModel):
    username: str
    password: str


MAX_FAMILIARITY = 5  # a partir de aquí ya no sube más, pero sigue saliendo de vez en cuando


def character_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "hanzi": row["hanzi"],
        "pinyin": row["pinyin"],
        "pinyinPlain": row["pinyin_plain"],
        "meaningEs": row["meaning_es"],
        "meaningEn": row["meaning_en"] or "",
        "hskLevel": row["hsk_level"],
        "radicals": json.loads(row["radicals"]) if row["radicals"] else [],
        "notes": row["notes"] or "",
        "source": row["source"],
        "dateAdded": row["date_added"],
        "reviewCount": row["review_count"],
        "lastReviewedAt": row["last_reviewed_at"],
        "familiarity": row["familiarity"],
        "explanation": row["explanation"] or "",
        "mnemonic": row["mnemonic"] or "",
    }


MISSING_KEY_MESSAGE = (
    "Falta tu ANTHROPIC_API_KEY. Copia .env.example a .env en la carpeta del proyecto, "
    "añade tu clave de https://console.anthropic.com/ y reinicia el servidor."
)


def _run_ai(label: str, fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except AIResponseError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except anthropic.AuthenticationError as exc:
        raise HTTPException(status_code=502, detail=MISSING_KEY_MESSAGE) from exc
    except anthropic.APIError as exc:
        raise HTTPException(status_code=502, detail=f"Error llamando a la IA ({label}): {exc}") from exc
    except TypeError as exc:
        # anthropic lanza TypeError (no una excepción propia) cuando no encuentra
        # ninguna clave configurada en absoluto, antes incluso de hacer la llamada HTTP.
        if "authentication" in str(exc).lower() or "api_key" in str(exc).lower():
            raise HTTPException(status_code=502, detail=MISSING_KEY_MESSAGE) from exc
        raise


# ===================== AUTENTICACIÓN =====================
# Cuentas muy simples (usuario + contraseña con bcrypt) para que cada persona
# tenga su propio vocabulario. La sesión se guarda en una cookie httponly; no
# hay JWT ni librerías externas de auth, con una tabla "sessions" basta para
# este tamaño de app. Ver app/auth.py.


@app.post("/api/auth/signup", status_code=201)
def signup(payload: SignupIn, response: Response) -> dict[str, Any]:
    username = payload.username.strip()
    if not username or len(payload.password) < 4:
        raise HTTPException(status_code=400, detail="Usuario y contraseña (mínimo 4 caracteres) son obligatorios")
    conn = get_connection()
    try:
        existing = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if existing is not None:
            raise HTTPException(status_code=400, detail="Ese nombre de usuario ya existe")

        is_first_user = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"] == 0

        cur = conn.execute(
            "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
            (username, hash_password(payload.password), datetime.now(timezone.utc).isoformat()),
        )
        user_id = cur.lastrowid

        if is_first_user:
            # Reclama los datos que ya existían antes de que hubiera cuentas
            # (tu vocabulario guardado antes de añadir este sistema de login).
            conn.execute("UPDATE characters SET user_id = ? WHERE user_id IS NULL", (user_id,))
            conn.execute("UPDATE settings SET user_id = ? WHERE user_id IS NULL", (user_id,))

        if conn.execute("SELECT 1 FROM settings WHERE user_id = ?", (user_id,)).fetchone() is None:
            conn.execute("INSERT INTO settings (user_id, hsk_level) VALUES (?, 3)", (user_id,))

        token = create_session(conn, user_id)
        conn.commit()
        response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax", max_age=SESSION_MAX_AGE)
        return {"id": user_id, "username": username}
    finally:
        conn.close()


@app.post("/api/auth/login")
def login(payload: LoginIn, response: Response) -> dict[str, Any]:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (payload.username.strip(),)).fetchone()
        if row is None or not verify_password(payload.password, row["password_hash"]):
            raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
        token = create_session(conn, row["id"])
        conn.commit()
        response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax", max_age=SESSION_MAX_AGE)
        return {"id": row["id"], "username": row["username"]}
    finally:
        conn.close()


@app.post("/api/auth/logout", status_code=204)
def logout(request: Request, response: Response) -> None:
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        conn = get_connection()
        try:
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            conn.commit()
        finally:
            conn.close()
    response.delete_cookie(SESSION_COOKIE)


@app.get("/api/auth/me")
def me(user_id: int = Depends(get_current_user_id)) -> dict[str, Any]:
    conn = get_connection()
    try:
        row = conn.execute("SELECT id, username FROM users WHERE id = ?", (user_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=401, detail="Sesión no válida")
        return {"id": row["id"], "username": row["username"]}
    finally:
        conn.close()


# ===================== CARACTERES =====================


@app.get("/api/characters")
def list_characters(
    search: str = "", hskLevel: Optional[int] = None, user_id: int = Depends(get_current_user_id)
) -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        query = "SELECT * FROM characters WHERE user_id = ?"
        params: list[Any] = [user_id]
        if search:
            query += " AND (hanzi LIKE ? OR pinyin LIKE ? OR meaning_es LIKE ?)"
            like = f"%{search}%"
            params += [like, like, like]
        if hskLevel is not None:
            query += " AND hsk_level = ?"
            params.append(hskLevel)
        query += " ORDER BY date_added DESC"
        rows = conn.execute(query, params).fetchall()
        return [character_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def _insert_character(conn: sqlite3.Connection, character: CharacterIn, user_id: int) -> sqlite3.Row:
    cur = conn.execute(
        """INSERT INTO characters
           (user_id, hanzi, pinyin, pinyin_plain, meaning_es, meaning_en, hsk_level, radicals, notes, source,
            date_added)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            user_id, character.hanzi, character.pinyin, pinyin_plain(character.pinyin), character.meaningEs,
            character.meaningEn, character.hskLevel, json.dumps(character.radicals), character.notes,
            character.source, date.today().isoformat(),
        ),
    )
    return conn.execute("SELECT * FROM characters WHERE id = ?", (cur.lastrowid,)).fetchone()


@app.post("/api/characters", status_code=201)
def create_character(character: CharacterIn, user_id: int = Depends(get_current_user_id)) -> dict[str, Any]:
    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT * FROM characters WHERE user_id = ? AND hanzi = ? AND pinyin = ?",
            (user_id, character.hanzi, character.pinyin),
        ).fetchone()
        if existing is not None:
            return character_row_to_dict(existing)
        row = _insert_character(conn, character, user_id)
        conn.commit()
        return character_row_to_dict(row)
    finally:
        conn.close()


@app.put("/api/characters/{character_id}")
def update_character(
    character_id: int, character: CharacterIn, user_id: int = Depends(get_current_user_id)
) -> dict[str, Any]:
    conn = get_connection()
    try:
        cur = conn.execute(
            """UPDATE characters SET hanzi=?, pinyin=?, pinyin_plain=?, meaning_es=?, meaning_en=?,
               hsk_level=?, radicals=?, notes=? WHERE id=? AND user_id=?""",
            (
                character.hanzi, character.pinyin, pinyin_plain(character.pinyin), character.meaningEs,
                character.meaningEn, character.hskLevel, json.dumps(character.radicals), character.notes,
                character_id, user_id,
            ),
        )
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Carácter no encontrado")
        row = conn.execute("SELECT * FROM characters WHERE id = ?", (character_id,)).fetchone()
        return character_row_to_dict(row)
    finally:
        conn.close()


@app.delete("/api/characters/{character_id}", status_code=204)
def delete_character(character_id: int, user_id: int = Depends(get_current_user_id)) -> None:
    conn = get_connection()
    try:
        cur = conn.execute("DELETE FROM characters WHERE id = ? AND user_id = ?", (character_id, user_id))
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Carácter no encontrado")
    finally:
        conn.close()


@app.get("/api/characters/random")
def random_character(user_id: int = Depends(get_current_user_id)) -> dict[str, Any]:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM characters WHERE user_id = ?", (user_id,)).fetchall()
        if not rows:
            raise HTTPException(status_code=404, detail="Todavía no has añadido ningún carácter")
        # Cuanto menor es la familiaridad, más probable es que salga la tarjeta:
        # familiarity=0 pesa 1, familiarity=5 pesa 1/6. Así las que "te cuestan"
        # (o las nuevas) aparecen más a menudo que las que ya dices saberte.
        weights = [1 / (row["familiarity"] + 1) for row in rows]
        row = random.choices(rows, weights=weights, k=1)[0]
        conn.execute(
            "UPDATE characters SET review_count = review_count + 1, last_reviewed_at = ? WHERE id = ?",
            (date.today().isoformat(), row["id"]),
        )
        conn.commit()
        return character_row_to_dict(row)
    finally:
        conn.close()


@app.post("/api/characters/{character_id}/mark")
def mark_character(character_id: int, payload: MarkIn, user_id: int = Depends(get_current_user_id)) -> dict[str, Any]:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM characters WHERE id = ? AND user_id = ?", (character_id, user_id)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Carácter no encontrado")
        new_familiarity = min(row["familiarity"] + 1, MAX_FAMILIARITY) if payload.known else 0
        conn.execute("UPDATE characters SET familiarity = ? WHERE id = ?", (new_familiarity, character_id))
        conn.commit()
        row = conn.execute("SELECT * FROM characters WHERE id = ?", (character_id,)).fetchone()
        return character_row_to_dict(row)
    finally:
        conn.close()


@app.post("/api/characters/{character_id}/explain")
def explain_character_endpoint(character_id: int, user_id: int = Depends(get_current_user_id)) -> dict[str, Any]:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM characters WHERE id = ? AND user_id = ?", (character_id, user_id)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Carácter no encontrado")
        if row["explanation"] and row["mnemonic"]:
            # Ya se generó antes para este carácter: no gastamos otra llamada a la IA.
            return {"explanation": row["explanation"], "mnemonic": row["mnemonic"]}

        radicals = json.loads(row["radicals"]) if row["radicals"] else []
        radicals_with_meanings = [(r, radical_meaning(r)) for r in radicals]
        result = _run_ai(
            "explain", explain_character, row["hanzi"], row["pinyin"], row["meaning_es"], radicals_with_meanings
        )
        conn.execute(
            "UPDATE characters SET explanation = ?, mnemonic = ? WHERE id = ?",
            (result.get("explanation", ""), result.get("mnemonic", ""), character_id),
        )
        conn.commit()
        return result
    finally:
        conn.close()


@app.get("/api/characters/{character_id}/similar")
def similar_characters(character_id: int, user_id: int = Depends(get_current_user_id)) -> dict[str, Any]:
    conn = get_connection()
    try:
        target = conn.execute(
            "SELECT * FROM characters WHERE id = ? AND user_id = ?", (character_id, user_id)
        ).fetchone()
        if target is None:
            raise HTTPException(status_code=404, detail="Carácter no encontrado")
        target_radicals = json.loads(target["radicals"]) if target["radicals"] else []

        others = conn.execute(
            "SELECT * FROM characters WHERE id != ? AND user_id = ?", (character_id, user_id)
        ).fetchall()
        others_by_radical: dict[str, list[dict[str, Any]]] = {r: [] for r in target_radicals}
        by_pinyin = []
        for row in others:
            row_radicals = set(json.loads(row["radicals"]) if row["radicals"] else [])
            for r in target_radicals:
                if r in row_radicals:
                    others_by_radical[r].append(character_row_to_dict(row))
            if row["pinyin_plain"] == target["pinyin_plain"]:
                by_pinyin.append(character_row_to_dict(row))

        return {
            "targetRadicals": [{"radical": r, "meaning": radical_meaning(r)} for r in target_radicals],
            "byRadical": [
                {"radical": r, "meaning": radical_meaning(r), "characters": chars}
                for r, chars in others_by_radical.items()
                if chars
            ],
            "byPinyin": by_pinyin,
        }
    finally:
        conn.close()


@app.post("/api/lookup")
def lookup(payload: LookupIn, user_id: int = Depends(get_current_user_id)) -> list[dict[str, Any]]:
    if not payload.query.strip():
        raise HTTPException(status_code=400, detail="Escribe algo para buscar")
    return _run_ai("lookup", lookup_word, payload.query.strip())


@app.post("/api/photo/extract")
async def photo_extract(file: UploadFile, user_id: int = Depends(get_current_user_id)) -> list[dict[str, Any]]:
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="La imagen está vacía")
    media_type = file.content_type or "image/jpeg"
    return _run_ai("photo", extract_from_photo, image_bytes, media_type)


@app.post("/api/hsk/batch")
def hsk_batch(payload: HskBatchIn, user_id: int = Depends(get_current_user_id)) -> list[dict[str, Any]]:
    return _run_ai("hsk-batch", generate_hsk_batch, payload.level, payload.excludeHanzi)


@app.post("/api/characters/bulk")
def bulk_create_characters(
    characters: list[CharacterIn], user_id: int = Depends(get_current_user_id)
) -> dict[str, Any]:
    conn = get_connection()
    try:
        inserted = 0
        skipped = 0
        for character in characters:
            existing = conn.execute(
                "SELECT id FROM characters WHERE user_id = ? AND hanzi = ? AND pinyin = ?",
                (user_id, character.hanzi, character.pinyin),
            ).fetchone()
            if existing:
                skipped += 1
                continue
            _insert_character(conn, character, user_id)
            inserted += 1
        conn.commit()
        return {"inserted": inserted, "skipped": skipped}
    finally:
        conn.close()


@app.post("/api/sentences/generate")
def sentence_generate(payload: SentenceIn, user_id: int = Depends(get_current_user_id)) -> dict[str, Any]:
    conn = get_connection()
    try:
        all_rows = conn.execute("SELECT * FROM characters WHERE user_id = ?", (user_id,)).fetchall()
        if not all_rows:
            raise HTTPException(status_code=400, detail="Añade algún carácter antes de generar frases")

        focus_word = None
        if payload.characterId is not None:
            focus_row = conn.execute(
                "SELECT * FROM characters WHERE id = ? AND user_id = ?", (payload.characterId, user_id)
            ).fetchone()
            if focus_row is None:
                raise HTTPException(status_code=404, detail="Carácter no encontrado")
            focus_word = {"hanzi": focus_row["hanzi"], "pinyin": focus_row["pinyin"]}

        sample_rows = (
            random.sample(all_rows, MAX_VOCAB_FOR_SENTENCE) if len(all_rows) > MAX_VOCAB_FOR_SENTENCE else all_rows
        )
        known_words = [
            {"hanzi": r["hanzi"], "pinyin": r["pinyin"], "meaningEs": r["meaning_es"]} for r in sample_rows
        ]

        settings_row = conn.execute("SELECT hsk_level FROM settings WHERE user_id = ?", (user_id,)).fetchone()
        hsk_level = settings_row["hsk_level"] if settings_row else 3

        return _run_ai("sentence", generate_sentence, known_words, hsk_level, focus_word)
    finally:
        conn.close()


@app.get("/api/settings")
def get_settings(user_id: int = Depends(get_current_user_id)) -> dict[str, Any]:
    conn = get_connection()
    try:
        row = conn.execute("SELECT hsk_level FROM settings WHERE user_id = ?", (user_id,)).fetchone()
        return {"hskLevel": row["hsk_level"] if row else 3}
    finally:
        conn.close()


@app.put("/api/settings")
def put_settings(payload: SettingsIn, user_id: int = Depends(get_current_user_id)) -> dict[str, Any]:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO settings (user_id, hsk_level) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET hsk_level = excluded.hsk_level",
            (user_id, payload.hskLevel),
        )
        conn.commit()
        return {"hskLevel": payload.hskLevel}
    finally:
        conn.close()


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
