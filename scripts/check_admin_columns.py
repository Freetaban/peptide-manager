import sqlite3
from pathlib import Path

for p in ['data/staging/peptide_management.db','data/development/peptide_management.db']:
    path = Path(p)
    if not path.exists():
        print(p, 'MISSING')
        continue
    print('\nDB:', p)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    try:
        cur.execute("PRAGMA table_info(administrations);")
        rows = cur.fetchall()
        if not rows:
            print('  administrations table not found or no columns')
        else:
            for r in rows:
                print(' ', dict(r))
    except Exception as e:
        print('  error:', e)
    finally:
        conn.close()
