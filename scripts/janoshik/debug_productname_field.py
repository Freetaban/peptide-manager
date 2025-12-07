"""Verifica campo product_name"""
import sys
sys.path.insert(0, 'scripts')
import sqlite3
from environment import get_environment

env = get_environment()
conn = sqlite3.connect(env.db_path)

# Sample random product_name
cursor = conn.execute("""
    SELECT id, product_name 
    FROM janoshik_certificates 
    LIMIT 50
""")

print("Sample primi 50 product_name:")
for row in cursor:
    print(f"  ID {row[0]:3d}: {row[1]}")

# Count NULL
cursor = conn.execute("""
    SELECT 
        COUNT(*) as total,
        COUNT(product_name) as non_null,
        COUNT(*) - COUNT(product_name) as nulls
    FROM janoshik_certificates
""")
row = cursor.fetchone()
print(f"\nTotal: {row[0]}, Non-NULL: {row[1]}, NULL: {row[2]}")

# Count distinct
cursor = conn.execute("""
    SELECT COUNT(DISTINCT product_name)
    FROM janoshik_certificates
    WHERE product_name IS NOT NULL
""")
print(f"Distinct product_name: {cursor.fetchone()[0]}")

conn.close()
