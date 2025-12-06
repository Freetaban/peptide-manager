"""
Report dettagliato Accuracy - Quantità dichiarata vs testata
"""
import sqlite3
import json
import re
import pandas as pd

db = "data/development/peptide_management.db"
conn = sqlite3.connect(db)

print("=" * 80)
print("📊 REPORT ACCURACY - Quantità Dichiarata vs Testata")
print("=" * 80)

# 1. Overview rankings con accuracy
print("\n🏆 TOP 10 SUPPLIERS (nuovo algoritmo con accuracy):")
rankings = pd.read_sql_query("""
    SELECT 
        rank_position,
        supplier_name,
        total_score,
        avg_purity,
        avg_accuracy,
        certs_with_accuracy,
        quality_score,
        accuracy_score
    FROM supplier_rankings
    ORDER BY rank_position
    LIMIT 10
""", conn)

for _, row in rankings.iterrows():
    acc_str = f"{row['avg_accuracy']:.1f}%" if pd.notna(row['avg_accuracy']) else "N/A"
    print(f"\n  {int(row['rank_position']):2d}. {row['supplier_name']}")
    print(f"      Score totale: {row['total_score']:.2f} pts")
    print(f"      Purezza: {row['avg_purity']:.2f}% (score: {row['quality_score']:.1f})")
    print(f"      Accuracy: {acc_str} su {int(row['certs_with_accuracy'])} certs (score: {row['accuracy_score']:.1f})")

# 2. Dettaglio certificati con grandi discrepanze
print("\n\n⚠️ CERTIFICATI CON BASSA ACCURACY (<80%):")
query = """
    SELECT 
        supplier_name,
        peptide_name,
        quantity_tested_mg,
        raw_data
    FROM janoshik_certificates
    WHERE quantity_tested_mg IS NOT NULL
    ORDER BY supplier_name
"""
cur = conn.cursor()
cur.execute(query)

low_accuracy_certs = []
for row in cur.fetchall():
    supplier, peptide, qty_tested, raw_json = row
    
    if raw_json:
        raw = json.loads(raw_json)
        sample = raw.get('sample', peptide)
    else:
        sample = peptide
    
    match = re.search(r'(\d+(?:\.\d+)?)\s*mg', sample, re.IGNORECASE)
    if not match:
        continue
    
    qty_declared = float(match.group(1))
    diff_pct = abs(qty_tested - qty_declared) / qty_declared * 100
    
    if diff_pct <= 10:
        accuracy = 100.0
    elif diff_pct <= 30:
        accuracy = 100 - (diff_pct - 10)
    else:
        accuracy = max(0, 70 - (diff_pct - 30) * 2)
    
    if accuracy < 80:
        low_accuracy_certs.append({
            'supplier': supplier,
            'sample': sample[:60],
            'declared': qty_declared,
            'tested': qty_tested,
            'diff_pct': diff_pct,
            'accuracy': accuracy
        })

if low_accuracy_certs:
    df_low = pd.DataFrame(low_accuracy_certs)
    for _, cert in df_low.iterrows():
        print(f"\n  Supplier: {cert['supplier']}")
        print(f"    Sample: {cert['sample']}")
        print(f"    Dichiarato: {cert['declared']} mg | Testato: {cert['tested']} mg")
        print(f"    Differenza: {cert['diff_pct']:.1f}% → Accuracy: {cert['accuracy']:.1f}%")
else:
    print("\n  ✅ Nessun certificato con accuracy < 80%!")

# 3. Best performers accuracy
print("\n\n🌟 BEST ACCURACY PERFORMERS:")
best = pd.read_sql_query("""
    SELECT 
        supplier_name,
        avg_accuracy,
        certs_with_accuracy
    FROM supplier_rankings
    WHERE avg_accuracy IS NOT NULL
    ORDER BY avg_accuracy DESC
    LIMIT 5
""", conn)

for i, row in best.iterrows():
    print(f"  {i+1}. {row['supplier_name']}: {row['avg_accuracy']:.2f}% avg ({int(row['certs_with_accuracy'])} certs)")

# 4. Pesi algoritmo
print("\n\n⚖️ PESI ALGORITMO SCORING:")
print("  • Volume: 20% (numero certificati)")
print("  • Quality: 25% (purezza media)")
print("  • Accuracy: 20% (quantità dichiarata vs testata) 🆕")
print("  • Consistency: 15% (variabilità purezza)")
print("  • Recency: 10% (attività recente)")
print("  • Endotoxin: 10% (livello endotossine)")
print("  ────────────────")
print("  TOTALE: 100%")

conn.close()
print("\n" + "=" * 80)
