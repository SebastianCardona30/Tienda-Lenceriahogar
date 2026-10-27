"""
Configuración del proyecto "Lencería de Hogar Ciudad Bonita".

Todo sale de variables de entorno (.env); ver .env.example.
Base de datos: SQLite (WAL) por defecto vía DATABASE_URL; se puede pasar a
PostgreSQL cambiando solo DATABASE_URL, sin tocar código.
"""
from pathlib import Path
import os

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Carga variables de entorno desde .env (si existe).
load_dotenv(BASE_DIR / ".env")

# ¿Estamos corriendo en Vercel? (la variable VERCEL=1 la pone Vercel sola)
EN_VERCEL = os.environ.get("VERCEL", "").strip() in ("1", "true", "yes")

# Seguridad
SECRET_KEY = os.getenv("SECRET_KEY", "clave-insegura-solo-para-desarrollo-local")
# En Vercel se despliega siempre con DEBUG apagado (a menos que se pida lo contrario)
DEBUG = os.getenv("DEBUG", "False" if EN_VERCEL else "True").strip().lower() in ("1", "true", "yes", "on")
ALLOWED_HOSTS = [
    h.strip() for h in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()
]
# Dominios de Vercel (*.vercel.app) permitidos en producción
CSRF_TRUSTED_ORIGINS = [
    o.strip()
    for o in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",")
    if o.strip()
]
if EN_VERCEL:
    ALLOWED_HOSTS += [
        ".vercel.app",
        "vercel.app",
        os.environ.get("VERCEL_URL", ""),
        os.environ.get("VERCEL_PROJECT_PRODUCTION_URL", ""),
    ]
    ALLOWED_HOSTS = [h for h in ALLOWED_HOSTS if h]
    CSRF_TRUSTED_ORIGINS += [
        "https://*.vercel.app",
        f"https://{os.environ.get('VERCEL_PROJECT_PRODUCTION_URL', '')}",
    ]
    CSRF_TRUSTED_ORIGINS = [o for o in CSRF_TRUSTED_ORIGINS if not o.endswith("://")]

# Aplicaciones
INSTALLED_APPS = [
    "unfold",  # Admin personalizado en español (gratuito, MIT)
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    # 2FA para administradores (gratuito, MIT)
    "django_otp",
    "django_otp.plugins.otp_static",
    "django_otp.plugins.otp_totp",
    # Límite de intentos de login (gratuito, MIT)
    "axes",
    # Apps del proyecto
    "core",
    "accounts",
    "catalog",
    "cart",
    "orders",
    "payments",
    "shipping",
    "promotions",
    "inventory",
    "notifications",
    "dashboard",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # Sirve estáticos compilados sin servidor web dedicado (útil en hosting gratis)
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "axes.middleware.AxesMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.site_config",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Base de datos: SQLite por defecto; PostgreSQL solo cambiando DATABASE_URL.
DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
        conn_health_checks=True,
    )
}

if EN_VERCEL and DATABASES["default"]["ENGINE"] == "django.db.backends.sqlite3":
    # En Vercel el disco de la función es de solo lectura; solo /tmp se puede escribir.
    # En el despliegue (build.py) se "hornea" la base con los datos demo; aquí se copia
    # a /tmp en el primer arranque de cada instancia para poder escribir (sesiones, etc.).
    import shutil

    _db_origen = BASE_DIR / "db.sqlite3"
    _db_destino = Path("/tmp/ciudad-bonita.sqlite3")
    try:
        if _db_origen.exists() and not _db_destino.exists():
            _db_destino.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(_db_origen, _db_destino)
        if _db_destino.exists():
            DATABASES["default"]["NAME"] = str(_db_destino)
    except OSError:
        # Si algo falla, se usa la ruta original (en Vercel /tmp siempre existe)
        pass

# Contraseñas
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Límite de intentos de login (django-axes)
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 15  # minutos
AXES_LOCKOUT_CALLABLE = None
AXES_RESET_ON_SUCCESS = True

# Usuario personalizado (accounts.Usuario)
AUTH_USER_MODEL = "accounts.Usuario"
AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesBackend",
    "django.contrib.auth.backends.ModelBackend",
]

# Internacionalización: español de Colombia
LANGUAGE_CODE = "es-co"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True

# Idiomas disponibles (uno solo por ahora, la tienda es en español)
LANGUAGES = [("es", "Español")]

# Estáticos y medios
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        # whitenoise comprime y sirve los estáticos en hosting gratis
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

# Caché local en memoria (sin Redis)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "ciudad-bonita",
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Tipo de documento y moneda del negocio (configurable en core.SiteConfig)
DEFAULT_FROM_EMAIL = os.getenv(
    "DEFAULT_FROM_EMAIL", "Lenceria Ciudad Bonita <no-responder@ejemplo.com>"
)

# Correo: consola en desarrollo; SMTP opcional por .env en producción
EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True").strip().lower() in ("1", "true", "yes")
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")

# Seguridad HTTPS (activar en producción con SSL_REDIRECT=True)
SSL_REDIRECT = os.getenv("SSL_REDIRECT", "False").strip().lower() in ("1", "true", "yes")
if SSL_REDIRECT:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
if not DEBUG:
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Cabeceras de seguridad
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# Registro de errores en consola (crecer a archivo cuando haya hosting)
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "{levelname} {asctime} {name} {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "django.request": {"handlers": ["console"], "level": "WARNING", "propagate": False},
    },
}

# Configuración de django-unfold (admin en español)
UNFOLD = {
    "SITE_TITLE": "Ciudad Bonita - Panel",
    "SITE_HEADER": "Lencería de Hogar Ciudad Bonita",
    "SITE_SUBHEADER": "Administración de la tienda",
    "SITE_SYMBOL": "storefront",
    "SITE_DROPDOWN": [
        {
            "icon": "visibility",
            "title": "Ver la tienda",
            "link": "/",
        },
    ],
    "COLORS": {
        "primary": {
            "50": "#f6f0fb",
            "100": "#ece0f7",
            "200": "#dcc3ef",
            "300": "#c49ae3",
            "400": "#a86dd4",
            "500": "#8a4fbf",
            "600": "#7a3eab",
            "700": "#6b3396",
            "800": "#5b2a86",
            "900": "#4a2170",
            "950": "#33134d",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            {
                "title": "Tienda",
                "separator": True,
                "items": [
                    {"title": "Panel principal", "icon": "dashboard", "link": "/admin/"},
                ],
            },
        ],
    },
}
