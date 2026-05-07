from pathlib import Path
import dj_database_url
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY', default='django-insecure-fallback-key-railway')

DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = []

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.facebook',
    'usuarios',
    'reconocimientos',
    'traduccion',
    'historial',
    
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', 
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'usuarios.middleware.AdminLoginRedirectMiddleware',
    'usuarios.middleware.NoCacheMiddleware',
]

ROOT_URLCONF = 'Signia.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'usuarios.context_processors.disability_modal',
            ],
        },
    },
]

WSGI_APPLICATION = 'Signia.wsgi.application'


# ── BASE DE DATOS con Neon PostgreSQL ─────────────────
DATABASES = {
    'default': {
        **dj_database_url.parse(config('DATABASE_URL', default='sqlite:///' + str(BASE_DIR / 'db.sqlite3')), conn_max_age=0),
        'DISABLE_SERVER_SIDE_CURSORS': True,
        'OPTIONS': {
            'sslmode': 'require',
            'connect_timeout': 10,
            'keepalives': 1,
            'keepalives_idle': 30,
            'keepalives_interval': 5,
            'keepalives_count': 5,
        },
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'es-co'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_ROOT = BASE_DIR / "media"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = '/media/'
# CompressedStaticFilesStorage (sin Manifest) para evitar que WhiteNoise renombre
# los archivos WASM de MediaPipe con hashes — MediaPipe los busca por nombre exacto.
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

import mimetypes
mimetypes.add_type("application/wasm", ".wasm")
mimetypes.add_type("application/octet-stream", ".task")
AUTH_USER_MODEL = 'usuarios.Usuario'

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/seleccionar-discapacidad/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── EMAIL ──────────────────────────────────────────────
EMAIL_BACKEND = 'usuarios.resend_backend.ResendEmailBackend'
RESEND_API_KEY = config('RESEND_API_KEY', default='')
DEFAULT_FROM_EMAIL = 'Signia <onboarding@resend.dev>'

# ── ALLAUTH ────────────────────────────────────────────
SITE_ID = config("SITE_ID", default=1, cast=int)

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {
            'access_type': 'online',
            'prompt': 'select_account',
        },
    },
    'facebook': {
        'METHOD': 'oauth2',
        'SCOPE': ['email', 'public_profile'],
        'FIELDS': ['id', 'email', 'name'],
    }
}

SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_AUTO_SIGNUP = True
ACCOUNT_SIGNUP_REDIRECT_URL = '/seleccionar-discapacidad/'
LOGIN_REDIRECT_URL = '/seleccionar-discapacidad/'
ACCOUNT_LOGIN_REDIRECT_URL = '/seleccionar-discapacidad/' 
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_AUTHENTICATION_METHOD = 'email'
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True
SOCIALACCOUNT_ADAPTER = 'usuarios.adapters.SocialAccountAdapter'

LOGOUT_REDIRECT_URL = '/'
LOGIN_URL = '/login/'

# Solución SSL para macOS sin certificados
import ssl
EMAIL_SSL_CERTFILE = None
EMAIL_SSL_KEYFILE = None
EMAIL_TIMEOUT = 10

# Sesión expira al cerrar el navegador
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Sesión expira después de 20 minutos de inactividad
SESSION_COOKIE_AGE = 1200  # 1200 segundos = 20 minutos

# Cada request renueva el tiempo de sesión
SESSION_SAVE_EVERY_REQUEST = True

# ── GROQ (capa gramatical LSC) ─────────────────────────
import os
os.environ['GROQ_API_KEY'] = config('GROQ_API_KEY', default='')


ALLOWED_HOSTS = ['localhost', '127.0.0.1', '10.4.1.54', '.onrender.com', '.up.railway.app']

# Railway specific domains
railway_domain = config('RAILWAY_PUBLIC_DOMAIN', default='')
if railway_domain:
    ALLOWED_HOSTS.append(railway_domain)
    CSRF_TRUSTED_ORIGINS = [f'https://{railway_domain}']

# Configuración crucial para que Django sepa que está bajo HTTPS detrás del proxy de Railway
# Esto arregla el error "redirect_uri_mismatch" de Google (http vs https)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
