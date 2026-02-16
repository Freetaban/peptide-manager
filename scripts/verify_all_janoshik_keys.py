#!/usr/bin/env python3
"""
Verify all Janoshik certificates against the official Janoshik verification API.

This script checks that each (task_number, verification_key) pair is valid
by querying the Janoshik website verification endpoint.

Usage:
    python scripts/verify_all_janoshik_keys.py
    
    # With custom settings:
    python scripts/verify_all_janoshik_keys.py --min-delay 3 --max-delay 8 --db data/production/peptide_management.db
"""

import sqlite3
import time
import random
import sys
import argparse
import requests
from pathlib import Path
from typing import Tuple, List, Dict


VERIFICATION_URL = "https://www.janoshik.com/verification/"


def verify_single(task_number: str, verification_key: str) -> Tuple[bool, str]:
    """
    Verify a single certificate against Janoshik website.
    
    Returns:
        (is_valid, message)
    """
    params = {
        'task': task_number,
        'key': verification_key
    }
    
    try:
        response = requests.get(VERIFICATION_URL, params=params, timeout=30)
        
        if response.status_code != 200:
            return False, f"HTTP {response.status_code}"
        
        # Check for success message
        if "This test is verified" in response.text:
            return True, "Verified"
        elif "No test found" in response.text:
            return False, "Not found"
        else:
            return False, "Unknown response"
            
    except requests.RequestException as e:
        return False, f"Error: {str(e)[:50]}"


def verify_all_certificates(db_path: str, min_delay: float = 2.0, max_delay: float = 5.0, 
                            limit: int = None, start_id: int = None) -> Dict:
    """
    Verify all certificates in the database.
    
    Args:
        db_path: Path to SQLite database
        min_delay: Minimum delay between requests (seconds)
        max_delay: Maximum delay between requests (seconds)
        limit: Maximum number to verify (None = all)
        start_id: Start from this ID (None = from beginning)
    
    Returns:
        Dict with verification results
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Get all certificates with verification_key
    query = '''
        SELECT id, task_number, verification_key 
        FROM janoshik_certificates 
        WHERE verification_key IS NOT NULL 
        AND verification_key != ''
    '''
    
    if start_id:
        query += f' AND id >= {start_id}'
    
    query += ' ORDER BY id'
    
    if limit:
        query += f' LIMIT {limit}'
    
    cur.execute(query)
    certificates = cur.fetchall()
    conn.close()
    
    results = {
        'verified': [],
        'failed': [],
        'errors': [],
        'total': len(certificates),
        'checked': 0
    }
    
    print(f"Found {len(certificates)} certificates to verify")
    print(f"Delay between requests: {min_delay}-{max_delay} seconds")
    print()
    
    for i, (cert_id, task_num, vk) in enumerate(certificates):
        results['checked'] += 1
        
        # Verify
        is_valid, message = verify_single(str(task_num), vk)
        
        if is_valid:
            results['verified'].append({
                'id': cert_id,
                'task': task_num,
                'key': vk
            })
            status = "OK"
        else:
            results['failed'].append({
                'id': cert_id,
                'task': task_num,
                'key': vk,
                'message': message
            })
            status = "FAIL"
        
        # Progress output
        progress = f"[{i+1}/{len(certificates)}]"
        print(f"{progress} ID {cert_id} task={task_num}: {status} - {message}")
        
        # Random delay between requests (except for the last one)
        if i < len(certificates) - 1:
            delay = random.uniform(min_delay, max_delay)
            time.sleep(delay)
    
    return results


def main():
    parser = argparse.ArgumentParser(description='Verify all Janoshik certificates against the website')
    parser.add_argument('--db', default='data/production/peptide_management.db', help='Database path')
    parser.add_argument('--min-delay', type=float, default=2.0, help='Minimum delay between requests (seconds)')
    parser.add_argument('--max-delay', type=float, default=5.0, help='Maximum delay between requests (seconds)')
    parser.add_argument('--limit', type=int, default=None, help='Limit number of certificates to verify')
    parser.add_argument('--start-id', type=int, default=None, help='Start from this certificate ID')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be verified without actually verifying')
    args = parser.parse_args()
    
    if args.dry_run:
        conn = sqlite3.connect(args.db)
        cur = conn.cursor()
        cur.execute('''
            SELECT id, task_number, verification_key 
            FROM janoshik_certificates 
            WHERE verification_key IS NOT NULL AND verification_key != ''
            ORDER BY id
        ''')
        certs = cur.fetchall()
        conn.close()
        print(f"Would verify {len(certs)} certificates")
        for cert in certs[:10]:
            print(f"  ID {cert[0]}: task={cert[1]}, key={cert[2]}")
        if len(certs) > 10:
            print(f"  ... and {len(certs) - 10} more")
        return 0
    
    print("=" * 60)
    print("JANOSHIK CERTIFICATE VERIFICATION")
    print("=" * 60)
    print()
    
    start_time = time.time()
    results = verify_all_certificates(
        args.db, 
        min_delay=args.min_delay,
        max_delay=args.max_delay,
        limit=args.limit,
        start_id=args.start_id
    )
    elapsed = time.time() - start_time
    
    print()
    print("=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Total checked: {results['checked']}")
    print(f"Verified OK:   {len(results['verified'])}")
    print(f"Failed:        {len(results['failed'])}")
    print(f"Elapsed time:  {elapsed:.1f} seconds")
    print()
    
    if results['failed']:
        print("=== FAILED VERIFICATIONS ===")
        for fail in results['failed']:
            print(f"  ID {fail['id']}: task={fail['task']}, key={fail['key']} - {fail['message']}")
        print()
        return 1
    else:
        print("All certificates verified successfully!")
        return 0


if __name__ == '__main__':
    sys.exit(main())
