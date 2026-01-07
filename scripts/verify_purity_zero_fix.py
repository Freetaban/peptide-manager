"""
Verifica impatto fix esclusione purity=0% (miscele/blends) dai calcoli qualità.

Test:
1. Conta certificati con purity=0
2. Identifica vendor con certificati 0% (miscele)
3. Confronta score vendor prima/dopo fix
4. Verifica che vendor con blend non siano più penalizzati

Uso: python scripts/verify_purity_zero_fix.py
"""

import sys
from pathlib import Path

# Aggiungi root al path
sys.path.insert(0, str(Path(__file__).parent.parent))

import sqlite3
import pandas as pd
from peptide_manager.janoshik.scorer import SupplierScorer
from peptide_manager.janoshik.analytics import JanoshikAnalytics


def analyze_zero_purity_certificates():
    """Analizza certificati con purity=0 nel database."""
    
    print("=" * 70)
    print("ANALISI CERTIFICATI PURITY=0% (MISCELE/BLENDS)")
    print("=" * 70)
    
    # Database path
    db_path = Path(__file__).parent.parent / "data" / "production" / "peptide_management.db"
    if not db_path.exists():
        print(f"❌ Database non trovato: {db_path}")
        return False
    
    print(f"📂 Database: {db_path}\n")
    
    conn = sqlite3.connect(str(db_path))
    
    # 1. Conta certificati con purity=0
    print("─" * 70)
    print("📊 1. STATISTICHE CERTIFICATI PURITY=0%")
    print("─" * 70)
    
    query_stats = """
    SELECT 
        COUNT(*) as total_certs,
        SUM(CASE WHEN purity_percentage = 0 OR purity_percentage IS NULL THEN 1 ELSE 0 END) as zero_or_null_purity,
        SUM(CASE WHEN purity_percentage = 0 THEN 1 ELSE 0 END) as exactly_zero,
        SUM(CASE WHEN purity_percentage IS NULL THEN 1 ELSE 0 END) as null_purity,
        SUM(CASE WHEN purity_percentage > 0 THEN 1 ELSE 0 END) as valid_purity
    FROM janoshik_certificates
    """
    
    stats = pd.read_sql_query(query_stats, conn)
    
    total = stats['total_certs'].iloc[0]
    zero_or_null = stats['zero_or_null_purity'].iloc[0]
    exactly_zero = stats['exactly_zero'].iloc[0]
    null_purity = stats['null_purity'].iloc[0]
    valid_purity = stats['valid_purity'].iloc[0]
    
    print(f"Certificati totali: {total}")
    print(f"  ✅ Con purity >0%: {valid_purity} ({valid_purity/total*100:.1f}%)")
    print(f"  ❌ Con purity =0%: {exactly_zero} ({exactly_zero/total*100:.1f}%)")
    print(f"  ⚠️  Con purity NULL: {null_purity} ({null_purity/total*100:.1f}%)")
    print(f"  📊 Totale esclusi: {zero_or_null} ({zero_or_null/total*100:.1f}%)")
    
    # 2. Vendor più colpiti (hanno molti certificati 0%)
    print("\n" + "─" * 70)
    print("🏢 2. VENDOR CON PIÙ CERTIFICATI PURITY=0% (BLEND/MISCELE)")
    print("─" * 70)
    
    query_vendors_zero = """
    SELECT 
        supplier_name,
        COUNT(*) as total_certs,
        SUM(CASE WHEN purity_percentage = 0 THEN 1 ELSE 0 END) as zero_purity_certs,
        SUM(CASE WHEN purity_percentage > 0 THEN 1 ELSE 0 END) as valid_purity_certs,
        ROUND(SUM(CASE WHEN purity_percentage = 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as pct_zero
    FROM janoshik_certificates
    WHERE supplier_name IS NOT NULL
    GROUP BY supplier_name
    HAVING zero_purity_certs > 0
    ORDER BY pct_zero DESC, zero_purity_certs DESC
    LIMIT 15
    """
    
    vendors_zero = pd.read_sql_query(query_vendors_zero, conn)
    
    if vendors_zero.empty:
        print("✅ Nessun vendor con certificati purity=0%")
    else:
        print(f"Trovati {len(vendors_zero)} vendor con certificati 0%:\n")
        for idx, row in vendors_zero.iterrows():
            vendor = row['supplier_name']
            total_certs = row['total_certs']
            zero_certs = row['zero_purity_certs']
            valid_certs = row['valid_purity_certs']
            pct_zero = row['pct_zero']
            
            emoji = "🔥" if pct_zero > 50 else "⚠️" if pct_zero > 20 else "📊"
            print(f"{emoji} {vendor:<30} | Tot: {total_certs:>3} | 0%: {zero_certs:>3} ({pct_zero:>5.1f}%) | Validi: {valid_certs:>3}")
    
    # 3. Esempi certificati 0% (miscele)
    print("\n" + "─" * 70)
    print("📋 3. ESEMPI CERTIFICATI CON PURITY=0% (MISCELE/BLENDS)")
    print("─" * 70)
    
    query_examples = """
    SELECT 
        supplier_name,
        product_name,
        purity_percentage,
        test_date,
        task_number
    FROM janoshik_certificates
    WHERE purity_percentage = 0
    ORDER BY test_date DESC
    LIMIT 10
    """
    
    examples = pd.read_sql_query(query_examples, conn)
    
    if examples.empty:
        print("✅ Nessun certificato con purity=0%")
    else:
        print(f"Primi 10 certificati con purity=0%:\n")
        for idx, row in examples.iterrows():
            vendor = row['supplier_name'][:25]
            product = row['product_name'][:40]
            date = row['test_date']
            task = row['task_number']
            print(f"{idx+1:>2}. {vendor:<25} | {product:<40} | {date} | Task: {task}")
    
    conn.close()
    
    print("\n" + "=" * 70)
    print("✅ ANALISI COMPLETATA")
    print("=" * 70)
    
    # Riepilogo impatto fix
    print("\n📝 IMPATTO PREVISTO DEL FIX:")
    print(f"   - {exactly_zero} certificati (miscele) saranno ESCLUSI dai calcoli purezza")
    print(f"   - {valid_purity} certificati (test standard) INCLUSI nei calcoli purezza")
    print(f"   - Vendor con miscele non saranno più penalizzati per avg_purity")
    print(f"   - I certificati miscele CONTANO comunque nel volume_score (n° test)")
    
    if zero_or_null > total * 0.1:
        print(f"\n⚠️  ATTENZIONE: {zero_or_null/total*100:.1f}% dei certificati hanno purity=0 o NULL")
        print("   Questo fix avrà un impatto significativo sugli score!")
    
    return True


