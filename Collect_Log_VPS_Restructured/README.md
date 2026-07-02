# 🛡️ Sophatel — VPS Log Collector & Analytics Dashboard

Plateforme complète de collecte, analyse et visualisation des logs Nginx depuis vos serveurs VPS.

## 📋 Table des matières

- [Architecture](#architecture)
- [Prérequis](#prérequis)
- [Installation](#installation)
- [Démarrage rapide](#démarrage-rapide)
- [Scripts CLI](#scripts-cli)
- [Endpoints API](#endpoints-api)
- [Flux de données](#flux-de-données)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)

---

## 🏗️ Architecture

```
Collect_Log_VPS_Restructured/
├── backend/                          ← FastAPI + PostgreSQL
│   ├── app/
│   │   ├── main.py                  ← Point d'entrée FastAPI
│   │   ├── core/
│   │   │   ├── config.py            ← Configuration (DATABASE_URL, etc.)
│   │   │   └── database.py          ← Connexion PostgreSQL + SQLAlchemy
│   │   ├── models/
│   │   │   └── models.py            ← ORM SQLAlchemy (VPSServer, LogCollection, LogEntry, LogSummary)
│   │   ├── schemas/
│   │   │   └── schemas.py           ← Schémas Pydantic (validation requêtes/réponses)
│   │   ├── routers/
│   │   │   ├── logs.py              ← GET /api/logs/*
│   │   │   ├── stats.py             ← GET /api/stats/*
│   │   │   └── vps.py               ← GET/POST/DELETE /api/vps/*
│   │   └── services/
│   │       └── analyze_service.py   ← Déclenche analyze.py via subprocess
│   ├── scripts/
│   │   ├── init_db.sql              ← Initialisation PostgreSQL (base sophatel_v2)
│   │   ├── collect.py               ← CLI collecte logs (SSH ou mock)
│   │   ├── analyze.py               ← CLI analyse CSV → base de données
│   │   └── dashboard.py             ← (Prototype)
│   ├── alembic/                     ← Migrations DB (optionnel)
│   ├── venv/                        ← Environnement Python
│   ├── .env                         ← Variables d'env (DATABASE_URL, SECRET_KEY, etc.)
│   ├── requirements.txt             ← Dépendances Python
│   ├── config/                      ← Dossier de config (consolidé depuis racine)
│   │   └── vps.yaml                 ← Inventaire VPS (SSH host, user, port)
│   ├── src/                         ← Code métier (consolidé depuis racine)
│   │   ├── config.py                ← Chargement vps.yaml
│   │   ├── collector/               ← Logique collecte (SSH, mock)
│   │   └── analyzer/                ← Logique analyse (parsing, statistiques)
│   └── logs/                        ← Dossier logs collectés (consolidé depuis racine)
│       ├── vps-prod-01/
│       ├── vps-prod-02/
│       └── vps-staging-01/
│
├── frontend/                         ← Angular 17 Dashboard
│   ├── src/
│   │   ├── app/
│   │   │   ├── core/
│   │   │   │   ├── services/
│   │   │   │   │   └── api.service.ts       ← Appels HTTP vers backend
│   │   │   │   └── models/models.ts         ← Types TypeScript
│   │   │   ├── features/
│   │   │   │   ├── dashboard/               ← Page KPIs globales
│   │   │   │   ├── logs/                    ← Page recherche/filtrage entrées
│   │   │   │   └── vps/                     ← Gestion VPS
│   │   │   └── shared/components/
│   │   └── index.html
│   ├── package.json
│   └── angular.json
│
├── .git/                             ← Historique git
└── README.md                         ← Ce fichier
```

---

## ✅ Prérequis

- **Python 3.11+**
- **PostgreSQL 14+** (avec service running)
- **Node.js 18+** + npm
- **Git**

### Vérification

```bash
python --version        # Python 3.11+
psql --version          # PostgreSQL 14+
node --version          # Node 18+
npm --version           # npm 9+
```

---

## 📦 Installation

### 1. Cloner & accéder au projet

```bash
cd C:\Users\info\Downloads\Collect_Log_VPS_Restructured\Collect_Log_VPS_Restructured
```

### 2. Backend - Créer la base de données

```bash
# Se placer dans le répertoire backend
cd backend

# Exécuter le script d'initialisation PostgreSQL
# (Remplacer admin123 par le mot de passe PostgreSQL)
set PGPASSWORD=admin123
psql -U postgres -f scripts/init_db.sql

# Vérifier la création
psql -U postgres -d sophatel_v2 -c "SELECT COUNT(*) FROM log_entries;"
# Devrait retourner 0 au départ
```

### 3. Backend - Installer Python & dépendances

```bash
# Créer venv (si pas déjà fait)
python -m venv venv

# Activer venv
# Sur Windows:
venv\Scripts\activate
# Sur Linux/Mac:
# source venv/bin/activate

# Installer dépendances
pip install -r requirements.txt
```

### 4. Backend - Vérifier le .env

```bash
# Le fichier .env doit contenir:
cat .env

# Doit ressembler à:
# DATABASE_URL=postgresql://sophatel:sophatel@localhost/sophatel_v2
# SECRET_KEY=your-secret-key-here
# DEBUG=false
# LOG_DIR=logs
# DATA_DIR=data
```

### 5. Frontend - Installer dépendances Angular

```bash
# Depuis la racine du projet
cd frontend

npm install
```

---

## 🚀 Démarrage rapide

### Terminal 1 - Backend FastAPI

```bash
cd backend
venv\Scripts\activate
uvicorn app.main:app --reload --port 8000

# Swagger auto disponible: http://localhost:8000/docs
# ReDoc disponible: http://localhost:8000/redoc
```

### Terminal 2 - Frontend Angular

```bash
cd frontend

npm start
# Accessible: http://localhost:4200
```

### Terminal 3 - Collecte & Analyse (optionnel)

```bash
cd backend
venv\Scripts\activate

# Collecte mock (génère logs aléatoires)
python scripts/collect.py --mock --all

# Lancer l'analyse sur les fichiers collectés
python scripts/analyze.py --file logs/vps-prod-01/nginx_logs_2026-06-09_19-41-52.csv --vps vps-prod-01
```

---

## 📜 Scripts CLI

### `collect.py` - Collecte des logs

```bash
# Mode interactif (choisir les VPS)
python scripts/collect.py

# Collecte tous les VPS en mock (simulation)
python scripts/collect.py --mock --all

# Collecter un VPS spécifique (SSH réel)
python scripts/collect.py --vps vps-prod-01

# Collecter depuis un fichier config spécifique
python scripts/collect.py --config /path/to/custom.yaml --all
```

**Output:** Crée des fichiers `.log` et `.csv` dans `logs/<vps_name>/`

### `analyze.py` - Analyse CSV → Base de données

```bash
# Mode interactif (choisir le fichier CSV)
python scripts/analyze.py

# Analyser un fichier spécifique
python scripts/analyze.py --file logs/vps-prod-01/nginx_logs_2026-06-09_19-41-52.csv --vps vps-prod-01

# Analyser et définir le mode
python scripts/analyze.py --file logs/vps-prod-01/nginx.csv --vps vps-prod-01 --mode ssh
```

**Output:** Insère les entrées dans `log_entries` et résumé dans `log_summaries`

### `dashboard.py` - Prototype CLI

```bash
python scripts/dashboard.py
```

---

## 🔌 Endpoints API

### VPS Management

| Méthode | Endpoint      | Description              | Params                    |
|---------|---------------|--------------------------|---------------------------|
| GET     | `/api/vps/`   | Liste des VPS            | -                         |
| POST    | `/api/vps/`   | Ajouter un VPS           | `name`, `host`, `user`    |
| GET     | `/api/vps/{id}` | Détails d'un VPS       | -                         |
| DELETE  | `/api/vps/{id}` | Supprimer un VPS       | -                         |

### Logs & Collections

| Méthode | Endpoint                                | Description                  | Params                        |
|---------|----------------------------------------|------------------------------|-------------------------------|
| GET     | `/api/logs/collections`                | Liste des collections        | `vps_id` (opt), `limit=50`    |
| GET     | `/api/logs/collections/{id}`           | Détails collection           | -                             |
| GET     | `/api/logs/collections/{id}/entries`   | Entrées paginées + filtres   | `page=1`, `size=100`, `status`, `method`, `ip` |
| GET     | `/api/logs/collections/{id}/summary`   | Résumé analytique            | -                             |

### Stats & Analytics

| Méthode | Endpoint                       | Description              | Params   |
|---------|--------------------------------|--------------------------|----------|
| GET     | `/api/stats/global`            | KPIs globaux (dashboard) | `vps_id` |
| GET     | `/api/stats/status-distribution` | Distribution codes HTTP  | -        |
| GET     | `/api/stats/top-paths`         | Top 20 chemins           | `limit`  |
| GET     | `/api/stats/top-ips`           | Top IPs les plus actives | `limit`  |
| GET     | `/api/stats/requests-over-time`| Requêtes/heure           | -        |
| GET     | `/api/stats/endpoints`         | Stats par endpoint       | -        |
| GET     | `/api/stats/alerts`            | Alertes (taux erreurs)   | -        |

---

## 🔄 Flux de données

```
┌─────────────────┐
│  VPS (SSH)      │
│ nginx access.log│
└────────┬────────┘
         │
         ▼
┌─────────────────────┐
│  src/collector/     │
│  - ssh_client.py    │ ← Connexion SSH + récupération logs
│  - mock.py          │ ← Génération mock pour tests
└────────┬────────────┘
         │
         ▼
┌──────────────────────┐
│  logs/<vps>/         │
│  nginx.log (brut)    │
│  nginx.csv (parsé)   │
└────────┬─────────────┘
         │
         ▼
┌──────────────────────┐
│  src/analyzer/       │
│  analyze.py          │ ← Parsing CSV + stats
└────────┬─────────────┘
         │
         ▼
┌────────────────────────────────┐
│  PostgreSQL (sophatel_v2)      │
│  ├── vps_servers               │
│  ├── log_collections           │
│  ├── log_entries (1500 lignes) │
│  └── log_summaries             │
└────────┬───────────────────────┘
         │
         ▼
┌──────────────────────┐
│  FastAPI Backend     │
│  /api/logs/*         │
│  /api/stats/*        │
│  /api/vps/*          │
└────────┬─────────────┘
         │
         ▼
┌──────────────────────┐
│  Angular Frontend    │
│  http://localhost:4200
│  - Dashboard (KPIs)  │
│  - Logs (recherche)  │
│  - VPS (gestion)     │
└──────────────────────┘
```

---

## ⚙️ Configuration

### `.env` - Variables d'environnement

```bash
# Base de données PostgreSQL
DATABASE_URL=postgresql://sophatel:sophatel@localhost/sophatel_v2

# Clé secrète API (FastAPI)
SECRET_KEY=your-super-secret-key-change-me

# Mode debug (dev: true, prod: false)
DEBUG=false

# Répertoires
LOG_DIR=logs
DATA_DIR=data
```

### `config/vps.yaml` - Inventaire VPS

```yaml
vps:
  - name: vps-prod-01
    host: 192.168.1.10
    user: root
    port: 22
    ssh_key: ~/.ssh/id_rsa

  - name: vps-prod-02
    host: 192.168.1.11
    user: ubuntu
    port: 22

  - name: vps-staging-01
    host: 192.168.1.20
    user: root
    port: 2222
```

---

## 📊 Base de données

### Tables principales

#### `vps_servers`
```sql
id | name | host | user | port | created_at
```

#### `log_collections`
```sql
id | vps_id | collected_at | total_lines | mode | status
```

#### `log_entries`
```sql
id | collection_id | ip | timestamp | method | path | status | size | response_time
```

#### `log_summaries`
```sql
id | collection_id | total_requests | error_count | unique_ips | avg_resp_time
```

### Vues pratiques

- **`v_vps_summary`** - Résumé par VPS (nb collections, requêtes totales, etc.)
- **`v_top_paths`** - Top 20 chemins les plus visités

---

## 🆘 Troubleshooting

### ❌ "CONNECTION REFUSED" PostgreSQL

```bash
# Vérifier si PostgreSQL tourne
# Windows: Services → PostgreSQL 18
# Linux: sudo systemctl status postgresql

# Ou tester la connexion
psql -U postgres -h localhost -d sophatel_v2
```

### ❌ "UnicodeEncodeError" lors de collect.py

```bash
# Solution: définir l'encodage Python
set PYTHONIOENCODING=utf-8
python scripts/collect.py --mock --all
```

### ❌ Backend retourne "Module not found"

```bash
# Vérifier que le venv est activé
venv\Scripts\activate

# Vérifier les dépendances
pip install -r requirements.txt
```

### ❌ Frontend affiche "Cannot GET /api/..."

```bash
# Vérifier que le backend tourne sur port 8000
# http://localhost:8000/docs

# Vérifier la config environment.ts
# src/environments/environment.ts doit avoir:
# apiUrl: 'http://localhost:8000'
```

### ❌ Seulement 50 entrées affichées

C'est la pagination par défaut (100 par page) — utilise les boutons de pagination pour voir les autres pages.

```bash
# Vérifier le total en BD:
psql -U postgres -d sophatel_v2 -c "SELECT COUNT(*) FROM log_entries;"
```

---

## 📈 Exemple d'utilisation

### Scénario complet

```bash
# 1. Démarrer le backend
cd backend && venv\Scripts\activate && uvicorn app.main:app --reload

# 2. Dans un autre terminal - Collecter les logs
cd backend
python scripts/collect.py --mock --all

# 3. Analyser les logs
python scripts/analyze.py --file logs/vps-prod-01/nginx_logs_2026-06-09_19-41-52.csv --vps vps-prod-01
python scripts/analyze.py --file logs/vps-prod-02/nginx_logs_2026-06-09_19-41-52.csv --vps vps-prod-02
python scripts/analyze.py --file logs/vps-staging-01/nginx_logs_2026-06-09_19-41-52.csv --vps vps-staging-01

# 4. Démarrer le dashboard
cd frontend && npm start

# 5. Accéder au dashboard
# http://localhost:4200 ✅
```

---

## 🔒 Sécurité

- **Clés SSH:** Stocker dans `~/.ssh/` (ne pas commiter)
- **Secrets:** Utiliser `.env` (ne pas commiter `.env`, inclure `.env.example`)
- **BD:** Mot de passe PostgreSQL forte (`admin123` est pour DEV uniquement)
- **API:** CORS limité à `http://localhost:4200` en dev

---

## 📝 Licences & Crédits

**Sophatel VPS Log Collector** - 2026
- Backend: FastAPI + SQLAlchemy + PostgreSQL
- Frontend: Angular 17 + TypeScript
- CLI: Python 3.11

---

## 📞 Support

Pour toute question ou bug, ouvre une issue sur le repository.

**Dernière mise à jour:** 2026-06-09
