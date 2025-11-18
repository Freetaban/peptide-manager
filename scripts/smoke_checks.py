import sqlite3
from pathlib import Path

paths = [
    Path('data/staging/peptide_management.db'),
    Path('data/development/peptide_management.db')
]

for p in paths:
    print('\nDB:', p)
    if not p.exists():
        print('  MISSING')
        continue
    conn = sqlite3.connect(str(p))
    cur = conn.cursor()
    try:
        # Basic counts
        for tbl in ['batches','preparations','administrations','cycles']:
            try:
                cur.execute(f'SELECT COUNT(*) FROM {tbl}')
                n = cur.fetchone()[0]
                print(f'  {tbl}: {n}')
            except Exception as e:
                print(f'  {tbl}: ERROR ({e})')
        # Show migrations
        try:
            cur.execute('SELECT migration_name, applied_at FROM schema_migrations ORDER BY applied_at')
            rows = cur.fetchall()
            print('  schema_migrations:')
            for r in rows:
                print('   -', r[0], r[1])
        except Exception as e:
            print('  schema_migrations: ERROR', e)
    finally:
        conn.close()
