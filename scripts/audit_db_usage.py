"""Auditoría rápida: filas por tabla en colegio.db"""
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parents[1] / "backend-sidecar" / "database" / "colegio.db"
conn = sqlite3.connect(DB)
tables = [
    r[0]
    for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
]
print(f"Base: {DB}")
print(f"Tablas: {len(tables)}\n")
for table in tables:
    count = conn.execute(f"SELECT COUNT(*) FROM [{table}]").fetchone()[0]
    print(f"{count:5d}  {table}")
conn.close()
