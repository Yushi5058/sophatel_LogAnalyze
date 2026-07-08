"""
app/core/ratelimit.py
Limiteur de débit (anti brute-force) partagé, basé sur slowapi.

Le stockage est en mémoire (suffisant pour un seul process). Pour plusieurs
workers/instances, configurer un backend Redis via `storage_uri`.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

# Clé = adresse IP du client. Pas de limite globale par défaut : on l'applique
# route par route (ex. /login) avec le décorateur @limiter.limit(...).
limiter = Limiter(key_func=get_remote_address, default_limits=[])
