#!/usr/bin/env python3
"""
Extract quantity_tested from raw_llm_response for IU-based certificates.
Updates quantity_tested_mg field with IU values for proper scoring.
"""
import sqlite3
import json
import re
from pathlib import Path

def extract_quantity_tested_iu():
    """Extract IU quantities from raw_llm_response and update quantity_tested_mg."""
    
    db_path = Path("data/production/peptide_management.db")
    
    if not db_path.exists():
        print(f"❌ Database non trovato: {db_path}")
        return False
    
    print("🔬 ESTRAZIONE QUANTITÀ TESTATE (IU)")
    print("=" * 80)
    print(f"📁 Database: {db_path}")
    print()
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Trova certificati con unit_of_measure = 'IU' e quantity_tested_mg NULL
        cursor.execute("""
            SELECT id, task_number, peptide_name_std, raw_llm_response 
            FROM janoshik_certificates 
            WHERE unit_of_measure = 'IU' 
              AND (quantity_tested_mg IS NULL OR quantity_tested_mg = 0)
              AND raw_llm_response IS NOT NULL
        """)
        
        certificates = cursor.fetchall()
        print(f"📊 Certificati IU da processare: {len(certificates)}")
        print()
        
        if not certificates:
            print("✅ Nessun certificato da aggiornare")
            return True
        
        updated = 0
        failed = 0
        
        for cert_id, task_number, peptide_name, raw_response in certificates:
            try:
                # Parse JSON response
                data = json.loads(raw_response)
                results = data.get('results', {})
                
                # Cerca valore IU nei results
                # Può essere: {"HCG": "10819 IU"} o {"peptide_name": "value IU"}
                quantity_tested = None
                
                for key, value in results.items():
                    if isinstance(value, str):
                        # Cerca pattern "numero IU"
                        match = re.search(r'(\d+(?:\.\d+)?)\s*IU', value, re.IGNORECASE)
                        if match:
                            quantity_tested = float(match.group(1))
                            break
                
                if quantity_tested:
                    # Aggiorna database
                    cursor.execute("""
                        UPDATE janoshik_certificates 
                        SET quantity_tested_mg = ? 
                        WHERE id = ?
                    """, (quantity_tested, cert_id))
                    
                    print(f"  ✅ {task_number} ({peptide_name}): {quantity_tested} IU")
                    updated += 1
                else:
                    print(f"  ⚠️  {task_number} ({peptide_name}): IU non trovate in results")
                    failed += 1
                    
            except json.JSONDecodeError:
                print(f"  ❌ {task_number}: JSON non valido")
                failed += 1
            except Exception as e:
                print(f"  ❌ {task_number}: Errore - {e}")
                failed += 1
        
        conn.commit()
        
        print()
        print("=" * 80)
        print("📈 RISULTATI")
        print("=" * 80)
        print(f"✅ Certificati aggiornati: {updated}")
        print(f"⚠️  Certificati falliti: {failed}")
        print()
        
        if updated > 0:
            print("🎉 ESTRAZIONE COMPLETATA!")
            return True
        else:
            print("⚠️  Nessun certificato aggiornato")
            return False
            
    except Exception as e:
        print(f"❌ ERRORE: {e}")
        conn.rollback()
        return False
    
    finally:
        conn.close()


if __name__ == "__main__":
    import sys
    success = extract_quantity_tested_iu()
    sys.exit(0 if success else 1)
