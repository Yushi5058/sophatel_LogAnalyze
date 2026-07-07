"""
src/collector/ssh_client.py
Connexion SSH réelle via Paramiko pour lire les logs Nginx distants.
"""
import os
from io import StringIO
from pathlib import Path
from typing import Optional
import paramiko

# Types de clés privées supportés (essayés dans l'ordre)
_KEY_TYPES = (paramiko.RSAKey, paramiko.Ed25519Key, paramiko.ECDSAKey)


class SSHClient:
    """Client SSH qui récupère le contenu d'un fichier distant."""

    def __init__(
        self,
        host: str,
        user: str,
        port: int = 22,
        key_path: Optional[str] = None,
        passphrase: Optional[str] = None,
        timeout: int = 30,
        password: Optional[str] = None,
        ssh_key: Optional[str] = None,
    ):
        self.host       = host
        self.user       = user
        self.port       = port
        self.key_path   = os.path.expanduser(key_path or "~/.ssh/id_rsa")
        self.passphrase = passphrase
        self.timeout    = timeout
        self.password   = password   # mot de passe de connexion SSH
        self.ssh_key    = ssh_key    # contenu d'une clé privée (ex. stockée en base)
        self._client: Optional[paramiko.SSHClient] = None

    # ── Chargement de la clé privée ───────────────────────────────────────────
    def _key_from_string(self, content: str):
        for cls in _KEY_TYPES:
            try:
                return cls.from_private_key(StringIO(content), password=self.passphrase or None)
            except paramiko.ssh_exception.PasswordRequiredException:
                raise ValueError(
                    "La clé SSH fournie est protégée par une passphrase ; renseignez SSH_PASSPHRASE."
                )
            except (paramiko.SSHException, ValueError):
                continue  # mauvais type de clé, on essaie le suivant
        raise ValueError("Clé SSH fournie invalide ou non supportée (RSA/Ed25519/ECDSA).")

    def _key_from_file(self, path: str):
        for cls in _KEY_TYPES:
            try:
                return cls.from_private_key_file(path, password=self.passphrase or None)
            except paramiko.ssh_exception.PasswordRequiredException:
                raise ValueError(
                    f"La clé SSH '{path}' est protégée par une passphrase ; renseignez SSH_PASSPHRASE."
                )
            except (paramiko.SSHException, ValueError):
                continue
        raise ValueError(f"Clé SSH '{path}' invalide ou non supportée (RSA/Ed25519/ECDSA).")

    def _load_key(self):
        # 1) clé fournie en contenu (prioritaire, ex. depuis la base chiffrée)
        if self.ssh_key:
            return self._key_from_string(self.ssh_key)
        # 2) sinon, fichier de clé local
        if self.key_path and os.path.exists(self.key_path):
            return self._key_from_file(self.key_path)
        return None

    def connect(self) -> None:
        """Ouvre la connexion SSH (clé fournie, clé locale, ou mot de passe)."""
        self._client = paramiko.SSHClient()
        self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        pkey = self._load_key()

        kwargs = dict(
            hostname=self.host,
            port=self.port,
            username=self.user,
            timeout=self.timeout,
        )
        if pkey is not None:
            kwargs["pkey"] = pkey
        if self.password:
            kwargs["password"] = self.password
        # Auth par mot de passe seul : ne pas piocher dans les clés locales / l'agent
        if self.password and pkey is None:
            kwargs["look_for_keys"] = False
            kwargs["allow_agent"] = False

        self._client.connect(**kwargs)

    def fetch_file(self, remote_path: str) -> str:
        """
        Lit un fichier distant et retourne son contenu sous forme de chaîne.
        Utilise SFTP (sans shell) pour éviter les injections de commandes.
        """
        if not self._client:
            raise RuntimeError("SSHClient non connecté. Appelez connect() d'abord.")

        with self._client.open_sftp() as sftp:
            with sftp.file(remote_path, "r") as f:
                return f.read().decode("utf-8", errors="replace")

    def fetch_last_n_lines(
        self, remote_path: str, n: int = 10_000, block: int = 1 << 20
    ) -> str:
        """
        Récupère les N dernières lignes du fichier via SFTP (sans shell).
        Lit le fichier en remontant depuis la fin par blocs de `block` octets :
        seules les dernières lignes sont chargées, la mémoire reste bornée
        (pas de lecture intégrale d'un gros access.log).
        """
        if not self._client:
            raise RuntimeError("SSHClient non connecté.")

        n = max(0, int(n))
        if n == 0:
            return ""

        with self._client.open_sftp() as sftp:
            size = sftp.stat(remote_path).st_size
            with sftp.file(remote_path, "rb") as f:
                data = b""
                pos = size
                # On remonte tant qu'on n'a pas assez de sauts de ligne
                # (n+1 pour couvrir une éventuelle dernière ligne partielle).
                while pos > 0 and data.count(b"\n") <= n:
                    read = min(block, pos)
                    pos -= read
                    f.seek(pos)
                    data = f.read(read) + data

        lines = data.decode("utf-8", errors="replace").splitlines()
        return "\n".join(lines[-n:])

    def close(self) -> None:
        """Ferme la connexion SSH."""
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *_):
        self.close()
