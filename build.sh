#!/usr/bin/env bash
set -o errexit
python -m pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate --noinput

# Création contrôlée du premier compte administrateur (facultatif).
if [[ -n "${TAFITA_BOOTSTRAP_ADMIN_USERNAME:-}" || \
      -n "${TAFITA_BOOTSTRAP_ADMIN_PASSWORD:-}" ]]; then

    if [[ -z "${TAFITA_BOOTSTRAP_ADMIN_USERNAME:-}" || \
          -z "${TAFITA_BOOTSTRAP_ADMIN_PASSWORD:-}" ]]; then
        echo "ERREUR : les variables administrateur sont incomplètes."
        exit 1
    fi

    python manage.py shell <<'PYADMIN'
import os
from django.contrib.auth import get_user_model

User = get_user_model()
field = User.USERNAME_FIELD
username = os.environ["TAFITA_BOOTSTRAP_ADMIN_USERNAME"]
password = os.environ["TAFITA_BOOTSTRAP_ADMIN_PASSWORD"]
email = os.environ.get("TAFITA_BOOTSTRAP_ADMIN_EMAIL", "").strip()

user = User.objects.filter(**{field: username}).first()

if user is None:
    user = User(**{field: username})
    if hasattr(user, "email") and email:
        user.email = email
    if hasattr(user, "is_staff"):
        user.is_staff = True
    if hasattr(user, "is_superuser"):
        user.is_superuser = True
    if hasattr(user, "is_active"):
        user.is_active = True

    user.set_password(password)
    user.save()
    print("Compte administrateur créé.")
elif getattr(user, "is_staff", False) and getattr(user, "is_superuser", False):
    reset_password = (
        os.environ.get("TAFITA_BOOTSTRAP_ADMIN_RESET_PASSWORD", "")
        .strip().lower() in {"1", "true", "yes"}
    )
    if reset_password:
        user.set_password(password)
        user.save(update_fields=["password"])
        print("Mot de passe du compte administrateur réinitialisé.")
    else:
        print("Le compte administrateur existe déjà ; mot de passe inchangé.")
else:
    raise SystemExit(
        "Ce nom existe déjà pour un compte non administrateur. "
        "Choisir un autre nom."
    )
PYADMIN
fi
