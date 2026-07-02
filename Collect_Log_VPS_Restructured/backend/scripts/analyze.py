#!/usr/bin/env python3
"""
scripts/analyze.py
CLI interactif : analyser un fichier CSV de logs existant
et l'insérer dans PostgreSQL.

Usage :
    python scripts/analyze.py
    python scripts/analyze.py --file logs/vps-prod-01/nginx_logs_2024-01-15.csv
    python scripts/analyze.py --file <path> --vps vps-prod-01
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import config


def find_csv_files() -> list[Path]:
    """Trouve tous les fichiers CSV dans le dossier logs/."""
    log_dir = config.LOG_DIR
    if not log_dir.exists():
        return []
    return sorted(log_dir.rglob("*.csv"))


def prompt_file_selection(csv_files: list[Path]) -> Path:
    """Menu interactif pour choisir un fichier CSV."""
    print("\n📂 Fichiers CSV disponibles :")
    for i, f in enumerate(csv_files, 1):
        size = f.stat().st_size
        size_str = f"{size // 1024} KB" if size > 1024 else f"{size} B"
        print(f"  [{i}] {f.relative_to(config.LOG_DIR.parent)} ({size_str})")

    choice = input(f"\nChoisissez (1-{len(csv_files)}) : ").strip()
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(csv_files):
            return csv_files[idx]
    except ValueError:
        pass

    print("Choix invalide, sélection du fichier le plus récent.")
    return csv_files[-1]


def extract_vps_name(csv_path: Path) -> str:
    """Extrait le nom du VPS depuis le chemin du fichier."""
    # Structure attendue : logs/<vps_name>/nginx_logs_*.csv
    try:
        parts = csv_path.relative_to(config.LOG_DIR).parts
        return parts[0] if len(parts) > 1 else "unknown"
    except ValueError:
        return csv_path.parent.name


def main():
    parser = argparse.ArgumentParser(description="Analyse de logs Nginx → PostgreSQL")
    parser.add_argument("--file", type=str, default=None, help="Chemin du CSV à analyser")
    parser.add_argument("--vps",  type=str, default=None, help="Nom du VPS source")
    parser.add_argument("--mode", type=str, default=None, choices=["ssh", "mock"], help="Mode de collecte")
    args = parser.parse_args()

    print("=" * 50)
    print("🛡️  Sophatel — Analyse de logs VPS")
    print("=" * 50)

    # Déterminer le fichier à analyser
    if args.file:
        csv_path = Path(args.file)
        if not csv_path.exists():
            print(f"❌ Fichier introuvable : {csv_path}")
            sys.exit(1)
    else:
        csv_files = find_csv_files()
        if not csv_files:
            print("❌ Aucun fichier CSV trouvé dans logs/")
            print("   Lancez d'abord : python scripts/collect.py")
            sys.exit(1)
        csv_path = prompt_file_selection(csv_files)

    vps_name = args.vps or extract_vps_name(csv_path)
    mode     = args.mode or ("mock" if "mock" in str(csv_path) else "ssh")

    print(f"\n📄 Fichier : {csv_path}")
    print(f"🖥️  VPS     : {vps_name}")
    print(f"⚙️  Mode    : {mode}")
    print("\n⏳ Analyse en cours...\n")

    # Import ici pour avoir les messages d'init de SQLAlchemy après l'UI
    from src.analyzer.analyze import analyze_csv

    try:
        result = analyze_csv(str(csv_path), vps_name=vps_name, mode=mode)
        print("\n" + "=" * 50)
        print("✅ Analyse terminée !")
        print(f"   Collection ID : #{result['collection_id']}")
        print(f"   Requêtes      : {result['total_requests']:,}")
        print(f"   IPs uniques   : {result['unique_ips']:,}")
        print(f"   Erreurs       : {result['error_count']:,} ({result['error_rate']}%)")
        print("\n💡 Démarrez le dashboard Angular pour visualiser les données :")
        print("   cd frontend && npm start")
    except Exception as e:
        print(f"\n❌ Erreur lors de l'analyse : {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
