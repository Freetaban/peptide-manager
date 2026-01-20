import sqlite3
conn = sqlite3.connect('data/production/peptide_management.db')
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [r[0] for r in cur.fetchall()]
print(f"Tables in peptide_management.db ({len(tables)}):")
for t in tables:
    print(f"  - {t}")
conn.close()
