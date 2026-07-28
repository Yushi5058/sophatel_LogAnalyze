"""
app/services/enrichment_service.py — Enrichissement des IP (RM-34)

Qualifie une adresse IP via des API externes :
  - géolocalisation (ip-api.com, sans clé par défaut) ;
  - réputation (AbuseIPDB, si ABUSEIPDB_KEY est défini).

Principes : cache en base (`ip_enrichment`) avec TTL, IP privées/réservées
traitées localement (aucun appel externe), et **dégradation gracieuse** — toute
panne d'une API est capturée et journalisée, jamais propagée (l'analyse ne casse
pas). Un plafond d'appels externes par requête respecte les quotas.
"""
import ipaddress
import logging
from datetime import datetime, timedelta, timezone

import requests

from app.core.config import settings
from app.models.models import IpEnrichment

logger = logging.getLogger(__name__)


def _now():
    return datetime.now(timezone.utc)


def _is_private(ip: str) -> bool:
    try:
        a = ipaddress.ip_address(ip)
        return (a.is_private or a.is_loopback or a.is_reserved
                or a.is_link_local or a.is_multicast or a.is_unspecified)
    except ValueError:
        return False  # IP invalide : la géoloc échouera proprement (dégradation)


# ── Fournisseurs externes (mockables en test) ────────────────────────────────
def _geolocate(ip: str) -> dict:
    """Géolocalisation via ip-api.com (sans clé). Lève en cas d'échec réseau."""
    r = requests.get(settings.GEOIP_URL.format(ip=ip), timeout=settings.ENRICHMENT_TIMEOUT)
    r.raise_for_status()
    d = r.json()
    if d.get("status") and d.get("status") != "success":
        return {}
    return {
        "country_code": d.get("countryCode"),
        "country":      d.get("country"),
        "city":         d.get("city"),
        "isp":          d.get("isp") or d.get("org"),
        "_provider":    "ip-api",
    }


def _reputation(ip: str) -> dict:
    """Réputation via AbuseIPDB (si clé configurée), sinon aucune donnée."""
    if not settings.ABUSEIPDB_KEY:
        return {}
    r = requests.get(
        "https://api.abuseipdb.com/api/v2/check",
        params={"ipAddress": ip, "maxAgeInDays": 90},
        headers={"Key": settings.ABUSEIPDB_KEY, "Accept": "application/json"},
        timeout=settings.ENRICHMENT_TIMEOUT,
    )
    r.raise_for_status()
    data = r.json().get("data", {})
    score = data.get("abuseConfidenceScore")
    return {
        "abuse_score":  score,
        "is_malicious": (score is not None and score >= 50),
        "_provider":    "abuseipdb",
    }


def _safe(fn, ip: str) -> dict:
    """Exécute un fournisseur en capturant toute erreur (dégradation gracieuse)."""
    try:
        return fn(ip) or {}
    except Exception as e:  # réseau, timeout, JSON, quota…
        logger.warning("Enrichissement %s échoué pour %s : %s", fn.__name__, ip, e)
        return {}


# ── API interne ───────────────────────────────────────────────────────────────
def _to_dict(row: IpEnrichment) -> dict:
    return {
        "ip":           row.ip,
        "is_private":   bool(row.is_private),
        "country_code": row.country_code,
        "country":      row.country,
        "city":         row.city,
        "isp":          row.isp,
        "abuse_score":  row.abuse_score,
        "is_malicious": row.is_malicious,
        "providers":    row.providers,
        "fetched_at":   row.fetched_at.isoformat() if row.fetched_at else None,
    }


def _ttl() -> timedelta:
    return timedelta(days=settings.ENRICHMENT_TTL_DAYS)


def _is_fresh(row) -> bool:
    return bool(row and row.fetched_at and (_now() - row.fetched_at) < _ttl())


def enrich_ip(ip: str, db, force: bool = False) -> dict:
    """Enrichit une IP (cache d'abord ; sinon appels externes) et met à jour le cache."""
    row = db.get(IpEnrichment, ip)
    if _is_fresh(row) and not force:
        return _to_dict(row)

    fields = {
        "is_private": _is_private(ip), "country_code": None, "country": None,
        "city": None, "isp": None, "abuse_score": None, "is_malicious": None,
    }
    providers = []
    if not fields["is_private"] and settings.ENRICHMENT_ENABLED:
        for part in (_safe(_geolocate, ip), _safe(_reputation, ip)):
            prov = part.pop("_provider", None)
            if prov:
                providers.append(prov)
            fields.update({k: v for k, v in part.items() if v is not None})
    fields["providers"] = ",".join(providers) or None

    if row is None:
        row = IpEnrichment(ip=ip)
        db.add(row)
    for k, v in fields.items():
        setattr(row, k, v)
    row.fetched_at = _now()
    db.commit()
    return _to_dict(row)


def enrich_ips(ips, db) -> list:
    """
    Enrichit une liste d'IP en respectant un plafond d'appels externes par requête
    (les IP au-delà du plafond renvoient le cache existant ou une valeur minimale).
    """
    results = []
    budget = settings.ENRICHMENT_MAX_PER_CALL
    for ip in ips:
        needs_external = (not _is_private(ip)) and not _is_fresh(db.get(IpEnrichment, ip))
        if needs_external and budget <= 0:
            row = db.get(IpEnrichment, ip)
            results.append(_to_dict(row) if row else {
                "ip": ip, "is_private": False, "country_code": None, "country": None,
                "city": None, "isp": None, "abuse_score": None, "is_malicious": None,
                "providers": None, "fetched_at": None,
            })
            continue
        if needs_external:
            budget -= 1
        results.append(enrich_ip(ip, db))
    return results
