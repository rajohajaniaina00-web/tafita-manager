"""Paramètres de production pour Render."""
import os

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

from .settings import *


def required_env(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise ImproperlyConfigured(
            f"La variable d'environnement {name} est obligatoire."
        )
    return value


def env_list(name):
    return [
        item.strip()
        for item in os.environ.get(name, "").split(",")
        if item.strip()
    ]


DEBUG = False

SECRET_KEY = required_env("DJANGO_SECRET_KEY")
if len(SECRET_KEY) < 32 or SECRET_KEY.startswith("django-insecure-"):
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY doit être une clé de production longue et aléatoire."
    )

render_hostname = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "").strip()
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS")
if render_hostname:
    ALLOWED_HOSTS.append(render_hostname)
ALLOWED_HOSTS = list(dict.fromkeys(ALLOWED_HOSTS))

if not ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        "Configure DJANGO_ALLOWED_HOSTS ou RENDER_EXTERNAL_HOSTNAME."
    )

CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")
if render_hostname:
    CSRF_TRUSTED_ORIGINS.append(f"https://{render_hostname}")
CSRF_TRUSTED_ORIGINS = list(dict.fromkeys(CSRF_TRUSTED_ORIGINS))

# Base PostgreSQL fournie par Render via DATABASE_URL.
database_url = required_env("DATABASE_URL")
if not database_url.startswith(("postgres://", "postgresql://")):
    raise ImproperlyConfigured(
        "DATABASE_URL doit pointer vers une base PostgreSQL en production."
    )

DATABASES = {
    "default": dj_database_url.parse(
        database_url,
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# Fichiers statiques : WhiteNoise, placé après SecurityMiddleware.
MIDDLEWARE = list(MIDDLEWARE)
whitenoise_middleware = "whitenoise.middleware.WhiteNoiseMiddleware"
security_middleware = "django.middleware.security.SecurityMiddleware"

if whitenoise_middleware not in MIDDLEWARE:
    if security_middleware not in MIDDLEWARE:
        raise ImproperlyConfigured(
            "SecurityMiddleware est introuvable dans MIDDLEWARE."
        )
    MIDDLEWARE.insert(
        MIDDLEWARE.index(security_middleware) + 1,
        whitenoise_middleware,
    )

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
WHITENOISE_MANIFEST_STRICT = False

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# HTTPS derrière le proxy de Render.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_HSTS_SECONDS = int(
    os.environ.get("DJANGO_SECURE_HSTS_SECONDS", "0")
)

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Indian/Antananarivo"
USE_I18N = True
USE_TZ = True

# Pour la démonstration scolaire, les e-mails sont consignés dans les logs.
# Le SMTP peut être configuré ultérieurement avec un fournisseur compatible.
email_host = os.environ.get("DJANGO_EMAIL_HOST", "").strip()

if email_host:
    email_use_tls = (
        os.environ.get("DJANGO_EMAIL_USE_TLS", "true").lower()
        in {"1", "true", "yes", "on"}
    )
    email_use_ssl = (
        os.environ.get("DJANGO_EMAIL_USE_SSL", "false").lower()
        in {"1", "true", "yes", "on"}
    )
    if email_use_tls and email_use_ssl:
        raise ImproperlyConfigured(
            "Choisir TLS ou SSL implicite, pas les deux."
        )

    MAILERS = {
        "default": {
            "BACKEND": "django.core.mail.backends.smtp.EmailBackend",
            "OPTIONS": {
                "host": email_host,
                "port": int(os.environ.get("DJANGO_EMAIL_PORT", "587")),
                "username": os.environ.get("DJANGO_EMAIL_USER", ""),
                "password": os.environ.get("DJANGO_EMAIL_PASSWORD", ""),
                "use_tls": email_use_tls,
                "use_ssl": email_use_ssl,
                "timeout": 10,
            },
        },
    }
else:
    MAILERS = {
        "default": {
            "BACKEND": "django.core.mail.backends.console.EmailBackend",
            "OPTIONS": {},
        },
    }

DEFAULT_FROM_EMAIL = os.environ.get(
    "DJANGO_DEFAULT_FROM_EMAIL", "webmaster@localhost"
)
SERVER_EMAIL = DEFAULT_FROM_EMAIL
