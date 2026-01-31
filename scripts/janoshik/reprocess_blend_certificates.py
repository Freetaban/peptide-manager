"""
Riprocessa certificati Janoshik per estrarre dati blend/replicati.

Usa lista task numbers da identify_blend_replicate_candidates.py
per riprocessare selettivamente solo i certificati che ne hanno bisogno.
"""

import sys
import json
import time
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from peptide_manager.janoshik.repositories import JanoshikCertificateRepository
from peptide_manager.janoshik.llm_providers import LLMProvider, get_llm_extractor
from peptide_manager.janoshik.models import JanoshikCertificate


def load_task_numbers(task_file: Path) -> List[str]:
    """Carica task numbers da file."""
    if not task_file.exists():
        raise FileNotFoundError(f"File task numbers non trovato: {task_file}")

    with open(task_file, 'r') as f:
        task_numbers = [line.strip() for line in f if line.strip()]

    return task_numbers


def reprocess_certificate(
    cert_id: int,
    task_number: str,
    image_path: Path,
    image_hash: str,
    provider,
    repo: JanoshikCertificateRepository
) -> Dict:
    """
    Riprocessa un singolo certificato.

    Returns:
        Dict con risultato: {'status': 'success'|'error', 'details': ...}
    """
    try:
        # Estrai dati con nuovo prompt
        extracted = provider.extract_certificate_data(str(image_path))

        # Parse in model
        cert_new = JanoshikCertificate.from_extracted_data(
            extracted=extracted,
            image_file=str(image_path),
            image_hash=image_hash
        )

        # Mantieni ID originale per update
        cert_new.id = cert_id

        # Update nel database
        repo.update(cert_new)

        # Return info su cosa è stato trovato
        return {
            'status': 'success',
            'task_number': task_number,
            'is_blend': cert_new.is_blend,
            'has_replicates': cert_new.has_replicates,
            'protocol_name': cert_new.protocol_name,
            'n_components': len(cert_new.get_blend_components()) if cert_new.is_blend else 0,
            'n_replicates': len(cert_new.get_replicate_measurements()) if cert_new.has_replicates else 0
        }

    except Exception as e:
        return {
            'status': 'error',
            'task_number': task_number,
            'error': str(e)
        }


