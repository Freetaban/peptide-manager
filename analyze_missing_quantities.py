"""
Analizza quanti certificati hanno quantity_tested_mg NULL ma dati disponibili in raw_llm_response.
"""

from pathlib import Path
import sys
import json
import sqlite3

sys.path.insert(0, str(Path(__file__).parent))


def analyze_missing_quantities():
    """Analizza certificati con quantità mancanti"""

    print("="*80)
    print("ANALISI: Certificati con Quantità Testata Mancante")
    print("="*80)
    print()

    # Database production
    db_path = Path(__file__).parent / 'data' / 'production' / 'peptide_management.db'

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Count totali
    cursor.execute("SELECT COUNT(*) as total FROM janoshik_certificates")
    total = cursor.fetchone()['total']

    # Count con quantity_tested_mg NULL
    cursor.execute("""
        SELECT COUNT(*) as missing
        FROM janoshik_certificates
        WHERE quantity_tested_mg IS NULL
    """)
    missing_quantity = cursor.fetchone()['missing']

    # Count certificati singoli (non blend, non replicati)
    cursor.execute("""
        SELECT COUNT(*) as singles
        FROM janoshik_certificates
        WHERE (is_blend IS NULL OR is_blend = 0)
        AND (has_replicates IS NULL OR has_replicates = 0)
    """)
    single_peptides = cursor.fetchone()['singles']

    # Count certificati singoli con quantity_tested_mg NULL
    cursor.execute("""
        SELECT COUNT(*) as singles_missing
        FROM janoshik_certificates
        WHERE (is_blend IS NULL OR is_blend = 0)
        AND (has_replicates IS NULL OR has_replicates = 0)
        AND quantity_tested_mg IS NULL
    """)
    singles_missing = cursor.fetchone()['singles_missing']

    print(f"Totale certificati: {total}")
    print(f"Certificati singoli (non blend/replicati): {single_peptides}")
    print()
    print(f"Certificati con quantity_tested_mg NULL: {missing_quantity} ({missing_quantity/total*100:.1f}%)")
    print(f"Certificati singoli con quantity NULL: {singles_missing} ({singles_missing/single_peptides*100:.1f}%)")
    print()

    # Trova esempi di certificati con dati recuperabili
    cursor.execute("""
        SELECT task_number, peptide_name_std, purity_percentage,
               quantity_tested_mg, quantity_nominal, raw_llm_response
        FROM janoshik_certificates
        WHERE quantity_tested_mg IS NULL
        AND raw_llm_response IS NOT NULL
        AND (is_blend IS NULL OR is_blend = 0)
        AND (has_replicates IS NULL OR has_replicates = 0)
        LIMIT 10
    """)

    recoverable = []
    for row in cursor.fetchall():
        task_number = row['task_number']
        raw_response = row['raw_llm_response']

        if not raw_response:
            continue

        try:
            llm_data = json.loads(raw_response)
            results = llm_data.get('results', {})

            # Cerca valori con "mg"
            for key, value in results.items():
                if key.lower() in ['purity', 'endotoxin']:
                    continue

                value_str = str(value)
                if 'mg' in value_str.lower() and 'eu/mg' not in value_str.lower():
                    # Estrai quantità
                    try:
                        clean_value = value_str.replace('mg', '').replace('mcg', '').strip()
                        if ';' not in clean_value:  # Skip replicati
                            quantity = float(clean_value)
                            recoverable.append({
                                'task_number': task_number,
                                'peptide': row['peptide_name_std'],
                                'purity': row['purity_percentage'],
                                'quantity_in_raw': quantity,
                                'raw_field': f"{key}: {value}"
                            })
                            break
                    except ValueError:
                        pass

        except (json.JSONDecodeError, TypeError):
            continue

    print("="*80)
    print("DATI RECUPERABILI DA raw_llm_response")
    print("="*80)
    print(f"Certificati con quantità recuperabile: {len(recoverable)}")
    print()

    if recoverable:
        print("Esempi (primi 10):")
        print(f"{'Task':<10} {'Peptide':<20} {'Purity':<10} {'Qty in raw':<12} {'Campo raw':<30}")
        print("-"*80)
        for cert in recoverable[:10]:
            peptide = (cert['peptide'] or 'N/A')[:19]
            purity = f"{cert['purity']:.2f}%" if cert['purity'] else 'N/A'
            qty = f"{cert['quantity_in_raw']:.2f} mg"
            raw_field = cert['raw_field'][:29]
            print(f"{cert['task_number']:<10} {peptide:<20} {purity:<10} {qty:<12} {raw_field:<30}")

    # Stima quanti totali sono recuperabili
    cursor.execute("""
        SELECT COUNT(*) as total_recoverable
        FROM janoshik_certificates
        WHERE quantity_tested_mg IS NULL
        AND raw_llm_response IS NOT NULL
        AND raw_llm_response LIKE '%mg%'
        AND (is_blend IS NULL OR is_blend = 0)
        AND (has_replicates IS NULL OR has_replicates = 0)
    """)
    total_recoverable = cursor.fetchone()['total_recoverable']

    print()
    print("="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Certificati singoli con quantity NULL: {singles_missing}")
    print(f"Stimati recuperabili da raw_llm_response: {total_recoverable}")
    print(f"Percentuale recuperabile: {total_recoverable/singles_missing*100:.1f}%" if singles_missing > 0 else "N/A")
    print()

    conn.close()

    return {
        'total': total,
        'single_peptides': single_peptides,
        'singles_missing': singles_missing,
        'recoverable': total_recoverable
    }


if __name__ == "__main__":
    analyze_missing_quantities()
