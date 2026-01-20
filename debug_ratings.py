"""Debug rating suppliers"""
import sqlite3

conn = sqlite3.connect('data/production/peptide_management.db')
cur = conn.cursor()

print('Verifica rating esistenti:')
cur.execute('''
    SELECT name, reliability_rating, janoshik_quality_score, janoshik_certificates
    FROM suppliers
    WHERE janoshik_certificates > 0
    ORDER BY janoshik_quality_score DESC
    LIMIT 10
''')

for row in cur.fetchall():
    name, rating, score, certs = row
    print(f'  {name[:35]:35} | Rating: {rating} | Score: {score} | Certs: {certs}')

conn.close()
