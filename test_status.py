"""Test preparation status feature."""
from peptide_manager import PeptideManager
from peptide_manager.models.preparation import PreparationRepository

# Inizializza
pm = PeptideManager('data/development/peptide_management.db')
repo = PreparationRepository(pm.db.conn)

print("=== Test Preparation Status Feature ===\n")

# Test 1: Verifica migration applicata
preps = pm.get_preparations(only_active=True)
print(f"✅ Preparazioni attive: {len(preps)}")

if preps:
    prep = preps[0]
    print(f"   Prima prep: ID={prep['id']}, Status={prep.get('status', 'active')}, Volume={prep['volume_remaining_ml']}ml")
    
    # Test 2: Verifica nuovi metodi disponibili
    print("\n=== Nuovi metodi repository ===")
    methods = [m for m in dir(repo) if 'depleted' in m or 'wastage' in m or 'available' in m]
    for m in methods:
        print(f"   - {m}")
    
    # Test 3: Test get_available()
    print("\n=== Test get_available() ===")
    available = repo.get_available(threshold_ml=0.1)
    print(f"✅ Preparazioni disponibili (>0.1ml): {len(available)}")
    for p in available[:3]:
        print(f"   ID={p.id}, Volume={p.volume_remaining_ml}ml, Status={p.status} {p.get_status_emoji()}")
    
    # Test 4: Test mark_as_depleted() (su prep di test)
    print("\n=== Test mark_as_depleted() ===")
    test_prep_id = prep['id']
    
    # Prima verifica stato
    test_prep = repo.get_by_id(test_prep_id)
    print(f"Prima: Prep #{test_prep_id} - Status={test_prep.status}, Volume={test_prep.volume_remaining_ml}ml")
    
    # Segna come esaurita
    success, msg = repo.mark_as_depleted(
        test_prep_id, 
        reason='measurement_error',
        notes='Test automatico - verifica funzionalità status tracking'
    )
    print(f"Risultato: {msg}")
    
    # Verifica dopo
    test_prep = repo.get_by_id(test_prep_id, include_deleted=False)
    if test_prep:
        print(f"Dopo: Prep #{test_prep_id} - Status={test_prep.status} {test_prep.get_status_emoji()}, Volume={test_prep.volume_remaining_ml}ml")
        print(f"      Wastage={test_prep.wastage_ml}ml, Reason={test_prep.wastage_reason}")
        print(f"      Depletion Date={test_prep.actual_depletion_date}")
        
        # Ripristina per test futuri (segna come active)
        repo._execute(f"UPDATE preparations SET status='active', wastage_ml=NULL, wastage_reason=NULL, wastage_notes=NULL, actual_depletion_date=NULL WHERE id={test_prep_id}")
        repo._commit()
        print(f"\n✅ Prep #{test_prep_id} ripristinata per test futuri")
else:
    print("⚠️ Nessuna preparazione disponibile per i test")

print("\n=== Test completato ===")
