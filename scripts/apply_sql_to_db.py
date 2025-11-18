import sqlite3
import sys
from pathlib import Path

if len(sys.argv) < 3:
    print('Usage: python apply_sql_to_db.py <db_path> <sql_file>')
    sys.exit(2)

db_path = Path(sys.argv[1])
sql_file = Path(sys.argv[2])

if not db_path.exists():
    print(f"DB not found: {db_path}")
    sys.exit(1)
if not sql_file.exists():
    print(f"SQL file not found: {sql_file}")
    sys.exit(1)

sql = sql_file.read_text(encoding='utf-8')
conn = sqlite3.connect(str(db_path))
cur = conn.cursor()

print(f"Applying {sql_file.name} to {db_path}")
try:
    cur.executescript(sql)
    conn.commit()
    print('OK')
except Exception as e:
    conn.rollback()
    print('ERROR:', e)
finally:
    conn.close()
