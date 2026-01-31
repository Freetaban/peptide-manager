"""
Demonstration: Component-Level Accuracy Calculation for Blend Protocols

Mostra come il sistema calcola l'accuratezza sia totale che per componente
usando i protocolli standard (GLOW, KLOW, BPC+TB).
"""

from pathlib import Path
import sys
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).parent))

from peptide_manager.janoshik.repositories import JanoshikCertificateRepository
from peptide_manager.janoshik.blend_protocols import calculate_component_nominal_quantities


def calculate_accuracy(cert):
    """
    Calcola accuratezza quantità misurata vs dichiarata.
    Include calcolo per componente se protocollo conosciuto.
    """

    if not cert.quantity_nominal:
        return {
            'accuracy_percent': None,
            'status': 'NO_NOMINAL',
            'message': 'Quantità nominale non disponibile'
        }

    # Per blend: somma totale componenti vs nominale
    if cert.is_blend:
        components = cert.get_blend_components()
        total_measured = sum(c.get('quantity', 0) for c in components)

        accuracy = (total_measured / cert.quantity_nominal) * 100
        deviation = abs(100 - accuracy)

        result = {
            'nominal_qty': cert.quantity_nominal,
            'measured_qty_total': total_measured,
            'n_components': len(components),
            'accuracy_percent': round(accuracy, 2),
            'deviation_percent': round(deviation, 2),
            'status': 'PASS' if deviation <= 10 else 'WARN',
            'message': f"Accuratezza blend: {accuracy:.1f}% (target: 100%)"
        }

        # Se protocollo conosciuto, calcola accuratezza per componente
        if cert.protocol_name:
            component_nominals = calculate_component_nominal_quantities(
                cert.protocol_name,
                cert.quantity_nominal
            )

            if component_nominals:
                component_accuracies = {}
                for comp in components:
                    peptide = comp.get('peptide')
                    measured = comp.get('quantity', 0)
                    nominal = component_nominals.get(peptide)

                    if nominal:
                        comp_accuracy = (measured / nominal) * 100
                        comp_deviation = abs(100 - comp_accuracy)
                        component_accuracies[peptide] = {
                            'nominal': nominal,
                            'measured': measured,
                            'accuracy_percent': round(comp_accuracy, 2),
                            'deviation_percent': round(comp_deviation, 2),
                            'status': 'PASS' if comp_deviation <= 10 else 'WARN'
                        }

                result['component_accuracies'] = component_accuracies
                result['protocol_name'] = cert.protocol_name

        return result

    # Per certificati con replicati: usa la media
    elif cert.has_replicates:
        stats = cert.get_replicate_statistics()
        measured_qty = stats.get('mean')

        if not measured_qty:
            return {
                'accuracy_percent': None,
                'status': 'ERROR',
                'message': 'Impossibile calcolare media replicati'
            }

        accuracy = (measured_qty / cert.quantity_nominal) * 100
        deviation = abs(100 - accuracy)

        return {
            'nominal_qty': cert.quantity_nominal,
            'measured_qty_mean': measured_qty,
            'measured_qty_stddev': stats.get('std_dev'),
            'cv_percent': stats.get('cv_percent'),
            'accuracy_percent': round(accuracy, 2),
            'deviation_percent': round(deviation, 2),
            'n_measurements': stats.get('n'),
            'status': 'PASS' if deviation <= 10 else 'WARN',
            'message': f"Accuratezza: {accuracy:.1f}% (target: 100%)"
        }

    # Certificati singoli standard
    else:
        measured_qty = cert.quantity_tested_mg

        if not measured_qty:
            return {
                'accuracy_percent': None,
                'status': 'ERROR',
                'message': 'Quantità misurata non disponibile'
            }

        accuracy = (measured_qty / cert.quantity_nominal) * 100
        deviation = abs(100 - accuracy)

        return {
            'nominal_qty': cert.quantity_nominal,
            'measured_qty': measured_qty,
            'accuracy_percent': round(accuracy, 2),
            'deviation_percent': round(deviation, 2),
            'status': 'PASS' if deviation <= 10 else 'WARN',
            'message': f"Accuratezza: {accuracy:.1f}% (target: 100%)"
        }


