"""
Test component-level accuracy calculation for Task #83568 (GLOW 70mg).

Verifica che il calcolo dell'accuratezza per componente funzioni correttamente
usando le proporzioni standard del protocollo GLOW (1:1:5).
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from peptide_manager.janoshik.repositories import JanoshikCertificateRepository
from peptide_manager.janoshik.blend_protocols import calculate_component_nominal_quantities


def test_task_83568():
    """Test accuratezza Task #83568"""

    print("="*80)
    print("TEST: Task #83568 - GLOW 70mg Component Accuracy")
    print("="*80)
    print()

    # Database production
    db_path = Path(__file__).parent / 'data' / 'production' / 'peptide_management.db'
    repo = JanoshikCertificateRepository(str(db_path))

    # Recupera certificato
    cert = repo.get_by_task_number('83568')

    if not cert:
        print("ERROR: Task #83568 non trovato nel database")
        return

    print(f"Task Number: {cert.task_number}")
    print(f"Peptide: {cert.peptide_name_std}")
    print(f"Protocol: {cert.protocol_name}")
    print(f"Is Blend: {cert.is_blend}")
    print(f"Quantity Nominal: {cert.quantity_nominal} mg")
    print()

    # Mostra componenti
    if cert.is_blend:
        components = cert.get_blend_components()
        print(f"Componenti ({len(components)}):")
        total_measured = 0
        for comp in components:
            peptide = comp.get('peptide')
            quantity = comp.get('quantity', 0)
            unit = comp.get('unit', 'mg')
            print(f"  - {peptide}: {quantity} {unit}")
            total_measured += quantity

        print(f"\nTotale misurato: {total_measured} mg")
        print(f"Totale nominale: {cert.quantity_nominal} mg")
        print(f"Accuratezza totale: {(total_measured / cert.quantity_nominal) * 100:.2f}%")
        print()

        # Calcola quantità nominali per componente
        if cert.protocol_name:
            print(f"Calcolo accuratezza per componente (protocollo {cert.protocol_name}):")
            print("-" * 80)

            component_nominals = calculate_component_nominal_quantities(
                cert.protocol_name,
                cert.quantity_nominal
            )

            if component_nominals:
                print(f"\nQuantità nominali calcolate (proporzioni 1:1:5):")
                for peptide, nominal in component_nominals.items():
                    print(f"  {peptide}: {nominal:.2f} mg")

                print(f"\nAccuratezza per componente:")
                print(f"{'Peptide':<15} {'Nominale':<12} {'Misurato':<12} {'Accuratezza':<12} {'Status':<8}")
                print("-" * 80)

                for comp in components:
                    peptide = comp.get('peptide')
                    measured = comp.get('quantity', 0)
                    nominal = component_nominals.get(peptide)

                    if nominal:
                        accuracy = (measured / nominal) * 100
                        deviation = abs(100 - accuracy)
                        status = 'PASS' if deviation <= 10 else 'WARN'

                        print(f"{peptide:<15} {nominal:<12.2f} {measured:<12.2f} {accuracy:<12.2f}% {status:<8}")

                print()
                print("Risultato atteso per Task #83568:")
                print("  - GHK-Cu: 51.2mg / 50mg = 102.4% (PASS)")
                print("  - BPC-157: 12.97mg / 10mg = 129.7% (WARN)")
                print("  - TB-500: 11.41mg / 10mg = 114.1% (WARN)")
            else:
                print(f"ERROR: Protocollo {cert.protocol_name} non trovato nel database")
        else:
            print("WARNING: Nessun protocol_name specificato, impossibile calcolare accuratezza per componente")
    else:
        print("ERROR: Certificato non è un blend")

    print()
    print("="*80)


if __name__ == "__main__":
    test_task_83568()
