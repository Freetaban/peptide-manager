"""Script temporaneo per verificare normalizzazioni"""
import sqlite3

conn = sqlite3.connect('data/production/peptide_management.db')
cur = conn.cursor()

print('PEPTIDI CONTENENTI BPC:')
for row in cur.execute('SELECT peptide_name_std, COUNT(*) FROM janoshik_certificates WHERE peptide_name_std LIKE "%BPC%" GROUP BY peptide_name_std').fetchall():
    print(f'  {row[0]} ({row[1]} certificati)')

print('\nPEPTIDI CONTENENTI GLP:')
for row in cur.execute('SELECT peptide_name_std, COUNT(*) FROM janoshik_certificates WHERE peptide_name_std LIKE "%GLP%" GROUP BY peptide_name_std').fetchall():
    print(f'  {row[0]} ({row[1]} certificati)')

print('\nSemaglutide, Tirzepatide, Retatrutide:')
for peptide in ['Semaglutide', 'Tirzepatide', 'Retatrutide']:
    cur.execute('SELECT COUNT(*) FROM janoshik_certificates WHERE peptide_name_std = ?', (peptide,))
    count = cur.fetchone()[0]
    print(f'  {peptide}: {count} certificati')

print('\nVENDOR CONTENENTI PEPTIDEGURUS:')
for row in cur.execute('SELECT supplier_name, COUNT(*) FROM janoshik_certificates WHERE LOWER(supplier_name) LIKE "%peptideguru%" GROUP BY supplier_name').fetchall():
    print(f'  {row[0]} ({row[1]} certificati)')

print('\nVENDOR CONTENENTI MANDY:')
for row in cur.execute('SELECT supplier_name, COUNT(*) FROM janoshik_certificates WHERE LOWER(supplier_name) LIKE "%mandy%" GROUP BY supplier_name').fetchall():
    print(f'  {row[0]} ({row[1]} certificati)')

print('\nPeptide Gurus unificato:')
cur.execute('SELECT COUNT(*) FROM janoshik_certificates WHERE supplier_name = "Peptide Gurus"')
count = cur.fetchone()[0]
print(f'  {count} certificati')

print('\n' + '=' * 80)
print('SUPPLIERS CON WEBSITE')
print('=' * 80)
cur.execute('SELECT name, website FROM suppliers WHERE website IS NOT NULL ORDER BY name LIMIT 15')
for row in cur.fetchall():
    print(f'  {row[0]}: {row[1]}')

print('\nMODERN RESEARCH:')
cur.execute('SELECT name, website FROM suppliers WHERE name LIKE "%Modern%"')
result = cur.fetchone()
if result:
    print(f'  {result[0]}')
    print(f'  Website: {result[1] or "(nessun website)"}')
else:
    print('  Non trovato')

print('\n' + '=' * 80)
print('STATISTICHE RATING SUPPLIERS')
print('=' * 80)
cur.execute('''
    SELECT 
        reliability_rating,
        COUNT(*) as count,
        ROUND(AVG(janoshik_quality_score), 1) as avg_score,
        GROUP_CONCAT(name, ", ") as examples
    FROM (
        SELECT 
            reliability_rating,
            janoshik_quality_score,
            name,
            ROW_NUMBER() OVER (PARTITION BY reliability_rating ORDER BY janoshik_quality_score DESC) as rn
        FROM suppliers
        WHERE deleted_at IS NULL 
          AND janoshik_certificates > 0
    )
    WHERE rn <= 3
    GROUP BY reliability_rating
    ORDER BY reliability_rating DESC
''')
for row in cur.fetchall():
    rating, count, avg_score, examples = row
    if rating:
        stars = '⭐' * rating
        print(f'{stars} Rating {rating}: {count} supplier | Avg Score: {avg_score}')
        # Mostra primi 3 esempi
        example_list = examples.split(', ')[:3]
        for ex in example_list:
            print(f'    - {ex}')

conn.close()
