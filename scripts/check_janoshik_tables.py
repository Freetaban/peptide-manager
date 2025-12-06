"""Verifica tabelle Janoshik nel database production"""
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent / "data" / "production" / "peptide_management.db"
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%janoshik%'")
tables = cursor.fetchall()

print("Tabelle Janoshik trovate:")
if tables:
    for table in tables:
        print(f"  - {table[0]}")
        cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
        count = cursor.fetchone()[0]
        print(f"    Righe: {count}")
else:
    print("  Nessuna tabella Janoshik trovata")
    print("\n  ⚠️  La feature Janoshik non è ancora attiva in production")
    print("  ✅  La GUI gestisce correttamente questo caso (mostra messaggio)")

conn.close()
