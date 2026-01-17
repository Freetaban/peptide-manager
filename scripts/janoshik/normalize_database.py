"""
Normalize existing Janoshik database entries

Applica normalizzatori per peptidi e supplier a tutti i certificati esistenti
per eliminare duplicati e sinonimi.
"""

import sqlite3
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from peptide_manager.janoshik.supplier_normalizer import SupplierNormalizer
from peptide_manager.janoshik.peptide_normalizer import PeptideNormalizer


def normalize_database(db_path: str, dry_run: bool = True):
    """
    Normalizza peptidi e supplier nel database.
    
    Args:
        db_path: Path al database
        dry_run: Se True, mostra solo cosa verrà modificato senza applicare
    """
    print("=" * 80)
    print("NORMALIZZAZIONE DATABASE JANOSHIK")
    print("=" * 80)
    print(f"Database: {db_path}")
    print(f"Modalità: {'DRY RUN (solo analisi)' if dry_run else 'MODIFICA EFFETTIVA'}")
    print()
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all certificates
    cursor.execute("""
        SELECT 
            id,
            supplier_name,
            peptide_name_std
        FROM janoshik_certificates
        WHERE supplier_name IS NOT NULL
           OR peptide_name_std IS NOT NULL
    """)
    
    certificates = cursor.fetchall()
    total_certs = len(certificates)
    
    print(f"📊 Certificati totali: {total_certs}")
    print()
    
    # Track changes
    supplier_changes = {}  # original → normalized
    peptide_changes = {}   # original → normalized
    supplier_update_count = 0
    peptide_update_count = 0
    
    # Process each certificate
    for cert_id, supplier, peptide in certificates:
        needs_update = False
        
        # Normalize supplier
        if supplier:
            normalized_supplier = SupplierNormalizer.normalize(supplier)
            if normalized_supplier != supplier:
                supplier_changes[supplier] = normalized_supplier
                supplier_update_count += 1
                needs_update = True
        else:
            normalized_supplier = supplier
        
        # Normalize peptide
        if peptide:
            normalized_peptide = PeptideNormalizer.normalize(peptide)
            if normalized_peptide != peptide:
                peptide_changes[peptide] = normalized_peptide
                peptide_update_count += 1
                needs_update = True
        else:
            normalized_peptide = peptide
        
        # Apply update
        if needs_update and not dry_run:
            cursor.execute("""
                UPDATE janoshik_certificates
                SET supplier_name = ?,
                    peptide_name_std = ?
                WHERE id = ?
            """, (normalized_supplier, normalized_peptide, cert_id))
    
    # Show supplier changes
    if supplier_changes:
        print("🏪 MODIFICHE SUPPLIER:")
        print("-" * 80)
        unique_supplier_mappings = {}
        for original, normalized in supplier_changes.items():
            if original != normalized:
                if (original, normalized) not in unique_supplier_mappings:
                    unique_supplier_mappings[(original, normalized)] = 0
                unique_supplier_mappings[(original, normalized)] += 1
        
        for (original, normalized), count in sorted(unique_supplier_mappings.items(), key=lambda x: x[1], reverse=True):
            print(f"  '{original}' → '{normalized}' ({count} certificati)")
        print()
    else:
        print("✅ Nessuna modifica necessaria per i supplier")
        print()
    
    # Show peptide changes
    if peptide_changes:
        print("💊 MODIFICHE PEPTIDI:")
        print("-" * 80)
        unique_peptide_mappings = {}
        for original, normalized in peptide_changes.items():
            if original != normalized:
                if (original, normalized) not in unique_peptide_mappings:
                    unique_peptide_mappings[(original, normalized)] = 0
                unique_peptide_mappings[(original, normalized)] += 1
        
        for (original, normalized), count in sorted(unique_peptide_mappings.items(), key=lambda x: x[1], reverse=True):
            print(f"  '{original}' → '{normalized}' ({count} certificati)")
        print()
    else:
        print("✅ Nessuna modifica necessaria per i peptidi")
        print()
    
    # Summary
    print("=" * 80)
    print("RIEPILOGO")
    print("=" * 80)
    print(f"Certificati analizzati: {total_certs}")
    print(f"Supplier da modificare: {supplier_update_count}")
    print(f"Peptidi da modificare: {peptide_update_count}")
    print(f"Totale modifiche: {supplier_update_count + peptide_update_count}")
    print()
    
    if dry_run:
        print("⚠️  DRY RUN: Nessuna modifica applicata al database")
        print("   Per applicare le modifiche, riesegui con --apply")
    else:
        conn.commit()
        print("✅ MODIFICHE APPLICATE con successo!")
        
        # Verifica duplicati rimasti
        print()
        print("🔍 Verifica duplicati rimanenti...")
        
        # Check supplier duplicates
        cursor.execute("""
            SELECT supplier_name, COUNT(*) as count
            FROM janoshik_certificates
            WHERE supplier_name IS NOT NULL
            GROUP BY LOWER(TRIM(supplier_name))
            HAVING COUNT(*) > 1
            ORDER BY count DESC
            LIMIT 10
        """)
        
        supplier_dupes = cursor.fetchall()
        if supplier_dupes:
            print(f"  ⚠️  {len(supplier_dupes)} gruppi di supplier con varianti case/whitespace:")
            for supplier, count in supplier_dupes[:5]:
                print(f"     '{supplier}' ({count} certificati)")
        else:
            print("  ✅ Nessun duplicato supplier rilevato")
        
        # Check peptide duplicates
        cursor.execute("""
            SELECT peptide_name_std, COUNT(*) as count
            FROM janoshik_certificates
            WHERE peptide_name_std IS NOT NULL
            GROUP BY LOWER(TRIM(peptide_name_std))
            HAVING COUNT(*) > 1
            ORDER BY count DESC
            LIMIT 10
        """)
        
        peptide_dupes = cursor.fetchall()
        if peptide_dupes:
            print(f"  ⚠️  {len(peptide_dupes)} gruppi di peptidi con varianti case/whitespace:")
            for peptide, count in peptide_dupes[:5]:
                print(f"     '{peptide}' ({count} certificati)")
        else:
            print("  ✅ Nessun duplicato peptide rilevato")
    
    conn.close()
    print()


def main():
    import argparse
    from scripts.environment import get_environment
    
    parser = argparse.ArgumentParser(description="Normalizza database Janoshik")
    parser.add_argument('--apply', action='store_true', 
                       help='Applica modifiche (default: dry-run)')
    parser.add_argument('--db', type=str, 
                       help='Path database (default: usa environment)')
    
    args = parser.parse_args()
    
    # Determine database path
    if args.db:
        db_path = args.db
    else:
        env = get_environment()
        db_path = env.db_path
    
    # Check database exists
    if not Path(db_path).exists():
        print(f"❌ Database non trovato: {db_path}")
        return 1
    
    # Run normalization
    try:
        normalize_database(db_path, dry_run=not args.apply)
        return 0
    except Exception as e:
        print(f"❌ ERRORE: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
