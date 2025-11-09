"""
Deploy feature da sviluppo a produzione
"""

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from environment import get_environment

def deploy_to_production(dry_run: bool = False):
    """
    Deploy modifiche da sviluppo a produzione.
    
    Args:
        dry_run: Se True, simula senza applicare modifiche
    """
    
    print("="*60)
    print("DEPLOY FEATURE: SVILUPPO → PRODUZIONE")
    print("="*60)
    print()
    
    # Carica ambienti
    dev_env = get_environment("development")
    prod_env = get_environment("production")
    
    if not dev_env.db_path.exists():
        print(f"❌ Database sviluppo non trovato: {dev_env.db_path}")
        return False
    
    if not prod_env.db_path.exists():
        print(f"❌ Database produzione non trovato: {prod_env.db_path}")
        return False
    
    # 1. Analizza differenze schema
    print("📊 Analisi differenze schema...")
    schema_diff = compare_schemas(dev_env.db_path, prod_env.db_path)
    
    if not schema_diff['has_changes']:
        print("✅ Nessuna modifica schema rilevata")
    else:
        print(f"⚠️  Modifiche schema rilevate:")
        for change in schema_diff['changes']:
            print(f"   • {change}")
    
    print()
    
    # 2. Mostra riepilogo
    print("📋 RIEPILOGO DEPLOY:")
    print(f"   Ambiente: {dev_env.name} → {prod_env.name}")
    print(f"   Database prod: {prod_env.db_path}")
    print(f"   Modifiche schema: {'Sì' if schema_diff['has_changes'] else 'No'}")
    print()
    
    if dry_run:
        print("🔍 DRY RUN - Nessuna modifica applicata")
        return True
    
    # 3. Conferma utente
    print("⚠️  ATTENZIONE: Questa operazione modificherà il database di PRODUZIONE!")
    response = input("Continuare con il deploy? (y/n): ")
    
    if response.lower() != 'y':
        print("Deploy annullato.")
        return False
    
    # 4. Backup produzione
    print("\n💾 Creazione backup produzione...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = prod_env.backup_dir / f"pre_deploy_{timestamp}.db"
    prod_env.backup_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(prod_env.db_path, backup_path)
    print(f"✅ Backup salvato: {backup_path}")
    
    # 5. Applica migrazioni (se presenti)
    if schema_diff['has_changes']:
        print("\n🔄 Applicazione migrazioni schema...")
        success = apply_schema_changes(prod_env.db_path, schema_diff['changes'])
        
        if not success:
            print("❌ Errore durante applicazione migrazioni!")
            print(f"   Ripristina da backup: {backup_path}")
            return False
        
        print("✅ Migrazioni applicate con successo")
    
    # 6. Deploy completato
    print("\n" + "="*60)
    print("✅ DEPLOY COMPLETATO!")
    print("="*60)
    print(f"📁 Database produzione aggiornato: {prod_env.db_path}")
    print(f"💾 Backup disponibile: {backup_path}")
    print()
    
    return True


def compare_schemas(db1_path: Path, db2_path: Path) -> dict:
    """
    Confronta schema tra due database.
    
    Returns:
        {
            'has_changes': bool,
            'changes': [str],  # Lista differenze
        }
    """
    
    def get_schema(db_path):
        """Recupera schema database."""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Tabelle
        cursor.execute("""
            SELECT name, sql 
            FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)
        tables = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Indici
        cursor.execute("""
            SELECT name, sql 
            FROM sqlite_master 
            WHERE type='index' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)
        indexes = {row[0]: row[1] for row in cursor.fetchall() if row[1]}
        
        conn.close()
        return {'tables': tables, 'indexes': indexes}
    
    schema1 = get_schema(db1_path)
    schema2 = get_schema(db2_path)
    
    changes = []
    
    # Nuove tabelle
    new_tables = set(schema1['tables'].keys()) - set(schema2['tables'].keys())
    for table in new_tables:
        changes.append(f"Nuova tabella: {table}")
    
    # Tabelle rimosse
    removed_tables = set(schema2['tables'].keys()) - set(schema1['tables'].keys())
    for table in removed_tables:
        changes.append(f"Tabella rimossa: {table}")
    
    # Tabelle modificate
    common_tables = set(schema1['tables'].keys()) & set(schema2['tables'].keys())
    for table in common_tables:
        if schema1['tables'][table] != schema2['tables'][table]:
            changes.append(f"Tabella modificata: {table}")
    
    # Nuovi indici
    new_indexes = set(schema1['indexes'].keys()) - set(schema2['indexes'].keys())
    for index in new_indexes:
        changes.append(f"Nuovo indice: {index}")
    
    return {
        'has_changes': len(changes) > 0,
        'changes': changes,
    }


def apply_schema_changes(db_path: Path, changes: list) -> bool:
    """
    Applica modifiche schema al database.
    
    IMPORTANTE: Questo è un placeholder!
    In produzione, usa script di migrazione specifici in migrations/
    """
    
    print("⚠️  ATTENZIONE: Applicazione automatica schema non implementata!")
    print("   Devi creare script di migrazione manuale in migrations/")
    print("   Esempio: migrations/003_add_new_feature.sql")
    print()
    print("   Usa: python migrations/migrate.py --env production")
    print()
    
    return False  # Sicuro: non applica modifiche automatiche


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Deploy feature a produzione')
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simula deploy senza applicare modifiche'
    )
    
    args = parser.parse_args()
    
    deploy_to_production(dry_run=args.dry_run)