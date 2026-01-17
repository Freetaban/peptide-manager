"""Verifica rating suppliers"""
import sqlite3

conn = sqlite3.connect('data/production/peptide_management.db')
cur = conn.cursor()

print('=' * 80)
print('STATISTICHE RATING SUPPLIERS')
print('=' * 80)

cur.execute('''
    SELECT 
        reliability_rating,
        COUNT(*) as count,
        ROUND(AVG(janoshik_quality_score), 1) as avg_score,
        ROUND(AVG(janoshik_certificates), 1) as avg_certs
    FROM suppliers
    WHERE deleted_at IS NULL 
      AND janoshik_certificates > 0
    GROUP BY reliability_rating
    ORDER BY reliability_rating DESC
''')

for row in cur.fetchall():
    rating, count, avg_score, avg_certs = row
    if rating:
        stars = '⭐' * rating
        print(f'\n{stars} Rating {rating}:')
        print(f'  Suppliers: {count}')
        print(f'  Avg Quality Score: {avg_score}')
        print(f'  Avg Certificati: {avg_certs}')
        
        # Top 3 per questo rating
        cur.execute('''
            SELECT name, janoshik_quality_score, janoshik_certificates
            FROM suppliers
            WHERE reliability_rating = ? AND deleted_at IS NULL
            ORDER BY janoshik_quality_score DESC
            LIMIT 3
        ''', (rating,))
        
        print(f'  Top {min(3, count)}:')
        for name, score, certs in cur.fetchall():
            print(f'    - {name[:35]:35} | Score: {score:5.1f} | Certs: {certs:3d}')

print('\n' + '=' * 80)
print('TOP 10 SUPPLIERS (Overall)')
print('=' * 80)

cur.execute('''
    SELECT name, reliability_rating, janoshik_quality_score, janoshik_certificates
    FROM suppliers
    WHERE deleted_at IS NULL AND janoshik_certificates > 0
    ORDER BY janoshik_quality_score DESC
    LIMIT 10
''')

for i, (name, rating, score, certs) in enumerate(cur.fetchall(), 1):
    stars = '⭐' * (rating or 0)
    print(f'{i:2d}. {name[:30]:30} | {stars:12} | Score: {score:5.1f} | Certs: {certs:3d}')

conn.close()
