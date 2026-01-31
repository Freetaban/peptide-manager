"""
Esempio: Calcolo accuratezza per algoritmo di ranking
Dimostra come usare quantity_nominal e replicate measurements
per calcolare la precisione della quantità misurata vs dichiarata.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from peptide_manager.janoshik.models import JanoshikCertificate
from peptide_manager.janoshik.repositories import JanoshikCertificateRepository
from peptide_manager.janoshik.blend_protocols import calculate_component_nominal_quantities
from scripts.environment import get_environment


def calculate_accuracy(cert: JanoshikCertificate) -> dict:
    """
    Calcola accuratezza quantità misurata vs dichiarata.

    Args:
        cert: JanoshikCertificate instance

    Returns:
        Dict con metriche di accuratezza
    """

    if not cert.quantity_nominal:
        return {
            'accuracy_percent': None,
            'deviation_percent': None,
            'status': 'NO_NOMINAL',
            'message': 'Quantità nominale non disponibile'
        }

    # Per blend: somma totale componenti vs nominale (ha priorità su replicati)
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
                'deviation_percent': None,
                'status': 'ERROR',
                'message': 'Impossibile calcolare media replicati'
            }

        # Calcola accuratezza
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
            'status': 'PASS' if deviation <= 10 else 'WARN',  # ±10% threshold
            'message': f"Accuratezza: {accuracy:.1f}% (target: 100%)"
        }

    # Certificati singoli standard
    else:
        measured_qty = cert.quantity_tested_mg

        if not measured_qty:
            return {
                'accuracy_percent': None,
                'deviation_percent': None,
                'status': 'ERROR',
                'message': 'Quantità misurata non disponibile'
            }

        # Convert unità se necessario
        nominal = cert.quantity_nominal
        if cert.unit_of_measure == 'mcg':
            measured_qty = measured_qty * 1000  # mg -> mcg per confronto

        accuracy = (measured_qty / nominal) * 100
        deviation = abs(100 - accuracy)

        return {
            'nominal_qty': nominal,
            'measured_qty': measured_qty,
            'accuracy_percent': round(accuracy, 2),
            'deviation_percent': round(deviation, 2),
            'status': 'PASS' if deviation <= 10 else 'WARN',
            'message': f"Accuratezza: {accuracy:.1f}% (target: 100%)"
        }


def demo_accuracy_from_test_data():
    """
    Dimostra calcolo accuratezza sui 3 certificati di test.
    """

    print("="*80)
    print("DEMO: Calcolo Accuratezza per Ranking")
    print("="*80)

    # Usa certificati di test estratti precedentemente
    test_certs = []

    # Task #93546: GLOW 70 blend
    # nominal=70mg, measured=80.64mg (57.21+11.36+12.07)
    from peptide_manager.janoshik.llm_providers import LLMProvider, get_llm_extractor

    provider = get_llm_extractor(LLMProvider.GPT4O)
    images_dir = Path("data/janoshik/images")

    # Certificate 1: GLOW 70 blend
    print("\n[1] Task #93546 - GLOW 70 Blend")
    print("-" * 80)

    extracted1 = provider.extract_certificate_data(str(images_dir / "93546_2690ea75.png"))
    cert1 = JanoshikCertificate.from_extracted_data(
        extracted=extracted1,
        image_file=str(images_dir / "93546_2690ea75.png"),
        image_hash="2690ea75"
    )

    accuracy1 = calculate_accuracy(cert1)
    print(f"Peptide: {cert1.peptide_name_std}")
    print(f"Protocol: {cert1.protocol_name}")
    print(f"Quantità nominale: {accuracy1['nominal_qty']} mg")
    print(f"Quantità misurata (totale): {accuracy1['measured_qty_total']} mg")
    print(f"Componenti: {accuracy1['n_components']}")
    print(f"Accuratezza totale: {accuracy1['accuracy_percent']}%")
    print(f"Deviazione: {accuracy1['deviation_percent']}%")
    print(f"Status: {accuracy1['status']}")

    # Mostra accuratezza componenti se disponibile
    if 'component_accuracies' in accuracy1:
        print("\nAccuratezza per componente:")
        for peptide, metrics in accuracy1['component_accuracies'].items():
            print(f"  {peptide}:")
            print(f"    Nominale: {metrics['nominal']:.2f} mg")
            print(f"    Misurato: {metrics['measured']:.2f} mg")
            print(f"    Accuratezza: {metrics['accuracy_percent']}%")
            print(f"    Status: {metrics['status']}")

    # Certificate 2: BPC+TB blend
    print("\n[2] Task #83375 - BPC+TB Blend")
    print("-" * 80)

    extracted2 = provider.extract_certificate_data(str(images_dir / "83375_d2fd6234.png"))
    cert2 = JanoshikCertificate.from_extracted_data(
        extracted=extracted2,
        image_file=str(images_dir / "83375_d2fd6234.png"),
        image_hash="d2fd6234"
    )

    accuracy2 = calculate_accuracy(cert2)
    print(f"Peptide: {cert2.peptide_name_std}")
    print(f"Protocol: {cert2.protocol_name}")
    print(f"Quantità nominale: {accuracy2['nominal_qty']} mg")
    if 'measured_qty_total' in accuracy2:
        print(f"Quantità misurata (totale): {accuracy2['measured_qty_total']} mg")
        print(f"Componenti: {accuracy2['n_components']}")
    elif 'measured_qty_mean' in accuracy2:
        print(f"Quantità misurata (media): {accuracy2['measured_qty_mean']} mg")
    print(f"Accuratezza totale: {accuracy2['accuracy_percent']}%")
    print(f"Deviazione: {accuracy2['deviation_percent']}%")
    print(f"Status: {accuracy2['status']}")

    # Mostra accuratezza componenti se disponibile
    if 'component_accuracies' in accuracy2:
        print("\nAccuratezza per componente:")
        for peptide, metrics in accuracy2['component_accuracies'].items():
            print(f"  {peptide}:")
            print(f"    Nominale: {metrics['nominal']:.2f} mg")
            print(f"    Misurato: {metrics['measured']:.2f} mg")
            print(f"    Accuratezza: {metrics['accuracy_percent']}%")
            print(f"    Status: {metrics['status']}")

    # Certificate 3: SLU-PP-332 replicates
    print("\n[3] Task #70497 - SLU-PP-332 Replicates")
    print("-" * 80)

    extracted3 = provider.extract_certificate_data(str(images_dir / "70497_fb92b61b.png"))
    cert3 = JanoshikCertificate.from_extracted_data(
        extracted=extracted3,
        image_file=str(images_dir / "70497_fb92b61b.png"),
        image_hash="fb92b61b"
    )

    accuracy3 = calculate_accuracy(cert3)
    print(f"Peptide: {cert3.peptide_name_std}")
    print(f"Quantità nominale: {accuracy3['nominal_qty']} mcg")
    print(f"Quantità misurata (media): {accuracy3['measured_qty_mean']} mcg")
    print(f"Deviazione standard: {accuracy3['measured_qty_stddev']} mcg")
    print(f"CV%: {accuracy3['cv_percent']}%")
    print(f"N misurazioni: {accuracy3['n_measurements']}")
    print(f"Accuratezza: {accuracy3['accuracy_percent']}%")
    print(f"Deviazione: {accuracy3['deviation_percent']}%")
    print(f"Status: {accuracy3['status']}")

    # Summary table
    print("\n" + "="*80)
    print("SUMMARY - Ranking Metrics")
    print("="*80)
    print(f"{'Task':<10} {'Type':<12} {'Nominal':<10} {'Measured':<12} {'Accuracy':<10} {'Status':<8}")
    print("-"*80)

    measured_1 = f"{accuracy1.get('measured_qty_total', 'N/A'):.2f} mg" if 'measured_qty_total' in accuracy1 else f"{accuracy1.get('measured_qty_mean', 'N/A'):.2f} mg"
    measured_2 = f"{accuracy2.get('measured_qty_total', 'N/A'):.2f} mg" if 'measured_qty_total' in accuracy2 else f"{accuracy2.get('measured_qty_mean', 'N/A'):.2f} mg"
    measured_3 = f"{accuracy3.get('measured_qty_mean', 'N/A'):.2f} mcg" if 'measured_qty_mean' in accuracy3 else f"{accuracy3.get('measured_qty_total', 'N/A'):.2f} mcg"

    print(f"#93546     Blend        70.0 mg    {measured_1:<12} {accuracy1['accuracy_percent']}%     {accuracy1['status']}")
    print(f"#83375     Blend        20.0 mg    {measured_2:<12} {accuracy2['accuracy_percent']}%     {accuracy2['status']}")
    print(f"#70497     Replicate    250 mcg    {measured_3:<12} {accuracy3['accuracy_percent']}%      {accuracy3['status']}")

    print("\n[Note]")
    print("- PASS: deviazione <=10% dal nominale")
    print("- WARN: deviazione >10% dal nominale")
    print("- Accuratezza = (misurato/nominale) x 100%")
    print("- Per replicati: usa media delle misurazioni")
    print("- Per blend: usa somma totale componenti")


if __name__ == "__main__":
    demo_accuracy_from_test_data()
