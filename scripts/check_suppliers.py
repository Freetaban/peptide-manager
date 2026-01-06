"""Quick script to check supplier variants"""
import sqlite3

db_path = "data/production/peptide_management.db"
conn = sqlite3.connect(db_path)

print("=== RAYSHINE VARIANTS ===")
cursor = conn.execute("""
    SELECT DISTINCT supplier_name, COUNT(*) as count 
    FROM janoshik_certificates 
    WHERE LOWER(supplier_name) LIKE '%rayshine%' 
    GROUP BY supplier_name
    ORDER BY count DESC
""")
for row in cursor.fetchall():
    print(f"{row[0]}: {row[1]} certs")

print("\n=== MAI/MEI VARIANTS ===")
cursor = conn.execute("""
    SELECT DISTINCT supplier_name, COUNT(*) as count 
    FROM janoshik_certificates 
    WHERE LOWER(supplier_name) LIKE '%mai%' OR LOWER(supplier_name) LIKE '%mei%' 
    GROUP BY supplier_name
    ORDER BY count DESC
""")
for row in cursor.fetchall():
    print(f"{row[0]}: {row[1]} certs")

conn.close()
