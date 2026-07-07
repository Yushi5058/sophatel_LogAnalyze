"""
src/collector/runner.py
Orchestre la collecte des logs (mock ou SSH) et écrit les fichiers
.log et .csv dans logs/<vps>/.
"""
import csv
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.collector.mock import generate_mock_log_lines
from src.collector.ssh_client import SSHClient
from src.config import config

# Regex Combined Log Format Nginx
# ip - - [timestamp] "method path proto" status size "referrer" "ua" [resp_time]
_LOG_RE = re.compile(
    r'(?P<ip>\S+) \S+ \S+ \[(?P<ts>[^\]]+)\] '
    r'"(?P<method>\S+) (?P<path>\S+) \S+" '
    r'(?P<status>\d{3}) (?P<size>\d+|-) '
    r'"(?P<referrer>[^"]*)" "(?P<ua>[^"]*)"'
    r'(?:\s+(?P<resp_time>[\d.]+))?'
)
# LINE_RE = re.compile(
#     r'^(?P<ip>\S+)\s+\S+\s+\S+\s+\[(?P<ts>[^\]]+)\]\s+'
#     r'"(?P<method>GET|HEAD|OPTIONS|TRACE|PUT|DELETE|POST|PATCH|CONNECT)?\s*(?P<target>[^" ]*)\s*(?P<protocol>[^"]*)"\s+'
#     r'(?P<status>\d{3})\s+(?P<body_bytes>\d+)\s+'
#     r'"(?P<referer>[^"]*)"\s+"(?P<ua>[^"]*)"\s+"(?P<xff>[^"]*)"\s+'
#     r'(?P<request_time>[\d\.]+)\s+(?P<upstream_time>[-\d\.,]+)\s*'
#     r'(?P<frontend_version>V([\d.]*|-))?$'
# )
CSV_HEADERS = ["ip", "timestamp", "method", "path", "status", "size", "referrer", "user_agent", "response_time"]


def _parse_line(line: str) -> Optional[dict]:
    """Parse une ligne Nginx Combined Log Format → dict ou None si invalide."""
    m = _LOG_RE.match(line.strip())
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
    parsed = [_parse_line(l) for l in lines if l.strip()]
    parsed = [p for p in parsed if p is not None]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writeheader()
        writer.writerows(parsed)

    print(f"  ✓ {vps_name} → {len(lines)} lignes brutes, {len(parsed)} entrées parsées")
    print(f"    LOG : {log_path}")
    print(f"    CSV : {csv_path}")
    return log_path, csv_path


def collect_mock(vps_name: str, n_lines: int = 500) -> tuple[Path, Path]:
    """Collecte en mode mock (génération aléatoire)."""
    print(f"[MOCK] Génération de {n_lines} lignes pour '{vps_name}'...")
    lines = generate_mock_log_lines(n_lines)
    return _write_outputs(vps_name, lines)


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
) -> tuple[Path, Path]:
    """Collecte réelle via SSH (clé fournie, clé locale, ou mot de passe)."""
    print(f"[SSH] Connexion à {user}@{host}:{port}...")
    with SSHClient(
        host=host, user=user, port=port, key_path=key_path,
        passphrase=passphrase, password=password, ssh_key=ssh_key,
        known_hosts=known_hosts, strict_host_key=strict_host_key,
    ) as ssh:
        print(f"[SSH] Lecture de '{log_path}' (dernières {last_n} lignes)...")
        content = ssh.fetch_last_n_lines(log_path, n=last_n)

    lines = [l for l in content.splitlines() if l.strip()]
    return _write_outputs(vps_name, lines)


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
                log_p, csv_p = collect_mock(name)
            else:
                log_p, csv_p = collect_ssh(
                    vps_name=name,
                    host=vps["host"],
                    user=vps["user"],
                    port=vps.get("port", 22),
                    key_path=vps.get("key_path", "~/.ssh/id_rsa"),
                    log_path=vps.get("log_path", "/var/log/nginx/access.log"),
                    passphrase=config.SSH_PASSPHRASE or None,
                    known_hosts=config.SSH_KNOWN_HOSTS,
                    strict_host_key=config.SSH_STRICT_HOST_KEY,
                )
            results.append({"vps": name, "log_path": str(log_p), "csv_path": str(csv_p), "ok": True})
        except Exception as e:
            print(f"  ✗ {name} — Erreur : {e}")
            results.append({"vps": name, "error": str(e), "ok": False})

    return results
