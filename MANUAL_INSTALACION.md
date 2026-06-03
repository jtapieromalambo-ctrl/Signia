# 📘 Manual de Instalación — SIGNIA

> **SIGNIA** es una aplicación web de traducción al Lenguaje de Señas Colombiano (LSC).  
> Stack: **Django 5.2 · PostgreSQL (Neon) · Python 3.11**  
> Despliegue en producción: **Railway** (via nixpacks)

---

## Tabla de Contenidos

1. [Requisitos previos](#1-requisitos-previos)
2. [Clonar el repositorio](#2-clonar-el-repositorio)
3. [Entorno virtual](#3-entorno-virtual)
4. [Instalar dependencias](#4-instalar-dependencias)
5. [Variables de entorno (.env)](#5-variables-de-entorno-env)
6. [Base de datos](#6-base-de-datos)
7. [Archivos estáticos y media](#7-archivos-estáticos-y-media)
8. [Ejecutar en desarrollo](#8-ejecutar-en-desarrollo)
9. [Entrenamiento del modelo ML](#9-entrenamiento-del-modelo-ml)
10. [Despliegue en Railway](#10-despliegue-en-railway)
11. [Configuración de OAuth (Google / Facebook)](#11-configuración-de-oauth-google--facebook)
12. [Configuración de correo (Brevo)](#12-configuración-de-correo-brevo)
13. [Árbol del proyecto](#13-árbol-del-proyecto)
14. [Solución de problemas comunes](#14-solución-de-problemas-comunes)

---

## 1. Requisitos previos

Antes de comenzar, asegúrate de tener instalado lo siguiente en tu sistema:

| Herramienta | Versión mínima | Descarga |
|---|---|---|
| Python | 3.11 | https://www.python.org/downloads/ |
| pip | 23+ | Incluido con Python |
| Git | cualquiera | https://git-scm.com/ |
| ffmpeg | cualquiera | https://ffmpeg.org/download.html |

> **Nota para Windows:** El proyecto incluye los binarios de `ffmpeg` en la carpeta `/ffmpeg/`. No es necesario instalarlo globalmente si solo se ejecuta en desarrollo local.

---

## 2. Clonar el repositorio

```bash
git clone <URL_DEL_REPOSITORIO>
cd SIGNIA
```

---

## 3. Entorno virtual

Se recomienda usar un entorno virtual para aislar las dependencias del proyecto.

**Windows (PowerShell):**
```powershell
python -m venv ENT
.\ENT\Scripts\Activate.ps1
```

**Linux / macOS:**
```bash
python3.11 -m venv ENT
source ENT/bin/activate
```

> Verifica que el entorno está activo: el prompt debe mostrar `(ENT)` al inicio.

---

## 4. Instalar dependencias

Con el entorno virtual activo, instala todos los paquetes necesarios:

```bash
pip install -r requirements.txt
```

### Dependencias principales incluidas

| Paquete | Propósito |
|---|---|
| `Django 5.2` | Framework web principal |
| `django-allauth 65` | Autenticación OAuth (Google, Facebook) |
| `faster-whisper` | Transcripción de audio a texto (STT) |
| `mediapipe` | Detección de landmarks de manos (cámara) |
| `scikit-learn` | Clasificador RandomForest para reconocimiento de señas |
| `groq` | API para conversión de texto a gramática LSC |
| `psycopg2-binary` | Conector PostgreSQL |
| `gunicorn` | Servidor WSGI para producción |
| `whitenoise` | Servicio de archivos estáticos en producción |
| `dj-database-url` | Parseo de `DATABASE_URL` |
| `python-decouple` | Gestión de variables de entorno desde `.env` |

---

## 5. Variables de entorno (.env)

Crea un archivo `.env` en la **raíz del proyecto** (al mismo nivel que `manage.py`):

```
SIGNIA/
├── .env          ← aquí
├── manage.py
├── requirements.txt
└── ...
```

### Contenido del archivo `.env`

```env
# ── Django ─────────────────────────────────────────────
SECRET_KEY=tu_clave_secreta_muy_larga_y_aleatoria
DEBUG=True

# ── Base de datos ───────────────────────────────────────
# Para desarrollo local con SQLite (no requiere Neon):
# DATABASE_URL se puede omitir y usará db.sqlite3 automáticamente

# Para PostgreSQL Neon (recomendado en producción):
DATABASE_URL=postgresql://usuario:password@host.neon.tech/signia?sslmode=require

# ── Correo (Brevo) ──────────────────────────────────────
BREVO_API_KEY=tu_api_key_de_brevo
EMAIL_HOST_USER=tu_correo@gmail.com
EMAIL_HOST_PASSWORD=tu_contraseña_de_aplicacion

# ── IA / LSC Grammar (Groq) ────────────────────────────
GROQ_API_KEY=tu_api_key_de_groq

# ── OAuth Social ────────────────────────────────────────
# (configurar en el panel de Django Admin después de migrar)
SITE_ID=1

# ── Railway (solo en producción) ────────────────────────
# RAILWAY_PUBLIC_DOMAIN=tu-app.up.railway.app
```

### ¿Cómo obtener cada clave?

- **`SECRET_KEY`:** Genera una nueva con:
  ```bash
  python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
  ```

- **`GROQ_API_KEY`:** Regístrate en https://console.groq.com y crea una API Key.

- **`BREVO_API_KEY`:** Regístrate en https://www.brevo.com y ve a *Settings → API Keys*.

- **`DATABASE_URL`:** Crea un proyecto gratuito en https://neon.tech y copia el connection string.

---

## 6. Base de datos

### Opción A — SQLite (local, desarrollo rápido)

No se necesita configuración adicional. Django usará `db.sqlite3` automáticamente si `DATABASE_URL` no está definida en `.env`.

```bash
python manage.py migrate
```

### Opción B — PostgreSQL con Neon (recomendado)

1. Crea un proyecto en [neon.tech](https://neon.tech)
2. Copia el **connection string** y ponlo en `DATABASE_URL` del `.env`
3. Ejecuta las migraciones:

```bash
python manage.py migrate
```

### Crear superusuario administrador

```bash
python manage.py createsuperuser
```

Sigue las instrucciones en pantalla. El superusuario tendrá acceso al panel de administración de videos en `/admin-videos/`.

---

## 7. Archivos estáticos y media

### Archivos estáticos (CSS, JS, imágenes)

En **desarrollo** Django los sirve automáticamente desde `/static/`.

En **producción** es necesario recolectarlos:

```bash
python manage.py collectstatic --no-input
```

Esto copia todo a `/staticfiles/`, que es servido por WhiteNoise.

> ⚠️ **Importante:** El proyecto usa `CompressedStaticFilesStorage` (NO `ManifestStaticFilesStorage`). Esto es requerido para que los archivos WASM de MediaPipe funcionen correctamente, ya que el Manifest mode renombra los archivos con hashes y rompe el cargador de WASM.

### Carpeta media

La carpeta `/media/` almacena los videos de señas subidos. Se crea automáticamente. En producción esta carpeta **no se persiste entre deploys en Railway**; se recomienda usar almacenamiento en la nube (S3, Cloudinary) para producción a largo plazo.

---

## 8. Ejecutar en desarrollo

Con el entorno virtual activo y el `.env` configurado:

```bash
python manage.py runserver
```

La aplicación estará disponible en: **http://127.0.0.1:8000**

### Rutas principales

| Ruta | Descripción |
|---|---|
| `/` | Página de inicio |
| `/login/` | Inicio de sesión |
| `/registro/` | Registro de nuevo usuario |
| `/perfil/` | Perfil del usuario |
| `/traduccion/` | Módulo texto → señas (LSC) |
| `/reconocimientos/camara/` | Módulo cámara → texto |
| `/admin-videos/` | Panel de administración (solo superusuario) |
| `/seleccionar-discapacidad/` | Selección de perfil de usuario |

---

## 9. Entrenamiento del modelo ML

El módulo de reconocimiento usa un clasificador **RandomForest** entrenado con landmarks de manos extraídos por MediaPipe.

### ¿Cuándo entrenar?

El modelo se debe entrenar **la primera vez** que se instala el sistema, o cada vez que se agreguen nuevos videos de señas desde el panel de administración.

### Cómo entrenar

1. Inicia sesión como superusuario
2. Ve a `/admin-videos/`
3. Sube videos de señas con su etiqueta correspondiente
4. Haz clic en el botón **"Entrenar modelo"**
5. Espera a que el proceso finalice (corre en segundo plano en un hilo daemon)

### Archivos generados

```
reconocimientos/
└── modelo/
    ├── model_seq.pkl      ← Clasificador RandomForest serializado
    └── label_encoder.npy  ← Codificador de etiquetas
```

> ⚠️ Si `model_seq.pkl` no existe, el módulo de reconocimiento devolverá un error **503**. Entrena el modelo antes de usar la cámara.

> ⚠️ El entrenamiento **elimina todos los videos** de la base de datos y del disco después de procesarlos. Esta es la conducta esperada del sistema.

---

## 10. Despliegue en Railway

### Archivos de configuración incluidos

| Archivo | Propósito |
|---|---|
| `Procfile` | Define el proceso web con gunicorn |
| `build.sh` | Script de build: instala deps, collectstatic, migrate |
| `nixpacks.toml` | Instala dependencias del sistema (libgl1, ffmpeg, etc.) |
| `runtime.txt` | Fija la versión de Python a usar |

### Pasos para desplegar

1. **Crea un nuevo proyecto** en [railway.app](https://railway.app)

2. **Conecta tu repositorio** de GitHub o sube el código directamente

3. **Agrega las variables de entorno** en el panel de Railway:
   ```
   SECRET_KEY=...
   DEBUG=False
   DATABASE_URL=...          (Neon PostgreSQL)
   GROQ_API_KEY=...
   BREVO_API_KEY=...
   EMAIL_HOST_USER=...
   EMAIL_HOST_PASSWORD=...
   RAILWAY_PUBLIC_DOMAIN=tu-app.up.railway.app
   ```

4. Railway detectará automáticamente el `Procfile` y `nixpacks.toml` y ejecutará el build.

5. El proceso de build ejecuta `build.sh`:
   ```bash
   pip install -r requirements.txt
   python manage.py collectstatic --no-input --clear
   python manage.py migrate
   ```

6. El proceso de release ejecuta:
   ```bash
   python manage.py migrate
   ```

7. El servidor inicia con:
   ```bash
   gunicorn Signia.wsgi --bind 0.0.0.0:$PORT --timeout 120
   ```

### Dependencias del sistema instaladas por nixpacks

```toml
[phases.setup]
aptPkgs = ["libgl1", "libglib2.0-0", "libgl1-mesa-glx", "ffmpeg"]
```

Estas librerías son requeridas por OpenCV y MediaPipe.

---

## 11. Configuración de OAuth (Google / Facebook)

La configuración de OAuth requiere pasos adicionales después del primer despliegue.

### Google OAuth

1. Ve a [Google Cloud Console](https://console.cloud.google.com)
2. Crea un proyecto → *APIs & Services → Credentials*
3. Crea un **OAuth 2.0 Client ID** de tipo "Web application"
4. Agrega los URIs de redirección autorizados:
   ```
   http://127.0.0.1:8000/accounts/google/login/callback/   (desarrollo)
   https://tu-app.up.railway.app/accounts/google/login/callback/  (producción)
   ```
5. Copia el **Client ID** y **Client Secret**

### Configurar en Django Admin

1. Ve a `/django-admin/` (admin nativo de Django)
2. En *Sites*, edita el sitio por defecto y cambia el dominio a tu dominio real
3. En *Social Applications*, crea una nueva aplicación:
   - Provider: **Google**
   - Client ID: (el que copiaste)
   - Secret Key: (el que copiaste)
   - Sites: selecciona tu sitio

Repite el proceso para **Facebook** si es necesario.

---

## 12. Configuración de correo (Brevo)

El sistema usa **Brevo (ex Sendinblue)** para enviar correos de:
- Verificación de cuenta (OTP)
- Bienvenida al registrarse
- Confirmación de cambio de contraseña
- Recuperación de contraseña

### Configurar Brevo

1. Crea una cuenta en [brevo.com](https://www.brevo.com)
2. Ve a *Settings → API Keys → Create a new API key*
3. Copia la clave y ponla en `BREVO_API_KEY` del `.env`
4. En *Senders*, verifica el correo que usarás como remitente

### Variables requeridas

```env
BREVO_API_KEY=xkeysib-...
EMAIL_HOST_USER=tu_correo_verificado@gmail.com
```

> El campo `EMAIL_HOST_PASSWORD` puede dejarse vacío si se usa el backend personalizado de Brevo (`usuarios/email_backend.py`).

---

## 13. Árbol del proyecto

```
SIGNIA/
├── Signia/                  # Paquete de configuración Django
│   ├── settings.py          # Configuración principal
│   ├── urls.py              # URLs raíz
│   ├── wsgi.py
│   └── asgi.py
│
├── usuarios/                # App: autenticación, perfiles, OTP, OAuth
│   ├── models.py            # Modelo Usuario personalizado + CodigoOTP
│   ├── views.py             # Login, registro, perfil, contacto, OTP
│   ├── forms.py             # Formularios de registro y edición
│   ├── adapters.py          # Adaptador de allauth para OAuth social
│   ├── email_backend.py     # Backend de correo Brevo
│   ├── signals.py           # Señales post-login
│   └── middleware.py        # Middleware de sesión y caché
│
├── traduccion/              # App: texto/audio → videos LSC
│   ├── views.py             # Procesamiento con Whisper + Groq + BD
│   └── models.py            # Modelo de videos del traductor
│
├── reconocimientos/         # App: cámara → texto (MediaPipe + sklearn)
│   ├── views.py             # Detección con HandLandmarker (thread-safe)
│   └── modelo/              # Archivos del modelo ML
│       ├── model_seq.pkl    # RandomForest entrenado
│       └── label_encoder.npy
│
├── historial/               # App: historial de traducciones/reconocimientos
│
├── lsc_grammar.py           # Capa gramatical LSC (Groq API, 4 modelos fallback)
│
├── templates/               # Templates HTML globales
├── static/                  # Archivos estáticos (dev)
├── staticfiles/             # collectstatic output (producción)
├── media/                   # Videos subidos por usuarios
├── ffmpeg/                  # Binarios ffmpeg incluidos
│
├── manage.py
├── requirements.txt
├── Procfile                 # Configuración proceso Railway
├── build.sh                 # Script de build Railway
├── nixpacks.toml            # Dependencias sistema Railway
├── runtime.txt              # Versión Python
├── .env                     # Variables de entorno (NO subir a Git)
└── .gitignore
```

---

## 14. Solución de problemas comunes

### ❌ Error: `model_seq.pkl` no encontrado → reconocimiento retorna 503

**Causa:** El modelo de RandomForest no ha sido entrenado.  
**Solución:** Inicia sesión como superusuario, sube videos de señas desde `/admin-videos/` y entrena el modelo.

---

### ❌ Error de CSRF en producción ("CSRF verification failed")

**Causa:** El dominio de Railway no está en `CSRF_TRUSTED_ORIGINS`.  
**Solución:** Asegúrate de que `RAILWAY_PUBLIC_DOMAIN` esté configurado en las variables de entorno de Railway.

```env
RAILWAY_PUBLIC_DOMAIN=tu-app.up.railway.app
```

---

### ❌ MediaPipe no carga en el navegador (error WASM)

**Causa:** WhiteNoise comprime los archivos `.wasm` o los renombra con hash.  
**Solución:** El proyecto ya está configurado correctamente con `CompressedStaticFilesStorage` y `WHITENOISE_SKIP_COMPRESS_EXTENSIONS`. Si el error persiste, verifica que no se haya cambiado `STORAGES` en `settings.py`.

---

### ❌ El reconocimiento se congela o genera deadlocks

**Causa:** Se está usando una sola instancia de `HandLandmarker` compartida entre hilos de Django.  
**Solución:** El código ya usa `threading.local()` para crear un detector por hilo. No compartir instancias entre workers.

---

### ❌ Error de conexión a la base de datos Neon ("SSL required")

**Causa:** La cadena de conexión no incluye `?sslmode=require`.  
**Solución:** Asegúrate de que `DATABASE_URL` termine en `?sslmode=require`:
```
postgresql://user:pass@host.neon.tech/dbname?sslmode=require
```

---

### ❌ Los correos no se envían

**Causa:** API key de Brevo inválida o correo remitente no verificado.  
**Solución:**
1. Verifica que `BREVO_API_KEY` sea correcto y esté activo
2. Confirma que el correo en `DEFAULT_FROM_EMAIL` esté verificado en Brevo
3. Revisa los logs de Django para el error exacto

---

### ❌ Google OAuth redirige a `http://` en lugar de `https://` en Railway

**Causa:** Django no detecta que está detrás de un proxy HTTPS.  
**Solución:** El archivo `settings.py` ya incluye:
```python
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
```
Asegúrate de no haberlo eliminado.

---

### ❌ ffmpeg no encontrado (error de Whisper)

**Causa:** El directorio `ffmpeg/` no está en el `PATH`.  
**Solución:** El código en `traduccion/views.py` agrega automáticamente la carpeta `ffmpeg/` al `PATH`. No mover ni eliminar esta carpeta.

---

## Contacto y Soporte

Para soporte técnico o reportar bugs, usa el formulario de contacto en la aplicación (`/contacto/`) o comunícate directamente con el equipo de desarrollo.

---

*Manual generado para SIGNIA v1.0 — Junio 2026*
