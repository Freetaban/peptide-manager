import sys
sys.path.insert(0, 'scripts')
import sqlite3
from environment import get_environment

env = get_environment()
conn = sqlite3.connect(env.db_path)

# Test 1: CASE sulle righe Tirzepatide
print("Test 1: CASE su righe Tirzepatide")
cursor = conn.execute("""
    SELECT 
        product_name,
        CASE 
            WHEN product_name LIKE '%Tirzepatide%' THEN 'MATCH'
            ELSE 'NO_MATCH'
        END as match_result
    FROM janoshik_certificates
    WHERE product_name LIKE '%Tirzepatide%'
    LIMIT 5
""")
for row in cursor:
    print(f"  {row[0]:30s} → {row[1]}")

# Test 2: CASE con GROUP BY su subset
print("\nTest 2: CASE con GROUP BY su prime 100 righe")
cursor = conn.execute("""
    SELECT 
        CASE 
            WHEN product_name LIKE '%Tirzepatide%' THEN 'Tirzepatide'
            WHEN product_name LIKE '%Retatrutide%' THEN 'Retatrutide'
            ELSE 'Other'
        END as peptide_name,
        COUNT(*) as cnt
    FROM (
        SELECT product_name 
        FROM janoshik_certificates 
        WHERE purity_percentage IS NOT NULL
        LIMIT 100
    )
    GROUP BY peptide_name
    ORDER BY cnt DESC
""")
print("Result:")
for row in cursor:
    print(f"  {row[1]:3d} - {row[0]}")

# Test 3: Verifica schema tabella
print("\nTest 3: Schema tabella janoshik_certificates")
cursor = conn.execute("PRAGMA table_info(janoshik_certificates)")
print("Columns:")
for row in cursor:
    print(f"  {row[1]:25s} {row[2]:15s} NOT NULL={row[3]} PK={row[5]}")

conn.close()
