"""Debug query CASE peptide_name"""
import sys
sys.path.insert(0, 'scripts')
import sqlite3
from environment import get_environment

env = get_environment()
conn = sqlite3.connect(env.db_path)

# Query attuale con COUNT
cursor = conn.execute("""
    SELECT 
        CASE 
            -- GLP-1 Agonisti
            WHEN product_name LIKE '%Tirzepatide%' OR product_name LIKE '%Tirze%' THEN 'Tirzepatide'
            WHEN product_name LIKE '%Semaglutide%' OR product_name LIKE '%Sema%' THEN 'Semaglutide'
            WHEN product_name LIKE '%Retatrutide%' OR product_name LIKE '%Reta%' THEN 'Retatrutide'
            
            -- Fallback
            ELSE RTRIM(SUBSTR(product_name, 1, INSTR(product_name || ' ', ' ') - 1), '0123456789')
        END as peptide_name,
        COUNT(*) as cnt
    FROM janoshik_certificates
    WHERE product_name IS NOT NULL
    GROUP BY peptide_name
    HAVING COUNT(*) >= 2
    ORDER BY cnt DESC
    LIMIT 30
""")

print("Risultati query CASE (top 30):")
for row in cursor:
    print(f"{row[1]:3d} - {row[0]}")

# Verifica quanti "GLP" ci sono
cursor = conn.execute("""
    SELECT COUNT(*) 
    FROM janoshik_certificates 
    WHERE product_name LIKE '%GLP%'
""")
print(f"\n❓ Certificati con 'GLP' nel nome: {cursor.fetchone()[0]}")

# Verifica HGH/Somatropin
cursor = conn.execute("""
    SELECT product_name, COUNT(*) 
    FROM janoshik_certificates 
    WHERE product_name LIKE '%HGH%' OR product_name LIKE '%Somatropin%' OR product_name LIKE '%Qitrope%' OR product_name LIKE '%Hgh%'
    GROUP BY product_name
    ORDER BY COUNT(*) DESC
    LIMIT 10
""")
print("\n🧬 Prodotti HGH/Somatropin:")
for row in cursor:
    print(f"  {row[1]:3d} - {row[0]}")

conn.close()
