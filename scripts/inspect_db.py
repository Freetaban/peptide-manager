#!/usr/bin/env python3
"""
Inspect SQLite database schema: list all tables and for each table show columns, foreign keys, indexes and optional row counts.
Usage:
    python .\scripts\inspect_db.py -p data\development\peptide_management.db
    python .\scripts\inspect_db.py -p path\to\db -j out.json --include-sql --include-rows
"""
from pathlib import Path
import sqlite3
import argparse
import json
from pprint import pprint

def inspect_db(db_path: Path, include_sql: bool = False, include_rows: bool = False):
    if not db_path.exists():
        raise FileNotFoundError(f"Database file not found: {db_path}")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Get tables (exclude internal sqlite_* tables)
    cur.execute("SELECT name, type, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
    tables = []
    for master_row in cur.fetchall():
        tname = master_row["name"]
        create_sql = master_row["sql"]

        # Columns
        cur.execute(f"PRAGMA table_info('{tname}')")
        cols = []
        for r in cur.fetchall():
            # r: (cid, name, type, notnull, dflt_value, pk)
            cols.append({
                "cid": r[0],
                "name": r[1],
                "type": r[2],
                "notnull": bool(r[3]),
                "default_value": r[4],
                "pk": bool(r[5]),
            })

        # Foreign keys
        cur.execute(f"PRAGMA foreign_key_list('{tname}')")
        fks = []
        for r in cur.fetchall():
            # r: (id, seq, table, from, to, on_update, on_delete, match)
            fks.append({
                "id": r[0],
                "seq": r[1],
                "table": r[2],
                "from": r[3],
                "to": r[4],
                "on_update": r[5],
                "on_delete": r[6],
                "match": r[7],
            })

        # Indexes
        cur.execute(f"PRAGMA index_list('{tname}')")
        idxs = []
        for ir in cur.fetchall():
            # ir: (seq, name, unique, origin, partial)
            idx_name = ir[1]
            is_unique = bool(ir[2])
            cur.execute(f"PRAGMA index_info('{idx_name}')")
            idx_cols = [ci[2] for ci in cur.fetchall()]  # ci: (seqno, cid, name)
            idxs.append({
                "name": idx_name,
                "unique": is_unique,
                "columns": idx_cols
            })

        # Row count (optional; can be slow on large tables)
        row_count = None
        if include_rows:
            try:
                cur.execute(f"SELECT COUNT(*) as cnt FROM '{tname}'")
                cnt_row = cur.fetchone()
                if cnt_row is not None:
                    # sqlite3.Row supports both index and key
                    row_count = cnt_row["cnt"] if "cnt" in cnt_row.keys() else cnt_row[0]
            except Exception:
                row_count = None

        tables.append({
            "name": tname,
            "columns": cols,
            "foreign_keys": fks,
            "indexes": idxs,
            "create_sql": create_sql if include_sql else None,
            "row_count": row_count
        })

    conn.close()
    return tables

def pretty_print(tables):
    for t in tables:
        print("=" * 80)
        print(f"Table: {t['name']}")
        if t.get("row_count") is not None:
            print(f"Rows: {t['row_count']}")
        if t.get("create_sql"):
            print("CREATE TABLE SQL:")
            print(t["create_sql"])
        print("\nColumns:")
        for c in t["columns"]:
            pk = " PK" if c["pk"] else ""
            nn = " NOT NULL" if c["notnull"] else ""
            dflt = f" DEFAULT={c['default_value']}" if c["default_value"] is not None else ""
            print(f"  - {c['name']} ({c['type']}){pk}{nn}{dflt}")
        if t["foreign_keys"]:
            print("\nForeign keys:")
            for fk in t["foreign_keys"]:
                print(f"  - {fk['from']} -> {fk['table']}.{fk['to']} (on_update={fk['on_update']}, on_delete={fk['on_delete']})")
        if t["indexes"]:
            print("\nIndexes:")
            for idx in t["indexes"]:
                uniq = " UNIQUE" if idx["unique"] else ""
                cols = ", ".join(idx["columns"])
                print(f"  - {idx['name']}{uniq} ({cols})")
        print()

def main():
    parser = argparse.ArgumentParser(description="Inspect a SQLite database and list tables + schema.")
    parser.add_argument("-p", "--path", type=str, default="data/development/peptide_management.db",
                        help="Path to SQLite DB file (default: data/development/peptide_management.db)")
    parser.add_argument("-j", "--json", type=str, default=None,
                        help="Write output JSON to this file")
    parser.add_argument("--include-sql", action="store_true", help="Include CREATE TABLE SQL in output")
    parser.add_argument("--include-rows", action="store_true", help="Include row counts for each table (may be slow)")
    args = parser.parse_args()

    db_path = Path(args.path)
    try:
        tables = inspect_db(db_path, include_sql=args.include_sql, include_rows=args.include_rows)
    except Exception as e:
        print(f"Error: {e}")
        return

    # Print human-friendly
    pretty_print(tables)

    # Optionally dump JSON
    if args.json:
        out_path = Path(args.json)
        with out_path.open("w", encoding="utf-8") as fh:
            json.dump(tables, fh, indent=2, ensure_ascii=False)
        print(f"JSON saved to: {out_path}")

if __name__ == "__main__":
    main()