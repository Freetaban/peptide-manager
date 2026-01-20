"""Check scores discrepancy"""
import sqlite3

conn = sqlite3.connect('data/production/peptide_management.db')
cur = conn.cursor()

print('\n' + '=' * 80)
print('TOP 10 SUPPLIERS - janoshik_quality_score (from suppliers table)')
print('=' * 80)

cur.execute("""
    SELECT name, janoshik_quality_score, janoshik_certificates
    FROM suppliers
    WHERE janoshik_quality_score IS NOT NULL
    ORDER BY janoshik_quality_score DESC
    LIMIT 10
""")

for row in cur.fetchall():
    name, score, certs = row
    print(f'{name[:35]:35} | Score: {score:5.1f} | Certs: {certs:3d}')

print('\n' + '=' * 80)
print('COMPOSITE SCORE from Janoshik UI (scorer.calculate_rankings)')
print('=' * 80)

# Simula il calcolo della GUI
from peptide_manager.janoshik.analytics import JanoshikAnalytics

analytics = JanoshikAnalytics('data/production/peptide_management.db')
df = analytics.get_top_vendors(time_window_days=None, min_certificates=3, limit=10)

if not df.empty:
    for _, row in df.iterrows():
        print(f'{row["supplier_name"][:35]:35} | Score: {row["composite_score"]:5.1f} | Certs: {row["total_certificates"]:3d}')

conn.close()
