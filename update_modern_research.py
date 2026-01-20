"""Aggiorna Modern Research con website"""
import sqlite3

conn = sqlite3.connect('data/production/peptide_management.db')
cur = conn.cursor()

cur.execute('UPDATE suppliers SET website = ? WHERE name = ?', 
            ('www.modernpeptides.com', 'Modern Research'))
conn.commit()

print('✅ Modern Research aggiornato!')

cur.execute('SELECT name, website FROM suppliers WHERE name = "Modern Research"')
result = cur.fetchone()
print(f'  {result[0]}: {result[1]}')

conn.close()
