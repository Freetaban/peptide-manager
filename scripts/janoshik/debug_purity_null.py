import sys
sys.path.insert(0, 'scripts')
import sqlite3
from environment import get_environment

env = get_environment()
conn = sqlite3.connect(env.db_path)

# Count purity
cursor = conn.execute("""
    SELECT 
        COUNT(*) as total,
        COUNT(purity_percentage) as with_purity,
        COUNT(*) - COUNT(purity_percentage) as null_purity
    FROM janoshik_certificates
""")
row = cursor.fetchone()
print(f"Total: {row[0]}, With purity: {row[1]}, NULL purity: {row[2]}")

# Sample Tirzepatide SENZA purity
cursor = conn.execute("""
    SELECT product_name, test_date, purity_percentage
    FROM janoshik_certificates 
    WHERE product_name LIKE '%Tirzepatide%' 
      AND purity_percentage IS NULL 
    LIMIT 5
""")
print("\nSample Tirzepatide senza purity:")
for row in cursor:
    print(f"  - {row[0]} | {row[1]} | purity={row[2]}")

# Sample Tirzepatide CON purity
cursor = conn.execute("""
    SELECT product_name, test_date, purity_percentage
    FROM janoshik_certificates 
    WHERE product_name LIKE '%Tirzepatide%' 
      AND purity_percentage IS NOT NULL 
    LIMIT 5
""")
print("\nSample Tirzepatide CON purity:")
for row in cursor:
    print(f"  - {row[0]} | {row[1]} | purity={row[2]}")

conn.close()
