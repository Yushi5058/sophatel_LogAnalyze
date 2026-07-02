"""
backend/app/services/analyze_service.py
Service qui déclenche l'analyse d'un fichier CSV depuis l'API.
Permet de lancer une analyse à distance via un endpoint POST /api/logs/analyze.
"""
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def trigger_analysis(csv_path: str, vps_name: str, mode: str = "ssh") -> dict:
    """
    Déclenche src/analyzer/analyze.py en sous-processus.
    Retourne le résultat ou l'erreur.
    """
    script = ROOT / "src" / "analyzer" / "analyze.py"
    if not script.exists():
        raise FileNotFoundError(f"Script introuvable : {script}")

    cmd = [
        sys.executable, str(script),
        csv_path,
        "--vps", vps_name,
        "--mode", mode,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))

    if result.returncode != 0:
        raise RuntimeError(result.stderr or "Erreur inconnue lors de l'analyse")

    return {
        "ok":     True,
        "stdout": result.stdout,
        "vps":    vps_name,
        "file":   csv_path,
    }
