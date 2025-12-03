"""
Script per sincronizzare dati da produzione a staging.
- Copia tabelle comuni (peptides, suppliers, batches, preparations, administrations, ecc.)
- Applica automaticamente migrazioni per nuove tabelle (cycles, ecc.)
- Mantiene integrità referenziale
"""

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
import sys


def backup_database(db_path: Path) -> Path:
    """Crea backup del database."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.with_suffix(f".backup_{timestamp}")
    shutil.copy2(db_path, backup_path)
    print(f"  💾 Backup creato: {backup_path}")
    return backup_path


def get_table_names(conn: sqlite3.Connection) -> set:
    """Recupera nomi di tutte le tabelle nel database."""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    return {row[0] for row in cursor.fetchall()}


def copy_table_data(src_conn: sqlite3.Connection, dst_conn: sqlite3.Connection, table_name: str) -> int:
    """Copia dati da una tabella source a destination."""
    src_cursor = src_conn.cursor()
    dst_cursor = dst_conn.cursor()
    
    # Recupera nomi colonne dalla tabella destination
    dst_cursor.execute(f"PRAGMA table_info({table_name})")
    dst_columns = {row[1] for row in dst_cursor.fetchall()}
    
    # Recupera nomi colonne dalla tabella source
    src_cursor.execute(f"PRAGMA table_info({table_name})")
    src_columns = {row[1] for row in src_cursor.fetchall()}
    
    # Trova colonne comuni
    common_columns = dst_columns & src_columns
    
    if not common_columns:
        print(f"    ⚠️  Nessuna colonna comune in {table_name}")
        return 0
    
    columns_str = ", ".join(common_columns)
    placeholders = ", ".join(["?" for _ in common_columns])
    
    # Leggi dati da source
    src_cursor.execute(f"SELECT {columns_str} FROM {table_name}")
    rows = src_cursor.fetchall()
    
    if not rows:
        print(f"    ℹ️  {table_name}: nessun dato da copiare")
        return 0
    
    # Svuota tabella destination
    dst_cursor.execute(f"DELETE FROM {table_name}")
    
    # Inserisci dati
    dst_cursor.execute(f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})", rows[0])
    for row in rows[1:]:
        dst_cursor.execute(f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})", row)
    
    dst_conn.commit()
    print(f"    ✅ {table_name}: {len(rows)} righe copiate")
    return len(rows)


def sync_prod_to_staging():
    """Sincronizza database produzione → staging."""
    
    print("="*70)
    print("SINCRONIZZAZIONE DATABASE: PRODUZIONE → STAGING")
    print("="*70)
    print()
    
    # Percorsi diretti (environment.py non ha supporto staging)
    root_dir = Path(__file__).parent.parent
    prod_db_path = root_dir / "data" / "production" / "peptide_management.db"
    staging_db_path = root_dir / "data" / "staging" / "peptide_management.db"
    
    print(f"📁 Produzione: {prod_db_path}")
    print(f"📁 Staging:    {staging_db_path}")
    print()
    
    # Verifica esistenza DB produzione
    if not prod_db_path.exists():
        print(f"❌ Database produzione non trovato: {prod_db_path}")
        return False
    
    # Conferma utente
    response = input("⚠️  Il database staging sarà sovrascritto con i dati di produzione.\n   Le migrazioni (cycles, ecc.) saranno riapplicate.\n   Continuare? (y/n): ")
    
    if response.lower() != 'y':
        print("❌ Operazione annullata")
        return False
    
    print()
    print("🔄 Inizio sincronizzazione...")
    print()
    
    # 1. Backup staging corrente
    print("📦 Step 1: Backup staging corrente")
    backup_path = backup_database(staging_db_path)
    print()
    
    # 2. Connessioni
    print("🔌 Step 2: Apertura connessioni database")
    prod_conn = sqlite3.connect(prod_db_path)
    staging_conn = sqlite3.connect(staging_db_path)
    print("  ✅ Connessioni aperte")
    print()
    
    # 3. Analizza tabelle
    print("🔍 Step 3: Analisi strutture database")
    prod_tables = get_table_names(prod_conn)
    staging_tables = get_table_names(staging_conn)
    
    common_tables = prod_tables & staging_tables
    staging_only_tables = staging_tables - prod_tables
    
    print(f"  📊 Tabelle in produzione: {len(prod_tables)}")
    print(f"  📊 Tabelle in staging: {len(staging_tables)}")
    print(f"  📊 Tabelle comuni: {len(common_tables)}")
    print(f"  📊 Tabelle solo in staging: {len(staging_only_tables)}")
    if staging_only_tables:
        print(f"      → {', '.join(sorted(staging_only_tables))}")
    print()
    
    # 4. Copia dati tabelle comuni (ordine per rispettare foreign keys)
    print("📋 Step 4: Svuotamento e copia dati")
    
    # Ordine di copia per rispettare dipendenze foreign key
    tables_order = [
        'suppliers',
        'peptides',
        'batches',
        'batch_composition',
        'certificates',
        'certificate_details',
        'preparations',
        'protocols',
        'protocol_peptides',
        'administrations',
    ]
    
    # Aggiungi altre tabelle comuni non nell'ordine predefinito
    remaining_tables = common_tables - set(tables_order)
    tables_order.extend(sorted(remaining_tables))
    
    # Prima svuota TUTTE le tabelle in staging (incluse quelle solo in staging!)
    print("  🗑️  Svuotamento TUTTE le tabelle staging...")
    staging_cursor = staging_conn.cursor()
    
    # Svuota anche tabelle solo in staging (es: cycles)
    all_staging_tables = staging_cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    
    staging_tables_to_clear = [t[0] for t in all_staging_tables if t[0] != 'schema_migrations']
    
    # Ordina per foreign keys (inverso)
    tables_clear_order = ['administrations', 'protocol_peptides', 'protocols', 'cycles', 'preparations', 
                          'certificate_details', 'certificates', 'batch_composition', 'batches', 'peptides', 'suppliers']
    
    # Aggiungi altre tabelle non nell'ordine
    for t in staging_tables_to_clear:
        if t not in tables_clear_order:
            tables_clear_order.append(t)
    
    for table in tables_clear_order:
        if table in staging_tables_to_clear:
            staging_cursor.execute(f"DELETE FROM {table}")
            staging_conn.commit()
            print(f"    ✓ {table} svuotata")
    print()
    
    # Poi copia i dati da produzione
    print("  📦 Copia dati da produzione...")
    total_rows = 0
    for table in tables_order:
        if table in common_tables and table != 'schema_migrations':
            rows_copied = copy_table_data(prod_conn, staging_conn, table)
            total_rows += rows_copied
    
    print()
    print(f"  ✅ Totale righe copiate: {total_rows}")
    print()
    
    # 5. Chiudi connessioni
    print("🔒 Step 5: Chiusura connessioni")
    prod_conn.close()
    staging_conn.close()
    print("  ✅ Connessioni chiuse")
    print()
    
    # 6. Applica migrazioni
    print("🔧 Step 6: Applicazione migrazioni al database staging")
    print("  → Eseguo run_migrations_on_db.py...")
    print()
    
    import subprocess
    result = subprocess.run(
        ["python", "scripts/run_migrations_on_db.py", "--db", str(staging_db_path)],
        cwd=Path(__file__).parent.parent,
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    if result.returncode != 0:
        print(f"  ⚠️  Errore durante applicazione migrazioni:")
        print(result.stderr)
    
    print()
    
    # 7. Riepilogo finale
    print("="*70)
    print("✅ SINCRONIZZAZIONE COMPLETATA")
    print("="*70)
    print()
    print(f"📊 Dati copiati: {total_rows} righe da {len(common_tables)} tabelle")
    print(f"💾 Backup staging: {backup_path}")
    print(f"🗄️  Database staging pronto: {staging_db_path}")
    print()
    
    return True


if __name__ == "__main__":
    try:
        sync_prod_to_staging()
    except Exception as ex:
        print(f"\n❌ ERRORE: {ex}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
