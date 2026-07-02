"""
src/collector/ssh_client.py
Connexion SSH réelle via Paramiko pour lire les logs Nginx distants.
"""
import os
from pathlib import Path
from typing import Optional
import paramiko


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
    ):
        self.host       = host
        self.user       = user
        self.port       = port
        self.key_path   = os.path.expanduser(key_path or "~/.ssh/id_rsa")
        self.passphrase = passphrase
        self.timeout    = timeout
        self._client: Optional[paramiko.SSHClient] = None

    def connect(self) -> None:
        """Ouvre la connexion SSH."""
        self._client = paramiko.SSHClient()
        self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        pkey = None
        if os.path.exists(self.key_path):
            try:
                pkey = paramiko.RSAKey.from_private_key_file(
                    self.key_path,
                    password=self.passphrase or None,
                )
            except paramiko.ssh_exception.PasswordRequiredException:
                raise ValueError(
                    f"La clé SSH '{self.key_path}' est protégée par mot de passe. "
                    "Définissez SSH_PASSPHRASE dans votre .env."
                )

        self._client.connect(
            hostname=self.host,
            port=self.port,
            username=self.user,
            pkey=pkey,
            timeout=self.timeout,
        )

    def fetch_file(self, remote_path: str) -> str:
        """
        Lit un fichier distant et retourne son contenu sous forme de chaîne.
        Utilise `cat` pour lire le fichier en une seule commande.
        """
        if not self._client:
            raise RuntimeError("SSHClient non connecté. Appelez connect() d'abord.")

        cmd = f"cat {remote_path}"
        _, stdout, stderr = self._client.exec_command(cmd, timeout=60)
        content = stdout.read().decode("utf-8", errors="replace")
        error   = stderr.read().decode("utf-8", errors="replace").strip()

        if error:
            raise RuntimeError(f"Erreur SSH lors de la lecture de '{remote_path}': {error}")

        return content

    def fetch_last_n_lines(self, remote_path: str, n: int = 10_000) -> str:
        """Récupère les N dernières lignes du fichier (tail)."""
        if not self._client:
            raise RuntimeError("SSHClient non connecté.")

        cmd = f"tail -n {n} {remote_path}"
        _, stdout, stderr = self._client.exec_command(cmd, timeout=60)
        return stdout.read().decode("utf-8", errors="replace")

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
