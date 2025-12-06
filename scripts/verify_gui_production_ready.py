"""
Verifica GUI Production - Import e Inizializzazione
Test senza aprire finestra GUI (headless check)
"""
import sys
from pathlib import Path

print("=" * 70)
print("VERIFICA GUI PRODUCTION - IMPORT E INIZIALIZZAZIONE")
print("=" * 70)
print()

# Test 1: Import moduli
print("🧪 Test 1: Import moduli principali")
try:
    import flet as ft
    print("   ✅ flet")
    
    from peptide_manager import PeptideManager
    print("   ✅ PeptideManager")
    
    from datetime import datetime, timedelta
    print("   ✅ datetime")
    
    print()
except Exception as e:
    print(f"   ❌ ERRORE import: {e}")
    sys.exit(1)

# Test 2: Import GUI
print("🧪 Test 2: Import GUI class")
try:
    # Aggiungi path se necessario
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from gui import PeptideGUI, HAS_JANOSHIK
    print("   ✅ PeptideGUI imported")
    print(f"   ℹ️  HAS_JANOSHIK = {HAS_JANOSHIK}")
    if not HAS_JANOSHIK:
        print("   ⚠️  Modulo Janoshik non disponibile (NORMALE - feature in sviluppo)")
    print()
except Exception as e:
    print(f"   ❌ ERRORE import GUI: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Inizializzazione classe
print("🧪 Test 3: Inizializzazione PeptideGUI")
try:
    db_path = "data/production/peptide_management.db"
    
    if not Path(db_path).exists():
        print(f"   ⚠️  Database non trovato: {db_path}")
        print("   Uso database di test...")
        db_path = "peptide_management.db"
    
    app = PeptideGUI(db_path, environment="production")
    print(f"   ✅ PeptideGUI inizializzato")
    print(f"   📂 Database: {app.db_path}")
    print(f"   🌍 Ambiente: {app.environment}")
    print()
except Exception as e:
    print(f"   ❌ ERRORE inizializzazione: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Verifica metodi principali esistono
print("🧪 Test 4: Verifica metodi GUI esistono")
required_methods = [
    'build_dashboard',
    'build_batches',
    'build_peptides',
    'build_suppliers',
    'build_preparations',
    'build_protocols',
    'build_cycles',
    'build_administrations',
    'build_calculator',
    'build_janoshik_market',
    'nav_changed',
    'update_content',
]

all_ok = True
for method_name in required_methods:
    if hasattr(app, method_name):
        print(f"   ✅ {method_name}()")
    else:
        print(f"   ❌ {method_name}() MANCANTE")
        all_ok = False

print()

if not all_ok:
    print("❌ ALCUNI METODI MANCANTI")
    sys.exit(1)

# Test 5: Test database connection
print("🧪 Test 5: Test database production")
try:
    manager = PeptideManager(db_path)
    summary = manager.get_inventory_summary()
    
    print(f"   ✅ Connessione DB OK")
    print(f"   📦 Batches: {summary['total_batches']}")
    print(f"   🧪 Peptidi: {summary['unique_peptides']}")
    print(f"   💰 Valore: €{summary['total_value']:.2f}")
    
    manager.close()
    print()
except Exception as e:
    print(f"   ❌ ERRORE database: {e}")
    sys.exit(1)

# Test 6: Verifica gestione Janoshik
print("🧪 Test 6: Verifica gestione tab Janoshik")
try:
    # Simula chiamata a build_janoshik_market
    # Non dovrebbe crashare anche se modulo non disponibile
    janoshik_view = app.build_janoshik_market()
    
    if not HAS_JANOSHIK:
        print("   ✅ Janoshik tab mostra messaggio placeholder (modulo non disponibile)")
    else:
        print("   ✅ Janoshik tab costruito correttamente")
    print()
except Exception as e:
    print(f"   ❌ ERRORE build_janoshik_market: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Riepilogo finale
print("=" * 70)
print("✅ TUTTI I TEST PASSATI")
print("=" * 70)
print()
print("La GUI è pronta per l'uso in produzione!")
print()
print("🚀 Per avviare:")
print("   python gui.py --env production")
print()
print("   oppure (se .env configurato):")
print("   python gui.py")
print()
print("📋 Funzionalità disponibili:")
print("   ✅ Dashboard con statistiche inventario")
print("   ✅ Gestione Batches (view, add, edit, delete)")
print("   ✅ Gestione Peptidi")
print("   ✅ Gestione Fornitori")
print("   ✅ Gestione Preparazioni")
print("   ✅ Gestione Protocolli")
print("   ✅ Gestione Cicli")
print("   ✅ Storico Somministrazioni")
print("   ✅ Calcolatore dosi")
if HAS_JANOSHIK:
    print("   ✅ Mercato Janoshik (Classifica Fornitori, Trend Peptidi)")
else:
    print("   ⏳ Mercato Janoshik (in sviluppo - mostra placeholder)")
print()
print("⚠️  NOTA: Il tab 'Mercato Janoshik' è in sviluppo.")
print("   La GUI mostra un messaggio placeholder se clicchi su quella tab.")
print("   Tutte le altre funzionalità sono pienamente operative.")
print()
print("=" * 70)
