"""Verifica contenuto product_name"""
import sys
sys.path.insert(0, 'scripts')
import sqlite3
from environment import get_environment

env = get_environment()
conn = sqlite3.connect(env.db_path)

# Sample diversi product_name
cursor = conn.execute("""
    SELECT DISTINCT product_name 
    FROM janoshik_certificates 
    WHERE product_name NOT LIKE '%Tirzepatide%' 
      AND product_name NOT LIKE '%Semaglutide%'
      AND product_name NOT LIKE '%Retatrutide%'
      AND product_name NOT LIKE '%BPC%'
    ORDER BY product_name 
    LIMIT 40
""")

print("Sample product_name (no major peptides):")
for row in cursor.fetchall():
    print(f"  - {row[0]}")

# Test fallback RTRIM
print("\n--- Test fallback RTRIM su sample ---")
cursor = conn.execute("""
    SELECT 
        product_name,
        SUBSTR(product_name, 1, INSTR(product_name || ' ', ' ') - 1) as first_word,
        RTRIM(SUBSTR(product_name, 1, INSTR(product_name || ' ', ' ') - 1), '0123456789') as cleaned
    FROM janoshik_certificates
    WHERE product_name NOT LIKE '%Tirzepatide%'
      AND product_name NOT LIKE '%Semaglutide%'
      AND product_name NOT LIKE '%Retatrutide%'
    LIMIT 20
""")

for row in cursor:
    print(f"'{row[0]}' → first:'{row[1]}' → cleaned:'{row[2]}'")

conn.close()
