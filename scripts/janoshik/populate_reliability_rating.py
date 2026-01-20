"""
Popola reliability_rating nella tabella suppliers basandosi su janoshik_quality_score

Converte quality_score (0-100) in rating (1-5):
- 90-100: 5 stelle (eccellente)
- 80-89:  4 stelle (molto buono)
- 70-79:  3 stelle (buono)
- 60-69:  2 stelle (sufficiente)
- 0-59:   1 stella (insufficiente)
"""

import sqlite3
import argparse
from pathlib import Path


def quality_score_to_rating(score: float) -> int:
    """
    Converte quality score (0-100) in rating stelle (1-5).
    
    Args:
        score: Quality score 0-100
        
    Returns:
        Rating 1-5
    """
    if score >= 90:
        return 5
    elif score >= 80:
        return 4
    elif score >= 70:
        return 3
    elif score >= 60:
        return 2
    else:
        return 1


def populate_reliability_rating(db_path: str, dry_run: bool = True):
    """
    Popola reliability_rating basandosi su janoshik_quality_score.
    
    Args:
        db_path: Path al database
        dry_run: Se True, mostra solo cosa farebbe
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    print("=" * 80)
    print("POPOLAMENTO RELIABILITY RATING DA JANOSHIK QUALITY SCORE")
    print("=" * 80)
    print(f"Database: {db_path}")
    print(f"Modalità: {'DRY RUN (solo analisi)' if dry_run else 'MODIFICA EFFETTIVA'}")
    print()
    
    # 2. Leggi suppliers con janoshik_quality_score
    print("📊 Lettura supplier con quality score...")
    
    cur.execute("""
        SELECT id, name, janoshik_quality_score, reliability_rating
        FROM suppliers
        WHERE deleted_at IS NULL
          AND janoshik_quality_score IS NOT NULL
          AND janoshik_quality_score > 0
        ORDER BY janoshik_quality_score DESC
    """)
    
    suppliers = cur.fetchall()
    print(f"   ✓ {len(suppliers)} suppliers con quality score")
    print()
    
    # 3. Calcola rating per ogni supplier
    updates = []  # (supplier_id, name, old_rating, new_rating, score)
    
    for supplier_id, name, current_score, old_rating in suppliers:
        # Converti score in rating
        new_rating = quality_score_to_rating(current_score)
        
        if old_rating != new_rating:
            updates.append((supplier_id, name, old_rating, new_rating, current_score))
    
    # 3. Report
    print("📋 ANALISI:")
    print("-" * 80)
    print(f"Suppliers con certificati: {len(suppliers)}")
    print(f"Rating da aggiornare: {len(updates)}")
    print()
    
    if updates:
        print("🔄 RATING DA AGGIORNARE:")
        print("-" * 80)
        
        # Raggruppa per rating
        by_rating = {}
        for supplier_id, name, old_rating, new_rating, score in updates:
            if new_rating not in by_rating:
                by_rating[new_rating] = []
            by_rating[new_rating].append((name, old_rating, score))
        
        # Mostra per rating
        for rating in sorted(by_rating.keys(), reverse=True):
            rating_stars = "⭐" * rating
            print(f"\n{rating_stars} Rating {rating}:")
            for name, old_rating, score in sorted(by_rating[rating], key=lambda x: x[2], reverse=True)[:10]:
                old_str = f"{old_rating}★" if old_rating else "(vuoto)"
                print(f"  {name[:40]:40} | Score: {score:5.1f} | Old: {old_str}")
            
            if len(by_rating[rating]) > 10:
                print(f"  ... e altri {len(by_rating[rating]) - 10} supplier")
        
        print()
    
    # 4. Applica modifiche se non dry_run
    if not dry_run and updates:
        print("🔄 Aggiornamento rating...")
        for supplier_id, name, old_rating, new_rating, score in updates:
            cur.execute("""
                UPDATE suppliers
                SET reliability_rating = ?
                WHERE id = ?
            """, (new_rating, supplier_id))
        
        conn.commit()
        print(f"✅ {len(updates)} rating aggiornati con successo!")
        print()
    
    # 5. Statistiche finali
    print("=" * 80)
    print("STATISTICHE RATING")
    print("=" * 80)
    
    cur.execute("""
        SELECT 
            reliability_rating,
            COUNT(*) as count,
            AVG(janoshik_quality_score) as avg_score,
            AVG(janoshik_certificates) as avg_certs
        FROM suppliers
        WHERE deleted_at IS NULL 
          AND janoshik_certificates > 0
        GROUP BY reliability_rating
        ORDER BY reliability_rating DESC
    """)
    
    for row in cur.fetchall():
        rating, count, avg_score, avg_certs = row
        if rating is None:
            continue
        stars = "⭐" * rating
        print(f"{stars} Rating {rating}: {count:2d} suppliers | Avg Score: {avg_score:5.1f} | Avg Certs: {avg_certs:5.1f}")
    
    print()
    
    # 6. Riepilogo finale
    print("=" * 80)
    print("RIEPILOGO")
    print("=" * 80)
    print(f"Suppliers analizzati: {len(suppliers)}")
    print(f"Rating aggiornati: {len(updates) if not dry_run else 0}")
    print()
    
    if dry_run:
        print("⚠️  DRY RUN: Nessuna modifica applicata al database")
        print("   Per applicare le modifiche, riesegui con --apply")
    else:
        print("✅ MODIFICHE APPLICATE con successo!")
    
    conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Popola reliability_rating da Janoshik quality score"
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
    
    populate_reliability_rating(str(db_path), dry_run=not args.apply)
    return 0


if __name__ == "__main__":
    exit(main())
