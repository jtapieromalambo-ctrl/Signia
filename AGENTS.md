# SIGNIA — Agent Guide

Colombian Sign Language (LSC) translation web app. Django 5.2 + PostgreSQL (Neon). Deployed on Railway via nixpacks.

## Commands

```bash
# Local dev (requires .env at project root)
python manage.py runserver

# After cloning: install deps + setup DB
pip install -r requirements.txt
python manage.py migrate

# Collect static (required for production / WhiteNoise)
python manage.py collectstatic --no-input
```

Runtime: **Python 3.11**. No test suite, linter, formatter, or CI configured.

## Project Structure

```
Signia/          # Django project package (settings, urls, wsgi, asgi)
usuarios/        # Auth, profiles, OTP email verification, OAuth (Google/Facebook), contact form
traduccion/      # Text/audio → LSC sign videos (Whisper STT + Groq LSC grammar + BD video lookup)
reconocimientos/ # Camera hand-sign → text (MediaPipe landmarks + sklearn RandomForest)
historial/       # Per-user translation/recognition history
lsc_grammar.py   # Standalone LSC grammar layer (Groq API, fallback chain of 4 Llama models)
ffmpeg/          # Bundled ffmpeg binaries (required by faster-whisper)
media/           # User-uploaded sign videos + reference videos
static/          # Dev static files (templates reference this)
staticfiles/     # collectstatic output (served by WhiteNoise in prod)
```

## Critical Gotchas

### MediaPipe HandLandmarker is NOT thread-safe
`reconocimientos/views.py` uses `threading.local()` to create one detector per Django worker thread. Never use a single shared `HandLandmarker` instance — it causes deadlocks and dropped frames.

### Static files + MediaPipe WASM
`STATICFILES_STORAGE` uses `CompressedStaticFilesStorage` (NOT `ManifestStaticFilesStorage`). Manifest mode renames files with hashes, which breaks MediaPipe's WASM loader that expects exact filenames.

### ML model loading
The RandomForest model (`reconocimientos/modelo/model_seq.pkl`) loads at import time in `reconocimientos/views.py`. If the file doesn't exist, recognition returns 503. Train a model via the admin panel first (`/reconocimientos/admin/`).

### Training runs in-process
`entrenar_modelo` spawns a daemon thread inside the Django process. It processes all `VideoSeña` records from DB, extracts landmarks, augments data (3 variations per sample), retrains the RandomForest (300 trees, n_jobs=-1), saves `.pkl` + `.npy` files, then **deletes all processed videos** from DB and disk.

### ffmpeg path
`traduccion/views.py` prepends the local `ffmpeg/` directory to `PATH` so Whisper can find ffmpeg. Do not move or remove this directory.

### SSL context override
`usuarios/views.py` sets `ssl._create_default_https_context = ssl._create_unverified_context`. This is a global side-effect needed for the email backend on some environments.

### Session config
Sessions expire on browser close OR after 20 min inactivity (`SESSION_COOKIE_AGE = 1200`). `SESSION_SAVE_EVERY_REQUEST = True` renews on each request.

## Auth Flow

- Custom user model: `usuarios.Usuario` (`AUTH_USER_MODEL = 'usuarios.Usuario'`)
- Email-based login (no username required by allauth)
- Registration requires OTP email verification (10-min expiry, stored in `CodigoOTP` model)
- Post-login disability selection routes: `sordo` → traductor, `mudo` → reconocimiento
- Superusers skip disability selection and go straight to admin video panel
- Google/Facebook OAuth via django-allauth; auto-connects emails

## Deployment (Railway)

- `build.sh`: pip install → collectstatic → migrate
- `Procfile`: `gunicorn Signia.wsgi --bind 0.0.0.0:8080` + release migration
- `nixpacks.toml`: installs system deps (`libgl1`, `libglib2.0-0`, `libgl1-mesa-glx`, `ffmpeg`)
- `DATABASE_URL` from env (Neon PostgreSQL with SSL). Falls back to `db.sqlite3` locally.
- `RAILWAY_PUBLIC_DOMAIN` env var dynamically appends to `ALLOWED_HOSTS` + `CSRF_TRUSTED_ORIGINS`

## Required Env Vars

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Neon PostgreSQL connection string |
| `SECRET_KEY` | Django secret key |
| `DEBUG` | `True` for local dev |
| `GROQ_API_KEY` | LSC grammar LLM API key |
| `EMAIL_HOST_USER` | Gmail address for outbound mail |
| `EMAIL_HOST_PASSWORD` | Gmail app password |

## LSC Grammar Layer (`lsc_grammar.py`)

Converts Spanish text → LSC gloss order via Groq API. Uses a fallback chain of 4 models (tries next on 429/503/decommissioned). Returns structured JSON with tokens, sentence type, facial expression markers, and missing sign candidates. Has a rule-based fallback if all models fail. Import: `from lsc_grammar import convertir_a_lsc, tokens_para_busqueda`.

## Database

`DISABLE_SERVER_SIDE_CURSORS = True` required for Neon's connection pooling. All DB connections use `sslmode=require`.
