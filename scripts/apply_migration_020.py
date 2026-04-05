"""
Applica la migration 020 (fix cycles schema) ai database esistenti.

Rende cycles.protocol_id nullable e aggiunge la colonna plan_phase_id.
Necessario per i cicli generati dal treatment planner.

Uso:
    python scripts/apply_migration_020.py [--env development|production|both]
    python scripts/apply_migration_020.py --dry-run
"""

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
MIGRATION = ROOT / "migrations" / "020_fix_cycles_schema.sql"


def already_applied(conn: sqlite3.Connection) -> bool:
    """True se plan_phase_id esiste già in cycles (migration già applicata)."""
    cols = [r[1] for r in conn.execute("PRAGMA table_info(cycles)").fetchall()]
    return "plan_phase_id" in cols


def apply(db_path: Path, dry_run: bool) -> None:
    if not db_path.exists():
        print(f"  SKIP — DB non trovato: {db_path}")
        return

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = OFF")

    if already_applied(conn):
        print(f"  SKIP — migration già applicata su {db_path.name}")
        conn.close()
        return

    if dry_run:
        print(f"  DRY-RUN — applicerei migration 020 su {db_path.name}")
        conn.close()
        return

    sql = MIGRATION.read_text(encoding="utf-8")
    # executescript gestisce commit impliciti e più statement
    conn.executescript(sql)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()
    conn.close()
    print(f"  OK — migration 020 applicata su {db_path.name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--env", choices=["development", "production", "both"], default="both"
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    envs = ["development", "production"] if args.env == "both" else [args.env]

    for env in envs:
        db_path = ROOT / "data" / env / "peptide_management.db"
        print(f"{env}:")
        apply(db_path, args.dry_run)


if __name__ == "__main__":
    main()
