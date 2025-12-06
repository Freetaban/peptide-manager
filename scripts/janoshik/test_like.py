import sys
sys.path.insert(0, 'scripts')
import sqlite3
from environment import get_environment

env = get_environment()
conn = sqlite3.connect(env.db_path)

# Test LIKE '%Tirzepatide%'
cursor = conn.execute("""
    SELECT product_name 
    FROM janoshik_certificates 
    WHERE product_name LIKE '%Tirzepatide%' 
    LIMIT 10
""")
res = cursor.fetchall()
print(f"Match '%Tirzepatide%': {len(res)}")
for r in res:
    print(f"  - {r[0]}")

# Test RTRIM su primo risultato
if res:
    sample = res[0][0]
    cursor = conn.execute("""
        SELECT 
            ? as original,
            SUBSTR(?, 1, INSTR(? || ' ', ' ') - 1) as first_word,
            RTRIM(SUBSTR(?, 1, INSTR(? || ' ', ' ') - 1), '0123456789') as cleaned
    """, (sample, sample, sample, sample, sample))
    row = cursor.fetchone()
    print(f"\nTest fallback su '{row[0]}':")
    print(f"  first_word: '{row[1]}'")
    print(f"  cleaned: '{row[2]}'")

conn.close()
