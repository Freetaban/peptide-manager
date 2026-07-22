"""
Backfill degli eventi di spreco dalle vecchie colonne wastage_* .

Prima della migrazione 024 gli sprechi vivevano in `preparations.wastage_notes`
come testo libero append-only, nel formato:

    YYYY-MM-DD: X.XX ml - motivo/note

Questo script riparsa quel testo e crea i record corrispondenti in
`preparation_events`. E' idempotente: salta le preparazioni che hanno gia'
almeno un evento.

Le colonne wastage_* NON vengono cancellate: restano come rete di sicurezza
e come cache derivata (wastage_ml/wastage_reason continuano a essere
riallineati da PreparationRepository._apply_event_delta).

Uso:
    python scripts/backfill_preparation_events.py --env development
    python scripts/backfill_preparation_events.py --env development --apply
    python scripts/backfill_preparation_events.py --env production --apply
"""

import argparse
import re
import sqlite3
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.environment import get_environment


# "2025-11-28: 0.75 ml - spillage"
LINE_RE = re.compile(r'^(\d{4}-\d{2}-\d{2})\s*:\s*([\d.]+)\s*ml\s*(?:-\s*(.*))?$')

VALID_REASONS = ('measurement_error', 'spillage', 'contamination', 'other')


def parse_wastage_notes(notes, fallback_reason, fallback_date):
    """
    Riparsa wastage_notes in una lista di eventi.

    Returns:
        Tuple (eventi, righe_non_parsate)
    """
    events = []
    unparsed = []

    for raw_line in (notes or '').strip().split('\n'):
        line = raw_line.strip()
        if not line:
            continue

        match = LINE_RE.match(line)
        if not match:
            unparsed.append(line)
            continue

        event_date, volume, trailing = match.groups()
        trailing = (trailing or '').strip()

        # Il testo dopo " - " e' il motivo se coincide con un valore valido,
        # altrimenti sono note libere scritte dall'utente
        if trailing in VALID_REASONS:
            reason, event_notes = trailing, None
        else:
            reason, event_notes = fallback_reason, (trailing or None)

        events.append({
            'event_date': event_date,
            'volume_ml': float(volume),
            'reason': reason if reason in VALID_REASONS else 'other',
            'notes': event_notes,
        })

    return events, unparsed


def backfill(db_path, apply_changes):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    preps = conn.execute('''
        SELECT id, wastage_ml, wastage_reason, wastage_notes,
               actual_depletion_date, status
        FROM preparations
        WHERE wastage_ml IS NOT NULL AND wastage_ml > 0
        ORDER BY id
    ''').fetchall()

    created = skipped = 0
    warnings = []

    for prep in preps:
        prep_id = prep['id']

        existing = conn.execute(
            'SELECT COUNT(*) FROM preparation_events WHERE preparation_id = ?',
            (prep_id,)
        ).fetchone()[0]

        if existing:
            skipped += 1
            continue

        fallback_date = prep['actual_depletion_date'] or date.today().isoformat()
        events, unparsed = parse_wastage_notes(
            prep['wastage_notes'], prep['wastage_reason'], fallback_date
        )

        for line in unparsed:
            warnings.append(f"Prep #{prep_id}: riga non parsata -> {line!r}")

        total_parsed = round(sum(e['volume_ml'] for e in events), 2)
        recorded = round(float(prep['wastage_ml']), 2)

        if not events:
            # Nessuna nota utilizzabile: creiamo un evento unico dal totale,
            # cosi' non perdiamo il volume gia' registrato
            warnings.append(
                f"Prep #{prep_id}: wastage_notes non parsabile, "
                f"creo un evento unico da {recorded} ml"
            )
            events = [{
                'event_date': fallback_date,
                'volume_ml': recorded,
                'reason': prep['wastage_reason'] if prep['wastage_reason'] in VALID_REASONS else 'other',
                'notes': prep['wastage_notes'],
            }]
        elif abs(total_parsed - recorded) > 0.01:
            # Il totale ricostruito non torna: lo segnaliamo invece di
            # correggerlo in silenzio
            warnings.append(
                f"Prep #{prep_id}: somma eventi {total_parsed} ml != "
                f"wastage_ml {recorded} ml (differenza {round(recorded - total_parsed, 2)} ml)"
            )

        for e in events:
            print(
                f"  Prep #{prep_id}: {e['event_date']} {e['volume_ml']:.2f} ml "
                f"[{e['reason']}] {e['notes'] or ''}"
            )
            if apply_changes:
                conn.execute('''
                    INSERT INTO preparation_events
                        (preparation_id, event_type, volume_ml, event_date, reason, notes)
                    VALUES (?, 'wastage', ?, ?, ?, ?)
                ''', (prep_id, e['volume_ml'], e['event_date'], e['reason'], e['notes']))
            created += 1

    if apply_changes:
        conn.commit()

    conn.close()

    print()
    print(f"Preparazioni esaminate : {len(preps)}")
    print(f"Gia' con eventi (skip) : {skipped}")
    print(f"Eventi {'creati' if apply_changes else 'da creare'} : {created}")

    if warnings:
        print()
        print(f"AVVISI ({len(warnings)}):")
        for w in warnings:
            print(f"  ! {w}")

    if not apply_changes:
        print()
        print("DRY RUN - nessuna modifica scritta. Rilancia con --apply per applicare.")


def main():
    parser = argparse.ArgumentParser(
        description='Backfill preparation_events dalle colonne wastage_*'
    )
    parser.add_argument('--env', choices=['production', 'development', 'staging'],
                        default='development')
    parser.add_argument('--apply', action='store_true',
                        help='Applica le modifiche (default: dry run)')
    args = parser.parse_args()

    env = get_environment(args.env)

    print(f"Database: {env.db_path}")
    print(f"Modalita': {'APPLY' if args.apply else 'DRY RUN'}")
    print()

    if args.apply and env.is_production():
        print("ATTENZIONE: stai per scrivere sul database di PRODUZIONE.")
        if input("Continuare? (y/n): ").lower() != 'y':
            print("Operazione annullata.")
            return

    backfill(env.db_path, args.apply)


if __name__ == '__main__':
    main()
