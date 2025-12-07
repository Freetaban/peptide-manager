import sys
sys.path.insert(0, 'scripts')
import sqlite3
from environment import get_environment

env = get_environment()
conn = sqlite3.connect(env.db_path)

print("Query 1: SOLO WHERE product_name LIKE '%Tirzepatide%'")
cursor = conn.execute("""
    SELECT COUNT(*) 
    FROM janoshik_certificates
    WHERE product_name LIKE '%Tirzepatide%'
""")
print(f"Result: {cursor.fetchone()[0]} rows")

print("\nQuery 2: + AND purity_percentage IS NOT NULL")
cursor = conn.execute("""
    SELECT COUNT(*) 
    FROM janoshik_certificates
    WHERE product_name LIKE '%Tirzepatide%'
      AND purity_percentage IS NOT NULL
""")
print(f"Result: {cursor.fetchone()[0]} rows")

print("\nQuery 3: CASE su product_name con purity filter")
cursor = conn.execute("""
    SELECT 
        CASE 
            WHEN product_name LIKE '%Tirzepatide%' THEN 'Tirzepatide'
            ELSE 'Other'
        END as peptide_name,
        COUNT(*) as cnt
    FROM janoshik_certificates
    WHERE product_name IS NOT NULL
      AND purity_percentage IS NOT NULL
    GROUP BY peptide_name
    ORDER BY cnt DESC
""")
print("Result:")
for row in cursor:
    print(f"  {row[1]:3d} - {row[0]}")

print("\nQuery 4: Verifica sample con purity")
cursor = conn.execute("""
    SELECT product_name, purity_percentage
    FROM janoshik_certificates
    WHERE purity_percentage IS NOT NULL
    LIMIT 10
""")
print("Sample rows con purity:")
for row in cursor:
    print(f"  - {row[0][:40]:40s} | purity={row[1]}")

conn.close()