def reprocess_certificates(
    task_file: Path,
    env_name: str,
    provider: LLMProvider,
    images_dir: Optional[Path] = None,
    dry_run: bool = False,
    yes: bool = False
) -> Dict:
    """
    Riprocessa certificati da lista task numbers.

    Args:
        task_file: Path al file con task numbers
        env_name: 'production' o 'development'
        provider: LLM provider da usare
        images_dir: Directory immagini (auto-detect se None)
        dry_run: Se True, solo simula senza modificare DB

    Returns:
        Dict con statistiche finali
    """

    print("="*80)
    print("RIPROCESSAMENTO CERTIFICATI JANOSHIK - BLEND/REPLICATI")
    print("="*80)
    print()

    # Determina paths
    if env_name == 'production':
        db_path = Path(__file__).parent.parent.parent / 'data' / 'production' / 'peptide_management.db'
        if images_dir is None:
            images_dir = Path(__file__).parent.parent.parent / 'data' / 'production' / 'janoshik' / 'images'
    else:
        db_path = Path(__file__).parent.parent.parent / 'data' / 'peptide_manager.db'
        if images_dir is None:
            images_dir = Path(__file__).parent.parent.parent / 'data' / 'janoshik' / 'images'

    print(f"Database: {db_path}")
    print(f"Images dir: {images_dir}")
    print(f"Provider: {provider.value}")
    print(f"Dry run: {dry_run}")
    print()

    # Carica task numbers
    task_numbers = load_task_numbers(task_file)
    print(f"Task numbers da processare: {len(task_numbers)}")
    print()

    if dry_run:
        print("MODE: DRY RUN - Nessuna modifica al database")
        print()

    # Conferma utente
    if not yes:
        response = input("Continuare? (y/n): ")
        if response.lower() != 'y':
            print("Operazione annullata.")
            return {'status': 'cancelled'}
    else:
        print("Auto-confermato (--yes)")
        print()

    # Inizializza provider LLM
    print("\nInizializzazione LLM provider...")
    llm_provider = get_llm_extractor(provider)
    print(f"Provider inizializzato: {provider.value}")
    print()

    # Inizializza repository
    repo = JanoshikCertificateRepository(str(db_path))

    # Statistiche
    stats = {
        'total': len(task_numbers),
        'processed': 0,
        'success': 0,
        'errors': 0,
        'not_found': 0,
        'missing_image': 0,
        'blends_found': 0,
        'replicates_found': 0,
        'start_time': time.time()
    }

    results = []

    # Processa ogni certificato
    print("Inizio riprocessamento...")
    print("-"*80)

    for i, task_number in enumerate(task_numbers, start=1):
        print(f"\n[{i}/{len(task_numbers)}] Task #{task_number}")

        # Recupera certificato esistente
        cert_old = repo.get_by_task_number(task_number)

        if not cert_old:
            print(f"  SKIP: Certificato non trovato nel database")
            stats['not_found'] += 1
            results.append({
                'status': 'not_found',
                'task_number': task_number
            })
            continue

        # Trova immagine
        # Pattern: task_number_hash.png o task_number.png
        image_files = list(images_dir.glob(f"{task_number}_*.png")) or \
                     list(images_dir.glob(f"{task_number}.png"))

        if not image_files:
            print(f"  SKIP: Immagine non trovata in {images_dir}")
            stats['missing_image'] += 1
            results.append({
                'status': 'missing_image',
                'task_number': task_number
            })
            continue

        image_path = image_files[0]
        print(f"  Immagine: {image_path.name}")

        # Dry run: solo mostra cosa farebbe
        if dry_run:
            print(f"  DRY RUN: Sarebbe riprocessato")
            stats['processed'] += 1
            continue

        # Riprocessa
        result = reprocess_certificate(
            cert_id=cert_old.id,
            task_number=task_number,
            image_path=image_path,
            image_hash=cert_old.image_hash,
            provider=llm_provider,
            repo=repo
        )

        results.append(result)
        stats['processed'] += 1

        if result['status'] == 'success':
            stats['success'] += 1

            # Mostra risultato
            if result['is_blend']:
                stats['blends_found'] += 1
                print(f"  BLEND: {result['n_components']} componenti")
                if result['protocol_name']:
                    print(f"    Protocollo: {result['protocol_name']}")

            if result['has_replicates']:
                stats['replicates_found'] += 1
                print(f"  REPLICATI: {result['n_replicates']} misurazioni")

            if not result['is_blend'] and not result['has_replicates']:
                print(f"  SINGOLO: Nessun blend/replicati trovato")

        else:
            stats['errors'] += 1
            print(f"  ERROR: {result['error']}")

        # Rate limiting (evita rate limits API)
        if i < len(task_numbers):
            time.sleep(0.5)

    # Calcola tempo totale
    elapsed = time.time() - stats['start_time']
    stats['elapsed_seconds'] = round(elapsed, 2)
    stats['elapsed_minutes'] = round(elapsed / 60, 2)

    # Report finale
    print("\n" + "="*80)
    print("REPORT FINALE")
    print("="*80)
    print(f"Totale task numbers: {stats['total']}")
    print(f"Processati: {stats['processed']}")
    print(f"Successi: {stats['success']}")
    print(f"Errori: {stats['errors']}")
    print(f"Non trovati in DB: {stats['not_found']}")
    print(f"Immagini mancanti: {stats['missing_image']}")
    print()
    print(f"BLEND trovati: {stats['blends_found']}")
    print(f"REPLICATI trovati: {stats['replicates_found']}")
    print()
    print(f"Tempo totale: {stats['elapsed_minutes']:.2f} minuti")
    print(f"Tempo medio per certificato: {elapsed/stats['processed']:.2f} secondi" if stats['processed'] > 0 else "N/A")
    print()

    # Salva report JSON
    if not dry_run:
        report_file = Path(__file__).parent.parent.parent / 'data' / 'janoshik' / 'reprocess_report.json'
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'environment': env_name,
            'provider': provider.value,
            'statistics': stats,
            'results': results
        }

        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2)

        print(f"Report salvato in: {report_file}")

    return stats


def main():
    """Entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Riprocessa certificati Janoshik per blend/replicati'
    )
    parser.add_argument(
        '--task-file',
        type=Path,
        default=Path(__file__).parent.parent.parent / 'data' / 'janoshik' / 'task_numbers_to_reprocess.txt',
        help='File con task numbers da riprocessare'
    )
    parser.add_argument(
        '--env',
        choices=['production', 'development'],
        default='production',
        help='Ambiente database (default: production)'
    )
    parser.add_argument(
        '--provider',
        choices=['gpt4o', 'claude', 'gemini-flash'],
        default='gemini-flash',
        help='LLM provider da usare (default: gemini-flash per costi)'
    )
    parser.add_argument(
        '--images-dir',
        type=Path,
        help='Directory immagini (auto-detect se non specificato)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simula senza modificare database'
    )
    parser.add_argument(
        '--yes',
        action='store_true',
        help='Conferma automatica senza prompt'
    )

    args = parser.parse_args()

    # Map provider names
    provider_map = {
        'gpt4o': LLMProvider.GPT4O,
        'claude': LLMProvider.CLAUDE_SONNET,
        'gemini-flash': LLMProvider.GEMINI_FLASH
    }

    provider = provider_map[args.provider]

    # Run reprocessing
    stats = reprocess_certificates(
        task_file=args.task_file,
        env_name=args.env,
        provider=provider,
        images_dir=args.images_dir,
        dry_run=args.dry_run,
        yes=args.yes
    )

    # Exit code
    if stats.get('status') == 'cancelled':
        sys.exit(1)

    if stats.get('errors', 0) > 0:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
