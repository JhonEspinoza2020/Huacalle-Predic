import sqlite3
from pathlib import Path

conn = sqlite3.connect(Path("backend-sidecar/database/colegio.db"))
rows = conn.execute(
    "SELECT type, name, sql FROM sqlite_master WHERE sql IS NOT NULL"
).fetchall()
for typ, name, sql in rows:
    if "legacy" in (sql or "").lower() or "legacy" in name.lower():
        print("---", typ, name)
        print(sql)

print("\nAll triggers:")
for typ, name, sql in rows:
    if typ == "trigger":
        print(name, sql)
