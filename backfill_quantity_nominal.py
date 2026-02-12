"""
Backfill quantity_nominal for records where it's NULL.

Two-pass strategy:
1. Try to parse from raw_llm_response JSON (quantity_nominal field may exist there)
2. Fallback: parse from product_name using regex (e.g. "Tirzepatide 30mg" -> 30)

Only touches records where quantity_nominal IS NULL.
"""

import json
import os
import re
import sqlite3
import sys
from pathlib import Path

# Fix Windows console encoding for emoji output from environment.py
os.environ.setdefault('PYTHONUTF8', '1')
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Add scripts to path for environment module
sys.path.insert(0, str(Path(__file__).parent / "scripts"))

from environment import get_environment

# Regex: match a number followed by a unit (mg, mgs, mgl, mcg, iu)
# (?<!\w) prevents matching inside words like "PNC-27" or "SNAP-8"
QTY_PATTERN = re.compile(
    r'(?<!\w)(\d+(?:\.\d+)?)\s*(?:mg[ls]?|mcg|iu)\b',
    re.IGNORECASE
)


def parse_qty_from_text(text: str):
    """Parse (quantity, unit) from a text string. Returns (None, None) if no match."""
    if not text:
        return None, None

    m = QTY_PATTERN.search(text)
    if not m:
        return None, None

    quantity = float(m.group(1))
    # Extract unit substring from match
    unit_raw = text[m.start(1):m.end()].split(m.group(1))[-1].strip().lower()

    if unit_raw.startswith('mg'):
        unit = 'mg'
    elif unit_raw.startswith('mcg'):
        unit = 'mcg'
    elif unit_raw.startswith('iu'):
        unit = 'IU'
    else:
        unit = 'mg'  # safe default given regex only matches mg/mcg/iu

    return quantity, unit


def backfill():
    env = get_environment("production")
    conn = sqlite3.connect(env.db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, task_number, product_name, raw_llm_response, unit_of_measure
        FROM janoshik_certificates
        WHERE quantity_nominal IS NULL
        ORDER BY id
    """)

    rows = cursor.fetchall()
    total = len(rows)
    print(f"\nRecords with quantity_nominal IS NULL: {total}\n")

    updated_from_llm = 0
    updated_from_name = 0
    still_null = 0

    for row in rows:
        cert_id = row['id']
        task = row['task_number']
        product_name = row['product_name'] or ''
        raw_json = row['raw_llm_response']
        existing_unit = row['unit_of_measure']

        quantity = None
        unit = existing_unit
        source = None

        # Pass 1: try raw_llm_response JSON
        if raw_json:
            try:
                data = json.loads(raw_json)
                llm_qty = data.get('quantity_nominal')
                if llm_qty is not None:
                    quantity = float(llm_qty)
                    source = 'llm_json'
                    if not unit:
                        unit = data.get('unit_of_measure') or 'mg'
            except (json.JSONDecodeError, ValueError, TypeError):
                pass

        # Pass 2: try parsing from product_name (sample field)
        if quantity is None:
            quantity, parsed_unit = parse_qty_from_text(product_name)
            if quantity is not None:
                source = 'product_name'
                if not unit:
                    unit = parsed_unit

        # Pass 3: try parsing from sample field inside raw_llm_response
        if quantity is None and raw_json:
            try:
                data = json.loads(raw_json)
                sample = data.get('sample', '')
                quantity, parsed_unit = parse_qty_from_text(sample)
                if quantity is not None:
                    source = 'llm_sample'
                    if not unit:
                        unit = parsed_unit
            except (json.JSONDecodeError, ValueError, TypeError):
                pass

        if quantity is not None:
            cursor.execute("""
                UPDATE janoshik_certificates
                SET quantity_nominal = ?, unit_of_measure = ?
                WHERE id = ?
            """, (quantity, unit, cert_id))

            if source == 'llm_json':
                updated_from_llm += 1
            else:
                updated_from_name += 1

            print(f"  [{source:>12}] #{task:>6} | {product_name[:40]:<40} -> {quantity} {unit}")
        else:
            still_null += 1
            print(f"  [  NO MATCH ] #{task:>6} | {product_name[:40]:<40}")

    conn.commit()
    conn.close()

    print(f"\n{'='*60}")
    print(f"RESULTS:")
    print(f"  Total NULL records:     {total}")
    print(f"  Updated from LLM JSON:  {updated_from_llm}")
    print(f"  Updated from name/text: {updated_from_name}")
    print(f"  Still NULL:             {still_null}")
    print(f"{'='*60}")


if __name__ == "__main__":
    backfill()
