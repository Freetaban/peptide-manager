"""
Test integrazione analytics GUI - Verifica query con campi standardizzati.
Uso: python scripts/test_analytics_integration.py
"""

import sys
from pathlib import Path

# Aggiungi root al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from peptide_manager.janoshik.analytics import JanoshikAnalytics
from peptide_manager.janoshik.views_logic import TimeWindow
from peptide_manager.janoshik.scorer import SupplierScorer
from peptide_manager.janoshik.repositories import JanoshikCertificateRepository
from peptide_manager.database import DatabaseManager
import sqlite3

def test_analytics_queries():
    """Test tutte le query analytics con campi standardizzati."""
    print("=" * 60)
    print("TEST ANALYTICS INTEGRATION")
    print("=" * 60)
    
    # Inizializza DB e logic
    db_path = Path(__file__).parent.parent / "data" / "production" / "peptide_management.db"
    if not db_path.exists():
        print(f"❌ Database non trovato: {db_path}")
        return False
    
    print(f"📂 Database: {db_path}")
    
    # Inizializza componenti analytics
    analytics = JanoshikAnalytics(str(db_path))
    
    all_passed = True
    
    # Test 1: get_top_vendors (che usa get_supplier_rankings internamente)
    print("\n" + "─" * 60)
    print("🧪 Test 1: get_top_vendors")
    try:
        vendors = analytics.get_top_vendors(time_window=TimeWindow.ALL, min_certificates=3, limit=10)
        print(f"✅ Query completata: {len(vendors)} fornitori trovati")
        if vendors:
            top = vendors[0]
            print(f"   Top fornitore: {top['supplier_name']}")
            print(f"   Certificati: {top['total_certificates']}, Purezza media: {top['avg_purity']:.2f}%")
            
            # Verifica presenza campi standardizzati
            if 'peptide_name_std' in str(top):
                print("   ✅ Query usa campi standardizzati")
    except Exception as e:
        print(f"❌ ERRORE: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False
    
    # Test 2: get_hottest_peptides (query refactored con peptide_name_std)
    print("\n" + "─" * 60)
    print("🧪 Test 2: get_hottest_peptides")
    try:
        peptides = analytics.get_hottest_peptides(time_window=TimeWindow.QUARTER, limit=10)
        print(f"✅ Query completata: {len(peptides)} peptidi trovati")
        if peptides:
            top = peptides[0]
            print(f"   Peptide più testato: {top['peptide_name']}")
            print(f"   Test: {top['test_count']}, Fornitori: {top['unique_suppliers']}")
            print(f"   Purezza media: {top['avg_purity']:.2f}%")
            if 'units_tested' in top:
                print(f"   Unità testate: {top['units_tested']}")
    except Exception as e:
        print(f"❌ ERRORE: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False
    
    # Test 3: get_best_vendor_for_peptide (usa peptide_name_std exact match)
    print("\n" + "─" * 60)
    print("🧪 Test 3: get_best_vendor_for_peptide (Tirzepatide)")
    try:
        result = analytics.get_best_vendor_for_peptide("Tirzepatide")
        if result:
            print(f"✅ Query completata: Miglior fornitore trovato")
            print(f"   Fornitore: {result['supplier_name']}")
            print(f"   Purezza media: {result['avg_purity']:.2f}%")
            print(f"   Certificati: {result['total_certificates']}")
            if 'avg_quantity_declared' in result:
                print(f"   Quantità media dichiarata: {result['avg_quantity_declared']:.1f}")
            if 'units_available' in result:
                print(f"   Unità disponibili: {result['units_available']}")
        else:
            print("⚠️  Nessun fornitore trovato per Tirzepatide")
    except Exception as e:
        print(f"❌ ERRORE: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False
    
    # Test 4: Verifica uso campi standardizzati
    print("\n" + "─" * 60)
    print("🧪 Test 4: Verifica campi standardizzati nel DB")
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Conta certificati con campi standardizzati popolati
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN peptide_name_std IS NOT NULL THEN 1 ELSE 0 END) as with_std_name,
                SUM(CASE WHEN quantity_nominal IS NOT NULL THEN 1 ELSE 0 END) as with_qty,
                SUM(CASE WHEN unit_of_measure IS NOT NULL THEN 1 ELSE 0 END) as with_unit
            FROM janoshik_certificates
        """)
        
        row = cursor.fetchone()
        total, with_std_name, with_qty, with_unit = row
        
        print(f"✅ Certificati totali: {total}")
        print(f"   Con peptide_name_std: {with_std_name} ({with_std_name/total*100:.1f}%)")
        print(f"   Con quantity_nominal: {with_qty} ({with_qty/total*100:.1f}%)")
        print(f"   Con unit_of_measure: {with_unit} ({with_unit/total*100:.1f}%)")
        
        if with_std_name < total * 0.8:
            print(f"⚠️  ATTENZIONE: Solo {with_std_name/total*100:.1f}% dei certificati hanno peptide_name_std")
            print("   Considera di eseguire backfill script")
        
        conn.close()
    except Exception as e:
        print(f"❌ ERRORE: {e}")
        all_passed = False
    
    # Test 5: Verifica query usa peptide_name_std (non LIKE)
    print("\n" + "─" * 60)
    print("🧪 Test 5: Verifica query exact match su peptide_name_std")
    try:
        # Test con nome standardizzato esatto
        result = analytics.get_best_vendor_for_peptide("Tirzepatide")
        
        # Conta varianti nel DB
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(DISTINCT product_name)
            FROM janoshik_certificates
            WHERE product_name LIKE '%Tirzepatide%' OR product_name LIKE '%Tirze%'
        """)
        variants_count = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(DISTINCT peptide_name_std)
            FROM janoshik_certificates
            WHERE peptide_name_std = 'Tirzepatide'
        """)
        std_count = cursor.fetchone()[0]
        
        conn.close()
        
        print(f"✅ Varianti product_name nel DB: {variants_count}")
        print(f"   Valore standardizzato peptide_name_std: {std_count} (consolidato)")
        if result:
            print(f"   Fornitore trovato per 'Tirzepatide': {result['supplier_name']}")
        
        if std_count == 1 and variants_count > 1:
            print("✅ OTTIMO: Standardizzazione funziona (molte varianti → 1 standard)")
        
    except Exception as e:
        print(f"❌ ERRORE: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False
    
    # Riepilogo
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ TUTTI I TEST PASSATI")
        print("La GUI può usare le funzionalità analytics senza problemi")
    else:
        print("❌ ALCUNI TEST FALLITI")
        print("Verifica gli errori sopra prima di usare analytics in GUI")
    print("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    success = test_analytics_queries()
    sys.exit(0 if success else 1)
