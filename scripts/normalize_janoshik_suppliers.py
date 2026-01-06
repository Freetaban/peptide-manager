"""
Script per normalizzare nomi supplier nel database Janoshik.

Uso:
    python scripts/normalize_janoshik_suppliers.py [--dry-run] [--db-path PATH]
"""

import sys
import argparse
from pathlib import Path

# Aggiungi root al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from peptide_manager.janoshik.supplier_normalizer import SupplierNormalizer
from peptide_manager.janoshik.repositories import JanoshikCertificateRepository


def main():
    parser = argparse.ArgumentParser(description="Normalizza nomi supplier nel database Janoshik")
    parser.add_argument('--dry-run', action='store_true', help="Mostra modifiche senza applicarle")
    parser.add_argument('--db-path', default='data/production/peptide_management.db', help="Path database")
    parser.add_argument('--stats-only', action='store_true', help="Mostra solo statistiche senza modificare")
    
    args = parser.parse_args()
    
    # Connetti al database
    repo = JanoshikCertificateRepository(args.db_path)
    
    print("=" * 80)
    print("NORMALIZZAZIONE NOMI SUPPLIER JANOSHIK")
    print("=" * 80)
    print(f"Database: {args.db_path}")
    print(f"Modalita': {'DRY-RUN (nessuna modifica)' if args.dry_run else 'APPLICAZIONE MODIFICHE'}")
    print()
    
    # Carica tutti i certificati
    print(">> Caricamento certificati...")
    all_certs = repo.get_all_as_dicts()
    print(f"OK Caricati {len(all_certs)} certificati")
    print()
    
    # Estrai supplier names
    raw_names = [cert['supplier_name'] for cert in all_certs if cert.get('supplier_name')]
    
    # Calcola statistiche
    print("STATISTICHE PRE-NORMALIZZAZIONE")
    print("-" * 80)
    stats = SupplierNormalizer.get_normalization_stats(raw_names)
    print(f"Totale nomi: {stats['total']}")
    print(f"Nomi unici (raw): {stats['unique_raw']}")
    print(f"Nomi unici (dopo normalizzazione): {stats['unique_normalized']}")
    print(f"Basati su URL: {stats['url_based']}")
    print(f"Basati su contatti: {stats['contact_based']}")
    print(f"Sconosciuti: {stats['unknown']}")
    print()
    
    # Mostra mappings con consolidamento
    print("MAPPINGS (Raw -> Normalized)")
    print("-" * 80)
    
    # Raggruppa per normalized name
    for normalized_name in sorted(stats['mappings'].keys()):
        variants = stats['mappings'][normalized_name]
        if len(variants) > 1 or args.stats_only:
            print(f"\n{normalized_name}:")
            for variant in sorted(variants):
                count = raw_names.count(variant)
                print(f"  - {variant} ({count}x)")
    
    if args.stats_only:
        print("\nOK Stats-only mode - nessuna modifica applicata")
        return
    
    # Applica normalizzazione
    print("\n" + "=" * 80)
    print("APPLICAZIONE NORMALIZZAZIONE")
    print("=" * 80)
    
    updates = []
    for cert in all_certs:
        raw_name = cert.get('supplier_name')
        if not raw_name:
            continue
        
        normalized_name = SupplierNormalizer.normalize(raw_name)
        website = SupplierNormalizer.extract_website(raw_name)
        
        # Se diverso, aggiungi a updates
        if normalized_name != raw_name or (website and not cert.get('supplier_website')):
            updates.append({
                'id': cert['id'],
                'raw': raw_name,
                'normalized': normalized_name,
                'website': website,
                'current_website': cert.get('supplier_website'),
            })
    
    print(f"Certificati da aggiornare: {len(updates)}")
    
    if not updates:
        print("OK Nessun aggiornamento necessario!")
        return
    
    # Mostra sample
    print("\nEsempio modifiche (prime 10):")
    for update in updates[:10]:
        print(f"  ID {update['id']}: '{update['raw']}' -> '{update['normalized']}'")
        if update['website']:
            print(f"           Website: {update['website']}")
    
    if args.dry_run:
        print(f"\n!! DRY-RUN: {len(updates)} certificati sarebbero aggiornati")
        print("   Riesegui senza --dry-run per applicare le modifiche")
        return
    
    # Chiedi conferma
    print(f"\n!! Stai per aggiornare {len(updates)} certificati nel database")
    response = input("Procedere? (si/no): ")
    
    if response.lower() not in ['si', 'yes', 'y']:
        print("XX Operazione annullata")
        return
    
    # Applica aggiornamenti
    print("\n>> Applicazione aggiornamenti...")
    
    import sqlite3
    conn = sqlite3.connect(args.db_path)
    cursor = conn.cursor()
    
    updated_count = 0
    for update in updates:
        try:
            cursor.execute("""
                UPDATE janoshik_certificates 
                SET supplier_name = ?,
                    supplier_website = COALESCE(?, supplier_website)
                WHERE id = ?
            """, (update['normalized'], update['website'], update['id']))
            updated_count += 1
        except Exception as e:
            print(f"XX Errore aggiornamento ID {update['id']}: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"OK Aggiornati {updated_count}/{len(updates)} certificati!")
    
    # Ricalcola rankings
    print("\n>> Ricalcolo supplier rankings...")
    from peptide_manager.janoshik.manager import JanoshikManager
    
    manager = JanoshikManager(args.db_path)
    rankings_df = manager.recalculate_rankings()
    
    print(f"OK Ricalcolati {len(rankings_df)} supplier rankings")
    print("\nOK COMPLETATO!")


if __name__ == "__main__":
    main()
