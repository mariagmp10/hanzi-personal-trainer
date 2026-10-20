"""Único punto de contacto con la API de Claude para todo lo relacionado con
vocabulario chino: buscar una palabra, leer una foto y generar frases.

Deliberadamente no se usa ningún diccionario chino-español ni base de datos
de radicales de terceros: la propia IA devuelve hanzi, pinyin, significado,
nivel HSK aproximado y radical(es) en un único formato JSON. Por eso el
nivel HSK y el radical son aproximados, no una fuente oficial, y por eso la
app deja editar esos campos a mano (ver app/main.py).
"""

import base64
import json
import re
from typing import Any, Optional

import anthropic
import httpx2

MODEL = "claude-sonnet-5-5"

_CHARACTER_SCHEMA_HINT = (
    '{"hanzi": "...", "pinyin": "... (con marcas de tono)", '
    '"meaningEs": "...", "meaningEn": "...", '
    '"hskLevel": 1-6 o null si no es vocabulario HSK estándar, '
    '"radicals": ["..."] (un radical por cada carácter de "hanzi")}'
)


class AIResponseError(Exception):
    """La respuesta de la IA no se pudo interpretar como el JSON esperado."""


def _client() -> anthropic.Anthropic:
    # Esta red tiene una ruta IPv6 rota hacia la API (las conexiones se quedan
    # colgadas indefinidamente en CLOSE_WAIT): forzamos IPv4 vinculando el
    # socket local a 0.0.0.0, y añadimos además un timeout explícito como red
    # de seguridad por si cualquier otra conexión se queda colgada igual.
    http_client = httpx2.Client(transport=httpx2.HTTPTransport(local_address="0.0.0.0"))
    return anthropic.Anthropic(timeout=45.0, http_client=http_client)


def _text_from_response(response: Any) -> str:
    return "".join(block.text for block in response.content if block.type == "text")


