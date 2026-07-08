# 🛡️ Sophatel — Supervision des logs Nginx (VPS Log Analyzer)

Plateforme de **collecte, analyse et visualisation** des logs d'accès Nginx de plusieurs serveurs
**VPS**. Le backend se connecte en **SSH** aux serveurs, récupère les journaux Nginx, les parse,
les stocke dans **PostgreSQL** et expose des **statistiques** (trafic, latences, taux d'erreurs,
top endpoints/IP, alertes) via une **API REST** consommée par un tableau de bord web.

> Le dossier applicatif est [`Collect_Log_VPS_Restructured/`](Collect_Log_VPS_Restructured/) — voir la
> [documentation technique](Collect_Log_VPS_Restructured/DOCUMENTATION.md) pour le détail complet
> (endpoints, flux de données, scripts CLI…).

---

## 🧱 Stack technique

| Couche | Techno |
|---|---|
| API | **FastAPI** (Python 3.12), SQLAlchemy 2, JWT |
| Base de données | **PostgreSQL** (migrations **Alembic**) |
| Collecte | **Paramiko** (SSH/SFTP) + parsing regex Nginx |
| Ordonnancement | **APScheduler** (collecte + analyse périodiques) |
| Frontend | HTML/JS statique servi via une coquille **Angular 17** (iframe) |

---

## 🏗️ Architecture (vue d'ensemble)

```
Navigateur ──> Frontend (HTML statique) ──> API FastAPI ──> PostgreSQL
                                              │
                                              ├─ Collecte SSH/SFTP ──> VPS distants (/var/log/nginx)
                                              ├─ Analyse CSV ──────────> log_entries / summaries / endpoint_stats
                                              └─ Scheduler (collecte + analyse)
```

- **backend/app/** : API (routers, modèles ORM, schémas, sécurité, config).
- **backend/src/** : cœur métier collecte/analyse (`collector/`, `analyzer/`).
- **backend/alembic/** : migrations de schéma.
- **frontend/** : application Angular (charge le tableau de bord HTML en iframe).

---

## 🚀 Démarrage rapide (dev)

> Cible **Python 3.12** et **PostgreSQL** en local.

```bash
# 1. Environnement Python 3.12
cd Collect_Log_VPS_Restructured
python -m venv .venv
.venv\Scripts\activate            # Windows  (ou: source .venv/bin/activate)
pip install -r backend/requirements.txt

# 2. Base de données PostgreSQL (exemple)
#    créer une base, puis renseigner DATABASE_URL dans backend/.env

# 3. Configuration : copier l'exemple et compléter les secrets
copy .env.example backend\.env    # Windows  (ou: cp .env.example backend/.env)
#    -> définir SECRET_KEY, DATABASE_URL, CREDENTIALS_KEY, ADMIN_PASSWORD…

# 4. Migrations de schéma
cd backend
alembic upgrade head

# 5. Lancer l'API
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

API disponible sur `http://127.0.0.1:8000` — documentation interactive : `/docs`.
Le compte **admin** initial est créé au 1er démarrage à partir de `ADMIN_PASSWORD`
(ou un mot de passe aléatoire journalisé une seule fois si non défini).

---

## 🔑 Variables d'environnement principales (`backend/.env`)

| Variable | Rôle |
|---|---|
| `DATABASE_URL` | Connexion PostgreSQL (**obligatoire**) |
| `SECRET_KEY` | Clé de signature des tokens JWT (**obligatoire**, `openssl rand -hex 32`) |
| `CREDENTIALS_KEY` | Clé Fernet de chiffrement des identifiants VPS (sinon dérivée de `SECRET_KEY`) |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | Compte admin initial |
| `CORS_ORIGINS` | Origines autorisées (séparées par des virgules) |
| `DEBUG` | `false` en production (n'expose pas le détail des erreurs) |
| `USE_MOCK` | `true` = génère des logs simulés (sans SSH) |
| `SSH_STRICT_HOST_KEY` | `true` = rejette les hôtes SSH inconnus (sinon TOFU) |
| `SSH_KEY_PATH`, `SSH_PASSPHRASE`, `SSH_KNOWN_HOSTS` | Paramètres SSH |

Un modèle est fourni dans [`Collect_Log_VPS_Restructured/.env.example`](Collect_Log_VPS_Restructured/.env.example).
Le fichier `.env` **ne doit jamais être committé**.

---

## 🔐 Authentification & rôles

- Connexion par **JWT** : `POST /api/auth/login` (form `username`/`password`) → token `Bearer`.
- Toutes les routes (hors `/api/auth`) exigent un token valide.
- **Rôles** : `admin` (tout pouvoir) et `viewer` (lecture seule). Les actions de **modification**
  (créer/supprimer un VPS, lancer collecte/analyse) sont **réservées à `admin`**.

---

## 🛡️ Sécurité (durcissements appliqués)

Le backend a fait l'objet d'un audit et d'un durcissement progressif :

- **Injection SSH éliminée** : lecture des logs via **SFTP** (aucune commande shell) + validation des chemins.
- **Secrets hors du code** : `SECRET_KEY`, mots de passe et clés en variables d'environnement ; échec au
  démarrage si absents ; plus de secrets dans les logs.
- **Mots de passe** hachés en **argon2** (pwdlib).
- **Identifiants VPS chiffrés au repos** (Fernet).
- **RBAC** sur les routes sensibles ; **rate limiting** anti brute-force sur `/login`.
- **CORS restreint** (méthodes/headers/origines) ; **erreurs génériques** côté client (détail en logs).
- **Vérification de la clé d'hôte SSH** (anti-MITM) ; **migrations Alembic** opérationnelles.

---

## 📄 Documentation & suivi

- [Documentation technique](Collect_Log_VPS_Restructured/DOCUMENTATION.md) — endpoints, flux de données, scripts CLI.
- Documentation interactive de l'API : `http://127.0.0.1:8000/docs`.
