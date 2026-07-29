"""Tests du pipeline d'analyse : stockage, déduplication, pas de collection vide."""
import csv
import tempfile
from pathlib import Path

from app.core.database import SessionLocal
from app.models.models import VPSServer, LogCollection, LogEntry
from src.analyzer.analyze import analyze_csv

_HEADER = ["ip", "timestamp", "method", "path", "status", "size",
           "referrer", "user_agent", "response_time"]
_ROWS = [
    (f"1.2.3.{i}", f"[10/Oct/2024:13:55:0{i} +0000]", "GET", f"/p{i}",
     "200", "123", "-", "ua", "0.05")
    for i in range(5)
]


def _write_csv():
    p = Path(tempfile.mkdtemp()) / "nginx_logs_test.csv"
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(_HEADER)
        w.writerows(_ROWS)
    return str(p)


def test_analyze_stores_entries_and_summary():
    res = analyze_csv(_write_csv(), "vps-analyze-test", mode="mock")
    assert res["total_requests"] == 5
    assert res["collection_id"] is not None
    db = SessionLocal()
    try:
        vps = db.query(VPSServer).filter_by(name="vps-analyze-test").first()
        assert vps is not None
        assert db.query(LogEntry).filter_by(vps_id=vps.id).count() == 5
        assert db.query(LogCollection).filter_by(vps_id=vps.id).count() == 1
    finally:
        db.close()


def test_analyze_dedup_creates_no_empty_collection():
    # 1re analyse : 5 lignes ; 2e analyse (même contenu, autre fichier) : rien de neuf.
    analyze_csv(_write_csv(), "vps-dedup-test", mode="mock")
    db = SessionLocal()
    try:
        vps = db.query(VPSServer).filter_by(name="vps-dedup-test").first()
        cols_before = db.query(LogCollection).filter_by(vps_id=vps.id).count()
        entries_before = db.query(LogEntry).filter_by(vps_id=vps.id).count()
    finally:
        db.close()

    res2 = analyze_csv(_write_csv(), "vps-dedup-test", mode="mock")
    assert res2["total_requests"] == 0
    assert res2["duplicates_skipped"] == 5
    assert res2["collection_id"] is None  # aucune collection créée

    db = SessionLocal()
    try:
        vps = db.query(VPSServer).filter_by(name="vps-dedup-test").first()
        assert db.query(LogCollection).filter_by(vps_id=vps.id).count() == cols_before
        assert db.query(LogEntry).filter_by(vps_id=vps.id).count() == entries_before
    finally:
        db.close()
