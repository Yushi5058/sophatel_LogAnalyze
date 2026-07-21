"""
src/collector/runner.py
Orchestre la collecte des logs (mock ou SSH) et écrit les fichiers
.log et .csv dans logs/<vps>/.
"""
import csv
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.collector.mock import generate_mock_log_lines
from src.collector.ssh_client import SSHClient
from src.config import config

logger = logging.getLogger("collector")

# Partie commune : ip - - [ts] "method path proto" status size "referrer" "ua"
_HEAD = (
    r'(?P<ip>\S+) \S+ \S+ \[(?P<ts>[^\]]+)\] '
    r'"(?P<method>\S+) (?P<path>\S+) \S+" '
    r'(?P<status>\d{3}) (?P<size>\d+|-) '
    r'"(?P<referrer>[^"]*)" "(?P<ua>[^"]*)"'
)

# Format "combined" simple (+ temps de réponse optionnel) — produit par le mock.
_LOG_RE = re.compile(_HEAD + r'(?:\s+(?P<resp_time>[\d.]+))?\s*$')

# Format étendu Sophatel : + "xff" request_time upstream_time [Vversion].
# On capture request_time comme response_time (le vrai temps de traitement) ;
# upstream_time et version frontend (formats variés : "0.01, 0.02", "-", "V-"…) sont ignorés.
_LOG_RE_EXT = re.compile(
    _HEAD +
    r' "(?P<xff>[^"]*)" '
    r'(?P<resp_time>[\d.]+)'
    r'(?: .*)?$'
)

CSV_HEADERS = ["ip", "timestamp", "method", "path", "status", "size", "referrer", "user_agent", "response_time"]


def _parse_line(line: str) -> Optional[dict]:
    """Parse une ligne Nginx (format étendu Sophatel ou combined simple) → dict ou None."""
    line = line.strip()
    m = _LOG_RE_EXT.match(line) or _LOG_RE.match(line)
    if not m:
        return None
    size = m.group("size")
    return {
        "ip":            m.group("ip"),
        "timestamp":     m.group("ts"),
        "method":        m.group("method"),
        "path":          m.group("path"),
        "status":        m.group("status"),
        "size":          "0" if size == "-" else size,
        "referrer":      m.group("referrer"),
        "user_agent":    m.group("ua"),
        "response_time": m.group("resp_time") or "",
    }


def _write_outputs(vps_name: str, lines: list[str]) -> tuple[Path, Path]:
    """
    Écrit les fichiers .log et .csv dans logs/<vps_name>/.
    Retourne (log_path, csv_path).
    """
    now    = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    outdir = config.LOG_DIR / vps_name
    outdir.mkdir(parents=True, exist_ok=True)

    log_path = outdir / f"nginx_logs_{now}.log"
    csv_path = outdir / f"nginx_logs_{now}.csv"

    # Fichier .log brut
    log_path.write_text("\n".join(lines), encoding="utf-8")

    # Fichier .csv parsé
    non_empty = [l for l in lines if l.strip()]
    parsed = [p for p in (_parse_line(l) for l in non_empty) if p is not None]
    n_in, n_ok = len(non_empty), len(parsed)
    n_ko = n_in - n_ok

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writeheader()
        writer.writerows(parsed)

    logger.info("%s : %d lignes brutes, %d parsées, %d ignorées", vps_name, len(lines), n_ok, n_ko)
    # Rend visible un format de log inattendu (échec silencieux) plutôt que 0 entrée sans alerte.
    if n_in and n_ko / n_in > 0.10:
        logger.warning(
            "%s : %.0f%% de lignes non parsées (%d/%d) — format de log Nginx inattendu ?",
            vps_name, 100 * n_ko / n_in, n_ko, n_in,
        )
    print(f"  {vps_name} -> {len(lines)} lignes brutes, {n_ok} parsees, {n_ko} ignorees")
    return log_path, csv_path


def collect_mock(vps_name: str, n_lines: int = 500) -> tuple[Path, Path, Optional[int]]:
    """Collecte en mode mock (génération aléatoire). Pas de curseur (offset None)."""
    print(f"[MOCK] Génération de {n_lines} lignes pour '{vps_name}'...")
    lines = generate_mock_log_lines(n_lines)
    log_p, csv_p = _write_outputs(vps_name, lines)
    return log_p, csv_p, None


def collect_ssh(
    vps_name: str,
    host: str,
    user: str,
    port: int = 22,
    key_path: str = "~/.ssh/id_rsa",
    log_path: str = "/var/log/nginx/access.log",
    last_n: int = 50_000,
    passphrase: Optional[str] = None,
    password: Optional[str] = None,
    ssh_key: Optional[str] = None,
    known_hosts: str = "~/.ssh/known_hosts",
    strict_host_key: bool = False,
    start_offset: int = 0,
) -> tuple[Optional[Path], Optional[Path], int]:
    """
    Collecte réelle via SSH (clé fournie, clé locale, ou mot de passe).

    Collecte **incrémentale** : ne récupère que le contenu ajouté depuis
    `start_offset` (curseur d'octets). Retourne `(log_path, csv_path, new_offset)`.
    Si aucun nouveau contenu : `(None, None, new_offset)` (pas de CSV écrit).
    """
    print(f"[SSH] Connexion à {user}@{host}:{port}...")
    with SSHClient(
        host=host, user=user, port=port, key_path=key_path,
        passphrase=passphrase, password=password, ssh_key=ssh_key,
        known_hosts=known_hosts, strict_host_key=strict_host_key,
    ) as ssh:
        print(f"[SSH] Lecture incrémentale de '{log_path}' (offset={start_offset})...")
        content, new_offset = ssh.fetch_incremental(log_path, offset=start_offset, n=last_n)

    lines = [l for l in content.splitlines() if l.strip()]
    if not lines:
        print(f"  {vps_name} -> aucun nouveau contenu (offset inchangé)")
        return None, None, new_offset

    log_p, csv_p = _write_outputs(vps_name, lines)
    return log_p, csv_p, new_offset


def run_collection(vps_list: list[dict], use_mock: bool = False) -> list[dict]:
    """
    Lance la collecte pour tous les VPS de l'inventaire.
    Retourne une liste de résultats {vps, log_path, csv_path}.
    """
    results = []
    for vps in vps_list:
        name = vps.get("name", "unknown")
        try:
            if use_mock or config.USE_MOCK:
                log_p, csv_p, new_offset = collect_mock(name)
            else:
                log_p, csv_p, new_offset = collect_ssh(
                    vps_name=name,
                    host=vps["host"],
                    user=vps["user"],
                    port=vps.get("port", 22),
                    key_path=vps.get("key_path", "~/.ssh/id_rsa"),
                    log_path=vps.get("log_path", "/var/log/nginx/access.log"),
                    password=vps.get("password") or None,   # VPS issus de la base
                    ssh_key=vps.get("ssh_key") or None,
                    passphrase=config.SSH_PASSPHRASE or None,
                    known_hosts=config.SSH_KNOWN_HOSTS,
                    strict_host_key=config.SSH_STRICT_HOST_KEY,
                    start_offset=vps.get("collect_offset", 0) or 0,
                )
            results.append({
                "vps": name,
                "log_path": str(log_p) if log_p else None,
                "csv_path": str(csv_p) if csv_p else None,
                "new_offset": new_offset,   # None en mock ; sinon curseur à persister
                "ok": True,
            })
        except Exception as e:
            print(f"  ✗ {name} — Erreur : {e}")
            results.append({"vps": name, "error": str(e), "ok": False})

    return results
