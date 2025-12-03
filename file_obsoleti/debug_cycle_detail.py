from peptide_manager import PeptideManager
from datetime import date
import sqlite3

# Verifica somministrazioni con cycle_id
db = sqlite3.connect('data/staging/peptide_management.db')
cursor = db.cursor()

print("\n=== Somministrazioni oggi con cycle_id ===")
cursor.execute("""
SELECT id, administration_datetime, cycle_id, preparation_id
FROM administrations 
WHERE DATE(administration_datetime) = '2025-11-18' AND deleted_at IS NULL
""")
for row in cursor.fetchall():
    print(f"Admin {row[0]}: datetime={row[1]}, cycle_id={row[2]}, prep_id={row[3]}")

print("\n=== Cicli attivi ===")
cursor.execute("SELECT id, name, status FROM cycles WHERE status='active'")
for row in cursor.fetchall():
    print(f"Cycle {row[0]}: {row[1]} (status={row[2]})")

db.close()

# Test manager
mgr = PeptideManager('data/staging/peptide_management.db')
result = mgr.get_scheduled_administrations(date.today())

print(f'\n=== Risultati manager: {len(result)} ===')
for r in result:
    print(f"Peptide: {r.get('peptide_names')}")
    print(f"  cycle_id: {r.get('cycle_id')}")
    print(f"  cycle_name: {r.get('cycle_name')}")
    print()
