"""
Analisi statistica scostamenti quantità dichiarata vs testata
"""
import sqlite3
import json
import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

db = "data/development/peptide_management.db"
conn = sqlite3.connect(db)

print("=" * 80)
print("📊 ANALISI STATISTICA SCOSTAMENTI QUANTITÀ")
print("=" * 80)

# Estrai tutti i certificati con quantità dichiarata e testata
query = """
    SELECT 
        task_number,
        supplier_name,
        peptide_name,
        quantity_tested_mg,
        raw_data
    FROM janoshik_certificates
    WHERE quantity_tested_mg IS NOT NULL
"""

df_certs = pd.read_sql_query(query, conn)
conn.close()

# Calcola scostamenti
data = []
for _, row in df_certs.iterrows():
    qty_tested = row['quantity_tested_mg']
    
    if row['raw_data']:
        raw = json.loads(row['raw_data'])
        sample = raw.get('sample', row['peptide_name'])
    else:
        sample = row['peptide_name']
    
    # Cerca quantità dichiarata
    match = re.search(r'(\d+(?:\.\d+)?)\s*mg', sample, re.IGNORECASE)
    if not match:
        continue
    
    qty_declared = float(match.group(1))
    
    # Scostamento assoluto e percentuale
    deviation_mg = qty_tested - qty_declared
    deviation_pct = (deviation_mg / qty_declared) * 100
    
    data.append({
        'task_number': row['task_number'],
        'supplier': row['supplier_name'],
        'sample': sample[:50],
        'declared_mg': qty_declared,
        'tested_mg': qty_tested,
        'deviation_mg': deviation_mg,
        'deviation_pct': deviation_pct
    })

df = pd.DataFrame(data)

print(f"\n📈 Dataset: {len(df)} certificati con quantità dichiarata e testata")
print(f"   Suppliers: {df['supplier'].nunique()} unici")

# 1. Statistiche descrittive scostamenti percentuali
print("\n📊 STATISTICHE SCOSTAMENTI PERCENTUALI:")
print(f"   Media: {df['deviation_pct'].mean():.2f}%")
print(f"   Mediana: {df['deviation_pct'].median():.2f}%")
print(f"   Std Dev: {df['deviation_pct'].std():.2f}%")
print(f"   Min: {df['deviation_pct'].min():.2f}%")
print(f"   Max: {df['deviation_pct'].max():.2f}%")
print(f"\n   Percentili:")
print(f"     5%:  {df['deviation_pct'].quantile(0.05):.2f}%")
print(f"     25%: {df['deviation_pct'].quantile(0.25):.2f}%")
print(f"     50%: {df['deviation_pct'].quantile(0.50):.2f}%")
print(f"     75%: {df['deviation_pct'].quantile(0.75):.2f}%")
print(f"     95%: {df['deviation_pct'].quantile(0.95):.2f}%")

# 2. Outliers detection (metodo IQR)
Q1 = df['deviation_pct'].quantile(0.25)
Q3 = df['deviation_pct'].quantile(0.75)
IQR = Q3 - Q1
lower_bound = Q1 - 1.5 * IQR
upper_bound = Q3 + 1.5 * IQR

outliers = df[(df['deviation_pct'] < lower_bound) | (df['deviation_pct'] > upper_bound)]

print(f"\n🔍 OUTLIERS DETECTION (metodo IQR 1.5x):")
print(f"   Range normale: [{lower_bound:.2f}%, {upper_bound:.2f}%]")
print(f"   Outliers trovati: {len(outliers)} ({len(outliers)/len(df)*100:.1f}%)")

if len(outliers) > 0:
    print("\n   Outliers identificati:")
    for _, out in outliers.iterrows():
        print(f"     • #{out['task_number']}: {out['supplier']}")
        print(f"       {out['sample']}")
        print(f"       Dichiarato: {out['declared_mg']}mg → Testato: {out['tested_mg']}mg")
        print(f"       Scostamento: {out['deviation_pct']:+.1f}%")
        print()

# 3. Distribuzione scostamenti positivi vs negativi
positive = df[df['deviation_pct'] > 0]
negative = df[df['deviation_pct'] < 0]
zero = df[df['deviation_pct'] == 0]

print("\n📊 DISTRIBUZIONE SCOSTAMENTI:")
print(f"   Positivi (+): {len(positive)} ({len(positive)/len(df)*100:.1f}%)")
print(f"     Media: +{positive['deviation_pct'].mean():.2f}%")
print(f"     Mediana: +{positive['deviation_pct'].median():.2f}%")
print(f"\n   Negativi (-): {len(negative)} ({len(negative)/len(df)*100:.1f}%)")
print(f"     Media: {negative['deviation_pct'].mean():.2f}%")
print(f"     Mediana: {negative['deviation_pct'].median():.2f}%")
print(f"\n   Esatti (0): {len(zero)} ({len(zero)/len(df)*100:.1f}%)")

# 4. Senza outliers
df_clean = df[(df['deviation_pct'] >= lower_bound) & (df['deviation_pct'] <= upper_bound)]

print(f"\n📊 STATISTICHE SENZA OUTLIERS ({len(df_clean)} certificati):")
print(f"   Media: {df_clean['deviation_pct'].mean():.2f}%")
print(f"   Mediana: {df_clean['deviation_pct'].median():.2f}%")
print(f"   Std Dev: {df_clean['deviation_pct'].std():.2f}%")
print(f"   Range: [{df_clean['deviation_pct'].min():.2f}%, {df_clean['deviation_pct'].max():.2f}%]")

# 5. Suggerimenti per soglie
print("\n💡 SUGGERIMENTI PER SOGLIE:")
print("   Basandosi sui dati:")
print(f"   • Range 'normale' (IQR): [{lower_bound:.1f}%, {upper_bound:.1f}%]")
print(f"   • Range 95% dei dati: [{df['deviation_pct'].quantile(0.025):.1f}%, {df['deviation_pct'].quantile(0.975):.1f}%]")
print("\n   Proposta algoritmo:")
print("   1. Escludi outliers > ±50% (probabili mislabeling)")
print("   2. Scostamenti negativi sono PEGGIO di positivi")
print("   3. Range ottimale: -5% / +15%")
print("      • Entro range: score alto")
print("      • Fuori range: penalità proporzionale allo scostamento")

# 6. Export CSV per analisi
df.to_csv('data/exports/quantity_deviations_analysis.csv', index=False)
print(f"\n💾 Dati esportati: data/exports/quantity_deviations_analysis.csv")

print("\n" + "=" * 80)
