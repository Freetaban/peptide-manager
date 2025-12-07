"""Verifica schema completo janoshik_certificates"""
import sys
sys.path.insert(0, 'scripts')
import sqlite3
from environment import get_environment

env = get_environment()
conn = sqlite3.connect(env.db_path)

print("=" * 70)
print("SCHEMA janoshik_certificates")
print("=" * 70)

cursor = conn.execute("PRAGMA table_info(janoshik_certificates)")
columns = cursor.fetchall()

for col in columns:
    col_id, name, dtype, not_null, default, pk = col
    print(f"{col_id:2d}. {name:30s} {dtype:15s} NOT NULL={not_null} PK={pk}")

# Verifica se esistono peptide_name e quantity separati
print("\n" + "=" * 70)
print("SAMPLE DATI - Campi rilevanti per parsing peptide:")
print("=" * 70)

cursor = conn.execute("""
    SELECT 
        id,
        product_name,
        peptide_name,
        quantity_tested_mg,
        purity_mg_per_vial
    FROM janoshik_certificates
    LIMIT 10
""")

print(f"{'ID':<5} {'product_name':<35} {'peptide_name':<20} {'qty_tested':<12} {'purity_mg'}")
print("-" * 95)
for row in cursor:
    print(f"{row[0]:<5} {str(row[1] or '')[:35]:<35} {str(row[2] or '')[:20]:<20} {str(row[3] or ''):<12} {row[4]}")

conn.close()
