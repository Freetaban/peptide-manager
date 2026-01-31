"""
Identifica certificati Janoshik da riprocessare per blend/replicati.

Usa euristiche sui dati esistenti per minimizzare costi LLM:
- Analizza campo 'results' per multipli peptidi o valori separati da ";"
- Controlla sample/product_name per pattern di blend
- Filtra certificati già processati con nuovi campi
"""

import sys
import json
import re
from pathlib import Path
from typing import List, Dict, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from peptide_manager.janoshik.repositories import JanoshikCertificateRepository


def analyze_results_field(raw_llm_response: str) -> Dict:
    """
    Analizza campo raw_llm_response per identificare blend/replicati.

    Returns:
        Dict con chiavi: is_likely_blend, is_likely_replicate, reason
    """
    if not raw_llm_response:
        return {'is_likely_blend': False, 'is_likely_replicate': False, 'reason': 'No raw_llm_response'}

    # Estrai il campo results dal JSON raw_llm_response
    try:
        llm_data = json.loads(raw_llm_response)
        results = llm_data.get('results', {})
    except (json.JSONDecodeError, TypeError, AttributeError):
        return {'is_likely_blend': False, 'is_likely_replicate': False, 'reason': 'Invalid JSON'}

    # Filtra chiavi non-peptide
    peptide_keys = [k for k in results.keys()
                    if k.lower() not in ['purity', 'endotoxin', 'endotoxins', 'heavy metals']]

    # Euristica 1: Multipli peptidi distinti → probabile BLEND
    if len(peptide_keys) > 1:
        return {
            'is_likely_blend': True,
            'is_likely_replicate': False,
            'reason': f'Multiple peptides in results ({len(peptide_keys)}): {", ".join(peptide_keys[:3])}'
        }

    # Euristica 2: Valori con ";" → probabile REPLICATI
    for key, value in results.items():
        if key.lower() in ['purity', 'endotoxin']:
            continue
        if ';' in str(value):
            # Conta quanti valori separati
            values = [v.strip() for v in str(value).split(';')]
            return {
                'is_likely_blend': False,
                'is_likely_replicate': True,
                'reason': f'{key} has {len(values)} replicate values: {value[:50]}'
            }

    return {
        'is_likely_blend': False,
        'is_likely_replicate': False,
        'reason': 'Single peptide, single measurement'
    }


def analyze_sample_name(sample: str, product_name: str) -> Dict:
    """
    Analizza sample/product_name per pattern di blend.

    Returns:
        Dict con chiavi: is_likely_blend, protocol_pattern
    """
    combined = f"{sample or ''} {product_name or ''}".lower()

    # Pattern comuni per blend
    blend_patterns = [
        r'glow\s*\d+',           # GLOW 70, GLOW50, etc.
        r'bpc.*\+.*tb',          # BPC+TB, BPC-157+TB500
        r'tb.*\+.*bpc',          # TB+BPC
        r'\w+\s*\+\s*\w+',       # Generic "peptide + peptide"
        r'\([^)]*,\s*[^)]*\)',   # Parentheses with comma (BPC-157, TB500)
        r'blend',                # Explicit "blend"
        r'mix',                  # "peptide mix"
    ]

    for pattern in blend_patterns:
        if re.search(pattern, combined):
            return {
                'is_likely_blend': True,
                'protocol_pattern': pattern,
                'matched_text': re.search(pattern, combined).group(0)
            }

    return {'is_likely_blend': False, 'protocol_pattern': None}


