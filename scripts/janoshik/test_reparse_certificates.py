"""
Test riprocessamento certificati esistenti con parsing migliorato.
"""

import sqlite3
import json
from peptide_manager.janoshik.models.janoshik_certificate import JanoshikCertificate

def main():
    # Connetti al DB
    conn = sqlite3.connect('data/development/peptide_management.db')
    cursor = conn.cursor()
    
    # Leggi certificati
    cursor.execute('SELECT id, task_number, raw_data, image_file, image_hash FROM janoshik_certificates')
    certs = cursor.fetchall()
    
    print(f"🔍 Riprocessamento {len(certs)} certificati con parsing migliorato\n")
    
    for cert_id, task_number, raw_data_json, image_file, image_hash in certs:
        print(f"📄 Certificato #{task_number}")
        
        # Parse raw_data
        extracted = json.loads(raw_data_json)
        
        # Ricostruisci modello
        cert = JanoshikCertificate.from_extracted_data(
            extracted=extracted,
            image_file=image_file,
            image_hash=image_hash
        )
        
        print(f"   Supplier: {cert.supplier_name}")
        print(f"   Peptide: {cert.peptide_name}")
        print(f"   Purity: {cert.purity_percentage}%" if cert.purity_percentage else "   Purity: N/A (multi-peptide?)")
        print(f"   Quantity: {cert.quantity_tested_mg} mg" if cert.quantity_tested_mg else "   Quantity: N/A")
        print(f"   Endotoxin: {cert.endotoxin_level} EU/mg" if cert.endotoxin_level else "   Endotoxin: N/A")
        
        # Mostra results raw per debug
        results = extracted.get('results', {})
        print(f"   Results raw: {json.dumps(results, indent=6)}")
        
        # Aggiorna DB
        cursor.execute('''
            UPDATE janoshik_certificates
            SET purity_percentage = ?,
                quantity_tested_mg = ?,
                endotoxin_level = ?
            WHERE id = ?
        ''', (cert.purity_percentage, cert.quantity_tested_mg, cert.endotoxin_level, cert_id))
        
        print(f"   ✅ Aggiornato in DB\n")
    
    conn.commit()
    conn.close()
    
    print("✅ Riprocessamento completato!")
    print("\n📊 Verifica dati aggiornati:")
    
    # Mostra riepilogo
    conn = sqlite3.connect('data/development/peptide_management.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT task_number, supplier_name, peptide_name, 
               purity_percentage, quantity_tested_mg, endotoxin_level
        FROM janoshik_certificates
        ORDER BY task_number
    ''')
    
    print(f"\n{'Task':<8} {'Supplier':<30} {'Purity':<10} {'Quantity':<12} {'Endotoxin':<12}")
    print("-" * 80)
    
    for row in cursor.fetchall():
        task, supplier, peptide, purity, quantity, endotoxin = row
        purity_str = f"{purity:.2f}%" if purity else "N/A"
        quantity_str = f"{quantity:.2f} mg" if quantity else "N/A"
        endotoxin_str = f"{endotoxin:.0f} EU/mg" if endotoxin else "N/A"
        
        print(f"#{task:<7} {supplier[:28]:<30} {purity_str:<10} {quantity_str:<12} {endotoxin_str:<12}")
    
    conn.close()

if __name__ == '__main__':
    main()