def _parse_json(raw_text: str, allow_partial_array: bool = False) -> Any:
    # La IA a veces envuelve el JSON en un bloque ```json ... ``` aunque se le
    # pida que no lo haga; nos lo quitamos antes de parsear.
    cleaned = re.sub(r"^```(?:json)?|```$", "", raw_text.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        if allow_partial_array:
            repaired = _repair_truncated_array(cleaned)
            if repaired is not None:
                return repaired
        raise AIResponseError(f"La IA no devolvió JSON válido: {exc}") from exc


def _repair_truncated_array(text: str) -> Optional[list]:
    """Si la respuesta es un array JSON que se cortó a mitad de un elemento
    (p. ej. por quedarse sin tokens de salida con una foto con mucho
    contenido), recupera los elementos que sí llegaron a cerrarse del todo
    en vez de descartar toda la respuesta."""
    start = text.find("[")
    if start == -1:
        return None
    depth = 0
    last_complete_end = None
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                last_complete_end = i
    if last_complete_end is None:
        return None
    try:
        result = json.loads(text[start : last_complete_end + 1] + "]")
    except json.JSONDecodeError:
        return None
    return result if isinstance(result, list) else None


def _drop_incomplete_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Descarta cualquier entrada sin hanzi o pinyin (p. ej. si la IA genera
    una entrada vacía intentando forzar varias opciones donde solo hay una),
    para que nunca se llegue a mostrar una tarjeta en blanco en la app."""
    return [e for e in entries if isinstance(e, dict) and e.get("hanzi") and e.get("pinyin")]


def lookup_word(query: str) -> list[dict[str, Any]]:
    """query puede ser pinyin (con o sin tonos), una palabra en español, o
    directamente el hanzi. Devuelve una LISTA porque un pinyin sin tonos
    (p. ej. "shou") suele corresponder a varios caracteres distintos y sin
    relación entre sí (手 "mano", 瘦 "delgado", 受 "recibir/sufrir"...) — se
    deja que el estudiante elija cuál quería, en vez de adivinar uno solo."""
    prompt = (
        "Eres un diccionario de chino mandarín para un estudiante de nivel HSK3. "
        f'Te paso esta consulta (puede ser pinyin con o sin marcas de tono, una palabra en español, '
        f'o un hanzi): "{query}". '
        "REGLA IMPORTANTE: si la consulta es UNA SOLA SÍLABA en pinyin (con o sin marca de tono, "
        "p. ej. 'shou', 'ji', 'mǎ'), SIEMPRE devuelve TODOS los caracteres de uso común que comparten "
        "esa misma lectura (si no se especifica tono, incluye variantes de distintos tonos también) — "
        "nunca elijas uno solo 'el más probable' y te calles el resto. Pon hasta unos 10 si hay tantos. "
        "Si la consulta son VARIAS SÍLABAS seguidas (una palabra o expresión compuesta, p. ej. 'paobu', "
        "'xuesheng'), normalmente corresponde a una única palabra clara — ahí devuelve solo esa palabra, "
        "salvo que de verdad existan dos o más palabras de uso común y completamente distintas con "
        "exactamente esa misma secuencia de sílabas (caso raro), en cuyo caso lista esas pocas. "
        "Esta regla de listar homófonos solo aplica a sílabas sueltas, nunca fuerces varias entradas "
        "para una palabra compuesta si realmente solo hay una que tenga sentido. "
        "Si la consulta ya es inequívoca por sí misma (un hanzi concreto, o una palabra o frase en "
        "español muy específica que no sea una romanización), devuelve también solo esa única opción. "
        "Cada elemento de la respuesta debe tener SIEMPRE 'hanzi' y 'pinyin' rellenos y no vacíos — "
        "nunca incluyas una entrada a medias o con campos en blanco. "
        "Responde ÚNICAMENTE con un array JSON, sin texto adicional, donde cada elemento tiene este formato:\n"
        f"{_CHARACTER_SCHEMA_HINT}\n"
        "Si no encuentras ninguna coincidencia razonable, responde con un array vacío []."
    )
    response = _client().messages.create(
        model=MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    result = _parse_json(_text_from_response(response), allow_partial_array=True)
    if not isinstance(result, list):
        raise AIResponseError("La IA no devolvió una lista de candidatos.")
    return _drop_incomplete_entries(result)


def extract_from_photo(image_bytes: bytes, media_type: str) -> list[dict[str, Any]]:
    """Una sola foto sirve tanto para 'un carácter suelto' como para 'apuntes
    de la semana': si la foto trae varias palabras, simplemente se devuelven
    varias entradas en la lista."""
    prompt = (
        "Esta imagen contiene caracteres chinos (impresos o manuscritos, p. ej. "
        "apuntes de clase de chino mandarín de nivel HSK3). "
        "Identifica solo las palabras de VOCABULARIO SUELTO (una palabra o carácter cada una), no frases "
        "completas de ejemplo aunque aparezcan en la foto — de una frase de ejemplo, como mucho extrae "
        "como entradas sueltas las palabras de vocabulario nuevas que contenga, no la frase entera. "
        "Si junto a una palabra hay apuntada una traducción al español (aunque sea informal o abreviada), "
        "úsala como base para 'meaningEs' en vez de traducir tú desde cero. "
        "Responde ÚNICAMENTE con un array JSON, sin texto adicional, donde cada elemento tiene este formato:\n"
        f"{_CHARACTER_SCHEMA_HINT}\n"
        "Si no detectas ningún carácter chino en la imagen, responde con un array vacío []."
    )
    response = _client().messages.create(
        model=MODEL,
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": base64.b64encode(image_bytes).decode("ascii"),
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    )
    result = _parse_json(_text_from_response(response), allow_partial_array=True)
    if not isinstance(result, list):
        raise AIResponseError("La IA no devolvió una lista de palabras detectadas.")
    return _drop_incomplete_entries(result)


def generate_hsk_batch(level: int, exclude_hanzi: list[str]) -> list[dict[str, Any]]:
    """Genera un lote de vocabulario estándar de un nivel HSK que el estudiante
    todavía no tiene guardado. Pensado para rellenar de golpe niveles ya
    superados (p. ej. HSK1-2 si ya vas por HSK3) sin escribirlos uno a uno.
    Se pide en lotes pequeños (no la lista completa de una vez) para que la
    respuesta JSON no se trunque y el coste por llamada sea bajo."""
    exclude_line = (
        f"No repitas ninguna de estas palabras, que el estudiante ya tiene guardadas: {', '.join(exclude_hanzi)}. "
        if exclude_hanzi
        else ""
    )
    prompt = (
        f"Dame un lote de unas 30-40 palabras del vocabulario estándar de HSK{level} (chino mandarín), "
        "las más representativas/frecuentes de ese nivel que no me hayas dado ya en una respuesta anterior. "
        f"{exclude_line}"
        "Responde ÚNICAMENTE con un array JSON, sin texto adicional, donde cada elemento tiene este formato:\n"
        f"{_CHARACTER_SCHEMA_HINT}\n"
        "Si consideras que ya no quedan palabras de ese nivel distintas de las de la lista de exclusión, "
        "responde con un array vacío []."
    )
    response = _client().messages.create(
        model=MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    result = _parse_json(_text_from_response(response), allow_partial_array=True)
    if not isinstance(result, list):
        raise AIResponseError("La IA no devolvió una lista de vocabulario.")
    return _drop_incomplete_entries(result)


def explain_character(
    hanzi: str, pinyin: str, meaning_es: str, radicals_with_meanings: list[tuple[str, str]]
) -> dict[str, Any]:
    """Explica cómo se combinan los radicales de un carácter y da un truco
    mnemotécnico. Los radicales y su significado ya se conocen localmente
    (ver app/radicals.py, la tabla fija de los 214 radicales Kangxi), así que
    no se le pide a la IA que los identifique — solo que los explique y
    construya una ayuda de memoria, lo que mantiene el prompt corto y barato.
    El resultado se guarda en la base de datos (characters.explanation /
    .mnemonic) para no volver a gastar una llamada la próxima vez."""
    radicals_line = "; ".join(f"{r} ({m})" for r, m in radicals_with_meanings if m) or "sin radicales identificados"
    prompt = (
        f"Carácter chino: {hanzi} (pinyin: {pinyin}), significado: {meaning_es}. "
        f"Sus radicales/componentes son: {radicals_line}. "
        "Para un estudiante de HSK3, en español: "
        "1) explica en 1-2 frases cómo esos radicales se relacionan (o no) con el significado del carácter; "
        "2) dale un truco mnemotécnico breve y memorable (una imagen mental, historia corta o asociación "
        "visual) para recordar el carácter a partir de su forma y sus radicales. "
        'Responde ÚNICAMENTE con un objeto JSON con este formato exacto: '
        '{"explanation": "...", "mnemonic": "..."}'
    )
    response = _client().messages.create(
        model=MODEL,
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    return _parse_json(_text_from_response(response))


def generate_sentence(
    known_words: list[dict[str, Any]], hsk_level: int, focus_word: dict[str, Any] | None = None
) -> dict[str, Any]:
    vocab_lines = "\n".join(f"- {w['hanzi']} ({w['pinyin']}): {w['meaningEs']}" for w in known_words)
    focus_instruction = (
        f"La frase debe usar obligatoriamente la palabra \"{focus_word['hanzi']}\" ({focus_word['pinyin']}). "
        if focus_word
        else ""
    )
    prompt = (
        f"Eres un profesor de chino mandarín para un estudiante de nivel HSK{hsk_level}. "
        "Este es el vocabulario que el estudiante ya conoce:\n"
        f"{vocab_lines}\n\n"
        f"Construye UNA frase natural y sencilla, con gramática apropiada para HSK{hsk_level}, "
        "usando principalmente palabras de esa lista (puedes añadir partículas gramaticales básicas "
        "necesarias aunque no estén en la lista). "
        f"{focus_instruction}"
        'Responde ÚNICAMENTE con un objeto JSON con este formato exacto: '
        '{"hanzi": "...", "pinyin": "...", "translationEs": "...", '
        '"wordsUsed": ["..."] (hanzi de las palabras de la lista que usaste)}'
    )
    response = _client().messages.create(
        model=MODEL,
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    return _parse_json(_text_from_response(response))
