"""
Sincronizza tabella suppliers con dati da Janoshik

Funzionalità:
1. Legge suppliers unici da janoshik_certificates
2. Per suppliers già esistenti: aggiorna solo il nome se diverso
3. Per suppliers nuovi: li inserisce con website estratto dai certificati
"""

import sqlite3
import argparse
from pathlib import Path
from typing import Dict, Optional
import re


def extract_domain_from_text(text: str) -> Optional[str]:
    """
    Estrae dominio da testo libero (stesso di extract_supplier_websites.py).
    """
    if not text:
        return None
    
    text = text.strip()
    
    # Pattern per domini comuni
    domain_patterns = [
        # URL completo (con http/https)
        r'https?://(?:www\.)?([a-zA-Z0-9-]+\.[a-zA-Z]{2,})',
        # Dominio con www
        r'(?:^|[^a-zA-Z0-9])(?:www\.)?([a-zA-Z0-9-]+\.(?:com|net|org|io|co|uk|de|fr|it|eu|cn|ru|jp))',
        # Stringa che termina con .com, .net etc
        r'([a-zA-Z0-9-]+\.(?:com|net|org|io|co|uk|de|fr|it|eu|cn|ru|jp))(?:[^a-zA-Z0-9]|$)',
    ]
    
    for pattern in domain_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            domain = match.group(1).lower()
            if not domain.startswith('www.'):
                domain = f'www.{domain}'
            return domain
    
    return None


def sync_suppliers_from_janoshik(db_path: str, dry_run: bool = True):
    """
    Sincronizza tabella suppliers con dati Janoshik.
    
    Args:
        db_path: Path al database
        dry_run: Se True, mostra solo cosa farebbe senza modificare
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    print("=" * 80)
    print("SINCRONIZZAZIONE SUPPLIERS DA JANOSHIK")
    print("=" * 80)
    print(f"Database: {db_path}")
    print(f"Modalità: {'DRY RUN (solo analisi)' if dry_run else 'MODIFICA EFFETTIVA'}")
    print()
    
    # 1. Leggi suppliers unici da Janoshik con website
    cur.execute("""
        SELECT DISTINCT supplier_name, supplier_website 
        FROM janoshik_certificates 
        WHERE supplier_name IS NOT NULL AND supplier_name != ''
        ORDER BY supplier_name
    """)
    janoshik_data = cur.fetchall()
    
    # Crea mapping supplier -> website (prende il primo website non-NULL trovato)
    janoshik_suppliers: Dict[str, Optional[str]] = {}
    for name, website in janoshik_data:
        if name not in janoshik_suppliers:
            # Normalizza website
            normalized_website = extract_domain_from_text(website) if website else None
            janoshik_suppliers[name] = normalized_website
    
    print(f"📊 Suppliers unici in Janoshik: {len(janoshik_suppliers)}")
    with_website = sum(1 for w in janoshik_suppliers.values() if w)
    print(f"   - Con website: {with_website}")
    print(f"   - Senza website: {len(janoshik_suppliers) - with_website}")
    
    # 2. Leggi suppliers esistenti nella tabella suppliers
    cur.execute("SELECT id, name, website FROM suppliers WHERE deleted_at IS NULL")
    existing_suppliers = {row[1]: (row[0], row[2]) for row in cur.fetchall()}  # name -> (id, website)
    
    print(f"📊 Suppliers esistenti in tabella: {len(existing_suppliers)}")
    print()
    
    # 3. Analizza operazioni necessarie
    to_insert = []  # (supplier_name, website)
    to_update_website = []  # (supplier_id, supplier_name, old_website, new_website)
    already_ok = []  # Suppliers già presenti
    
    for supplier_name, janoshik_website in sorted(janoshik_suppliers.items()):
        if supplier_name in existing_suppliers:
            supplier_id, current_website = existing_suppliers[supplier_name]
            
            # Verifica se website va aggiornato
            if janoshik_website and (not current_website or current_website.strip() == ''):
                to_update_website.append((supplier_id, supplier_name, current_website, janoshik_website))
            else:
                already_ok.append(supplier_name)
        else:
            # Supplier non esiste, va inserito
            to_insert.append((supplier_name, janoshik_website))
    
    # Report
    print("📋 ANALISI:")
    print("-" * 80)
    print(f"✅ Suppliers già presenti: {len(already_ok)}")
    print(f"➕ Suppliers da inserire: {len(to_insert)}")
    print(f"🔄 Website da aggiornare: {len(to_update_website)}")
    print()
    
    if to_insert:
        print("➕ SUPPLIERS DA INSERIRE:")
        print("-" * 80)
        for name, website in to_insert[:20]:
            # Conta certificati per questo supplier
            cur.execute(
                "SELECT COUNT(*) FROM janoshik_certificates WHERE supplier_name = ?",
                (name,)
            )
            cert_count = cur.fetchone()[0]
            website_str = website or "(nessun website)"
            print(f"  {name} ({cert_count} certificati)")
            print(f"    Website: {website_str}")
        if len(to_insert) > 20:
            print(f"  ... e altri {len(to_insert) - 20} suppliers")
        print()
    
    if to_update_website:
        print("🔄 WEBSITE DA AGGIORNARE:")
        print("-" * 80)
        for supplier_id, name, old_website, new_website in to_update_website:
            print(f"  {name}")
            print(f"    Vecchio: {old_website or '(vuoto)'}")
            print(f"    Nuovo:   {new_website}")
        print()
    
    # 4. Applica modifiche se non dry_run
    inserted_count = 0
    updated_count = 0
    
    if not dry_run:
        if to_insert:
            print("🔄 Inserimento suppliers...")
            for name, website in to_insert:
                cur.execute("""
                    INSERT INTO suppliers (name, website, country, email, notes, reliability_rating)
                    VALUES (?, ?, NULL, NULL, 'Importato da Janoshik', NULL)
                """, (name, website))
                inserted_count += 1
            print(f"✅ {inserted_count} suppliers inseriti!")
        
        if to_update_website:
            print("🔄 Aggiornamento website...")
            for supplier_id, name, old_website, new_website in to_update_website:
                cur.execute("""
                    UPDATE suppliers
                    SET website = ?
                    WHERE id = ?
                """, (new_website, supplier_id))
                updated_count += 1
            print(f"✅ {updated_count} website aggiornati!")
        
        if inserted_count > 0 or updated_count > 0:
            conn.commit()
            print()
    
    # 5. Riepilogo finale
    print("=" * 80)
    print("RIEPILOGO")
    print("=" * 80)
    print(f"Suppliers in Janoshik: {len(janoshik_suppliers)}")
    print(f"Suppliers già presenti: {len(already_ok)}")
    print(f"Suppliers inseriti: {inserted_count}")
    print(f"Website aggiornati: {updated_count}")
    print()
    
    if dry_run:
        print("⚠️  DRY RUN: Nessuna modifica applicata al database")
        print("   Per applicare le modifiche, riesegui con --apply")
    else:
        print("✅ MODIFICHE APPLICATE con successo!")
    
    conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Sincronizza tabella suppliers con nomi da Janoshik"
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
    
    sync_suppliers_from_janoshik(str(db_path), dry_run=not args.apply)
    return 0


if __name__ == "__main__":
    exit(main())
