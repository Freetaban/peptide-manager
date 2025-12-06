"""Test query con LIMIT 10 prima del GROUP BY"""
import sys
sys.path.insert(0, 'scripts')
import sqlite3
from environment import get_environment

env = get_environment()
conn = sqlite3.connect(env.db_path)

# Test 1: Senza GROUP BY, primi 20 per vedere cosa produce il CASE
print("Test 1: CASE su primi 20, SENZA GROUP BY")
query1 = """
    SELECT 
        product_name,
        CASE 
            WHEN product_name LIKE '%Tirzepatide%' OR product_name LIKE '%Tirze%' THEN 'Tirzepatide'
            WHEN product_name LIKE '%Semaglutide%' OR product_name LIKE '%Sema%' THEN 'Semaglutide'
            WHEN product_name LIKE '%Retatrutide%' OR product_name LIKE '%Reta%' THEN 'Retatrutide'
            ELSE RTRIM(SUBSTR(product_name, 1, INSTR(product_name || ' ', ' ') - 1), '0123456789')
        END as peptide_name
    FROM janoshik_certificates
    WHERE product_name IS NOT NULL
    LIMIT 20
"""
cursor = conn.execute(query1)
for row in cursor:
    print(f"  {row[0]:40s} → {row[1]}")

# Test 2: CON GROUP BY su primi 100
print("\n\nTest 2: CON GROUP BY su subset (primi 100 via subquery)")
query2 = """
    SELECT 
        CASE 
            WHEN product_name LIKE '%Tirzepatide%' OR product_name LIKE '%Tirze%' THEN 'Tirzepatide'
            WHEN product_name LIKE '%Semaglutide%' OR product_name LIKE '%Sema%' THEN 'Semaglutide'
            WHEN product_name LIKE '%Retatrutide%' OR product_name LIKE '%Reta%' THEN 'Retatrutide'
            ELSE RTRIM(SUBSTR(product_name, 1, INSTR(product_name || ' ', ' ') - 1), '0123456789')
        END as peptide_name,
        COUNT(*) as cnt
    FROM (
        SELECT product_name 
        FROM janoshik_certificates 
        WHERE product_name IS NOT NULL
        LIMIT 100
    )
    GROUP BY peptide_name
    ORDER BY cnt DESC
"""
cursor = conn.execute(query2)
for row in cursor:
    print(f"  {row[1]:3d} - {row[0]}")

# Test 3: CON GROUP BY su TUTTI (query esatta da analytics.py)
print("\n\nTest 3: CON GROUP BY su TUTTI (query esatta)")
query3 = """
    SELECT 
        CASE 
            WHEN product_name LIKE '%Tirzepatide%' OR product_name LIKE '%Tirze%' THEN 'Tirzepatide'
            WHEN product_name LIKE '%Semaglutide%' OR product_name LIKE '%Sema%' THEN 'Semaglutide'
            WHEN product_name LIKE '%Retatrutide%' OR product_name LIKE '%Reta%' THEN 'Retatrutide'
            ELSE RTRIM(SUBSTR(product_name, 1, INSTR(product_name || ' ', ' ') - 1), '0123456789')
        END as peptide_name,
        COUNT(*) as cnt
    FROM janoshik_certificates
    WHERE product_name IS NOT NULL
    GROUP BY peptide_name
    HAVING COUNT(*) >= 2
    ORDER BY cnt DESC
    LIMIT 30
"""
cursor = conn.execute(query3)
for row in cursor:
    print(f"  {row[1]:3d} - {row[0]}")

conn.close()
