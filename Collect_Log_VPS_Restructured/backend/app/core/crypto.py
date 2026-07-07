"""
app/core/crypto.py
Chiffrement au repos des secrets (mots de passe / clés SSH des VPS).

- Algorithme : Fernet (AES-128-CBC + HMAC) via `cryptography`.
- Clé : variable d'env CREDENTIALS_KEY (recommandé, `Fernet.generate_key()`),
  sinon dérivée de SECRET_KEY en dépannage.
- Les valeurs chiffrées sont préfixées par `enc:v1:` pour être distinguées des
  anciennes valeurs en clair (migration transparente : le legacy est renvoyé tel quel).
"""
import base64
import hashlib
import os
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.types import TypeDecorator, Text

from app.core.config import settings

_PREFIX = "enc:v1:"


@lru_cache(maxsize=1)
def _get_fernet() -> Fernet:
    key = os.getenv("CREDENTIALS_KEY")
    if key:
        return Fernet(key.encode() if isinstance(key, str) else key)
    # Dépannage : dériver une clé Fernet valide depuis SECRET_KEY.
    digest = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt(value):
    """Chiffre une chaîne ; None/'' inchangés ; idempotent si déjà chiffré."""
    if value is None or value == "":
        return value
    if isinstance(value, str) and value.startswith(_PREFIX):
        return value
    token = _get_fernet().encrypt(value.encode("utf-8")).decode("ascii")
    return _PREFIX + token


def decrypt(value):
    """Déchiffre une valeur préfixée ; renvoie le clair legacy tel quel sinon."""
    if value is None or value == "":
        return value
    if not value.startswith(_PREFIX):
        return value  # ancienne valeur en clair (migration progressive)
    try:
        return _get_fernet().decrypt(value[len(_PREFIX):].encode("ascii")).decode("utf-8")
    except InvalidToken:
        return value


class EncryptedText(TypeDecorator):
    """Colonne texte chiffrée de façon transparente à l'écriture/lecture."""
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return encrypt(value)

    def process_result_value(self, value, dialect):
        return decrypt(value)
