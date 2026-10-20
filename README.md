# Hanzi Personal Trainer

App local para memorizar vocabulario de chino mandarín, comparar caracteres
por radical o pinyin (con el significado de cada radical y un truco
mnemotécnico), generar frases con tu vocabulario ya aprendido, escuchar la
pronunciación, y volcar el vocabulario de fotos de tus apuntes de clase.
Cada persona tiene su propia cuenta y su propio vocabulario. Ver `PLAN.md`
para la explicación completa de la arquitectura.

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
   Sin esta clave, la app arranca y puedes iniciar sesión y usar **Tarjetas**
   y **Lista** con datos que añadas a mano, pero **Añadir** (búsqueda/foto),
   **Apuntes semanales**, "Generar frase" y "Explicar radicales" necesitan la
   clave para funcionar.
4. Arranca el servidor (la base de datos SQLite se crea sola la primera vez):
   ```
   uvicorn app.main:app --reload --port 8010
   ```
   Abre `http://127.0.0.1:8010` en el navegador.
5. La primera vez que abras la app te pedirá iniciar sesión — pulsa "¿No
   tienes cuenta? Crear una" y date de alta tú misma. Si ya tenías vocabulario
   guardado de antes de que existieran las cuentas, la **primera** cuenta que
   se cree se lo queda automáticamente.
6. Inicializa git en esta carpeta si aún no lo has hecho:
   ```
   git init
   git add .
   git commit -m "Primera version"
   ```

## Acceder desde el móvil (misma WiFi)

Con el portátil y el móvil en la misma red, abre en el móvil
`http://<IP-local-de-tu-portátil>:8010` (la IP la ves con `ipconfig` en una
terminal, o te la doy yo). El servidor tiene que estar corriendo en el
portátil en ese momento.

## Cómo se usa

- **Cuentas**: usuario + contraseña, por cuenta propia (sin recuperación de
  contraseña ni verificación por email — es una app personal, no un
  producto). Cada cuenta ve solo su propio vocabulario.
- **Tarjetas**: carácter al azar, con más probabilidad de salir cuanto menos
  lo domines ("Me cuesta" lo vuelve a poner en primera línea; "Lo sé" lo hace
  aparecer menos, hasta un tope). Clic para revelar pinyin, otro clic para la
  traducción. 🔊 escucha la pronunciación. "Generar frase" construye una
  frase con tu vocabulario centrada en esa palabra. "Ver similares" agrupa
  otras palabras guardadas por el radical que comparten (con su significado)
  o por el mismo pinyin. "Explicar radicales" da una explicación de cómo se
  forma el carácter y un truco mnemotécnico (se guarda la primera vez, no
  vuelve a gastar en la IA para esa palabra).
- **Añadir**: escribe el pinyin (p. ej. `shou` si no sabes el tono —
  devuelve todos los caracteres comunes con esa lectura para que elijas) o
  el significado en español, o sube una foto de un carácter suelto.
- **Vocabulario HSK**: rellena de golpe el vocabulario estándar de un nivel
  que ya deberías saberte, en lotes, evitando repetir lo que ya tienes.
- **Apuntes semanales**: sube una o varias fotos de tus apuntes de clase; la
  IA detecta el vocabulario (no frases completas) y lo revisas antes de
  guardar.
- **Lista**: busca, filtra por nivel HSK, edita o borra cualquier entrada.
- **Resumen**: estadísticas por nivel HSK y el nivel objetivo usado al
  generar frases.

## Estructura

```
hanzi-trainer/
├── PLAN.md               <- arquitectura y roadmap explicado
├── requirements.txt
├── .env.example            <- ANTHROPIC_API_KEY
├── db/
│   ├── schema.sql           <- users, sessions, characters, settings
│   └── hanzi_trainer.db      <- la base de datos (no se sube a git)
├── ai/
│   └── vocab_ai.py            <- llamadas a Claude (buscar, leer foto, frase, explicar, lote HSK)
├── app/
│   ├── main.py                 <- API FastAPI
│   ├── auth.py                   <- cuentas: hash de contraseña + sesión por cookie
│   ├── db.py                      <- conexión SQLite + init_db() + migraciones
│   ├── radicals.py                 <- significados de los 214 radicales Kangxi (fijo, sin IA)
│   ├── util.py                      <- pinyin_plain() (quita tonos para comparar)
│   └── static/                       <- interfaz web (index.html/style.css/app.js)
└── .gitignore
```
