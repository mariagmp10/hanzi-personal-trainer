# Hanzi Trainer

App local para memorizar vocabulario de chino mandarín (nivel HSK3),
comparar caracteres por radical o pinyin, generar frases con tu vocabulario
ya aprendido, y volcar el vocabulario de una foto de tus apuntes de clase.
Ver `PLAN.md` para la explicación completa de la arquitectura.

## Primeros pasos (Windows)

1. Desde una terminal, sitúate dentro de esta carpeta:
   ```
   cd ruta/donde/tengas/hanzi-trainer
   ```
2. Crea un entorno virtual de Python e instala las dependencias:
   ```
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Copia `.env.example` a `.env` y añade tu clave de Anthropic (créala en
   https://console.anthropic.com/ si no tienes una):
   ```
   copy .env.example .env
   ```
   Sin esta clave, la app arranca y puedes usar **Tarjetas** y **Lista**
   con datos que añadas a mano, pero **Añadir** (búsqueda/foto), **Apuntes
   semanales** y "Generar frase" necesitan la clave para funcionar.
4. Inicializa la base de datos SQLite:
   ```
   python -c "from app.db import init_db; init_db()"
   ```
5. Arranca el servidor:
   ```
   uvicorn app.main:app --reload
   ```
   Abre `http://127.0.0.1:8000` en el navegador.
6. Inicializa git en esta carpeta (parte del aprendizaje de Claude Code):
   ```
   git init
   git add .
   git commit -m "Fase 0-5: app completa de vocabulario HSK3"
   ```

## Cómo se usa

- **Añadir**: escribe el pinyin de una palabra (p. ej. `xiexie`) o su
  significado en español (p. ej. `gracias`), o sube una foto de un carácter
  suelto. La IA propone hanzi/pinyin/significado/nivel/radicales — revísalo,
  corrígelo si falta algo, y pulsa "Guardar".
- **Tarjetas**: te muestra un carácter al azar de los que ya tienes
  guardados. Clic para ver el pinyin, otro clic para ver la traducción.
  "Generar frase" construye una frase con tu vocabulario guardado centrada
  en esa palabra. "Ver similares" busca otras palabras guardadas que
  comparten radical o pinyin (sin tono) — clic en una de ellas para saltar
  a su tarjeta.
- **Apuntes semanales**: sube una foto de tu página de apuntes de clase. La
  IA detecta todo el vocabulario que ve, lo muestra en una tabla editable
  con checkboxes, y guardas solo lo que quieras (los duplicados exactos se
  omiten automáticamente).
- **Lista**: busca, filtra por nivel HSK, edita o borra cualquier entrada.
  Útil para corregir un radical o nivel HSK que la IA haya adivinado mal.
- **Nivel objetivo** (en Inicio): el nivel HSK que se usa al generar frases.

## Estructura

```
hanzi-trainer/
├── PLAN.md               <- arquitectura y roadmap explicado
├── requirements.txt
├── .env.example            <- ANTHROPIC_API_KEY
├── db/
│   ├── schema.sql           <- characters, settings
│   └── hanzi_trainer.db      <- la base de datos (no se sube a git)
├── ai/
│   └── vocab_ai.py            <- las 3 llamadas a Claude (buscar, leer foto, generar frase)
├── app/
│   ├── main.py                 <- API FastAPI
│   ├── db.py                    <- conexión SQLite + init_db()
│   ├── util.py                    <- pinyin_plain() (quita tonos para comparar)
│   └── static/                     <- interfaz web (index.html/style.css/app.js)
└── .gitignore
```
