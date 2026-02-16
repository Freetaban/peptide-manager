#!/usr/bin/env python3
"""
Validate Janoshik certificates verification_key.

Checks that all verification_keys:
1. Are present (not NULL or empty)
2. Have exactly 12 uppercase alphanumeric characters
"""

import sqlite3
import re
import sys
from pathlib import Path


def validate_certificates(db_path: str) -> dict:
    """Validate all verification_keys in the database."""
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    pattern = re.compile(r'^[A-Z0-9]{12}$')
    
    # Get all certificates
    cur.execute('''
        SELECT id, task_number, verification_key, supplier_name
        FROM janoshik_certificates
    ''')
    
    issues = {
        'missing': [],
        'invalid_format': [],
        'valid': 0
    }
    
    for row in cur.fetchall():
        cert_id, task_num, vk, supplier = row
        
        if not vk or vk.strip() == '':
            issues['missing'].append({
                'id': cert_id,
                'task': task_num,
                'supplier': supplier
            })
        elif not pattern.match(vk):
            issues['invalid_format'].append({
                'id': cert_id,
                'task': task_num,
                'key': vk,
                'length': len(vk),
                'supplier': supplier
            })
        else:
            issues['valid'] += 1
    
    conn.close()
    return issues


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Validate Janoshik certificates')
    parser.add_argument('--db', default='data/production/peptide_management.db', help='Database path')
    args = parser.parse_args()
    
    print(f"Validating certificates in {args.db}...")
    print()
    
    issues = validate_certificates(args.db)
    
    print(f"=== VALIDATION RESULTS ===")
    print(f"Valid keys: {issues['valid']}")
    print(f"Missing keys: {len(issues['missing'])}")
    print(f"Invalid format: {len(issues['invalid_format'])}")
    print()
    
    if issues['missing']:
        print("=== MISSING VERIFICATION_KEYS ===")
        for item in issues['missing']:
            print(f"  ID {item['id']}: task {item['task']} ({item['supplier']})")
        print()
    
    if issues['invalid_format']:
        print("=== INVALID VERIFICATION_KEYS ===")
        for item in issues['invalid_format']:
            print(f"  ID {item['id']}: task {item['task']} - '{item['key']}' ({item['length']} chars)")
        print()
    
    if not issues['missing'] and not issues['invalid_format']:
        print("All certificates are valid!")
        return 0
    else:
        print(f"Found {len(issues['missing']) + len(issues['invalid_format'])} issues.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
