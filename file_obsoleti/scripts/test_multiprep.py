"""
Test script per multi-prep administration.
Scenario: Somministrazione che richiede volume da 2+ preparazioni.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from peptide_manager import PeptideManager
from datetime import datetime
from decimal import Decimal

def test_multi_prep_distribution():
    """Test distribuzione multi-prep."""
    print("\n=== TEST MULTI-PREP DISTRIBUTION ===\n")
    
    # Inizializza manager
    db_path = Path(__file__).parent.parent / 'data' / 'development' / 'peptide_management.db'
    manager = PeptideManager(str(db_path))
    
    # Scenario: Serve 2.5ml ma abbiamo 3 preparazioni con volumi parziali
    available_preps = [
        {'id': 1, 'volume_remaining_ml': 1.2, 'expiry_date': '2025-02-01'},
        {'id': 2, 'volume_remaining_ml': 0.8, 'expiry_date': '2025-01-15'},  # Scade prima (FIFO)
        {'id': 3, 'volume_remaining_ml': 1.5, 'expiry_date': '2025-02-10'},
    ]
    
    required_ml = 2.5
    
    print(f"Volume richiesto: {required_ml} ml")
    print("\nPreparazioni disponibili:")
    for prep in available_preps:
        print(f"  Prep #{prep['id']}: {prep['volume_remaining_ml']} ml (scade {prep['expiry_date']})")
    
    # Calcola distribuzione
    success, distribution, message = manager.calculate_multi_prep_distribution(
        required_ml=required_ml,
        available_preps=available_preps
    )
    
    print(f"\n✅ SUCCESS: {success}")
    print(f"MESSAGE: {message}")
    
    if success:
        print("\nDistribuzione calcolata (FIFO per scadenza):")
        total_distributed = 0
        for d in distribution:
            print(f"  Prep #{d['prep_id']}: {d['ml']} ml")
            total_distributed += float(d['ml'])
        print(f"\nTotale distribuito: {total_distributed} ml")
    
    print("\n" + "="*50 + "\n")
    
    # Test caso insufficiente
    print("=== TEST VOLUME INSUFFICIENTE ===\n")
    
    insufficient_preps = [
        {'id': 1, 'volume_remaining_ml': 0.5, 'expiry_date': '2025-02-01'},
        {'id': 2, 'volume_remaining_ml': 0.3, 'expiry_date': '2025-01-15'},
    ]
    
    required_ml = 2.0
    
    print(f"Volume richiesto: {required_ml} ml")
    print("\nPreparazioni disponibili:")
    for prep in insufficient_preps:
        print(f"  Prep #{prep['id']}: {prep['volume_remaining_ml']} ml")
    
    success2, distribution2, message2 = manager.calculate_multi_prep_distribution(
        required_ml=required_ml,
        available_preps=insufficient_preps
    )
    
    print(f"\n❌ SUCCESS: {success2}")
    print(f"MESSAGE: {message2}")
    
    print("\n" + "="*50 + "\n")

def test_multi_prep_creation():
    """Test creazione multi-prep administration (dry run)."""
    print("\n=== TEST MULTI-PREP CREATION (DRY RUN) ===\n")
    
    db_path = Path(__file__).parent.parent / 'data' / 'development' / 'peptide_management.db'
    manager = PeptideManager(str(db_path))
    
    # Distribution simulata
    distribution = [
        {'prep_id': 1, 'ml': 0.8},
        {'prep_id': 2, 'ml': 1.2},
    ]
    
    print("Distribution simulata:")
    for d in distribution:
        print(f"  Prep #{d['prep_id']}: {d['ml']} ml")
    
    # Recupera un protocollo reale per test
    protocols = manager.get_protocols()
    if not protocols:
        print("\n⚠️ Nessun protocollo trovato - skipping creation test")
        return
    
    protocol_id = protocols[0]['id']
    
    print(f"\nProtocollo test: #{protocol_id}")
    print("\nNOTE: Questo è un dry-run, non creerà realmente records")
    print("Per test completo, decommentare la chiamata a create_multi_prep_administration")
    
    # UNCOMMENT per test reale:
    # success, message = manager.create_multi_prep_administration(
    #     distribution=distribution,
    #     protocol_id=protocol_id,
    #     administration_datetime=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    #     dose_mcg=1000,
    #     injection_site='Addome',
    #     injection_method='Sottocutanea',
    #     notes='Test multi-prep',
    # )
    # print(f"\nRisultato: {success}")
    # print(f"Message: {message}")
    
    print("\n" + "="*50 + "\n")

if __name__ == '__main__':
    test_multi_prep_distribution()
    test_multi_prep_creation()
