"""
src/analyzer/analyze.py
Point d'entrée de l'analyseur.
- Parse les fichiers CSV collectés depuis les VPS
- Insère les entrées dans PostgreSQL (table log_entries)
- Génère un résumé dans log_summaries
"""

import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy.dialects.postgresql import insert as pg_insert

# Paquets `app` et `src` résolus depuis backend/ (répertoire de lancement,
# ajouté au path par les points d'entrée : uvicorn, scripts/, alembic).
from app.models.models import VPSServer, LogCollection, LogEntry, LogSummary
# Connexion DB centralisée : une seule source de DATABASE_URL (cf. app.core.config),
# plus de moteur ni de défaut divergent ici.
from app.core.database import engine, Base, SessionLocal as Session

Base.metadata.create_all(bind=engine)

# Champs bruts (dans l'ordre) servant d'empreinte de déduplication d'une ligne.
_HASH_FIELDS = ["ip", "timestamp", "method", "path", "status", "size",
                "referrer", "user_agent", "response_time"]


def _line_hash(row: dict) -> str:
    """Empreinte md5 des valeurs BRUTES du CSV : clé naturelle d'une ligne de log."""
    raw = "\x1f".join(row.get(k, "") or "" for k in _HASH_FIELDS)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


# ── Parsing ───────────────────────────────────────────────────────────────────
NGINX_DATETIME_FMT = "%d/%b/%Y:%H:%M:%S %z"

def parse_timestamp(raw: str) -> Optional[datetime]:
    try:
        return datetime.strptime(raw.strip("[]"), NGINX_DATETIME_FMT)
    except Exception:
        return None

def parse_size(raw: str) -> int:
    try:
        return int(raw)
    except Exception:
        return 0

def parse_status(raw: str) -> Optional[int]:
    try:
        return int(raw)
    except Exception:
        return None

def parse_resp_time(raw: str) -> Optional[float]:
    try:
        return float(raw)
    except Exception:
        return None


# ── Analyse principale ────────────────────────────────────────────────────────
def analyze_csv(csv_path: str, vps_name: str, mode: str = "ssh") -> dict:
    """
    Analyse un fichier CSV de logs Nginx et insère dans PostgreSQL.

    Colonnes CSV attendues :
        ip, timestamp, method, path, status, size, referrer, user_agent, response_time

    Retourne un dict avec le résumé de l'analyse.
    """
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Fichier introuvable : {csv_path}")

    db = Session()
    try:
        # 1. Récupérer ou créer le VPS (uniquement parmi les VPS actifs)
        vps = db.query(VPSServer).filter(
            VPSServer.name == vps_name, VPSServer.deleted_at.is_(None)
        ).first()
        if not vps:
            vps = VPSServer(name=vps_name, host=vps_name, user="unknown")
            db.add(vps)
            db.flush()

        # 2. Créer une collection
        collection = LogCollection(
            vps_id=vps.id,
            source_file=str(csv_path),
            mode=mode,
        )
        db.add(collection)
        db.flush()

        # 3. Parser les lignes + empreinte de déduplication (doublons intra-fichier écartés)
        parsed_rows = []
        seen_hashes: set[str] = set()
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                h = _line_hash(row)
                if h in seen_hashes:
                    continue
                seen_hashes.add(h)
                parsed_rows.append({
                    "collection_id": collection.id,
                    "vps_id":        vps.id,
                    "line_hash":     h,
                    "ip":            row.get("ip", "").strip() or None,
                    "timestamp":     parse_timestamp(row.get("timestamp", "")),
                    "method":        (row.get("method", "").strip().upper() or None),
                    "path":          row.get("path", "").strip() or None,
                    "status":        parse_status(row.get("status", "")),
                    "size":          parse_size(row.get("size", "0")),
                    "referrer":      row.get("referrer", "").strip() or None,
                    "user_agent":    row.get("user_agent", "").strip() or None,
                    "response_time": parse_resp_time(row.get("response_time", "")),
                })

        # 4. Écarter les lignes déjà présentes pour ce VPS (déduplication inter-collectes)
        existing: set[str] = set()
        all_hashes = [r["line_hash"] for r in parsed_rows]
        for i in range(0, len(all_hashes), 5000):
            chunk = all_hashes[i:i + 5000]
            existing.update(
                r[0] for r in db.query(LogEntry.line_hash).filter(
                    LogEntry.vps_id == vps.id, LogEntry.line_hash.in_(chunk)
                ).all()
            )
        new_rows = [r for r in parsed_rows if r["line_hash"] not in existing]
        duplicates = len(parsed_rows) - len(new_rows)

        # 5. Insertion en base (ON CONFLICT DO NOTHING = filet anti-course)
        for i in range(0, len(new_rows), 5000):
            db.execute(
                pg_insert(LogEntry)
                .values(new_rows[i:i + 5000])
                .on_conflict_do_nothing(index_elements=["vps_id", "line_hash"])
            )
        collection.total_lines = len(new_rows)

        # 6. Agrégats calculés sur les lignes RÉELLEMENT nouvelles (résumé non gonflé)
        ip_set  = set()
        status_dist: dict[int, int] = {}
        path_count:  dict[str, int] = {}
        ip_count:    dict[str, int] = {}
        total_size  = 0
        total_rt    = 0.0
        rt_count    = 0
        error_count = 0
        success_count = 0
        for r in new_rows:
            if r["ip"]:
                ip_set.add(r["ip"])
                ip_count[r["ip"]] = ip_count.get(r["ip"], 0) + 1
            if r["status"]:
                status_dist[r["status"]] = status_dist.get(r["status"], 0) + 1
                if r["status"] >= 400:
                    error_count += 1
                else:
                    success_count += 1
            if r["path"]:
                path_count[r["path"]] = path_count.get(r["path"], 0) + 1
            total_size += r["size"]
            if r["response_time"] is not None:
                total_rt += r["response_time"]
                rt_count += 1

        top_paths = sorted(path_count.items(), key=lambda x: x[1], reverse=True)[:10]
        top_ips   = sorted(ip_count.items(),   key=lambda x: x[1], reverse=True)[:10]

        summary = LogSummary(
            collection_id=collection.id,
            total_requests=len(new_rows),
            unique_ips=len(ip_set),
            error_count=error_count,
            success_count=success_count,
            avg_size=round(total_size / len(new_rows), 2) if new_rows else 0.0,
            avg_resp_time=round(total_rt / rt_count, 4) if rt_count else 0.0,
            top_paths=json.dumps([{"path": p, "count": c} for p, c in top_paths]),
            top_ips=json.dumps([{"ip": ip, "count": c} for ip, c in top_ips]),
            status_dist=json.dumps({str(k): v for k, v in sorted(status_dist.items())}),
        )
        db.add(summary)
        db.commit()
        if duplicates:
            print(f"    {duplicates} ligne(s) déjà connue(s) ignorée(s) (déduplication)")

        # ── Calcul des stats par endpoint ─────────────────────────────────
        try:
            from app.services.endpoint_stats_service import compute_endpoint_stats
            nb_endpoints = compute_endpoint_stats(collection.id, db)
            db.commit()
            print(f"    {nb_endpoints} endpoint(s) analysés")
        except Exception as _e:
            print(f"[!] endpoint_stats ignorés : {_e}")

        result = {
            "collection_id": collection.id,
            "vps": vps_name,
            "file": str(csv_path),
            "total_requests": len(new_rows),
            "unique_ips": len(ip_set),
            "error_count": error_count,
            "success_count": success_count,
            "duplicates_skipped": duplicates,
            "error_rate": round(error_count / len(new_rows) * 100, 2) if new_rows else 0.0,
        }
        print(f"[✓] Analyse terminée → collection #{collection.id}")
        print(f"    {result['total_requests']} requêtes | {result['unique_ips']} IPs uniques | "
              f"{result['error_rate']}% erreurs")
        return result

    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Analyseur de logs Nginx → PostgreSQL")
    parser.add_argument("csv_file", help="Chemin vers le fichier CSV à analyser")
    parser.add_argument("--vps",  default="unknown", help="Nom du VPS source")
    parser.add_argument("--mode", default="ssh", choices=["ssh", "mock"], help="Mode de collecte")
    args = parser.parse_args()

    analyze_csv(args.csv_file, vps_name=args.vps, mode=args.mode)