def demo_blend_accuracy():
    """Dimostra calcolo accuratezza per blend certificates"""

    print("="*80)
    print("DEMO: Calcolo Accuratezza per Componente - Blend Protocols")
    print("="*80)
    print()

    # Database production
    db_path = Path(__file__).parent / 'data' / 'production' / 'peptide_management.db'
    repo = JanoshikCertificateRepository(str(db_path))

    # Test con diversi protocolli
    test_tasks = [
        '83568',  # GLOW
        '93546',  # GLOW (se disponibile)
    ]

    # Cerca anche altri protocolli
    print("Ricerca certificati blend nel database...")
    all_blends = repo.get_all_blends()
    print(f"Trovati {len(all_blends)} blend certificates")
    print()

    # Raggruppa per protocollo
    protocols = {}
    for blend in all_blends:
        if blend.protocol_name:
            if blend.protocol_name not in protocols:
                protocols[blend.protocol_name] = []
            protocols[blend.protocol_name].append(blend.task_number)

    print("Protocolli disponibili:")
    for protocol, tasks in sorted(protocols.items()):
        print(f"  {protocol}: {len(tasks)} certificati (es. Task #{tasks[0]})")
    print()

    # Testa un esempio per ogni protocollo principale
    example_protocols = {
        'GLOW': None,
        'KLOW': None,
        'BPC+TB': None
    }

    for protocol in example_protocols.keys():
        for p, tasks in protocols.items():
            if p and p.upper().startswith(protocol):
                example_protocols[protocol] = tasks[0]
                break

    # Mostra dettagli per ogni protocollo
    for protocol, task_number in example_protocols.items():
        if not task_number:
            continue

        print("="*80)
        print(f"PROTOCOLLO: {protocol}")
        print("="*80)
        print()

        cert = repo.get_by_task_number(task_number)
        if not cert:
            print(f"WARNING: Task #{task_number} non trovato\n")
            continue

        print(f"Task Number: {cert.task_number}")
        print(f"Protocol Name: {cert.protocol_name}")
        print(f"Peptides: {cert.peptide_name_std}")
        print(f"Test Date: {cert.test_date}")
        print()

        # Calcola accuratezza
        accuracy = calculate_accuracy(cert)

        # Controlla se ha dati validi
        if accuracy.get('status') == 'NO_NOMINAL':
            print(f"SKIP: {accuracy['message']}\n")
            continue

        print(f"Quantità nominale totale: {accuracy.get('nominal_qty', 'N/A')} mg")
        print(f"Quantità misurata totale: {accuracy.get('measured_qty_total', 'N/A'):.2f} mg")
        print(f"Accuratezza totale: {accuracy.get('accuracy_percent', 'N/A')}% ({accuracy.get('status', 'N/A')})")
        print()

        # Mostra accuratezza componenti
        if 'component_accuracies' in accuracy:
            print("Accuratezza per componente:")
            print(f"{'Peptide':<15} {'Nominale':<12} {'Misurato':<12} {'Accuratezza':<15} {'Status':<8}")
            print("-" * 80)

            for peptide, metrics in accuracy['component_accuracies'].items():
                print(f"{peptide:<15} "
                      f"{metrics['nominal']:<12.2f} "
                      f"{metrics['measured']:<12.2f} "
                      f"{metrics['accuracy_percent']:<15.2f}% "
                      f"{metrics['status']:<8}")

            print()

            # Analisi deviazioni
            warnings = [p for p, m in accuracy['component_accuracies'].items()
                       if m['status'] == 'WARN']
            if warnings:
                print(f"ATTENZIONE: {len(warnings)} componente(i) fuori tolleranza (>10%):")
                for peptide in warnings:
                    metrics = accuracy['component_accuracies'][peptide]
                    print(f"   - {peptide}: {metrics['accuracy_percent']}% "
                          f"(deviazione: {metrics['deviation_percent']:.1f}%)")
            else:
                print("OK: Tutti i componenti entro tolleranza (10%)")

            print()
        else:
            print("(Protocollo sconosciuto - solo accuratezza totale disponibile)")
            print()

    # Summary finale
    print("="*80)
    print("SUMMARY - Statistiche Blend")
    print("="*80)

    total_blends = len(all_blends)
    known_protocols = sum(1 for b in all_blends if b.protocol_name)

    print(f"Totale blend certificates: {total_blends}")
    print(f"Con protocollo identificato: {known_protocols} ({known_protocols/total_blends*100:.1f}%)")
    print()

    print("Protocolli riconosciuti:")
    for protocol, tasks in sorted(protocols.items(), key=lambda x: -len(x[1]))[:10]:
        print(f"  {protocol}: {len(tasks)} certificati")

    print()
    print("Note:")
    print("- PASS: deviazione <=10% dal nominale per ogni componente")
    print("- WARN: deviazione >10% dal nominale")
    print("- Accuratezza componente = (misurato/nominale) x 100%")
    print("- Quantita nominali calcolate da proporzioni standard protocollo")
    print()


if __name__ == "__main__":
    demo_blend_accuracy()
