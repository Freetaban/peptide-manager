"""
Sincronizza tabella peptides con nomi normalizzati da Janoshik

Funzionalità:
1. Legge peptidi unici da janoshik_certificates (campo peptide_name_std)
2. Per peptidi già esistenti: aggiorna solo il nome se diverso
3. Per peptidi nuovi: li inserisce con campi vuoti
"""

import sqlite3
import argparse
from pathlib import Path


def sync_peptides_from_janoshik(db_path: str, dry_run: bool = True):
    """
    Sincronizza tabella peptides con dati Janoshik.
    
    Args:
        db_path: Path al database
        dry_run: Se True, mostra solo cosa farebbe senza modificare
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    print("=" * 80)
    print("SINCRONIZZAZIONE PEPTIDI DA JANOSHIK")
    print("=" * 80)
    print(f"Database: {db_path}")
    print(f"Modalità: {'DRY RUN (solo analisi)' if dry_run else 'MODIFICA EFFETTIVA'}")
    print()
    
    # 1. Leggi peptidi unici da Janoshik
    cur.execute("""
        SELECT DISTINCT peptide_name_std 
        FROM janoshik_certificates 
        WHERE peptide_name_std IS NOT NULL AND peptide_name_std != ''
        ORDER BY peptide_name_std
    """)
    janoshik_peptides = {row[0] for row in cur.fetchall()}
    
    print(f"📊 Peptidi unici in Janoshik: {len(janoshik_peptides)}")
    
    # 2. Leggi peptidi esistenti nella tabella peptides
    cur.execute("SELECT id, name FROM peptides WHERE deleted_at IS NULL")
    existing_peptides = {row[1]: row[0] for row in cur.fetchall()}  # name -> id
    
    print(f"📊 Peptidi esistenti in tabella peptides: {len(existing_peptides)}")
    print()
    
    # 3. Analizza operazioni necessarie
    to_insert = []  # Peptidi da inserire
    to_update = []  # Peptidi da aggiornare (se nome diverso in futuro)
    already_ok = []  # Peptidi già presenti con nome corretto
    
    for janoshik_name in sorted(janoshik_peptides):
        if janoshik_name in existing_peptides:
            # Peptide già esiste con nome corretto
            already_ok.append(janoshik_name)
        else:
            # Peptide non esiste, va inserito
            to_insert.append(janoshik_name)
    
    # Report
    print("📋 ANALISI:")
    print("-" * 80)
    print(f"✅ Peptidi già presenti con nome corretto: {len(already_ok)}")
    print(f"➕ Peptidi da inserire: {len(to_insert)}")
    print()
    
    if to_insert:
        print("➕ PEPTIDI DA INSERIRE:")
        print("-" * 80)
        for name in to_insert:
            # Conta certificati per questo peptide
            cur.execute(
                "SELECT COUNT(*) FROM janoshik_certificates WHERE peptide_name_std = ?",
                (name,)
            )
            cert_count = cur.fetchone()[0]
            print(f"  {name} ({cert_count} certificati)")
        print()
    
    # 4. Applica modifiche se non dry_run
    if not dry_run and to_insert:
        print("🔄 Inserimento peptidi...")
        for name in to_insert:
            cur.execute("""
                INSERT INTO peptides (name, description, common_uses, notes)
                VALUES (?, NULL, NULL, NULL)
            """, (name,))
        
        conn.commit()
        print(f"✅ {len(to_insert)} peptidi inseriti con successo!")
        print()
    
    # 5. Riepilogo finale
    print("=" * 80)
    print("RIEPILOGO")
    print("=" * 80)
    print(f"Peptidi in Janoshik: {len(janoshik_peptides)}")
    print(f"Peptidi già corretti: {len(already_ok)}")
    print(f"Peptidi inseriti: {len(to_insert) if not dry_run else 0}")
    print()
    
    if dry_run:
        print("⚠️  DRY RUN: Nessuna modifica applicata al database")
        print("   Per applicare le modifiche, riesegui con --apply")
    else:
        print("✅ MODIFICHE APPLICATE con successo!")
    
    conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Sincronizza tabella peptides con nomi da Janoshik"
    )
    parser.add_argument(
        "--db",
        default="data/production/peptide_management.db",
        help="Path al database (default: data/production/peptide_management.db)"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Applica le modifiche (default: dry-run)"
    )
    
    args = parser.parse_args()
    
    # Verifica che il database esista
    db_path = Path(args.db)
    if not db_path.exists():
        print(f"❌ Errore: Database non trovato: {db_path}")
        return 1
    
    sync_peptides_from_janoshik(str(db_path), dry_run=not args.apply)
    return 0


if __name__ == "__main__":
    exit(main())
