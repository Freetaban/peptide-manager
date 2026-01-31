"""
Controlla i dati raw LLM per Task #94386
"""

from pathlib import Path
import sys
import json

sys.path.insert(0, str(Path(__file__).parent))

from peptide_manager.janoshik.repositories import JanoshikCertificateRepository
import sqlite3


def check_raw_data():
    """Controlla raw_llm_response per Task #94386"""

    print("="*80)
    print("ANALISI RAW LLM DATA - Task #94386")
    print("="*80)
    print()

    # Database production
    db_path = Path(__file__).parent / 'data' / 'production' / 'peptide_management.db'

    # Query diretta per ottenere raw_llm_response
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT task_number, peptide_name_std, purity_percentage,
               quantity_tested_mg, quantity_nominal, raw_llm_response,
               image_hash
        FROM janoshik_certificates
        WHERE task_number = ?
    """, ('94386',))

    row = cursor.fetchone()

    if not row:
        print("ERROR: Task #94386 non trovato")
        conn.close()
        return

    print(f"Task Number: {row['task_number']}")
    print(f"Peptide: {row['peptide_name_std']}")
    print(f"Purezza DB: {row['purity_percentage']}")
    print(f"Quantità testata DB: {row['quantity_tested_mg']}")
    print(f"Quantità nominale DB: {row['quantity_nominal']}")
    print(f"Image hash: {row['image_hash'] or 'N/A'}")
    print()

    raw_llm_response = row['raw_llm_response']
    conn.close()

    # Mostra raw_llm_response
    if raw_llm_response:
        print("RAW LLM RESPONSE:")
        print("-" * 80)
        try:
            llm_data = json.loads(raw_llm_response)
            print(json.dumps(llm_data, indent=2))
        except json.JSONDecodeError:
            print("ERROR: Invalid JSON in raw_llm_response")
            print("Raw content:")
            print(raw_llm_response[:500])  # First 500 chars
    else:
        print("NESSUN RAW LLM RESPONSE DISPONIBILE")

    print()
    print("="*80)
    print("CAMPO 'results' NEL JSON:")
    print("="*80)

    if raw_llm_response:
        try:
            llm_data = json.loads(raw_llm_response)
            results = llm_data.get('results', {})

            if results:
                print(json.dumps(results, indent=2))
                print()

                # Analizza il contenuto
                print("ANALISI CONTENUTO:")
                print("-" * 80)
                for key, value in results.items():
                    print(f"{key}: {value}")
                    key_lower = key.lower()

                    # Verifica se è quantità
                    if 'dsip' in key_lower or 'quantity' in key_lower:
                        print(f"  -> Potenziale campo quantità peptide")

                    if 'purity' in key_lower:
                        print(f"  -> Campo purezza")

                print()

                # Verifica se c'è un valore con "mg" che potrebbe essere la quantità
                print("VALORI CON 'mg':")
                print("-" * 80)
                for key, value in results.items():
                    if 'mg' in str(value).lower():
                        print(f"{key}: {value}")
            else:
                print("CAMPO 'results' VUOTO")
        except Exception as e:
            print(f"ERROR durante parsing: {e}")

    print()


if __name__ == "__main__":
    check_raw_data()
