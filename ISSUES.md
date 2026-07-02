# Sophatel Log Analyzer — Liste des Issues

> Projet : Système de collecte, d'analyse et de visualisation des logs Nginx
> Stack : FastAPI + PostgreSQL + Angular 17

---

## ⚠️ Légende

| Icône | Priorité |
|-------|----------|
| 🔴 | Critique — bloquant |
| 🟡 | Moyen — important |
| 🟢 | Amélioration — nice to have |

---

## 🔴 P1 — Critique (bloquant / sécurité)

### ISSUE-001 — Module `logs` Angular manquant
**Fichier :** `frontend/src/app/app.routes.ts`
**Description :** La route `/logs` pointe vers `./features/logs/logs.component` mais le dossier `frontend/src/app/features/logs/` n'existe pas. L'application crashe au chargement de cette route.
**Solution :** Créer le composant manquant OU supprimer la route si non utilisée.

### ISSUE-002 — Configuration dupliquée en 3 endroits
**Fichiers :** `backend/app/core/config.py`, `backend/src/config.py`, `backend/src/analyzer/analyze.py`
**Description :** Deux classes `Settings`/`AppConfig` chargent `.env` séparément. `analyze.py` re-définit `DATABASE_URL` en dur. Crée des incohérences et des bugs.
**Solution :** Unifier en un seul point de configuration dans `backend/app/core/config.py` et supprimer `src/config.py`.

### ISSUE-003 — Secrets en clair dans le dépôt
**Fichiers :** `backend/alembic.ini`, `backend/scripts/init_db.sql`, `backend/.env.example`
**Description :**
- `alembic.ini` contient `postgresql://postgres:admin123@localhost:5432/sophatel_logs`
- `init_db.sql` contient `PASSWORD 'sophatel'`
- `.env.example` contient `SECRET_KEY=changeme-secret-key`
**Solution :** Externaliser tous les secrets dans `.env` (`.gitignore`), utiliser des variables d'environnement, supprimer les mots de passe des fichiers committés.

### ISSUE-004 — sys.path hack à l'import dans les routers
**Fichiers :** `backend/app/routers/collect_router.py`, `backend/app/routers/analyze_router.py`
**Description :** Les routers modifient `sys.path` à l'import pour accéder à `src/collector/runner.py`. Pattern dangereux et non maintenable.
**Solution :** Remplacer par des imports absolus depuis `backend/` (package `app` ou restructuration).

### ISSUE-005 — Analyse lancée en sous-processus
**Fichier :** `backend/app/services/analyze_service.py`
**Description :** `trigger_analysis()` lance `src/analyzer/analyze.py` via `subprocess.run()` au lieu d'appeler `analyze_csv()` directement. Perte de contrôle, pas d'accès à la session DB.
**Solution :** Refactorer pour appeler les fonctions métier directement.

### ISSUE-006 — Auth JWT : token jamais envoyé par le frontend
**Fichiers :** `frontend/src/app/core/services/api.service.ts`, `vps.service.ts`
**Description :** Les services Angular n'incluent pas le token JWT (`Authorization: Bearer ...`) dans les requêtes. Tous les appels aux endpoints protégés (POST/PUT/DELETE) retourneront 401.
**Solution :** Ajouter un intercepteur HTTP Angular qui attache le token automatiquement.

### ISSUE-007 — Endpoint `/api/auth/me` dupliqué
**Fichier :** `backend/app/routers/auth_router.py` (ligne 49) + `backend/app/main.py` (ligne 79)
**Description :** Deux endpoints `/api/auth/me` sont définis — un stub vide dans `auth_router.py` et un fonctionnel dans `main.py`. L'ordre d'inclusion des routers peut en masquer un.
**Solution :** Supprimer le stub dans `auth_router.py` et garder l'implémentation complète dans `main.py`.

### ISSUE-008 — Migrations Alembic hors du dossier `versions/`
**Fichiers :** `backend/alembic/Migration_0001_*.py`, `Migration_0002_*.py`
**Description :** Les fichiers de migration sont placés dans `alembic/` racine au lieu de `alembic/versions/`. Alembic ne les trouve pas → `alembic upgrade head` ne fonctionne pas.
**Solution :** Déplacer les fichiers dans `alembic/versions/` et corriger les `revision` / `down_revision`.

---

