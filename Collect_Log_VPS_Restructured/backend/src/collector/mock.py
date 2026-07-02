"""
src/collector/mock.py
Générateur de faux logs Nginx (mode développement).
Produit des lignes au format Combined Log Format.
"""
import random
import time
from datetime import datetime, timedelta, timezone


# ── Données aléatoires ────────────────────────────────────────────────────────
_IPS = [
    "82.15.44.12", "91.234.56.78", "185.220.101.5",
    "192.168.1.100", "10.0.0.55", "203.0.113.42",
    "45.33.32.156", "176.9.0.207", "172.67.190.3", "104.21.44.1",
]
_METHODS = ["GET", "GET", "GET", "GET", "POST", "PUT", "DELETE"]
_PATHS = [
    "/", "/index.html", "/api/v1/users", "/api/v1/orders",
    "/api/v1/products", "/login", "/logout", "/admin",
    "/static/css/main.css", "/static/js/app.js",
    "/favicon.ico", "/robots.txt", "/sitemap.xml",
    "/api/v1/health", "/api/v1/metrics",
]
_STATUSES = [
    200, 200, 200, 200, 200,
    201, 204, 301, 302, 304,
    400, 401, 403, 404, 404,
    500, 502, 503,
]
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) Gecko/20100101 Firefox/121.0",
    "curl/7.88.1",
    "python-requests/2.31.0",
    "Googlebot/2.1 (+http://www.google.com/bot.html)",
    "facebookexternalhit/1.1",
]
_REFERRERS = ["-", "https://google.com", "https://github.com", "-", "-", "-"]


def _random_timestamp(base: datetime, spread_hours: int = 24) -> str:
    delta = timedelta(seconds=random.randint(0, spread_hours * 3600))
    ts = base - delta
    return ts.strftime("[%d/%b/%Y:%H:%M:%S +0000]")


def _random_size(status: int) -> int:
    if status in (204, 304):
        return 0
    return random.randint(128, 50_000)


def _random_resp_time() -> float:
    return round(random.uniform(0.001, 2.5), 6)


def generate_mock_log_lines(n: int = 500, spread_hours: int = 24) -> list[str]:
    """
    Génère `n` lignes de log Nginx au format Combined Log Format.

    Format :
        IP - - [timestamp] "METHOD PATH HTTP/1.1" STATUS SIZE "REFERRER" "UA" RESP_TIME
    """
    now = datetime.now(tz=timezone.utc)
    lines = []
    for _ in range(n):
        ip        = random.choice(_IPS)
        ts        = _random_timestamp(now, spread_hours)
        method    = random.choice(_METHODS)
        path      = random.choice(_PATHS)
        status    = random.choice(_STATUSES)
        size      = _random_size(status)
        referrer  = random.choice(_REFERRERS)
        ua        = random.choice(_USER_AGENTS)
        resp_time = _random_resp_time()

        line = (
            f'{ip} - - {ts} "{method} {path} HTTP/1.1" '
            f'{status} {size} "{referrer}" "{ua}" {resp_time}'
        )
        lines.append(line)

    return sorted(lines, key=lambda l: l[8:35])  # tri par timestamp approximatif


if __name__ == "__main__":
    for line in generate_mock_log_lines(10):
        print(line)
