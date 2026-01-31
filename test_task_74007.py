"""
Test Task #74007 - Certificato con replicati (3 misurazioni)
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from peptide_manager.janoshik.repositories import JanoshikCertificateRepository


def test_task_74007():
    """Test Task #74007 - Replicati"""

    print("="*80)
    print("TEST: Task #74007 - Certificato con Replicati")
    print("="*80)
    print()

    # Database production
    db_path = Path(__file__).parent / 'data' / 'production' / 'peptide_management.db'
    repo = JanoshikCertificateRepository(str(db_path))

    # Recupera certificato
    cert = repo.get_by_task_number('74007')

    if not cert:
        print("ERROR: Task #74007 non trovato nel database")
        return

    print(f"Task Number: {cert.task_number}")
    print(f"Peptide: {cert.peptide_name_std}")
    print(f"Test Date: {cert.test_date}")
    print(f"Supplier: {cert.supplier_name}")
    print()

    print(f"Is Blend: {cert.is_blend}")
    print(f"Has Replicates: {cert.has_replicates}")
    print()

    # Se ha replicati, mostra dettagli
    if cert.has_replicates:
        measurements = cert.get_replicate_measurements()
        print(f"Numero misurazioni: {len(measurements)}")
        print(f"Misurazioni:")
        for i, value in enumerate(measurements, start=1):
            print(f"  Replica #{i}: {value} {cert.unit_of_measure or 'mg'}")
        print()

        # Statistiche
        stats = cert.get_replicate_statistics()
        if stats:
            print("Statistiche:")
            print(f"  Media: {stats.get('mean', 'N/A')}")
            print(f"  Deviazione standard: {stats.get('std_dev', 'N/A')}")
            print(f"  CV%: {stats.get('cv_percent', 'N/A')}%")
            print(f"  Min: {stats.get('min', 'N/A')}")
            print(f"  Max: {stats.get('max', 'N/A')}")
            print()

        # Accuratezza se ha quantità nominale
        if cert.quantity_nominal:
            print(f"Quantità nominale: {cert.quantity_nominal} {cert.unit_of_measure or 'mg'}")
            mean = stats.get('mean')
            if mean:
                accuracy = (mean / cert.quantity_nominal) * 100
                deviation = abs(100 - accuracy)
                status = 'PASS' if deviation <= 10 else 'WARN'
                print(f"Accuratezza: {accuracy:.2f}% ({status})")
                print(f"Deviazione dal nominale: {deviation:.2f}%")
        else:
            print("Quantità nominale: Non disponibile")
            print("(Impossibile calcolare accuratezza)")

    # Mostra anche blend_components se presente
    if cert.is_blend:
        components = cert.get_blend_components()
        print(f"\nComponenti blend ({len(components)}):")
        for comp in components:
            print(f"  - {comp.get('peptide')}: {comp.get('quantity')} {comp.get('unit', 'mg')}")

    print()
    print("="*80)


if __name__ == "__main__":
    test_task_74007()
