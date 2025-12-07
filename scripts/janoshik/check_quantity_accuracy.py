"""Verify quantity data availability"""
import sqlite3
import json
import re

conn = sqlite3.connect('data/development/peptide_management.db')
cur = conn.cursor()

cur.execute("""
    SELECT peptide_name, quantity_tested_mg, raw_data 
    FROM janoshik_certificates 
    WHERE purity_percentage > 0 
    LIMIT 10
""")

print("=" * 80)
print("ANALISI QUANTITÀ DICHIARATA VS TESTATA")
print("=" * 80)

for row in cur.fetchall():
    peptide_name, qty_tested, raw_data_json = row
    
    if raw_data_json:
        raw = json.loads(raw_data_json)
        sample = raw.get('sample', peptide_name)
    else:
        sample = peptide_name
    
    # Cerca quantità dichiarata nel nome (es: "Retatrutide 40mg", "BPC-157 10mg")
    match = re.search(r'(\d+(?:\.\d+)?)\s*mg', sample, re.IGNORECASE)
    declared_mg = float(match.group(1)) if match else None
    
    print(f"\n📋 Sample: {sample[:70]}")
    print(f"   Dichiarato: {declared_mg} mg" if declared_mg else "   Dichiarato: N/A (non trovato nel nome)")
    print(f"   Testato: {qty_tested} mg")
    
    if declared_mg and qty_tested:
        diff_pct = abs(qty_tested - declared_mg) / declared_mg * 100
        accuracy = max(0, 100 - diff_pct)
        print(f"   Differenza: {diff_pct:.1f}% → Accuracy: {accuracy:.1f}%")

conn.close()
print("\n" + "=" * 80)
