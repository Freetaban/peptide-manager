"""Verifica peptidi nel database"""
import sys
sys.path.insert(0, 'scripts')
import sqlite3
from environment import get_environment

env = get_environment()
conn = sqlite3.connect(env.db_path)

# Prodotti unici
cursor = conn.execute("""
    SELECT COUNT(DISTINCT product_name) 
    FROM janoshik_certificates 
    WHERE product_name IS NOT NULL
""")
print(f'Prodotti unici: {cursor.fetchone()[0]}')

# Top 20 prodotti
cursor = conn.execute("""
    SELECT product_name, COUNT(*) as cnt 
    FROM janoshik_certificates 
    WHERE product_name IS NOT NULL 
    GROUP BY product_name 
    ORDER BY cnt DESC 
    LIMIT 20
""")

print('\nTop 20 prodotti per numero test:')
for row in cursor:
    print(f'{row[1]:3d} - {row[0]}')

# Test query hottest peptides
print('\n--- Query hottest_peptides (ultimo mese) ---')
cursor = conn.execute("""
    SELECT 
        CASE 
            WHEN product_name LIKE '%Tirzepatide%' THEN 'Tirzepatide'
            WHEN product_name LIKE '%Semaglutide%' THEN 'Semaglutide'
            WHEN product_name LIKE '%Retatrutide%' THEN 'Retatrutide'
            WHEN product_name LIKE '%BPC%' THEN 'BPC-157'
            WHEN product_name LIKE '%TB-500%' THEN 'TB-500'
            WHEN product_name LIKE '%Ipamorelin%' THEN 'Ipamorelin'
            WHEN product_name LIKE '%CJC%' THEN 'CJC-1295'
            ELSE SUBSTR(product_name, 1, INSTR(product_name || ' ', ' ') - 1)
        END as peptide_name,
        COUNT(*) as test_count
    FROM janoshik_certificates
    WHERE test_date >= date('now', '-30 days')
      AND product_name IS NOT NULL
    GROUP BY peptide_name
    HAVING COUNT(*) >= 2
    ORDER BY test_count DESC
    LIMIT 30
""")

print(f'Peptidi trovati dalla query: {cursor.arraysize}')
for row in cursor:
    print(f'{row[1]:3d} - {row[0]}')

# Distribuzione temporale
print('\n--- Distribuzione temporale ---')
cursor = conn.execute("""
    SELECT 
        strftime('%Y-%m', test_date) as month, 
        COUNT(*) as cnt
    FROM janoshik_certificates 
    GROUP BY month 
    ORDER BY month DESC 
    LIMIT 12
""")
print('Ultimi 12 mesi:')
for row in cursor:
    print(f'{row[0]}: {row[1]:3d} certificati')

# Date min/max
cursor = conn.execute("""
    SELECT MIN(test_date), MAX(test_date), COUNT(*) 
    FROM janoshik_certificates
""")
row = cursor.fetchone()
print(f'\nRange date: {row[0]} → {row[1]} ({row[2]} certificati totali)')

conn.close()