def identify_candidates(env_name: str = 'production') -> Tuple[List[Dict], Dict]:
    """
    Identifica certificati candidati per riprocessing.

    Returns:
        (candidates_list, statistics)
    """

    # Determina path database direttamente per evitare problemi Unicode
    if env_name == 'production':
        db_path = Path(__file__).parent.parent.parent / 'data' / 'production' / 'peptide_management.db'
    else:
        db_path = Path(__file__).parent.parent.parent / 'data' / 'peptide_manager.db'

    repo = JanoshikCertificateRepository(str(db_path))

    print("="*80)
    print("IDENTIFICAZIONE CANDIDATI BLEND/REPLICATI")
    print("="*80)
    print(f"Database: {db_path}")
    print()

    # Recupera tutti i certificati come dict (più veloce)
    all_certs = repo.get_all_as_dicts()
    print(f"Totale certificati nel database: {len(all_certs)}")
    print()

    # Statistiche
    stats = {
        'total': len(all_certs),
        'already_processed': 0,
        'blend_candidates': 0,
        'replicate_candidates': 0,
        'single_peptide': 0,
        'no_results': 0
    }

    candidates = []

    for cert in all_certs:
        task_number = cert.get('task_number')

        # Skip se già processati con nuovi campi
        if cert.get('is_blend') == 1 or cert.get('has_replicates') == 1:
            stats['already_processed'] += 1
            continue

        # Analizza results field
        results_analysis = analyze_results_field(cert.get('raw_llm_response'))

        # Analizza product name (non c'è 'sample' nel DB)
        sample_analysis = analyze_sample_name(
            cert.get('product_name'),  # Usa product_name come sample
            cert.get('peptide_name')
        )

        # Combina analisi
        is_blend_candidate = (
            results_analysis['is_likely_blend'] or
            sample_analysis['is_likely_blend']
        )

        is_replicate_candidate = results_analysis['is_likely_replicate']

        if is_blend_candidate:
            stats['blend_candidates'] += 1
            candidates.append({
                'task_number': task_number,
                'type': 'blend',
                'supplier': cert.get('supplier_name'),
                'sample': cert.get('product_name'),  # Usa product_name come sample
                'test_date': cert.get('test_date'),
                'reason': results_analysis.get('reason') or sample_analysis.get('matched_text', 'Pattern match'),
                'confidence': 'high' if results_analysis['is_likely_blend'] else 'medium'
            })

        elif is_replicate_candidate:
            stats['replicate_candidates'] += 1
            candidates.append({
                'task_number': task_number,
                'type': 'replicate',
                'supplier': cert.get('supplier_name'),
                'sample': cert.get('product_name'),  # Usa product_name come sample
                'test_date': cert.get('test_date'),
                'reason': results_analysis['reason'],
                'confidence': 'high'
            })

        else:
            if not cert.get('raw_llm_response'):
                stats['no_results'] += 1
            else:
                stats['single_peptide'] += 1

    return candidates, stats


def estimate_costs(num_certificates: int) -> Dict:
    """
    Stima costi riprocessing per provider LLM.

    Args:
        num_certificates: Numero certificati da riprocessare

    Returns:
        Dict con stime costi per provider
    """

    # Costi per immagine (approssimativi)
    costs_per_image = {
        'GPT-4o Vision': 0.0075,      # ~$0.0075 per image (input tokens + vision)
        'Claude 3.5 Sonnet': 0.009,   # ~$0.009 per image
        'Gemini 2.0 Flash': 0.0005,   # ~$0.0005 per image (molto economico)
    }

    estimates = {}
    for provider, cost in costs_per_image.items():
        total = cost * num_certificates
        estimates[provider] = {
            'cost_per_image': cost,
            'total_cost': round(total, 2),
            'per_100': round(cost * 100, 2)
        }

    return estimates


