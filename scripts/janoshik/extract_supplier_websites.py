"""
Estrae e aggiorna website dei suppliers da certificati Janoshik

Estrae URL/domini dal campo 'client' nei raw_data dei certificati e aggiorna
il campo 'website' nella tabella suppliers.
"""

import sqlite3
import json
import re
import argparse
from pathlib import Path
from typing import Dict, Optional


def extract_domain_from_text(text: str) -> Optional[str]:
    """
    Estrae dominio da testo libero.
    
    Riconosce pattern come:
    - ModernPeptides.com → www.modernpeptides.com
    - www.example.com → www.example.com
    - example.com → www.example.com
    - https://example.com → www.example.com
    """
    if not text:
        return None
    
    text = text.strip()
    
    # Pattern per domini comuni
    # Cerca domini con TLD comuni (.com, .net, .org, etc)
    domain_patterns = [
        # URL completo (con http/https)
        r'https?://(?:www\.)?([a-zA-Z0-9-]+\.[a-zA-Z]{2,})',
        # Dominio con www
        r'(?:^|[^a-zA-Z0-9])(?:www\.)?([a-zA-Z0-9-]+\.(?:com|net|org|io|co|uk|de|fr|it|eu|cn|ru|jp))',
        # Stringa che termina con .com, .net etc (es: "ModernPeptides.com")
        r'([a-zA-Z0-9-]+\.(?:com|net|org|io|co|uk|de|fr|it|eu|cn|ru|jp))(?:[^a-zA-Z0-9]|$)',
    ]
    
    for pattern in domain_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            domain = match.group(1).lower()
            # Assicura che inizi con www se non ha già un sottodominio
            if not domain.startswith('www.'):
                domain = f'www.{domain}'
            return domain
    
    return None


def extract_websites_from_janoshik(db_path: str, dry_run: bool = True):
    """
    Estrae website dai certificati Janoshik e aggiorna tabella suppliers.
    
    Args:
        db_path: Path al database
        dry_run: Se True, mostra solo cosa farebbe
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    print("=" * 80)
    print("ESTRAZIONE WEBSITE DA CERTIFICATI JANOSHIK")
    print("=" * 80)
    print(f"Database: {db_path}")
    print(f"Modalità: {'DRY RUN (solo analisi)' if dry_run else 'MODIFICA EFFETTIVA'}")
    print()
    
    # 1. Leggi tutti i certificati con supplier_website
    cur.execute("""
        SELECT DISTINCT supplier_name, supplier_website
        FROM janoshik_certificates
        WHERE supplier_website IS NOT NULL AND supplier_website != ''
    """)
    certificates = cur.fetchall()
    
    print(f"📊 Supplier con website nei certificati: {len(certificates)}")
    
    # 2. Crea mapping supplier -> website
    supplier_domains: Dict[str, str] = {}  # supplier_name -> domain
    
    for supplier_name, website in certificates:
        # Normalizza URL
        domain = extract_domain_from_text(website)
        if domain:
            supplier_domains[supplier_name] = domain
    
    print(f"📊 Suppliers con domini estratti: {len(supplier_domains)}")
    print()
    
    # 3. Leggi suppliers esistenti
    cur.execute("SELECT id, name, website FROM suppliers WHERE deleted_at IS NULL")
    existing_suppliers = {row[1]: (row[0], row[2]) for row in cur.fetchall()}
    
    # 4. Analizza operazioni necessarie
    to_update = []  # (supplier_id, supplier_name, old_website, new_website)
    to_add_new = []  # (supplier_name, website) - supplier non esiste
    already_ok = []  # supplier con website già corretto
    
    for supplier_name, new_website in sorted(supplier_domains.items()):
        if supplier_name in existing_suppliers:
            supplier_id, current_website = existing_suppliers[supplier_name]
            
            if not current_website or current_website.strip() == '':
                # Website mancante, va aggiunto
                to_update.append((supplier_id, supplier_name, current_website, new_website))
            elif current_website != new_website:
                # Website diverso, potrebbe essere un aggiornamento
                # (per ora non aggiorniamo se già presente)
                already_ok.append((supplier_name, current_website, new_website))
            else:
                # Website già corretto
                already_ok.append((supplier_name, current_website, None))
        else:
            # Supplier non esiste nella tabella
            to_add_new.append((supplier_name, new_website))
    
    # Report
    print("📋 ANALISI:")
    print("-" * 80)
    print(f"✅ Suppliers con website già presente: {len([s for s in already_ok if s[2] is None])}")
    print(f"🔄 Suppliers da aggiornare (website mancante): {len(to_update)}")
    print(f"➕ Suppliers nuovi (non in tabella): {len(to_add_new)}")
    print()
    
    if to_update:
        print("🔄 WEBSITE DA AGGIUNGERE:")
        print("-" * 80)
        for supplier_id, supplier_name, old_website, new_website in to_update:
            print(f"  {supplier_name}")
            print(f"    Vecchio: {old_website or '(vuoto)'}")
            print(f"    Nuovo:   {new_website}")
        print()
    
    if to_add_new:
        print("⚠️  SUPPLIERS NON IN TABELLA (saltati):")
        print("-" * 80)
        for supplier_name, website in to_add_new[:10]:
            print(f"  {supplier_name} → {website}")
        if len(to_add_new) > 10:
            print(f"  ... e altri {len(to_add_new) - 10} suppliers")
        print()
    
    conflicts = [s for s in already_ok if s[2] is not None]
    if conflicts:
        print("ℹ️  SUPPLIERS CON WEBSITE DIVERSO (non modificati):")
        print("-" * 80)
        for supplier_name, current, extracted in conflicts[:10]:
            print(f"  {supplier_name}")
            print(f"    Corrente:  {current}")
            print(f"    Estratto:  {extracted}")
        if len(conflicts) > 10:
            print(f"  ... e altri {len(conflicts) - 10} suppliers")
        print()
    
    # 5. Applica modifiche se non dry_run
    if not dry_run and to_update:
        print("🔄 Aggiornamento website...")
        for supplier_id, supplier_name, old_website, new_website in to_update:
            cur.execute("""
                UPDATE suppliers
                SET website = ?
                WHERE id = ?
            """, (new_website, supplier_id))
        
        conn.commit()
        print(f"✅ {len(to_update)} website aggiornati con successo!")
        print()
    
    # 6. Riepilogo finale
    print("=" * 80)
    print("RIEPILOGO")
    print("=" * 80)
    print(f"Domini estratti da Janoshik: {len(supplier_domains)}")
    print(f"Website già presenti: {len([s for s in already_ok if s[2] is None])}")
    print(f"Website aggiunti: {len(to_update) if not dry_run else 0}")
    print(f"Conflitti ignorati: {len(conflicts)}")
    print()
    
    if dry_run:
        print("⚠️  DRY RUN: Nessuna modifica applicata al database")
        print("   Per applicare le modifiche, riesegui con --apply")
    else:
        print("✅ MODIFICHE APPLICATE con successo!")
    
    conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Estrae website da certificati Janoshik e aggiorna suppliers"
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
    
    extract_websites_from_janoshik(str(db_path), dry_run=not args.apply)
    return 0


if __name__ == "__main__":
    exit(main())
