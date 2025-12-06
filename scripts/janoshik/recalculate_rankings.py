"""
Recalculate supplier rankings from existing certificates in database.
Use this after fixing bugs in scoring logic without re-scraping.
"""

from peptide_manager.janoshik.repositories import JanoshikCertificateRepository, SupplierRankingRepository
from peptide_manager.janoshik.scorer import SupplierScorer
from peptide_manager.janoshik.models import SupplierRanking
import os
from dotenv import load_dotenv

def main():
    load_dotenv()
    
    print("=" * 80)
    print("🔄 RECALCULATING SUPPLIER RANKINGS")
    print("=" * 80)
    print()
    
    # Initialize
    db_path = 'data/development/peptide_management.db'
    cert_repo = JanoshikCertificateRepository(db_path)
    ranking_repo = SupplierRankingRepository(db_path)
    
    # Get certificates from database
    certs = cert_repo.get_all()
    print(f"📊 Found {len(certs)} certificates in database")
    
    if len(certs) == 0:
        print("❌ No certificates found. Run full_janoshik_update.py first.")
        return
    
    # Calculate rankings
    print("\n[SCORING] Calculating supplier rankings...")
    scorer = SupplierScorer()
    rankings_df = scorer.calculate_rankings(certs)
    
    # Save to database
    print("[STORAGE] Saving rankings to database...")
    for _, row in rankings_df.iterrows():
        ranking_obj = SupplierRanking.from_scorer_output(row.to_dict())
        ranking_repo.insert(ranking_obj)
    
    # Export CSV
    output_file = 'data/exports/janoshik_rankings_recalc.csv'
    rankings_df.to_csv(output_file, index=False)
    print(f"\n✅ Rankings exported to: {output_file}")
    
    # Display top 10
    print("\n" + "=" * 80)
    print("🏆 TOP 10 SUPPLIERS")
    print("=" * 80)
    print()
    
    display_cols = [
        'rank_position', 
        'supplier_name', 
        'total_score',
        'total_certificates',
        'avg_purity',
        'testing_completeness_score',
        'batches_fully_tested',
        'total_batches_tracked'
    ]
    
    top10 = rankings_df.head(10)[display_cols]
    for _, row in top10.iterrows():
        print(f"#{int(row['rank_position']):2d}  {row['supplier_name']:30s}  "
              f"Score: {row['total_score']:5.1f}  "
              f"Certs: {int(row['total_certificates']):3d}  "
              f"Purity: {row['avg_purity']:5.1f}%  "
              f"Testing: {row['testing_completeness_score']:5.1f} "
              f"({int(row['batches_fully_tested'])}/{int(row['total_batches_tracked'])} fully tested)")
    
    print("\n✅ Done!")

if __name__ == '__main__':
    main()
