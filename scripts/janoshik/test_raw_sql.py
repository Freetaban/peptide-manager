"""Test query SQL raw"""
import sys
sys.path.insert(0, 'scripts')
import sqlite3
from environment import get_environment

env = get_environment()
conn = sqlite3.connect(env.db_path)

# Prendo esattamente la query da analytics.py
query = """
    SELECT 
        CASE 
            -- GLP-1 Agonisti
            WHEN product_name LIKE '%Tirzepatide%' OR product_name LIKE '%Tirze%' THEN 'Tirzepatide'
            WHEN product_name LIKE '%Semaglutide%' OR product_name LIKE '%Sema%' THEN 'Semaglutide'
            WHEN product_name LIKE '%Retatrutide%' OR product_name LIKE '%Reta%' THEN 'Retatrutide'
            
            -- Fallback
            ELSE RTRIM(SUBSTR(product_name, 1, INSTR(product_name || ' ', ' ') - 1), '0123456789')
        END as peptide_name,
        COUNT(*) as test_count,
        COUNT(DISTINCT supplier_name) as vendor_count,
        AVG(purity_percentage) as avg_purity
    FROM janoshik_certificates
    WHERE product_name IS NOT NULL
    GROUP BY peptide_name
    HAVING COUNT(*) >= 2
    ORDER BY test_count DESC
    LIMIT 30
"""

cursor = conn.execute(query)
rows = cursor.fetchall()

print(f"Risultati: {len(rows)}")
print("\nTop 30:")
for idx, row in enumerate(rows, 1):
    print(f"#{idx:2d} {row[0]:20s} - {row[1]:3d} test, {row[2]:2d} vendors, avg_purity={row[3]}")

conn.close()
