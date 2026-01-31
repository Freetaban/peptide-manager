"""
Test Task #94386 - DSIP 5mg
Verifica che purezza (99.011%) e quantità (5.30mg) siano correttamente estratte e salvate.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from peptide_manager.janoshik.repositories import JanoshikCertificateRepository


def test_task_94386():
    """Test Task #94386 - DSIP 5mg"""

    print("="*80)
    print("TEST: Task #94386 - DSIP 5mg")
    print("="*80)
    print()

    # Database production
    db_path = Path(__file__).parent / 'data' / 'production' / 'peptide_management.db'
    repo = JanoshikCertificateRepository(str(db_path))

    # Recupera certificato
    cert = repo.get_by_task_number('94386')

    if not cert:
        print("ERROR: Task #94386 non trovato nel database")
        print()
        print("Possibili cause:")
        print("1. Task number non presente nel database production")
        print("2. Task non ancora processato")
        print()
        return

    print(f"Task Number: {cert.task_number}")
    print(f"Peptide: {cert.peptide_name_std}")
    print(f"Test Date: {cert.test_date}")
    print(f"Supplier: {cert.supplier_name}")
    print()

    # Verifica tipo
    print(f"Is Blend: {cert.is_blend}")
    print(f"Has Replicates: {cert.has_replicates}")
    print()

    # VERIFICA 1: Purezza
    print("VERIFICA PUREZZA:")
    print("-" * 80)
    if cert.purity_percentage is not None:
        print(f"Purezza estratta: {cert.purity_percentage}%")
        expected_purity = 99.011

        # Controlla se il valore è corretto (tolleranza 0.001 per floating point)
        if abs(cert.purity_percentage - expected_purity) < 0.001:
            print(f"[PASS] Purezza corretta (atteso: {expected_purity}%)")
        else:
            print(f"[FAIL] Purezza errata (atteso: {expected_purity}%, trovato: {cert.purity_percentage}%)")
    else:
        print("[FAIL] Purezza non estratta (valore NULL nel database)")
    print()

    # VERIFICA 2: Quantità
    print("VERIFICA QUANTITA':")
    print("-" * 80)
    if cert.quantity_tested_mg is not None:
        print(f"Quantità estratta: {cert.quantity_tested_mg} mg")
        expected_quantity = 5.30

        # Controlla se il valore è corretto (tolleranza 0.01 per floating point)
        if abs(cert.quantity_tested_mg - expected_quantity) < 0.01:
            print(f"[PASS] PASS: Quantità corretta (atteso: {expected_quantity} mg)")
        else:
            print(f"[FAIL] FAIL: Quantità errata (atteso: {expected_quantity} mg, trovato: {cert.quantity_tested_mg} mg)")
    else:
        print("[FAIL] FAIL: Quantità non estratta (valore NULL nel database)")
    print()

    # VERIFICA 3: Quantità nominale (se presente)
    print("VERIFICA QUANTITA' NOMINALE:")
    print("-" * 80)
    if cert.quantity_nominal is not None:
        print(f"Quantità nominale: {cert.quantity_nominal} mg")
        expected_nominal = 5.0

        if abs(cert.quantity_nominal - expected_nominal) < 0.01:
            print(f"[PASS] Quantità nominale corretta (atteso: {expected_nominal} mg)")

            # Calcola accuratezza solo se quantity_tested_mg è disponibile
            if cert.quantity_tested_mg is not None:
                accuracy = (cert.quantity_tested_mg / cert.quantity_nominal) * 100
                deviation = abs(100 - accuracy)
                status = 'PASS' if deviation <= 10 else 'WARN'

                print(f"\nAccuratezza: {accuracy:.2f}% ({status})")
                print(f"Deviazione dal nominale: {deviation:.2f}%")
            else:
                print("\nAccuratezza: Non calcolabile (quantità testata mancante)")
        else:
            print(f"NOTA: Quantità nominale presente ma diversa dall'atteso")
            print(f"      (atteso: {expected_nominal} mg, trovato: {cert.quantity_nominal} mg)")
    else:
        print("NOTA: Quantità nominale non disponibile (non sempre presente nei certificati)")
    print()

    # Informazioni aggiuntive
    print("INFORMAZIONI AGGIUNTIVE:")
    print("-" * 80)
    print(f"Unità di misura: {cert.unit_of_measure or 'N/A'}")
    print(f"Batch number: {cert.batch_number or 'N/A'}")
    print(f"Verification key: {cert.verification_key or 'N/A'}")
    print()

    # Summary
    print("="*80)
    print("SUMMARY")
    print("="*80)

    purity_ok = cert.purity_percentage is not None and abs(cert.purity_percentage - 99.011) < 0.001
    quantity_ok = cert.quantity_tested_mg is not None and abs(cert.quantity_tested_mg - 5.30) < 0.01

    if purity_ok and quantity_ok:
        print("[PASS] TUTTI I TEST PASSATI")
        print(f"  - Purezza: {cert.purity_percentage}%")
        print(f"  - Quantità: {cert.quantity_tested_mg} mg")
    else:
        print("[FAIL] ALCUNI TEST FALLITI")
        if not purity_ok:
            print(f"  - Purezza: {'NON ESTRATTA' if cert.purity_percentage is None else f'ERRATA ({cert.purity_percentage}%)'}")
        if not quantity_ok:
            print(f"  - Quantità: {'NON ESTRATTA' if cert.quantity_tested_mg is None else f'ERRATA ({cert.quantity_tested_mg} mg)'}")

    print()


if __name__ == "__main__":
    test_task_94386()
