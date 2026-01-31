"""
Script per correggere quantity_tested_mg mancanti usando dati da raw_llm_response.

Questo script NON richiede chiamate LLM - usa solo i dati già estratti e salvati.
"""

import sys
import json
import sqlite3
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def extract_quantity_from_raw(raw_llm_response: str) -> Optional[float]:
    """
    Estrae quantity_tested_mg da raw_llm_response.

    Returns:
        Float quantity in mg, or None if not extractable
    """
    if not raw_llm_response:
        return None

    try:
        llm_data = json.loads(raw_llm_response)
        results = llm_data.get('results', {})

        # Cerca il primo campo con "mg" (escludendo purity e endotoxin)
        for key, value in results.items():
            key_lower = key.lower()

            if key_lower in ['purity', 'endotoxin', 'endotoxins', 'heavy metals']:
                continue

            value_str = str(value)

            # Cerca pattern "X mg" o "X mcg"
            if 'mg' in value_str.lower() and 'eu/mg' not in value_str.lower():
                # Skip se contiene ";" (replicati - gestiti diversamente)
                if ';' in value_str:
                    continue

                # Estrai numero
                try:
                    # Rimuovi unità e converte
                    clean_value = value_str.replace('mg', '').replace('mcg', '').strip()
                    quantity = float(clean_value)

                    # Se era in mcg, converti a mg
                    if 'mcg' in value_str.lower():
                        quantity = quantity / 1000

                    return quantity
                except ValueError:
                    continue

        return None

    except (json.JSONDecodeError, TypeError, AttributeError):
        return None


def fix_missing_quantities(env_name: str = 'production', dry_run: bool = False):
    """
    Corregge quantity_tested_mg mancanti.

    Args:
        env_name: 'production' o 'development'
        dry_run: Se True, solo simula senza modificare database
    """

    print("="*80)
    print("FIX: Quantità Testate Mancanti")
    print("="*80)
    print()

    # Determina path database
    if env_name == 'production':
        db_path = Path(__file__).parent.parent.parent / 'data' / 'production' / 'peptide_management.db'
    else:
        db_path = Path(__file__).parent.parent.parent / 'data' / 'peptide_manager.db'

    print(f"Database: {db_path}")
    print(f"Dry run: {dry_run}")
    print()

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Trova tutti i certificati con quantity_tested_mg NULL
    cursor.execute("""
        SELECT id, task_number, peptide_name_std, purity_percentage,
               quantity_tested_mg, raw_llm_response, is_blend, has_replicates
        FROM janoshik_certificates
        WHERE quantity_tested_mg IS NULL
        AND raw_llm_response IS NOT NULL
        ORDER BY task_number
    """)

    certificates = cursor.fetchall()
    total = len(certificates)

    print(f"Certificati da processare: {total}")
    print()

    if dry_run:
        print("MODE: DRY RUN - Nessuna modifica al database")
        print()

    # Statistiche
    stats = {
        'total': total,
        'fixed': 0,
        'skipped_blend': 0,
        'skipped_replicate': 0,
        'skipped_no_data': 0,
        'errors': 0
    }

    fixed_examples = []

    # Processa ogni certificato
    for i, row in enumerate(certificates, start=1):
        cert_id = row['id']
        task_number = row['task_number']
        peptide = row['peptide_name_std']
        is_blend = row['is_blend']
        has_replicates = row['has_replicates']
        raw_response = row['raw_llm_response']

        if i <= 10 or i % 50 == 0:
            print(f"[{i}/{total}] Task #{task_number} - {peptide or 'N/A'}")

        # Skip blend e replicati (hanno logica diversa)
        if is_blend == 1:
            stats['skipped_blend'] += 1
            continue

        if has_replicates == 1:
            stats['skipped_replicate'] += 1
            continue

        # Estrai quantità da raw
        quantity = extract_quantity_from_raw(raw_response)

        if quantity is None:
            stats['skipped_no_data'] += 1
            continue

        # Update database
        if not dry_run:
            try:
                cursor.execute("""
                    UPDATE janoshik_certificates
                    SET quantity_tested_mg = ?
                    WHERE id = ?
                """, (quantity, cert_id))
                stats['fixed'] += 1

                # Salva esempio
                if len(fixed_examples) < 10:
                    fixed_examples.append({
                        'task_number': task_number,
                        'peptide': peptide,
                        'purity': row['purity_percentage'],
                        'quantity_fixed': quantity
                    })

            except Exception as e:
                print(f"  ERROR: {e}")
                stats['errors'] += 1
        else:
            # Dry run: solo conta
            stats['fixed'] += 1
            if len(fixed_examples) < 10:
                fixed_examples.append({
                    'task_number': task_number,
                    'peptide': peptide,
                    'purity': row['purity_percentage'],
                    'quantity_fixed': quantity
                })

    # Commit changes
    if not dry_run:
        conn.commit()

    conn.close()

    # Report finale
    print()
    print("="*80)
    print("REPORT FINALE")
    print("="*80)
    print(f"Totale certificati processati: {stats['total']}")
    print(f"Quantità corrette: {stats['fixed']}")
    print(f"Skipped (blend): {stats['skipped_blend']}")
    print(f"Skipped (replicati): {stats['skipped_replicate']}")
    print(f"Skipped (no data): {stats['skipped_no_data']}")
    print(f"Errori: {stats['errors']}")
    print()

    if fixed_examples:
        print("Esempi correzioni (primi 10):")
        print(f"{'Task':<10} {'Peptide':<25} {'Purity':<10} {'Qty Fixed':<12}")
        print("-"*80)
        for ex in fixed_examples:
            peptide = (ex['peptide'] or 'N/A')[:24]
            purity = f"{ex['purity']:.2f}%" if ex['purity'] else 'N/A'
            qty = f"{ex['quantity_fixed']:.2f} mg"
            print(f"{ex['task_number']:<10} {peptide:<25} {purity:<10} {qty:<12}")
        print()

    if not dry_run and stats['fixed'] > 0:
        print(f"[SUCCESS] {stats['fixed']} certificati aggiornati nel database")
    elif dry_run:
        print(f"[DRY RUN] {stats['fixed']} certificati sarebbero stati aggiornati")

    print()

    return stats


def main():
    """Entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Fix missing quantity_tested_mg from raw_llm_response data'
    )
    parser.add_argument(
        '--env',
        choices=['production', 'development'],
        default='production',
        help='Database environment (default: production)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulate without modifying database'
    )

    args = parser.parse_args()

    # Run fix
    stats = fix_missing_quantities(
        env_name=args.env,
        dry_run=args.dry_run
    )

    # Exit code
    if stats['errors'] > 0:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
