import sqlite3

conn = sqlite3.connect('data/production/peptide_management.db')
cur = conn.cursor()

print('='*70)
print('CORREZIONE LILITIDE')
print('='*70)

# Verifica nome in janoshik_certificates
cur.execute('''
    SELECT DISTINCT supplier_name, COUNT(*) as count
    FROM janoshik_certificates
    WHERE supplier_name LIKE '%litide%'
    GROUP BY supplier_name
''')

janoshik_name = None
for name, count in cur.fetchall():
    print(f'\nIn janoshik_certificates: {name} ({count} certificati)')
    janoshik_name = name

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
    
    # Aggiorna con nome semplificato e sito corretto
    new_name = 'Lilitide'
    new_website = 'www.lilipetide.com'
    
    cur.execute('''
        UPDATE suppliers 
        SET name = ?, website = ?
        WHERE id = ?
    ''', (new_name, new_website, supplier_id))
    
    conn.commit()
    
    print(f'\n✅ Aggiornato:')
    print(f'   Nome nuovo: {new_name}')
    print(f'   Sito nuovo: {new_website}')
    
    # NOTA: I certificati rimangono con "Lilitide Technology"
    # per il calcolo dello score dobbiamo usare quel nome
    print(f'\n⚠️  Nota: i certificati Janoshik restano con "{janoshik_name}"')
else:
    print('Fornitore non trovato')

conn.close()