## 🟡 P2 — Important (qualité, maintenabilité)

### ISSUE-009 — `vps.service.ts` duplique `api.service.ts`
**Fichier :** `frontend/src/app/core/services/vps.service.ts`
**Description :** Deux services Angular avec les mêmes méthodes CRUD VPS + collect/analyze, mais `vps.service.ts` n'est utilisé que par `vps.component.ts`. Crée de la redondance et de la confusion.
**Solution :** Fusionner dans `api.service.ts` ou garder un seul service.

### ISSUE-010 — Interface `AnalyzeResult` définie deux fois
**Fichier :** `frontend/src/app/core/models/models.ts`
**Description :** L'interface `AnalyzeResult` est déclarée deux fois (lignes 40 et 103) avec des champs différents. Provoque des erreurs TypeScript silencieuses.
**Solution :** Supprimer la doublonne et garder une seule définition complète.

### ISSUE-011 — Endpoints stats lourds : chargement en mémoire
**Fichier :** `backend/app/routers/stats.py`
**Description :** Les endpoints `/api/stats/endpoints`, `/api/stats/alerts` chargent toutes les entrées en mémoire avec `.all()` puis calculent les percentiles en Python. Ne passera pas à l'échelle (>100k entrées).
**Solution :** Utiliser les fonctions de fenêtrage PostgreSQL (`percentile_cont`, `NTILE`).

### ISSUE-012 — iframe vs routing Angular
**Fichier :** `frontend/src/app/app.component.ts`
**Description :** Le composant racine charge une iframe vers `assets/sophatel_nginx_v5_login.html` (1470 lignes de HTML statique). Concurrent direct du routing natif Angular (dashboard, vps).
**Solution :** Décider : soit intégrer le HTML statique en composant Angular, soit supprimer l'iframe et utiliser les routes.

### ISSUE-013 — `print(DATABASE_URL)` dans la config
**Fichiers :** `backend/app/core/config.py` (ligne 13), `backend/src/config.py` (ligne 52)
**Description :** Les prints exposent la chaîne de connexion PostgreSQL dans les logs. Risque de fuite de credentials.
**Solution :** Remplacer `print()` par `logging.debug()` avec masquage du mot de passe.

### ISSUE-014 — CORS trop permissif
**Fichier :** `backend/app/main.py`
**Description :** `allow_methods=["*"]` et `allow_headers=["*"]` en production.
**Solution :** Restreindre aux méthodes utilisées (`GET, POST, PUT, DELETE`) et aux headers nécessaires.

---

## 🟢 P3 — Améliorations (nice to have)

### ISSUE-015 — Absence de tests automatisés
**Description :** Aucun test unitaire ou d'intégration. Aucun fichier `test_*.py`.
**Proposition :** Ajouter pytest + httpx pour tester les endpoints API.

### ISSUE-016 — Pas de Docker
**Description :** Pas de `Dockerfile` ni `docker-compose.yml`. L'installation manuelle est verbeuse et non reproductible.
**Proposition :** Dockeriser backend + frontend + PostgreSQL.

### ISSUE-017 — Aucun rate limiting sur l'API
**Description :** Pas de protection contre les abus (bruteforce login, spam d'appels).
**Proposition :** Ajouter `slowapi` ou un middleware de rate limiting.

### ISSUE-018 — Pas de pagination sur la liste VPS
**Fichier :** `backend/app/routers/vps.py`
**Description :** `list_vps()` retourne tous les VPS sans limite. OK pour 10, pas pour 1000.
**Proposition :** Ajouter `limit`/`offset`.

### ISSUE-019 — Absence de validation d'IP dans VPS
**Fichier :** `backend/app/schemas/schemas.py`
**Description :** Le champ `host` accepte n'importe quelle chaîne.
**Proposition :** Ajouter une validation Pydantic avec `ip_address_validator`.

### ISSUE-020 — Logs scheduler non persistés
**Fichier :** `backend/app/core/scheduler.py`
**Description :** Les jobs planifiés sont perdus au redémarrage du serveur.
**Proposition :** Configurer `APScheduler` avec un store PostgreSQL.

---

## 📊 Statistiques

| Priorité | Nombre |
|----------|--------|
| 🔴 Critique | 8 |
| 🟡 Important | 6 |
| 🟢 Amélioration | 6 |
| **Total** | **20** |