"""
Fonction à ajouter à la fin de :
    backend/src/analyzer/analyze.py

Elle sert de point d'entrée appelé par le scheduler.
"""

from pathlib import Path


def run_analysis(log_dir: Path | None = None):
    """
    Parcourt tous les fichiers CSV dans logs/<vps>/*.csv
    et les insère en base via la logique existante d'analyze.py.

    Appelée par le scheduler (job_analyze) toutes les 35 min.
    """
    from src.config import config

    base_dir = log_dir or config.LOG_DIR

    if not base_dir.exists():
        print(f"[Analyseur] Dossier logs introuvable : {base_dir}")
        return

    csv_files = sorted(base_dir.rglob("*.csv"))
    if not csv_files:
        print("[Analyseur] Aucun fichier CSV à traiter.")
        return

    # Idempotence : ne traiter que les CSV jamais analysés.
    # Chaque collecte produit un fichier horodaté unique, dont le chemin est
    # enregistré dans log_collections.source_file. On saute ceux déjà présents
    # pour éviter la ré-analyse en boucle (duplication des données).
    db = Session()
    try:
        already = {row[0] for row in db.query(LogCollection.source_file).all() if row[0]}
    finally:
        db.close()

    new_files = [p for p in csv_files if str(p) not in already]
    skipped = len(csv_files) - len(new_files)
    if not new_files:
        print(f"[Analyseur] {len(csv_files)} CSV trouvé(s), tous déjà analysés — rien à faire.")
        return

    print(f"[Analyseur] {len(new_files)} nouveau(x) CSV à analyser ({skipped} déjà traité(s)).")
    for csv_path in new_files:
        # Extrait le nom du VPS depuis le chemin : logs/<vps_name>/fichier.csv
        vps_name = csv_path.parent.name
        print(f"  → Traitement : {csv_path.name}  (VPS: {vps_name})")
        try:
            analyze_csv(str(csv_path), vps_name)   # fonction déjà présente dans analyze.py
        except Exception as e:
            print(f"  ✗ Erreur sur {csv_path.name} : {e}")