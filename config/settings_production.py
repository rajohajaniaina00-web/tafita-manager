"""
Configuration de production de TaFiTa Manager.
Ne pas utiliser pour le développement local.
"""

import os
from .settings import *

# Secrets et hôtes fournis par l'environnement d'hébergement
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
DEBUG = False

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ["DJANGO_ALLOWED_HOSTS"].split(",")
    if host.strip()
]

# Protection HTTPS : à utiliser uniquement lorsque HTTPS fonctionne
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Fichiers statiques collectés pour le déploiement
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Paramètres adaptés à Madagascar
LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Indian/Antananarivo"
USE_I18N = True
USE_TZ = True
