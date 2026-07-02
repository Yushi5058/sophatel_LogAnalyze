"""
backend/app/services/endpoint_stats_service.py

Calcule et insère les statistiques par endpoint (EndpointStat)
à partir des LogEntry d'une collection.

Appelé par analyze_service.py après chaque collecte/analyse.
"""
import re
from collections import defaultdict
from datetime import timezone

from sqlalchemy.orm import Session

from app.models.models import LogEntry, EndpointStat

# ── Normalisation d'endpoint ──────────────────────────────────────────────────
# Remplace les segments variables (id numériques, UUIDs, hex) par un placeholder
_RE_ID       = re.compile(r"/\d+(?=/|$)")
_RE_UUID     = re.compile(r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)
_RE_HEX_EXT = re.compile(r"/[0-9a-f]{16,}\.[a-z0-9]+", re.I)   # ex: fichier.hash.ttf
_RE_HEX_SEG = re.compile(r"\.[0-9a-f]{8,}\.", re.I)              # ex: nunito.abc123de.ttf

BYTES_TO_MO = 1 / (1024 * 1024)


def _normalize_path(path: str) -> str:
    """Retourne une clé d'endpoint normalisée."""
    if not path:
        return "/"
    # Supprimer query string
    path = path.split("?")[0]
    # Fichier avec hash hexadécimal dans le nom (ex: nunito-semibold.abc123.ttf)
    path = _RE_HEX_SEG.sub(".{hex_str}.", path)
    # Segment hexadécimal long
    path = _RE_HEX_EXT.sub("/{hex_str}", path)
    # UUID
    path = _RE_UUID.sub("/{id}", path)
    # Segment numérique
    path = _RE_ID.sub("/{id}", path)
    return path


def _percentile(sorted_data: list, p: float) -> float | None:
    """Percentile sur une liste triée (0-100)."""
    if not sorted_data:
        return None
    idx = max(0, int(len(sorted_data) * p / 100) - 1)
    return sorted_data[idx]


# ── Fonction principale ───────────────────────────────────────────────────────

def compute_endpoint_stats(collection_id: int, db: Session) -> int:
    """
    Lit tous les LogEntry de la collection, les groupe par endpoint normalisé,
    calcule les 23 métriques et insère dans endpoint_stats.

    Retourne le nombre d'endpoints insérés.
    """
    # Supprimer les anciennes stats si on re-analyse
    db.query(EndpointStat).filter(EndpointStat.collection_id == collection_id).delete()

    # Charger les entrées utiles
    entries = db.query(
        LogEntry.path,
        LogEntry.status,
        LogEntry.size,
        LogEntry.response_time,
        LogEntry.timestamp,
    ).filter(LogEntry.collection_id == collection_id).all()

    if not entries:
        return 0

    # Grouper par endpoint normalisé
    groups: dict[str, dict] = defaultdict(lambda: {
        "rts":        [],   # response_time en secondes
        "sizes":      [],   # body bytes
        "statuses":   [],
        "timestamps": [],
    })

    for path, status, size, rt, ts in entries:
        key = _normalize_path(path or "/")
        grp = groups[key]
        if rt is not None:
            grp["rts"].append(rt)
        if size is not None:
            grp["sizes"].append(size)
        if status is not None:
            grp["statuses"].append(status)
        if ts is not None:
            grp["timestamps"].append(ts)

    stats_to_insert = []

    for endpoint, grp in groups.items():
        rts        = sorted(grp["rts"])
        sizes      = sorted(grp["sizes"])
        statuses   = grp["statuses"]
        timestamps = grp["timestamps"]
        n          = len(statuses)

        # ── Latences (s → ms) ─────────────────────────────────────────────
        def rt_pct(p):
            v = _percentile(rts, p)
            return round(v * 1000, 3) if v is not None else None

        lat_min  = round(rts[0]  * 1000, 3) if rts else None
        lat_max  = round(rts[-1] * 1000, 3) if rts else None
        lat_sum  = round(sum(rts) * 1000, 3) if rts else None
        lat_moy  = round(sum(rts) / len(rts) * 1000, 3) if rts else None
        lat_p50  = rt_pct(50)
        lat_p75  = rt_pct(75)
        lat_p95  = rt_pct(95)
        lat_p99  = rt_pct(99)

        # ── Body sizes (bytes → Mo) ────────────────────────────────────────
        def sz_pct(p):
            v = _percentile(sizes, p)
            return round(v * BYTES_TO_MO, 6) if v is not None else None

        body_min = round(sizes[0]  * BYTES_TO_MO, 6) if sizes else None
        body_max = round(sizes[-1] * BYTES_TO_MO, 6) if sizes else None
        body_sum = round(sum(sizes) * BYTES_TO_MO, 6) if sizes else None
        body_moy = round(sum(sizes) / len(sizes) * BYTES_TO_MO, 6) if sizes else None
        body_p50 = sz_pct(50)
        body_p75 = sz_pct(75)
        body_p95 = sz_pct(95)
        body_p99 = sz_pct(99)

        # ── Taux d'erreur ──────────────────────────────────────────────────
        count_4xx = sum(1 for s in statuses if 400 <= s < 500)
        count_5xx = sum(1 for s in statuses if s >= 500)
        taux_4xx  = round(count_4xx / n * 100, 2) if n else None
        taux_5xx  = round(count_5xx / n * 100, 2) if n else None

        # ── Plage temporelle ───────────────────────────────────────────────
        ts_sorted = sorted(timestamps)
        premiere  = ts_sorted[0]  if ts_sorted else None
        derniere  = ts_sorted[-1] if ts_sorted else None

        stats_to_insert.append(EndpointStat(
            collection_id=collection_id,
            endpoint=endpoint,
            nb_requetes=n,

            latence_min_ms=lat_min,
            latence_p50_ms=lat_p50,
            latence_moy_ms=lat_moy,
            latence_p75_ms=lat_p75,
            latence_p95_ms=lat_p95,
            latence_p99_ms=lat_p99,
            latence_max_ms=lat_max,
            latence_sum_ms=lat_sum,

            upstream_moy_ms=None,   # non disponible dans le CSV simplifié
            overhead_moy_ms=None,   # idem

            body_min_mo=body_min,
            body_p50_mo=body_p50,
            body_moy_mo=body_moy,
            body_p75_mo=body_p75,
            body_p95_mo=body_p95,
            body_p99_mo=body_p99,
            body_max_mo=body_max,
            body_sum_mo=body_sum,

            taux_erreur_4xx=taux_4xx,
            taux_erreur_5xx=taux_5xx,

            premiere_occurrence_utc=premiere,
            derniere_occurrence_utc=derniere,
        ))

    db.bulk_save_objects(stats_to_insert)
    db.flush()
    return len(stats_to_insert)