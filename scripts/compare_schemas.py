"""
Confronta gli schemi dei database produzione e development.
"""
import sqlite3
from typing import Dict, List, Tuple, Set


def get_table_schema(db_path: str, table_name: str) -> str:
    """Ottiene lo schema completo di una tabella."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    conn.close()
    
    # Format: (cid, name, type, notnull, dflt_value, pk)
    schema = []
    for col in columns:
        col_def = f"{col[1]} {col[2]}"
        if col[3]:  # notnull
            col_def += " NOT NULL"
        if col[4] is not None:  # default value
            col_def += f" DEFAULT {col[4]}"
        if col[5]:  # primary key
            col_def += " PRIMARY KEY"
        schema.append(col_def)
    
    return "\n  ".join(schema)


def get_all_tables(db_path: str) -> List[str]:
    """Ottiene lista di tutte le tabelle."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' 
        AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """)
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    return tables


def get_all_indexes(db_path: str) -> Dict[str, str]:
    """Ottiene tutti gli indici."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name, sql FROM sqlite_master 
        WHERE type='index' 
        AND sql IS NOT NULL
        ORDER BY name
    """)
    indexes = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()
    return indexes


def compare_databases(prod_path: str, dev_path: str):
    """Confronta due database."""
    
    print("=" * 80)
    print("CONFRONTO SCHEMA DATABASE")
    print("=" * 80)
    print(f"Production: {prod_path}")
    print(f"Development: {dev_path}")
    print()
    
    # 1. Confronta tabelle
    print("-" * 80)
    print("TABELLE")
    print("-" * 80)
    
    prod_tables = set(get_all_tables(prod_path))
    dev_tables = set(get_all_tables(dev_path))
    
    print(f"Production: {len(prod_tables)} tabelle")
    print(f"Development: {len(dev_tables)} tabelle")
    
    # Tabelle solo in prod
    only_prod = prod_tables - dev_tables
    if only_prod:
        print(f"\n❌ Solo in PRODUCTION ({len(only_prod)}):")
        for t in sorted(only_prod):
            print(f"   - {t}")
    
    # Tabelle solo in dev
    only_dev = dev_tables - prod_tables
    if only_dev:
        print(f"\n❌ Solo in DEVELOPMENT ({len(only_dev)}):")
        for t in sorted(only_dev):
            print(f"   - {t}")
    
    # Tabelle comuni
    common_tables = prod_tables & dev_tables
    print(f"\n✅ Tabelle comuni: {len(common_tables)}")
    
    # 2. Confronta schema delle tabelle comuni
    print("\n" + "-" * 80)
    print("DIFFERENZE SCHEMA TABELLE COMUNI")
    print("-" * 80)
    
    schema_diffs = []
    for table in sorted(common_tables):
        prod_schema = get_table_schema(prod_path, table)
        dev_schema = get_table_schema(dev_path, table)
        
        if prod_schema != dev_schema:
            schema_diffs.append((table, prod_schema, dev_schema))
    
    if schema_diffs:
        print(f"\n⚠️ {len(schema_diffs)} tabelle con schema diverso:\n")
        for table, prod_sch, dev_sch in schema_diffs:
            print(f"📋 {table}")
            print(f"\n   PRODUCTION:")
            for line in prod_sch.split('\n'):
                print(f"      {line}")
            print(f"\n   DEVELOPMENT:")
            for line in dev_sch.split('\n'):
                print(f"      {line}")
            print()
    else:
        print("\n✅ Tutte le tabelle comuni hanno schema identico")
    
    # 3. Confronta indici
    print("-" * 80)
    print("INDICI")
    print("-" * 80)
    
    prod_indexes = get_all_indexes(prod_path)
    dev_indexes = get_all_indexes(dev_path)
    
    print(f"Production: {len(prod_indexes)} indici")
    print(f"Development: {len(dev_indexes)} indici")
    
    only_prod_idx = set(prod_indexes.keys()) - set(dev_indexes.keys())
    if only_prod_idx:
        print(f"\n❌ Indici solo in PRODUCTION ({len(only_prod_idx)}):")
        for idx in sorted(only_prod_idx):
            print(f"   - {idx}")
            print(f"     {prod_indexes[idx][:80]}...")
    
    only_dev_idx = set(dev_indexes.keys()) - set(prod_indexes.keys())
    if only_dev_idx:
        print(f"\n❌ Indici solo in DEVELOPMENT ({len(only_dev_idx)}):")
        for idx in sorted(only_dev_idx):
            print(f"   - {idx}")
            print(f"     {dev_indexes[idx][:80]}...")
    
    common_idx = set(prod_indexes.keys()) & set(dev_indexes.keys())
    print(f"\n✅ Indici comuni: {len(common_idx)}")
    
    # 4. Verifica migrations
    print("\n" + "-" * 80)
    print("MIGRATIONS APPLICATE")
    print("-" * 80)
    
    def get_migrations(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT version, name, applied_at FROM schema_migrations ORDER BY version")
            migrations = cursor.fetchall()
        except sqlite3.OperationalError:
            migrations = []
        conn.close()
        return migrations
    
    prod_migrations = get_migrations(prod_path)
    dev_migrations = get_migrations(dev_path)
    
    print(f"\nProduction: {len(prod_migrations)} migrations")
    if prod_migrations:
        for ver, name, applied in prod_migrations:
            print(f"   {ver}. {name} (applied: {applied})")
    
    print(f"\nDevelopment: {len(dev_migrations)} migrations")
    if dev_migrations:
        for ver, name, applied in dev_migrations:
            print(f"   {ver}. {name} (applied: {applied})")
    
    # 5. Summary
    print("\n" + "=" * 80)
    print("RIEPILOGO")
    print("=" * 80)
    
    is_identical = (
        not only_prod and 
        not only_dev and 
        not schema_diffs and 
        not only_prod_idx and 
        not only_dev_idx
    )
    
    if is_identical:
        print("✅ Gli schemi sono IDENTICI")
        print("💡 Le differenze sono solo nei dati, non nella struttura")
    else:
        print("❌ Gli schemi sono DIVERSI")
        print("\n📋 Differenze trovate:")
        if only_prod or only_dev:
            print(f"   - Tabelle diverse: {len(only_prod) + len(only_dev)}")
        if schema_diffs:
            print(f"   - Schema tabelle diversi: {len(schema_diffs)}")
        if only_prod_idx or only_dev_idx:
            print(f"   - Indici diversi: {len(only_prod_idx) + len(only_dev_idx)}")
        
        print("\n⚠️ AZIONE RICHIESTA:")
        if only_dev or schema_diffs or only_dev_idx:
            print("   Le modifiche in DEVELOPMENT devono essere migrate a PRODUCTION")
            print("   Usa: python scripts/deploy_to_production.py")


if __name__ == "__main__":
    compare_databases(
        prod_path="data/production/peptide_management.db",
        dev_path="data/development/peptide_management.db"
    )
