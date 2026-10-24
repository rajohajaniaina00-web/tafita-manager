# TaFiTa Manager

**Application web de gestion d'association développée avec Django et JavaScript.**

TaFiTa Manager est un projet de gestion associative conçu pour centraliser les informations des membres, organiser les événements et faciliter le suivi des cotisations au sein d'une association.

## Fonctionnalités

- **Authentification** : connexion et déconnexion des utilisateurs.
- **Gestion des membres** : enregistrement et consultation des membres.
- **Gestion des événements** : création, modification et consultation des événements.
- **Gestion des cotisations** : suivi des cotisations des membres.
- **Tableau de bord** : accès centralisé aux principales informations de l'association.
- **Interface web** : navigation entre les différentes fonctionnalités.

## Technologies utilisées

- **Backend :** Python, Django
- **Base de données :** SQLite pour le développement local, selon la configuration du projet
- **Frontend :** HTML, CSS et JavaScript
- **Gestion de versions :** Git et GitHub

## Structure du projet

```text
tafita-manager/
├── accounts/
├── config/
├── contributions/
├── dashboard/
├── events/
├── members/
├── static/
├── templates/
├── manage.py
└── requirements.txt
```

## Installation locale

### 1. Cloner le dépôt

```bash
git clone https://github.com/rajohajaniaina00-web/tafita-manager.git
cd tafita-manager
```

### 2. Créer et activer un environnement virtuel

Sur macOS ou Linux :

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Installer les dépendances

```bash
python -m pip install -r requirements.txt
```

### 4. Préparer la base de données

```bash
python manage.py migrate
```

### 5. Créer un compte administrateur

```bash
python manage.py createsuperuser
```

### 6. Lancer le serveur de développement

```bash
python manage.py runserver
```

Ouvre ensuite [http://127.0.0.1:8000/](http://127.0.0.1:8000/) dans ton navigateur.

## Objectif du projet

Ce projet met en pratique le développement d'une application web avec Django, la structuration d'un backend, la gestion des données relationnelles et la création d'interfaces destinées aux utilisateurs.

## Auteur

**RAMANANA Hajaniaina Rajo David**

Développeur Web Junior — Python, Django, JavaScript

- GitHub : https://github.com/rajohajaniaina00-web

---

*Projet de portfolio à vocation pédagogique et professionnelle.*
