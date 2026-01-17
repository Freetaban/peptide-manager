import sqlite3

conn = sqlite3.connect('data/production/peptide_management.db')
cur = conn.cursor()

print('='*70)
print('CORREZIONE LILITIDE')
print('='*70)

# Cerca in janoshik_certificates
print('\nNomi in janoshik_certificates con "litide":')
cur.execute('''
    SELECT DISTINCT supplier_name, COUNT(*) as count
    FROM janoshik_certificates
    WHERE supplier_name LIKE '%litide%'
    GROUP BY supplier_name
''')

for name, count in cur.fetchall():
    print(f'  {name}: {count} certificati')

# Cerca anche nel manufacturer
print('\nNomi in manufacturer con "litide":')
cur.execute('''
    SELECT DISTINCT manufacturer, COUNT(*) as count
    FROM janoshik_certificates
    WHERE manufacturer LIKE '%litide%'
    GROUP BY manufacturer
''')

for name, count in cur.fetchall():
    print(f'  {name}: {count} certificati')

# Aggiorna supplier
print('\n' + '='*70)
print('AGGIORNAMENTO SUPPLIER')
print('='*70)

cur.execute('SELECT id, name, website FROM suppliers WHERE name LIKE "%lipetide%"')
supplier = cur.fetchone()

if supplier:
    supplier_id, old_name, website = supplier
    print(f'\nID: {supplier_id}')
    print(f'Nome vecchio: {old_name}')
    print(f'Sito web attuale: {website}')
    
    new_name = 'Lilitide'
    new_website = 'www.lilipetide.com'
    
    cur.execute('''
        UPDATE suppliers 
        SET name = ?, website = ?
        WHERE id = ?
    ''', (new_name, new_website, supplier_id))
    
    conn.commit()
    
    print(f'\n✅ Aggiornato:')
    print(f'   Nome: {new_name}')
    print(f'   Sito: {new_website}')
else:
    print('Fornitore non trovato')

conn.close()
