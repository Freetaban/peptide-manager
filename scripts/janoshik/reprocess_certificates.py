"""Re-process existing certificates with updated parsing logic"""
import sqlite3
import json
from pathlib import Path
from peptide_manager.janoshik.models.janoshik_certificate import JanoshikCertificate

conn = sqlite3.connect('data/development/peptide_management.db')

# Get all certificates
query = "SELECT id, raw_data, image_file, image_hash FROM janoshik_certificates ORDER BY task_number"
certificates = conn.execute(query).fetchall()

print(f"Found {len(certificates)} certificates to re-process\n")

for cert_id, raw_data, image_file, image_hash in certificates:
    try:
        # Parse raw_data JSON
        extracted = json.loads(raw_data)
        
        # Re-create certificate with updated parsing logic
        cert = JanoshikCertificate.from_extracted_data(
            extracted=extracted,
            image_file=image_file or '',
            image_hash=image_hash or ''
        )
        
        # Update only purity and quantity fields
        conn.execute('''
            UPDATE janoshik_certificates 
            SET purity_percentage = ?, quantity_tested_mg = ?
            WHERE id = ?
        ''', (cert.purity_percentage, cert.quantity_tested_mg, cert_id))
        
        print(f"✓ Updated certificate #{extracted.get('task_number', '?')}")
        print(f"  Purity: {cert.purity_percentage}% | Quantity: {cert.quantity_tested_mg} mg")
        
    except Exception as e:
        print(f"✗ Error processing certificate ID {cert_id}: {e}")

conn.commit()
conn.close()

print(f"\n{'='*80}")
print("Re-processing complete! Run show_certificates.py to verify.")
