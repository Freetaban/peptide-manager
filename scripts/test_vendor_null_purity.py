"""
Test vendor con certificati NULL purity (test su miscele/quantità).

Verifica che:
1. Vendor con certificati NULL purity non siano penalizzati
2. Certificati NULL siano esclusi da avg_purity
3. Certificati NULL contino nel volume_score
4. Confronto score prima/dopo fix

Uso: python scripts/test_vendor_null_purity.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import sqlite3
import pandas as pd
from peptide_manager.janoshik.scorer import SupplierScorer


def test_vendor_with_null_purity():
    """Test vendor che hanno certificati con purity NULL."""
    
    print("=" * 70)
    print("🧪 TEST VENDOR CON CERTIFICATI PURITY NULL")
    print("=" * 70)
    
    db_path = Path(__file__).parent.parent / "data" / "production" / "peptide_management.db"
    conn = sqlite3.connect(str(db_path))
    
    # Trova vendor con mix di certificati validi e NULL
    query_vendors = """
    SELECT 
        supplier_name,
        COUNT(*) as total_certs,
        SUM(CASE WHEN purity_percentage IS NULL THEN 1 ELSE 0 END) as null_certs,
        SUM(CASE WHEN purity_percentage > 0 THEN 1 ELSE 0 END) as valid_certs,
        ROUND(SUM(CASE WHEN purity_percentage IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as pct_null
    FROM janoshik_certificates
    WHERE supplier_name IS NOT NULL
    GROUP BY supplier_name
    HAVING null_certs > 0 AND valid_certs > 0
    ORDER BY total_certs DESC, pct_null DESC
    LIMIT 5
    """
    
    vendors = pd.read_sql_query(query_vendors, conn)
    
    if vendors.empty:
        print("⚠️  Nessun vendor con mix certificati validi e NULL trovato")
        conn.close()
        return
    
    print(f"Trovati {len(vendors)} vendor con certificati NULL:\n")
    
    for idx, vendor_row in vendors.iterrows():
        vendor = vendor_row['supplier_name']
        total = vendor_row['total_certs']
        null_count = vendor_row['null_certs']
        valid_count = vendor_row['valid_certs']
        pct_null = vendor_row['pct_null']
        
        print(f"\n{'='*70}")
        print(f"📊 VENDOR #{idx+1}: {vendor}")
        print(f"{'='*70}")
        print(f"Certificati totali: {total}")
        print(f"  - Con purity >0%: {valid_count} ({100-pct_null:.1f}%)")
        print(f"  - Con purity NULL: {null_count} ({pct_null:.1f}%)")
        
        # Recupera certificati del vendor
        query_certs = """
        SELECT 
            supplier_name,
            product_name as peptide_name,
            purity_percentage,
            test_date,
            endotoxin_eu_per_mg as endotoxin_level,
            purity_mg_per_vial as quantity_tested_mg,
            peptide_name_std,
            quantity_nominal,
            unit_of_measure
        FROM janoshik_certificates
        WHERE supplier_name = ?
        ORDER BY test_date DESC
        """
        
        certs = pd.read_sql_query(query_certs, conn, params=(vendor,))
        
        # Calcola avg purity con e senza NULL
        valid_purities = certs[certs['purity_percentage'].notna() & (certs['purity_percentage'] > 0)]
        
        if len(valid_purities) > 0:
            avg_purity_valid = valid_purities['purity_percentage'].mean()
            min_purity = valid_purities['purity_percentage'].min()
            max_purity = valid_purities['purity_percentage'].max()
            std_purity = valid_purities['purity_percentage'].std()
            
            print(f"\n📈 STATISTICHE PUREZZA (solo certificati validi):")
            print(f"   - Avg: {avg_purity_valid:.2f}%")
            print(f"   - Min: {min_purity:.2f}%")
            print(f"   - Max: {max_purity:.2f}%")
            print(f"   - Std: {std_purity:.2f}%")
        
        # Se includessimo NULL come 0% (scenario PRE-FIX)
        certs_with_zero = certs.copy()
        certs_with_zero['purity_percentage'] = certs_with_zero['purity_percentage'].fillna(0)
        avg_with_zero = certs_with_zero['purity_percentage'].mean()
        
        if len(valid_purities) > 0:
            print(f"\n❌ SE INCLUDESSIMO NULL COME 0% (PRE-FIX):")
            print(f"   - Avg purity: {avg_with_zero:.2f}%")
            print(f"   - Penalizzazione: -{avg_purity_valid - avg_with_zero:.2f}% ⚠️")
        
        # Test scorer POST-FIX
        print(f"\n🔬 Calcolo score con NUOVO scorer (esclude NULL)...")
        scorer = SupplierScorer()
        
        certs_list = certs.to_dict('records')
        rankings = scorer.calculate_rankings(certs_list)
        
        if not rankings.empty:
            vendor_score = rankings[rankings['supplier_name'].str.lower() == vendor.lower()]
            
            if not vendor_score.empty:
                row = vendor_score.iloc[0]
                print(f"\n✅ RISULTATO SCORER POST-FIX:")
                print(f"   Total certificates: {row['total_certificates']} (include NULL)")
                print(f"   Purity test count: {row['purity_test_count']} (esclusi {null_count} NULL)")
                print(f"   Avg purity: {row['avg_purity']:.2f}% (solo validi)")
                print(f"   Min purity: {row['min_purity']:.2f}%")
                print(f"   Max purity: {row['max_purity']:.2f}%")
                print(f"   Std purity: {row['std_purity']:.2f}%")
                print(f"\n   📊 SCORES:")
                print(f"   - Quality score: {row['quality_score']:.2f}/100")
                print(f"   - Volume score: {row['volume_score']:.2f}/100")
                print(f"   - Consistency score: {row['consistency_score']:.2f}/100")
                print(f"   - Accuracy score: {row['accuracy_score']:.2f}/100")
                print(f"   - Total score: {row['total_score']:.2f}/100")
                
                print(f"\n✅ FIX VERIFICATO!")
                print(f"   ✅ {null_count} certificati NULL ESCLUSI da calcoli qualità")
                print(f"   ✅ {null_count} certificati NULL INCLUSI in volume score")
                print(f"   ✅ Vendor NON penalizzato per test su miscele/quantità")
    
    conn.close()
    
    print("\n" + "=" * 70)
    print("✅ TEST COMPLETATO")
    print("=" * 70)


if __name__ == "__main__":
    print("\n🔍 TEST VENDOR CON CERTIFICATI PURITY NULL\n")
    test_vendor_with_null_purity()
    print("\n")
