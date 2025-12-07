#!/usr/bin/env python3
"""
Crea e applica mapping di alias peptidi per consolidare varianti.

Gestisce:
- Typo comuni (Trizepatide -> Tirzepatide)
- Abbreviazioni (Tirz -> Tirzepatide, TB -> TB500)
- Varianti naming (BPC vs BPC-157, GLP-2T vs GLP-2)
- Nomi troncati o ambigui
"""

import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple

# Mapping: alias -> nome canonico
PEPTIDE_ALIASES = {
    # Tirzepatide variants
    "Tirz": "Tirzepatide",
    "Trizepatide": "Tirzepatide",
    "tir": "Tirzepatide",
    
    # TB500 variants
    "TB": "TB500",
    "TB4": "TB500",
    "TB-4": "TB500",
    "Thymosin-Beta-4": "TB500",
    
    # BPC-157 variants
    "BPC": "BPC-157",
    "BPC157": "BPC-157",
    
    # AOD variants
    "A0D": "AOD-9604",
    
    # TR variants (solo abbreviazioni chiare)
    "TR": "Retatrutide",
    
    # PT-141 variants
    "PT141": "PT-141",
    "PT 141": "PT-141",
    "Bremelanotide": "PT-141",
    
    # SNAP variants
    "SNAP": "SNAP-8",
    
    # PNC variants
    "PNC": "PNC-27",
    
    # GLP variants (stessa composizione)
    "GLP-2T": "GLP-2TZ",
}

# NOTE: GLP, GLP-2TZ, GLP-3RT sono prodotti DIVERSI
# Non consolidare senza conferma del significato dei codici


def analyze_aliases(db_path: str) -> List[Tuple[str, int, str]]:
    """
    Analizza il DB per trovare peptidi che dovrebbero essere aliasati.
    
    Returns:
        List of (peptide_name_std, cert_count, suggested_canonical)
    """
    conn = sqlite3.connect(db_path)
    
    query = """
    SELECT 
        peptide_name_std,
        COUNT(*) as cert_count,
        GROUP_CONCAT(DISTINCT product_name) as products
    FROM janoshik_certificates
    WHERE purity_percentage IS NOT NULL
      AND purity_percentage > 0
    GROUP BY peptide_name_std
    HAVING cert_count <= 5  -- Focus su low-frequency
    ORDER BY cert_count ASC, peptide_name_std
    """
    
    cursor = conn.execute(query)
    results = []
    
    for row in cursor.fetchall():
        peptide, count, products = row
        
        # Cerca match in alias mapping
        canonical = PEPTIDE_ALIASES.get(peptide)
        if canonical:
            results.append((peptide, count, canonical))
    
    conn.close()
    return results


def apply_aliases(db_path: str, dry_run: bool = True) -> Dict[str, int]:
    """
    Applica alias mapping al DB aggiornando peptide_name_std.
    
    Args:
        db_path: Path to database
        dry_run: If True, only report changes without applying
        
    Returns:
        Dict with counts per canonical name
    """
    conn = sqlite3.connect(db_path)
    conn.execute("BEGIN TRANSACTION")
    
    stats = {}
    
    try:
        for alias, canonical in PEPTIDE_ALIASES.items():
            # Conta quanti record verranno aggiornati
            cursor = conn.execute(
                "SELECT COUNT(*) FROM janoshik_certificates WHERE peptide_name_std = ?",
                (alias,)
            )
            count = cursor.fetchone()[0]
            
            if count > 0:
                print(f"  {alias} -> {canonical}: {count} certificati")
                stats[canonical] = stats.get(canonical, 0) + count
                
                if not dry_run:
                    conn.execute(
                        """
                        UPDATE janoshik_certificates 
                        SET peptide_name_std = ? 
                        WHERE peptide_name_std = ?
                        """,
                        (canonical, alias)
                    )
        
        if dry_run:
            print("\n[DRY RUN] Nessuna modifica applicata")
            conn.execute("ROLLBACK")
        else:
            conn.execute("COMMIT")
            print(f"\n✅ Applicati {len(stats)} consolidamenti")
    
    except Exception as e:
        conn.execute("ROLLBACK")
        print(f"❌ Errore: {e}")
        raise
    finally:
        conn.close()
    
    return stats


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Gestione alias peptidi")
    parser.add_argument(
        "--db",
        default="data/development/peptide_management.db",
        help="Path to database"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Applica modifiche (default: dry-run)"
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Analizza peptidi candidati per aliasing"
    )
    
    args = parser.parse_args()
    
    if not Path(args.db).exists():
        print(f"❌ Database non trovato: {args.db}")
        return 1
    
    if args.analyze:
        print(f"\n🔍 Analisi peptidi low-frequency in {args.db}...\n")
        candidates = analyze_aliases(args.db)
        
        if candidates:
            print("Peptidi che verrebbero consolidati:\n")
            for peptide, count, canonical in candidates:
                print(f"  {peptide:20} ({count:2} certs) -> {canonical}")
        else:
            print("Nessun peptide trovato nel mapping")
    
    else:
        mode = "APPLICAZIONE" if args.apply else "DRY RUN"
        print(f"\n🔄 {mode} alias mapping su {args.db}...\n")
        
        stats = apply_aliases(args.db, dry_run=not args.apply)
        
        if stats:
            print("\nConsolidamenti per peptide canonico:")
            for canonical, count in sorted(stats.items()):
                print(f"  {canonical}: +{count} certificati")
    
    return 0


if __name__ == "__main__":
    exit(main())
