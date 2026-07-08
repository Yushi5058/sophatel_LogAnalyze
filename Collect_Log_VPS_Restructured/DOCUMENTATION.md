# 🛡️ Sophatel — Documentation technique (VPS Log Collector & Analytics)

Plateforme de collecte, analyse et visualisation des logs Nginx depuis des serveurs VPS.
Backend **FastAPI + PostgreSQL**, collecte **SSH/SFTP**, tableau de bord web.

## 📋 Table des matières

- [Architecture](#architecture)
- [Prérequis](#prérequis)
- [Installation](#installation)
- [Démarrage rapide](#démarrage-rapide)
- [Authentification & rôles](#authentification--rôles)
- [Endpoints API](#endpoints-api)
- [Scripts CLI](#scripts-cli)
- [Flux de données](#flux-de-données)
- [Configuration](#configuration)
- [Base de données](#base-de-données)
- [Migrations (Alembic)](#migrations-alembic)
- [Sécurité](#sécurité)
- [Troubleshooting](#troubleshooting)

---

## 🏗️ Architecture

```
Collect_Log_VPS_Restructured/
├── backend/                          ← FastAPI + PostgreSQL
│   ├── app/
│   │   ├── main.py                   ← Point d'entrée FastAPI (CORS, JWT, rate limiting, scheduler)
│   │   ├── core/
│   │   │   ├── config.py             ← Config API (source unique : DATABASE_URL, SECRET_KEY, CORS…)
│   │   │   ├── database.py           ← Moteur SQLAlchemy (utilise settings)
│   │   │   ├── security.py           ← JWT, hachage argon2 (pwdlib), require_role (RBAC)
│   │   │   ├── crypto.py             ← Chiffrement Fernet des identifiants VPS
│   │   │   └── ratelimit.py          ← Limiteur anti brute-force (slowapi)
│   │   ├── models/models.py          ← ORM (User, VPSServer, LogCollection, LogEntry, LogSummary, EndpointStat)
│   │   ├── schemas/schemas.py        ← Schémas Pydantic (+ validation log_path)
│   │   ├── routers/
│   │   │   ├── auth_router.py        ← /api/auth (login)
│   │   │   ├── vps.py                ← /api/vps (CRUD, mutations réservées admin)
│   │   │   ├── collect_router.py     ← /api/collect (admin)
│   │   │   ├── analyze_router.py     ← /api/analyze (admin)
│   │   │   ├── logs.py               ← /api/logs
│   │   │   ├── stats.py              ← /api/stats
│   │   │   └── endpoint_stats_router.py ← /api/endpoint-stats
│   │   └── core/scheduler.py         ← APScheduler (collecte + analyse)
│   ├── src/                          ← Cœur métier collecte/analyse
│   │   ├── config.py                 ← Config sous-système (chemins, USE_MOCK, SSH, vps.yaml)
│   │   ├── collector/                ← ssh_client (SFTP), runner, mock
│   │   └── analyzer/analyze.py       ← Parsing CSV → base (idempotent)
│   ├── alembic/versions/             ← Migrations de schéma
│   ├── config/vps.yaml               ← Inventaire VPS (utilisé par le scheduler)
│   ├── scripts/                      ← CLI (collect.py, analyze.py) + init_db.sql
│   ├── requirements.txt
│   └── .env                          ← Secrets (NON committé)
│
├── frontend/                         ← Coquille Angular 17 (charge le dashboard HTML en iframe)
│   └── src/assets/sophatel_nginx_v5_login.html   ← Frontend réel (login + appels API)
│
├── .venv/                            ← Environnement Python 3.12
├── .env.example                      ← Modèle de configuration
└── DOCUMENTATION.md                  ← Ce fichier (README court : à la racine du dépôt)
```

> **Note frontend :** l'application Angular sert principalement de coquille qui charge le tableau de bord
> **HTML statique** (`assets/sophatel_nginx_v5_login.html`) dans une iframe ; c'est ce HTML qui gère le
> login et tous les appels à l'API.

---

## ✅ Prérequis

- **Python 3.12** (cible du projet)
- **PostgreSQL** (testé sur PostgreSQL 18, service démarré)
- **Node.js 18+** + npm (pour le frontend Angular)
- **Git**

```bash
python --version        # 3.12.x
psql --version          # PostgreSQL 14+ (18 recommandé)
node --version          # 18+
```

---

## 📦 Installation

### 1. Environnement Python 3.12

```bash
cd Collect_Log_VPS_Restructured
python -m venv .venv
.venv\Scripts\activate            # Windows  (Linux/Mac : source .venv/bin/activate)
pip install -r backend/requirements.txt
```

### 2. Base de données PostgreSQL

Créer une base (ex. `sophatel_logs`) et un accès. Exemple minimal :

```bash
set PGPASSWORD=<mdp_postgres>
psql -U postgres -c "CREATE DATABASE sophatel_logs;"
```

> Le schéma est géré par **Alembic** (voir plus bas). Le script `scripts/init_db.sql` fournit aussi des
> extensions et des vues pratiques.

### 3. Configuration `.env`

```bash
copy .env.example backend\.env    # Windows  (Linux/Mac : cp .env.example backend/.env)
```

Renseigner au minimum `DATABASE_URL`, `SECRET_KEY`, `CREDENTIALS_KEY`, `ADMIN_PASSWORD`
(voir [Configuration](#configuration)).

### 4. Migrations de schéma

```bash
cd backend
alembic upgrade head
```

### 5. Frontend (optionnel, pour le mode Angular)

```bash
cd frontend
npm install
```

---

## 🚀 Démarrage rapide

### Backend FastAPI

```bash
cd backend
..\.venv\Scripts\activate
uvicorn app.main:app --host 127.0.0.1 --port 8000
# Swagger : http://localhost:8000/docs   |   ReDoc : http://localhost:8000/redoc
```

Au premier démarrage, un compte **admin** est créé à partir de `ADMIN_PASSWORD`
(ou un mot de passe aléatoire affiché une fois dans les logs si non défini).

### Frontend Angular (optionnel)

```bash
cd frontend
npm start        # http://localhost:4200
```

### Collecte & analyse rapides (mock)

```bash
cd backend
..\.venv\Scripts\activate
python scripts/collect.py --mock --all      # génère des logs simulés
python scripts/analyze.py --file logs/<vps>/<fichier>.csv --vps <vps>
```

---

## 🔐 Authentification & rôles

- **Login** : `POST /api/auth/login` (form `username`/`password`) → renvoie un token **JWT**.
- Le client renvoie ce token dans l'en-tête `Authorization: Bearer <token>`.
- **Toutes** les routes (hors `/api/auth`, `/`, `/health`) exigent un token valide.
- **Rôles** : `admin` (tout) et `viewer` (lecture seule). Les mutations (créer/modifier/supprimer un
  VPS, collecte, analyse, recalcul) sont **réservées à `admin`** (sinon `403`).
- **Anti brute-force** : `POST /api/auth/login` est limité à **5 tentatives/minute par IP** (`429` au-delà).

---

## 🔌 Endpoints API

Légende : 🔓 public · 🔑 JWT requis · 👑 rôle `admin` requis.

### Auth
| Méthode | Endpoint | Accès | Description |
|---|---|---|---|
| POST | `/api/auth/login` | 🔓 | Authentifie, renvoie un JWT |
| GET | `/api/auth/me` | 🔑 | Profil de l'utilisateur connecté |

### VPS
| Méthode | Endpoint | Accès | Description |
|---|---|---|---|
| GET | `/api/vps/` | 🔑 | Liste des VPS |
| GET | `/api/vps/{id}` | 🔑 | Détails d'un VPS |
| POST | `/api/vps/` | 👑 | Créer un VPS |
| PUT | `/api/vps/{id}` | 👑 | Modifier un VPS (identifiants inclus, chiffrés) |
| DELETE | `/api/vps/{id}` | 👑 | Supprimer un VPS (+ ses données) |

### Collecte & analyse
| Méthode | Endpoint | Accès | Description |
|---|---|---|---|
| POST | `/api/collect/{vps_id}` | 👑 | Collecte les logs (SSH/SFTP ou mock) → CSV |
| POST | `/api/analyze/{vps_id}` | 👑 | Analyse le dernier CSV → base |

### Logs & collections
| Méthode | Endpoint | Accès | Params |
|---|---|---|---|
| GET | `/api/logs/collections` | 🔑 | `vps_id?`, `limit=50` |
| GET | `/api/logs/collections/{id}` | 🔑 | — |
| GET | `/api/logs/collections/{id}/entries` | 🔑 | `page`, `size`, `status?`, `method?`, `ip?` |
| GET | `/api/logs/collections/{id}/summary` | 🔑 | — |

### Stats & endpoint-stats
| Méthode | Endpoint | Accès | Description |
|---|---|---|---|
| GET | `/api/stats/global` | 🔑 | KPIs (latences P50/P95/P99, taux 4xx/5xx…) |
| GET | `/api/stats/status-distribution` | 🔑 | Distribution des codes HTTP |
| GET | `/api/stats/top-paths` · `/top-ips` | 🔑 | Top chemins / IP |
| GET | `/api/stats/requests-over-time` | 🔑 | Trafic par heure |
| GET | `/api/stats/endpoints` · `/alerts` | 🔑 | Métriques par endpoint / alertes seuillées |
| GET | `/api/endpoint-stats/` | 🔑 | Stats d'endpoints (tri/filtre/pagination) |
| GET | `/api/endpoint-stats/collection/{id}` | 🔑 | Stats d'une collection |
| POST | `/api/endpoint-stats/compute/{id}` | 👑 | Recalcul à la demande |

### Divers
| Méthode | Endpoint | Accès | Description |
|---|---|---|---|
| GET | `/api/scheduler/jobs` | 🔑 | Jobs planifiés |
| GET | `/` · `/health` | 🔓 | Health checks |

---

## 📜 Scripts CLI

### `collect.py` — Collecte des logs
```bash
python scripts/collect.py --mock --all          # simulation (sans SSH)
python scripts/collect.py --vps vps-prod-01      # SSH réel
```
Crée des fichiers `.log` et `.csv` dans `logs/<vps>/`.

### `analyze.py` — Analyse CSV → base
```bash
python scripts/analyze.py --file logs/<vps>/<fichier>.csv --vps <vps>
```
Insère les entrées (`log_entries`), le résumé (`log_summaries`) et les stats d'endpoints.

> **Encodage Windows :** en cas de `UnicodeEncodeError`, préfixer par `set PYTHONIOENCODING=utf-8`.

---

## 🔄 Flux de données

```
VPS (nginx access.log)
      │  SSH / SFTP (sans shell)
      ▼
src/collector (ssh_client, runner, mock)
      │  écrit
      ▼
logs/<vps>/nginx_logs_<date>.log + .csv
      │  parsing
      ▼
src/analyzer/analyze.py  (idempotent : chaque CSV analysé une seule fois)
      │
      ▼
PostgreSQL (sophatel_logs)
  users · vps_servers · log_collections · log_entries · log_summaries · endpoint_stats
      │
      ▼
API FastAPI (/api/*)  ──>  Frontend (dashboard HTML) http://localhost:4200
```

---

## ⚙️ Configuration

### `backend/.env`

| Variable | Rôle |
|---|---|
| `DATABASE_URL` | Connexion PostgreSQL (**obligatoire**) — ex. `postgresql://postgres:...@localhost:5432/sophatel_logs` |
| `SECRET_KEY` | Signature JWT (**obligatoire**) — `openssl rand -hex 32` |
| `CREDENTIALS_KEY` | Clé Fernet (chiffrement des identifiants VPS) ; sinon dérivée de `SECRET_KEY` |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | Compte admin initial |
| `CORS_ORIGINS` | Origines autorisées (séparées par des virgules) |
| `DEBUG` | `false` en prod (n'expose pas le détail des erreurs) |
| `LOG_DIR` / `DATA_DIR` | Répertoires de sortie |
| `USE_MOCK` | `true` = logs simulés (sans SSH) |
| `SSH_KEY_PATH` / `SSH_PASSPHRASE` | Clé locale de repli / passphrase |
| `SSH_KNOWN_HOSTS` / `SSH_STRICT_HOST_KEY` | Vérification de la clé d'hôte (anti-MITM) |

### `config/vps.yaml` — inventaire utilisé par le scheduler

```yaml
vps:
  - name: vps-prod-01
    host: 192.168.1.10
    user: root
    port: 22
    key_path: ~/.ssh/id_rsa
    log_path: /var/log/nginx/access.log
```

---

## 📊 Base de données

Tables principales : `users`, `vps_servers`, `log_collections`, `log_entries`, `log_summaries`,
`endpoint_stats`.

- `vps_servers` : `password` et `ssh_key` sont **chiffrés au repos** (Fernet).
- Vues pratiques (via `init_db.sql`) : `v_vps_summary`, `v_top_paths`.

---

## 🧬 Migrations (Alembic)

```bash
cd backend
alembic upgrade head              # applique les migrations
alembic revision --autogenerate -m "message"   # génère une migration depuis les modèles
alembic current                   # révision courante
```

`env.py` lit `DATABASE_URL` depuis l'environnement (l'URL d'`alembic.ini` est un placeholder surchargé).

---

## 🔒 Sécurité

Le backend a été audité et durci :

- **Collecte via SFTP** (aucune commande shell) + validation des chemins → pas d'injection.
- **Mots de passe** hachés en **argon2** (pwdlib) ; **identifiants VPS chiffrés** (Fernet).
- **Secrets hors du code** (`.env`), validés au démarrage ; `DEBUG=false` par défaut ; erreurs
  génériques côté client (détail complet en logs serveur).
- **RBAC** (admin/viewer) sur les mutations ; **rate limiting** anti brute-force sur `/login`.
- **CORS restreint** (méthodes/en-têtes/origines) ; **vérification de la clé d'hôte SSH** (anti-MITM).
- Ne **jamais** committer `.env` ni les clés privées SSH.

---

## 🆘 Troubleshooting

**PostgreSQL « connection refused »** — vérifier que le service tourne et tester
`psql -U postgres -h localhost -d sophatel_logs`.

**`RuntimeError: Variables d'environnement manquantes`** — `SECRET_KEY` et/ou `DATABASE_URL` absentes
du `.env`. Les renseigner.

**`UnicodeEncodeError` (scripts)** — `set PYTHONIOENCODING=utf-8` avant de lancer le script.

**`HTTP 429` au login** — limite anti brute-force atteinte (5/min par IP) ; patienter une minute.

**`HTTP 403` sur une action** — le compte est `viewer` ; une action de modification requiert `admin`.

**Module introuvable** — vérifier que le venv 3.12 est activé et les dépendances installées.

---

**Sophatel VPS Log Collector** — Backend FastAPI + SQLAlchemy + PostgreSQL · Frontend Angular 17 / HTML.
Voir aussi le [README du dépôt](../README.md) (présentation courte) et `/docs` (API interactive).
