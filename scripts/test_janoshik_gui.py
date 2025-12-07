"""
Test rapido per verificare integrazione Janoshik nella GUI
"""

import sys
from pathlib import Path

# Aggiungi root al path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_imports():
    """Testa che tutti gli import necessari funzionino."""
    print("🔍 Test import moduli...")
    
    try:
        from peptide_manager.janoshik.views_logic import JanoshikViewsLogic, TimeWindow
        print("  ✅ JanoshikViewsLogic importato")
    except ImportError as e:
        print(f"  ❌ Errore import JanoshikViewsLogic: {e}")
        return False
    
    try:
        from peptide_manager.janoshik.analytics import JanoshikAnalytics
        print("  ✅ JanoshikAnalytics importato")
    except ImportError as e:
        print(f"  ❌ Errore import JanoshikAnalytics: {e}")
        return False
    
    return True

def test_views_logic():
    """Testa che JanoshikViewsLogic funzioni con il database."""
    print("\n🔍 Test JanoshikViewsLogic...")
    
    try:
        from peptide_manager.janoshik.views_logic import JanoshikViewsLogic, TimeWindow
        from scripts.environment import get_environment
        
        # Usa development DB
        env = get_environment('development')
        logic = JanoshikViewsLogic(str(env.db_path))
        
        # Test supplier rankings
        print("  📊 Test supplier rankings...")
        rankings = logic.get_supplier_rankings(TimeWindow.ALL, min_certificates=1)
        print(f"    ✅ {len(rankings)} fornitori trovati")
        if rankings:
            top = rankings[0]
            print(f"    🥇 Top: {top.supplier_name} ({top.avg_purity:.2f}%, {top.total_certificates} certs)")
        
        # Test peptide rankings
        print("  📊 Test peptide rankings...")
        peptides = logic.get_peptide_rankings(TimeWindow.QUARTER, limit=10)
        print(f"    ✅ {len(peptides)} peptidi trovati")
        if peptides:
            hot = peptides[0]
            print(f"    🔥 #1: {hot.peptide_name} ({hot.test_count} test)")
        
        # Test vendor search
        print("  🔍 Test vendor search...")
        result = logic.search_vendors_for_peptide("Semaglutide")
        if result['all_vendors']:
            print(f"    ✅ {len(result['all_vendors'])} vendor per Semaglutide")
            best = result['best_vendor']
            print(f"    ⭐ Best: {best.supplier_name} (score {best.recommendation_score:.0f}/100)")
        else:
            print("    ⚠️  Nessun vendor trovato per Semaglutide")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Errore: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_gui_integration():
    """Verifica che la GUI possa caricare la vista Janoshik."""
    print("\n🔍 Test integrazione GUI...")
    
    try:
        # Import GUI class
        from gui import PeptideGUI
        print("  ✅ PeptideGUI importato")
        
        # Verifica che il metodo build_janoshik_market esista
        if hasattr(PeptideGUI, 'build_janoshik_market'):
            print("  ✅ Metodo build_janoshik_market presente")
        else:
            print("  ❌ Metodo build_janoshik_market NON trovato")
            return False
        
        # Verifica mapping navigation
        # (non possiamo testare facilmente senza avviare Flet)
        print("  ✅ Integrazione GUI OK (smoke test)")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Errore: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Esegue tutti i test."""
    print("="*60)
    print("TEST INTEGRAZIONE JANOSHIK GUI")
    print("="*60)
    
    all_ok = True
    
    # Test 1: Import
    if not test_imports():
        all_ok = False
    
    # Test 2: Views Logic
    if not test_views_logic():
        all_ok = False
    
    # Test 3: GUI Integration
    if not test_gui_integration():
        all_ok = False
    
    print("\n" + "="*60)
    if all_ok:
        print("✅ TUTTI I TEST SUPERATI")
        print("\nPer testare la GUI completa, esegui:")
        print("  python gui.py --env development")
        print("\nPoi naviga alla voce 'Mercato Janoshik' nella sidebar")
    else:
        print("❌ ALCUNI TEST FALLITI")
    print("="*60)
    
    return 0 if all_ok else 1

if __name__ == '__main__':
    sys.exit(main())