def print_report(candidates: List[Dict], stats: Dict):
    """Stampa report dettagliato."""

    print("\n" + "="*80)
    print("STATISTICHE")
    print("="*80)
    print(f"Totale certificati:          {stats['total']}")
    print(f"Già processati (skip):       {stats['already_processed']}")
    print(f"Candidati BLEND:             {stats['blend_candidates']}")
    print(f"Candidati REPLICATI:         {stats['replicate_candidates']}")
    print(f"Single peptide (skip):       {stats['single_peptide']}")
    print(f"Nessun results (skip):       {stats['no_results']}")
    print()

    total_to_process = stats['blend_candidates'] + stats['replicate_candidates']
    print(f"TOTALE DA RIPROCESSARE:      {total_to_process}")

    # Stima costi
    if total_to_process > 0:
        print("\n" + "="*80)
        print("STIMA COSTI RIPROCESSING")
        print("="*80)

        estimates = estimate_costs(total_to_process)
        for provider, data in estimates.items():
            print(f"\n{provider}:")
            print(f"  Costo per immagine: ${data['cost_per_image']:.4f}")
            print(f"  Totale {total_to_process} certificati: ${data['total_cost']:.2f}")
            print(f"  Per 100 certificati: ${data['per_100']:.2f}")

        print("\nRaccomandazione: Usa Gemini 2.0 Flash per minimizzare costi")

    # Lista dettagliata blend candidates
    if stats['blend_candidates'] > 0:
        print("\n" + "="*80)
        print(f"BLEND CANDIDATES ({stats['blend_candidates']})")
        print("="*80)
        print(f"{'Task':<8} {'Supplier':<20} {'Sample':<40} {'Confidence':<10}")
        print("-"*80)

        blend_cands = [c for c in candidates if c['type'] == 'blend']
        for c in blend_cands[:20]:  # Mostra primi 20
            supplier = (c.get('supplier') or 'N/A')[:19]
            sample = (c.get('sample') or 'N/A')[:39]
            print(f"{c['task_number']:<8} {supplier:<20} {sample:<40} {c['confidence']:<10}")

        if len(blend_cands) > 20:
            print(f"... and {len(blend_cands) - 20} more")

        print("\nReason examples:")
        for c in blend_cands[:5]:
            print(f"  {c['task_number']}: {c['reason']}")

    # Lista dettagliata replicate candidates
    if stats['replicate_candidates'] > 0:
        print("\n" + "="*80)
        print(f"REPLICATE CANDIDATES ({stats['replicate_candidates']})")
        print("="*80)
        print(f"{'Task':<8} {'Supplier':<20} {'Sample':<40}")
        print("-"*80)

        rep_cands = [c for c in candidates if c['type'] == 'replicate']
        for c in rep_cands[:20]:  # Mostra primi 20
            supplier = (c.get('supplier') or 'N/A')[:19]
            sample = (c.get('sample') or 'N/A')[:39]
            print(f"{c['task_number']:<8} {supplier:<20} {sample:<40}")

        if len(rep_cands) > 20:
            print(f"... and {len(rep_cands) - 20} more")

        print("\nReason examples:")
        for c in rep_cands[:5]:
            print(f"  {c['task_number']}: {c['reason']}")


def export_task_numbers(candidates: List[Dict], output_file: str = 'task_numbers_to_reprocess.txt'):
    """Esporta lista task numbers in file."""

    task_numbers = [c['task_number'] for c in candidates]

    output_path = Path(output_file)
    with open(output_path, 'w') as f:
        for tn in task_numbers:
            f.write(f"{tn}\n")

    print(f"\n[Export] Task numbers salvati in: {output_path}")
    print(f"         Totale: {len(task_numbers)} task numbers")

    return output_path


def main():
    """Entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Identifica certificati Janoshik da riprocessare per blend/replicati'
    )
    parser.add_argument(
        '--env',
        choices=['production', 'development', 'staging'],
        default='production',
        help='Ambiente database (default: production)'
    )
    parser.add_argument(
        '--export',
        action='store_true',
        help='Esporta task numbers in file'
    )
    parser.add_argument(
        '--export-file',
        default='data/janoshik/task_numbers_to_reprocess.txt',
        help='File output per export (default: data/janoshik/task_numbers_to_reprocess.txt)'
    )

    args = parser.parse_args()

    # Identifica candidati
    candidates, stats = identify_candidates(args.env)

    # Stampa report
    print_report(candidates, stats)

    # Export se richiesto
    if args.export and candidates:
        export_task_numbers(candidates, args.export_file)

        # Export anche JSON dettagliato
        json_file = args.export_file.replace('.txt', '_detailed.json')
        with open(json_file, 'w') as f:
            json.dump({
                'statistics': stats,
                'candidates': candidates,
                'cost_estimates': estimate_costs(len(candidates))
            }, f, indent=2)

        print(f"[Export] Dettagli JSON salvati in: {json_file}")

    print("\n" + "="*80)
    print("NEXT STEPS")
    print("="*80)
    print("1. Review la lista candidati sopra")
    print("2. Se corretto, esporta task numbers con --export")
    print("3. Usa script di riprocessing con task numbers filtrati:")
    print("   python scripts/janoshik/reprocess_blend_certificates.py \\")
    print("          --task-file data/janoshik/task_numbers_to_reprocess.txt \\")
    print("          --provider gemini-flash")
    print()


if __name__ == "__main__":
    main()
