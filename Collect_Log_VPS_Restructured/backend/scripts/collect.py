#!/usr/bin/env python3
"""
scripts/collect.py
CLI interactif : collecter les logs depuis les VPS (SSH ou mock).

Usage :
    python scripts/collect.py
    python scripts/collect.py --mock
    python scripts/collect.py --vps vps-prod-01
    python scripts/collect.py --all
"""
import argparse
import sys
from pathlib import Path

# Ajouter la racine au path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import load_vps_inventory, config
from src.collector.runner import run_collection, collect_mock


def prompt_vps_selection(vps_list: list[dict]) -> list[dict]:
    """Affiche un menu interactif pour choisir les VPS."""
    print("\n📡 VPS disponibles :")
    for i, v in enumerate(vps_list, 1):
        print(f"  [{i}] {v['name']} ({v['user']}@{v['host']}:{v.get('port', 22)})")
    print(f"  [0] Tous les VPS")

    choice = input("\nChoisissez (0-{}) : ".format(len(vps_list))).strip()
    if choice == "0":
        return vps_list
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(vps_list):
            return [vps_list[idx]]
    except ValueError:
        pass

    print("Choix invalide, sélection de tous les VPS.")
    return vps_list


def main():
    parser = argparse.ArgumentParser(description="Collecte de logs Nginx depuis les VPS")
    parser.add_argument("--mock",   action="store_true",      help="Utiliser le générateur mock")
    parser.add_argument("--all",    action="store_true",      help="Collecter tous les VPS sans confirmation")
    parser.add_argument("--vps",    type=str, default=None,   help="Nom du VPS spécifique")
    parser.add_argument("--config", type=str, default=None,   help="Chemin vers vps.yaml")
    args = parser.parse_args()

    use_mock = args.mock or config.USE_MOCK

    print("=" * 50)
    print("🛡️  Sophatel — Collecte de logs VPS")
    print("=" * 50)
    print(f"Mode : {'MOCK (développement)' if use_mock else 'SSH (production)'}")

    # Charger l'inventaire
    try:
        vps_list = load_vps_inventory(args.config)
    except FileNotFoundError as e:
        print(f"❌ {e}")
        sys.exit(1)

    if not vps_list:
        print("❌ Aucun VPS dans l'inventaire.")
        sys.exit(1)

    # Sélection
    if args.vps:
        vps_list = [v for v in vps_list if v["name"] == args.vps]
        if not vps_list:
            print(f"❌ VPS '{args.vps}' introuvable dans l'inventaire.")
            sys.exit(1)
    elif not args.all:
        vps_list = prompt_vps_selection(vps_list)

    print(f"\n🚀 Lancement de la collecte pour {len(vps_list)} VPS...\n")

    results = run_collection(vps_list, use_mock=use_mock)

    print("\n" + "=" * 50)
    print("📊 Résumé :")
    ok  = [r for r in results if r.get("ok")]
    err = [r for r in results if not r.get("ok")]
    print(f"  ✓ {len(ok)} succès")
    if err:
        print(f"  ✗ {len(err)} erreurs :")
        for e in err:
            print(f"    - {e['vps']}: {e.get('error')}")

    if ok:
        print("\n💡 Pour analyser les logs collectés :")
        print(f"   python scripts/analyze.py")


if __name__ == "__main__":
    main()
