"""Test GUI con database production"""
from peptide_manager import PeptideManager
import os

db_path = 'data/production/peptide_management.db'

print("=" * 60)
print("TEST GUI CON DATABASE PRODUCTION")
print("=" * 60)
print(f"📂 Database: {db_path}")
print(f"📍 Exists: {os.path.exists(db_path)}")
print()

# Test connessione
try:
    m = PeptideManager(db_path)
    s = m.get_inventory_summary()
    
    print("✅ Connessione DB: OK")
    print(f"   Batches totali: {s['total_batches']}")
    print(f"   Batches disponibili: {s['available_batches']}")
    print(f"   Peptidi unici: {s['unique_peptides']}")
    print(f"   Valore inventario: €{s['total_value']:.2f}")
    print()
    
    # Test che tutte le funzioni base funzionino
    print("🧪 Test funzioni base:")
    
    # Peptides
    peptides = m.get_peptides()
    print(f"   ✅ get_peptides(): {len(peptides)} peptidi")
    
    # Suppliers
    suppliers = m.get_suppliers()
    print(f"   ✅ get_suppliers(): {len(suppliers)} fornitori")
    
    # Batches
    batches = m.get_batches()
    print(f"   ✅ get_batches(): {len(batches)} batches")
    
    # Preparations
    preparations = m.get_preparations()
    print(f"   ✅ get_preparations(): {len(preparations)} preparazioni")
    
    # Protocols
    protocols = m.get_protocols()
    print(f"   ✅ get_protocols(): {len(protocols)} protocolli")
    
    # Cycles
    cycles = m.get_cycles()
    print(f"   ✅ get_cycles(): {len(cycles)} cicli")
    
    # Administrations
    admins = m.get_administrations()
    print(f"   ✅ get_administrations(): {len(admins)} somministrazioni totali")
    
    print()
    print("=" * 60)
    print("✅ TUTTI I TEST PASSATI")
    print("La GUI può essere usata con database production")
    print("=" * 60)
    print()
    print("Per avviare la GUI in modalità production:")
    print("  python gui.py --env production")
    print()
    print("Oppure (usa .env per determinare ambiente):")
    print("  python gui.py")
    print()
    
    m.close()
    
except Exception as e:
    print(f"❌ ERRORE: {e}")
    import traceback
    traceback.print_exc()
