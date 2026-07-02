#!/usr/bin/env python3
"""
scripts/dashboard.py
Lance le backend FastAPI (remplace l'ancien dashboard Streamlit).

Usage :
    python scripts/dashboard.py
    python scripts/dashboard.py --port 8080 --reload
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description="Lance le backend FastAPI Sophatel")
    parser.add_argument("--host",   default="0.0.0.0",    help="Hôte d'écoute (défaut: 0.0.0.0)")
    parser.add_argument("--port",   default=8000, type=int, help="Port (défaut: 8000)")
    parser.add_argument("--reload", action="store_true",   help="Rechargement automatique (dev)")
    args = parser.parse_args()

    print("=" * 50)
    print("🛡️  Sophatel — Backend FastAPI")
    print("=" * 50)
    print(f"  URL API     : http://localhost:{args.port}")
    print(f"  Swagger UI  : http://localhost:{args.port}/docs")
    print(f"  Dashboard   : http://localhost:4200 (Angular, lancer séparément)")
    print("=" * 50)
    print()

    cmd = [
        sys.executable, "-m", "uvicorn",
        "app.main:app",
        "--host", args.host,
        "--port", str(args.port),
    ]
    if args.reload:
        cmd.append("--reload")

    # Lancer depuis le dossier backend/
    backend_dir = ROOT / "backend"
    try:
        subprocess.run(cmd, cwd=backend_dir, check=True)
    except KeyboardInterrupt:
        print("\n👋 Backend arrêté.")
    except FileNotFoundError:
        print("❌ uvicorn introuvable. Installez les dépendances :")
        print("   pip install -r backend/requirements.txt")
        sys.exit(1)


if __name__ == "__main__":
    main()
