# Hanzi Trainer — Plan técnico

**Objetivo:** app local para memorizar vocabulario de chino mandarín (nivel
HSK3), comparar caracteres por radical o por pinyin, generar frases con el
vocabulario ya aprendido, y volcar el vocabulario de una foto de apuntes de
clase. Objetivo secundario explícito: que el proyecto sirva para aprender a
usar Claude Code.

---

## Decisión de arquitectura: un único motor lingüístico (API de Claude)

En vez de bundlear un diccionario chino-español y una base de datos de
radicales de terceros (paquetes de disponibilidad incierta), **toda la
inteligencia lingüística pasa por la API de Claude** (modelo con visión),
en un único módulo `ai/vocab_ai.py` con tres llamadas:

1. `lookup_word(query)` — texto (pinyin, palabra en español, o el propio
   hanzi) → hanzi, pinyin con tonos, significado ES/EN, nivel HSK
   aproximado y radical(es).
2. `extract_from_photo(image_bytes, media_type)` — foto (un carácter suelto
   o una página entera de apuntes) → lista de palabras detectadas, mismos
   campos. Es la misma función para "añadir un carácter por foto" y para
   "apuntes semanales": si la foto trae varias palabras, la lista
   simplemente tiene varios elementos.
3. `generate_sentence(known_words, hsk_level, focus_word=None)` — con el
   vocabulario ya guardado (y opcionalmente centrada en una palabra
   concreta), genera una frase con gramática apropiada al nivel indicado.

Cada llamada pide **JSON estructurado** y se parsea con manejo de error
(`AIResponseError` en `ai/vocab_ai.py`, convertido a HTTP 502 en
`app/main.py` si la IA devuelve algo no interpretable).

Una vez guardado un carácter, **"ver similares" es una consulta local**
sobre lo ya guardado (`GET /api/characters/{id}/similar`), sin volver a
llamar a la IA: se guarda `pinyin_plain` (sin tonos, calculado en Python
con `unicodedata`, ver `app/util.py`) y `radicals` (lista JSON, tal cual la
devuelve la IA, uno por cada carácter del hanzi — así una palabra de dos
caracteres como 老师 puede compartir radical con otra palabra a través de
cualquiera de sus dos caracteres).

**Limitación conocida:** el nivel HSK y el radical que asigna la IA son
aproximados, no provienen de una lista oficial. Por eso todos los campos de
un carácter son editables a mano desde la vista "Lista".

---

## Esquema de base de datos

Ver `db/schema.sql`. Dos tablas: `characters` (todo el vocabulario) y
`settings` (una sola fila con el nivel HSK objetivo, usado al generar
frases).

## Stack

Mismo patrón que `climate-tech-job-agent`: **FastAPI + SQLite** (vía
`sqlite3` directo, sin ORM) sirviendo una interfaz **HTML/CSS/JS plano**
(sin build step) desde `app/static/`. Cero infraestructura, fácil de leer
de principio a fin.

## Roadmap (ya implementado de una vez, documentado aquí como fases para que quede claro qué hace cada parte)

| Fase | Contenido |
|---|---|
| **0. Fundaciones** | Esquema SQLite + servidor FastAPI + esqueleto de interfaz |
| **1. Añadir vocabulario** | Búsqueda por texto (`POST /api/lookup`) y por foto de un carácter suelto (`POST /api/photo/extract`), con tarjeta de confirmación editable antes de guardar |
| **2. Tarjetas** | Flashcards aleatorias con revelado progresivo (hanzi → pinyin → traducción), "ver similares" por radical/pinyin |
| **3. Frases** | Generación de frases con el vocabulario guardado y el nivel HSK objetivo |
| **4. Apuntes semanales** | Misma extracción por foto, pero mostrando una tabla con varias filas para revisar y guardar en bloque |
| **5. Lista** | Buscar, filtrar por nivel HSK, editar y borrar cualquier entrada guardada |

Fases futuras posibles (no implementadas): repetición espaciada real
(priorizar tarjetas por `review_count`/`last_reviewed_at`, que ya se
guardan pero no se usan todavía para elegir qué tarjeta mostrar), historial
de frases generadas, estadísticas de aciertos.
