import sqlite3

# Check production DB
conn = sqlite3.connect('data/production/peptide_management.db')
cur = conn.cursor()

print('Production DB - First 10 suppliers:')
cur.execute('SELECT id, name, janoshik_quality_score FROM suppliers ORDER BY id LIMIT 10')
for row in cur.fetchall():
    print(f'  ID {row[0]}: {row[1][:30]:30} | Score: {row[2]}')

print('\n' + '='*60)
print('Suppliers with janoshik_quality_score:')
cur.execute('SELECT COUNT(*) FROM suppliers WHERE janoshik_quality_score IS NOT NULL')
count = cur.fetchone()[0]
print(f'  Total: {count}')

conn.close()

# Check development DB
print('\n' + '='*60)
try:
    conn = sqlite3.connect('data/development/peptide_management.db')
    cur = conn.cursor()
    
    print('Development DB - First 10 suppliers:')
    cur.execute('SELECT id, name, janoshik_quality_score FROM suppliers ORDER BY id LIMIT 10')
    for row in cur.fetchall():
        print(f'  ID {row[0]}: {row[1][:30]:30} | Score: {row[2]}')
    
    print('\nSuppliers with janoshik_quality_score:')
    cur.execute('SELECT COUNT(*) FROM suppliers WHERE janoshik_quality_score IS NOT NULL')
    count = cur.fetchone()[0]
    print(f'  Total: {count}')
    
    conn.close()
except Exception as e:
    print(f'  Development DB not found or error: {e}')