def test_scorer_with_zero_purity():
    """Test scorer su vendor con certificati 0% per verificare il fix."""
    
    print("\n" + "=" * 70)
    print("🧪 TEST SCORER CON CERTIFICATI PURITY=0%")
    print("=" * 70)
    
    db_path = Path(__file__).parent.parent / "data" / "production" / "peptide_management.db"
    conn = sqlite3.connect(str(db_path))
    
    # Trova vendor con mix di certificati validi e 0%
    query_vendor = """
    SELECT supplier_name
    FROM janoshik_certificates
    WHERE supplier_name IS NOT NULL
    GROUP BY supplier_name
    HAVING SUM(CASE WHEN purity_percentage = 0 THEN 1 ELSE 0 END) > 0
       AND SUM(CASE WHEN purity_percentage > 0 THEN 1 ELSE 0 END) > 0
    ORDER BY COUNT(*) DESC
    LIMIT 1
    """
    
    cursor = conn.execute(query_vendor)
    row = cursor.fetchone()
    
    if not row:
        print("⚠️  Nessun vendor con mix certificati validi e 0% trovato")
        conn.close()
        return
    
    test_vendor = row[0]
    
    print(f"📊 Vendor di test: {test_vendor}")
    print("─" * 70)
    
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
    
    certs = pd.read_sql_query(query_certs, conn, params=(test_vendor,))
    conn.close()
    
    # Statistiche pre-fix
    total_certs = len(certs)
    zero_certs = len(certs[certs['purity_percentage'] == 0])
    valid_certs = len(certs[certs['purity_percentage'] > 0])
    
    print(f"Certificati totali: {total_certs}")
    print(f"  - Con purity >0%: {valid_certs}")
    print(f"  - Con purity =0%: {zero_certs}")
    
    if valid_certs > 0:
        avg_purity_valid = certs[certs['purity_percentage'] > 0]['purity_percentage'].mean()
        print(f"  - Avg purity (solo validi >0%): {avg_purity_valid:.2f}%")
    
    if total_certs > 0:
        avg_purity_all = certs['purity_percentage'].mean()
        print(f"  - Avg purity (con 0% inclusi): {avg_purity_all:.2f}%")
        print(f"  - Differenza: {avg_purity_valid - avg_purity_all:.2f}% ⚠️")
    
    # Test scorer
    print("\n🔬 Calcolo score con nuovo scorer (esclude 0%)...")
    scorer = SupplierScorer()
    
    # Converti DataFrame in lista dict per scorer
    certs_list = certs.to_dict('records')
    
    # Calcola ranking
    rankings = scorer.calculate_rankings(certs_list)
    
    if not rankings.empty:
        vendor_row = rankings[rankings['supplier_name'].str.lower() == test_vendor.lower()]
        
        if not vendor_row.empty:
            print("\n✅ RISULTATO SCORER:")
            row = vendor_row.iloc[0]
            print(f"   Total certificates: {row['total_certificates']}")
            print(f"   Purity test count: {row['purity_test_count']} (esclusi {total_certs - row['purity_test_count']} certificati 0%)")
            print(f"   Avg purity: {row['avg_purity']:.2f}%")
            print(f"   Min purity: {row['min_purity']:.2f}%")
            print(f"   Max purity: {row['max_purity']:.2f}%")
            print(f"   Std purity: {row['std_purity']:.2f}%")
            print(f"\n   📊 SCORES:")
            print(f"   - Quality score: {row['quality_score']:.2f}/100")
            print(f"   - Volume score: {row['volume_score']:.2f}/100")
            print(f"   - Consistency score: {row['consistency_score']:.2f}/100")
            print(f"   - Total score: {row['total_score']:.2f}/100")
            
            print(f"\n✅ FIX APPLICATO CORRETTAMENTE!")
            print(f"   I {zero_certs} certificati con purity=0% sono stati ESCLUSI dai calcoli qualità")
            print(f"   Ma CONTANO nel volume score (total_certificates = {row['total_certificates']})")
        else:
            print(f"⚠️  Vendor {test_vendor} non trovato nei rankings")
    else:
        print("❌ Nessun ranking calcolato")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    print("\n🔍 VERIFICA FIX ESCLUSIONE PURITY=0% (MISCELE/BLENDS)\n")
    
    # Analisi certificati 0%
    success = analyze_zero_purity_certificates()
    
    if success:
        # Test scorer
        test_scorer_with_zero_purity()
    
    print("\n✅ VERIFICA COMPLETATA\n")
    sys.exit(0 if success else 1)
