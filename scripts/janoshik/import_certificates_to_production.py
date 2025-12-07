#!/usr/bin/env python3
"""
Import Janoshik certificates from development to production database.
"""
import sqlite3
from pathlib import Path

def import_janoshik_certificates():
    """Copy all janoshik_certificates from development to production."""
    
    dev_db = Path("data/development/peptide_management.db")
    prod_db = Path("data/production/peptide_management.db")
    
    if not dev_db.exists():
        print(f"❌ Development DB non trovato: {dev_db}")
        return False
    
    if not prod_db.exists():
        print(f"❌ Production DB non trovato: {prod_db}")
        return False
    
    print("📋 IMPORT CERTIFICATI JANOSHIK")
    print("=" * 80)
    print(f"🔵 Source: {dev_db}")
    print(f"🟢 Target: {prod_db}")
    print()
    
    # Connetti a entrambi i database
    dev_conn = sqlite3.connect(dev_db)
    prod_conn = sqlite3.connect(prod_db)
    
    try:
        # Conta certificati in development
        dev_count = dev_conn.execute("SELECT COUNT(*) FROM janoshik_certificates").fetchone()[0]
        print(f"📊 Certificati in development: {dev_count}")
        
        # Conta certificati già in production (dovrebbe essere 0)
        prod_count_before = prod_conn.execute("SELECT COUNT(*) FROM janoshik_certificates").fetchone()[0]
        print(f"📊 Certificati in production (prima): {prod_count_before}")
        print()
        
        if dev_count == 0:
            print("⚠️  Nessun certificato da importare")
            return True
        
        # Leggi tutti i certificati da development
        dev_cursor = dev_conn.execute("SELECT * FROM janoshik_certificates")
        columns = [desc[0] for desc in dev_cursor.description]
        rows = dev_cursor.fetchall()
        
        print(f"🔄 Importazione {len(rows)} certificati...")
        
        # Prepara INSERT con tutti i campi
        placeholders = ','.join(['?' for _ in columns])
        insert_sql = f"INSERT OR IGNORE INTO janoshik_certificates ({','.join(columns)}) VALUES ({placeholders})"
        
        # Inserisci in production
        imported = 0
        skipped = 0
        
        for row in rows:
            try:
                prod_conn.execute(insert_sql, row)
                imported += 1
            except sqlite3.IntegrityError:
                # Duplicato (task_number o image_hash già esistente)
                skipped += 1
        
        prod_conn.commit()
        
        # Verifica finale
        prod_count_after = prod_conn.execute("SELECT COUNT(*) FROM janoshik_certificates").fetchone()[0]
        
        print()
        print("=" * 80)
        print("📈 RISULTATI IMPORT")
        print("=" * 80)
        print(f"✅ Certificati importati: {imported}")
        print(f"⏭️  Certificati saltati (duplicati): {skipped}")
        print(f"📊 Totale in production (dopo): {prod_count_after}")
        print()
        
        if prod_count_after == dev_count:
            print("🎉 IMPORT COMPLETATO CON SUCCESSO!")
            return True
        else:
            print(f"⚠️  Alcuni certificati potrebbero essere stati saltati")
            print(f"   Development: {dev_count} | Production: {prod_count_after}")
            return True
        
    except Exception as e:
        print(f"❌ ERRORE durante import: {e}")
        prod_conn.rollback()
        return False
    
    finally:
        dev_conn.close()
        prod_conn.close()


if __name__ == "__main__":
    import sys
    success = import_janoshik_certificates()
    sys.exit(0 if success else 1)
