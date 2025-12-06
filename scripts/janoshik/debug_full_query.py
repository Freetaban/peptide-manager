import sys
sys.path.insert(0, 'scripts')
import sqlite3
from environment import get_environment

env = get_environment()
conn = sqlite3.connect(env.db_path)

print("Step 1: Count BEFORE CASE")
cursor = conn.execute("""
    SELECT COUNT(*) as total,
           COUNT(CASE WHEN product_name LIKE '%Tirzepatide%' THEN 1 END) as tirz,
           COUNT(CASE WHEN product_name LIKE '%Retatrutide%' THEN 1 END) as reta,
           COUNT(CASE WHEN product_name LIKE '%Semaglutide%' THEN 1 END) as sema
    FROM janoshik_certificates
    WHERE product_name IS NOT NULL
      AND purity_percentage IS NOT NULL
""")
row = cursor.fetchone()
print(f"Total: {row[0]}, Tirz: {row[1]}, Reta: {row[2]}, Sema: {row[3]}")

print("\nStep 2: CASE with GROUP BY")
cursor = conn.execute("""
    SELECT 
        CASE 
            WHEN product_name LIKE '%Tirzepatide%' THEN 'Tirzepatide'
            WHEN product_name LIKE '%Retatrutide%' THEN 'Retatrutide'
            WHEN product_name LIKE '%Semaglutide%' THEN 'Semaglutide'
            ELSE 'Other'
        END as peptide_name,
        COUNT(*) as cnt
    FROM janoshik_certificates
    WHERE product_name IS NOT NULL
      AND purity_percentage IS NOT NULL
    GROUP BY peptide_name
    ORDER BY cnt DESC
""")
for row in cursor:
    print(f"{row[1]:3d} - {row[0]}")

print("\nStep 3: Full query (senza min_certificates)")
cursor = conn.execute("""
    SELECT 
        CASE 
            WHEN product_name LIKE '%Tirzepatide%' OR product_name LIKE '%Tirze%' THEN 'Tirzepatide'
            WHEN product_name LIKE '%Semaglutide%' OR product_name LIKE '%Sema%' THEN 'Semaglutide'
            WHEN product_name LIKE '%Retatrutide%' OR product_name LIKE '%Reta%' THEN 'Retatrutide'
            ELSE RTRIM(SUBSTR(product_name, 1, INSTR(product_name || ' ', ' ') - 1), '0123456789')
        END as peptide_name,
        COUNT(*) as test_count
    FROM janoshik_certificates
    WHERE product_name IS NOT NULL
      AND purity_percentage IS NOT NULL
    GROUP BY peptide_name
    ORDER BY test_count DESC
    LIMIT 10
""")
print("\nTop 10:")
for row in cursor:
    print(f"{row[1]:3d} - {row[0]}")

conn.close()
