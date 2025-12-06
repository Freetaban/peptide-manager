"""
Analisi dati Janoshik estratti
"""
import sqlite3
import pandas as pd

db_path = "data/development/peptide_management.db"
conn = sqlite3.connect(db_path)

print("=" * 80)
print("ANALISI DATI JANOSHIK")
print("=" * 80)

# 1. Statistiche certificati
print("\n📊 CERTIFICATI NEL DATABASE:")
query = "SELECT COUNT(*) as total FROM janoshik_certificates"
total = pd.read_sql_query(query, conn).iloc[0]['total']
print(f"   Totale certificati: {total}")

# 2. Distribuzione per supplier
print("\n🏢 DISTRIBUZIONE PER SUPPLIER:")
query = """
    SELECT 
        supplier_name,
        COUNT(*) as num_certs,
        AVG(purity_percentage) as avg_purity,
        AVG(quantity_tested_mg) as avg_quantity
    FROM janoshik_certificates
    GROUP BY supplier_name
    ORDER BY num_certs DESC
    LIMIT 15
"""
df_suppliers = pd.read_sql_query(query, conn)
for _, row in df_suppliers.iterrows():
    purity = row['avg_purity'] if pd.notna(row['avg_purity']) else 'N/A'
    print(f"   {row['supplier_name']}: {row['num_certs']} certs, "
          f"purity={purity}%, qty={row['avg_quantity']:.2f}mg")

# 3. Certificati con problemi di parsing
print("\n⚠️ CERTIFICATI CON PURITY=0 O NULL:")
query = """
    SELECT task_number, supplier_name, peptide_name, purity_percentage, quantity_tested_mg
    FROM janoshik_certificates
    WHERE purity_percentage IS NULL OR purity_percentage = 0
    LIMIT 10
"""
df_issues = pd.read_sql_query(query, conn)
if len(df_issues) > 0:
    print(f"   Trovati {len(df_issues)} certificati:")
    for _, row in df_issues.iterrows():
        print(f"   - #{row['task_number']}: {row['supplier_name']} - {row['peptide_name']}, "
              f"purity={row['purity_percentage']}, qty={row['quantity_tested_mg']}")
else:
    print("   Nessun problema trovato!")

# 4. Certificati validi
print("\n✅ CERTIFICATI CON DATI VALIDI:")
query = """
    SELECT COUNT(*) as valid_count
    FROM janoshik_certificates
    WHERE purity_percentage > 0 AND quantity_tested_mg > 0
"""
valid = pd.read_sql_query(query, conn).iloc[0]['valid_count']
print(f"   Certificati con purity e quantity validi: {valid} ({valid/total*100:.1f}%)")

# 5. Rankings
print("\n🏆 SUPPLIER RANKINGS:")
query = """
    SELECT 
        supplier_name,
        total_score,
        total_certificates,
        avg_purity,
        days_since_last_cert
    FROM supplier_rankings
    ORDER BY total_score DESC
    LIMIT 10
"""
df_rankings = pd.read_sql_query(query, conn)
for i, row in df_rankings.iterrows():
    print(f"   {i+1}. {row['supplier_name']}: {row['total_score']:.2f} pts "
          f"({row['total_certificates']} certs, {row['avg_purity']:.2f}% purity, "
          f"{row['days_since_last_cert']} days)")

conn.close()

print("\n" + "=" * 80)
