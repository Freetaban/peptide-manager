"""
Janoshik Manager - Usage Example

Esempio semplificato usando JanoshikManager per workflow completo.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from peptide_manager.janoshik import JanoshikManager, LLMProvider


def main():
    """Run full Janoshik update using Manager"""
    
    print("=" * 70)
    print("Janoshik Supplier Ranking - Manager Demo")
    print("=" * 70)
    
    # ========================================
    # Initialize Manager
    # ========================================
    print("\n[Setup] Initializing Janoshik Manager...")
    
    manager = JanoshikManager(
        db_path="data/production/peptide_management.db",
        llm_provider=LLMProvider.GEMINI_FLASH,  # Free provider
        llm_api_key="YOUR_API_KEY_HERE"  # Replace with real key or set in env
    )
    
    print("✓ Manager initialized")
    
    # ========================================
    # Show Current Statistics
    # ========================================
    print("\n[Statistics] Current database state:")
    stats = manager.get_statistics()
    print(f"  Total certificates: {stats['total_certificates']}")
    print(f"  Unique suppliers: {stats['unique_suppliers']}")
    print(f"  Ranking calculations: {stats['calculations_performed']}")
    
    # ========================================
    # Run Full Update
    # ========================================
    print("\n[Update] Running full update (scraping + extraction + scoring)...")
    print("  This may take several minutes...\n")
    
    def progress_callback(stage: str, message: str):
        print(f"  [{stage.upper()}] {message}")
    
    try:
        result = manager.run_full_update(
            max_pages=2,  # Limit to 2 pages for demo
            progress_callback=progress_callback
        )
        
        print("\n✓ Update completed successfully!")
        print(f"\n  Results:")
        print(f"    Certificates scraped: {result['certificates_scraped']}")
        print(f"    New certificates: {result['certificates_new']}")
        print(f"    Data extracted: {result['certificates_extracted']}")
        print(f"    Rankings calculated: {result['rankings_calculated']}")
        if result['top_supplier']:
            print(f"    🔥 Top supplier: {result['top_supplier']}")
    
    except Exception as e:
        print(f"\n✗ Update failed: {e}")
        return
    
    # ========================================
    # Display Latest Rankings
    # ========================================
    print("\n[Rankings] Top 10 Suppliers:")
    print("=" * 70)
    
    top_suppliers = manager.get_latest_rankings(top_n=10)
    
    for ranking in top_suppliers:
        print(f"\n#{ranking.rank_position} {ranking.get_quality_badge()} {ranking.supplier_name}")
        print(f"  Score: {ranking.total_score:.1f}/100 ({ranking.get_quality_label()})")
        print(f"  Certificates: {ranking.total_certificates} total, {ranking.certs_last_30d} last 30d")
        print(f"  Purity: {ranking.avg_purity:.2f}% avg (±{ranking.std_purity:.2f}%)")
        
        if ranking.avg_endotoxin_level:
            print(f"  Endotoxins: {ranking.avg_endotoxin_level:.1f} EU/mg")
        
        print(f"  Component Scores:")
        print(f"    Volume: {ranking.volume_score:.0f} | Quality: {ranking.quality_score:.0f} | "
              f"Consistency: {ranking.consistency_score:.0f} | Recency: {ranking.recency_score:.0f} | "
              f"Endotoxin: {ranking.endotoxin_score:.0f}")
    
    # ========================================
    # Export Rankings
    # ========================================
    print("\n[Export] Exporting rankings to CSV...")
    
    try:
        output_file = manager.export_rankings_to_csv(
            "data/janoshik/rankings/latest_rankings.csv"
        )
        print(f"✓ Rankings exported to: {output_file}")
    except ValueError as e:
        print(f"✗ Export failed: {e}")
    
    # ========================================
    # Cleanup Old Data
    # ========================================
    print("\n[Cleanup] Cleaning up old ranking calculations...")
    deleted = manager.cleanup_old_rankings(keep_last_n=10)
    print(f"✓ Deleted {deleted} old ranking records")
    
    print("\n" + "=" * 70)
    print("Demo completed!")
    print("=" * 70)


def show_supplier_detail(supplier_name: str):
    """Show detailed info for specific supplier"""
    print(f"\nSupplier Detail: {supplier_name}")
    print("-" * 70)
    
    manager = JanoshikManager(db_path="data/production/peptide_management.db")
    
    # Get certificates
    certificates = manager.get_supplier_certificates(supplier_name)
    print(f"\nCertificates: {len(certificates)}")
    
    if certificates:
        print("\nRecent certificates:")
        for cert in certificates[:5]:
            print(f"  - {cert.task_number}: {cert.peptide_name} ({cert.purity_percentage}%)")
    
    # Get trend
    trend = manager.get_supplier_trend(supplier_name)
    print(f"\nScore Trend: {len(trend)} data points")
    
    if trend:
        print("\nRecent scores:")
        for point in trend[-5:]:
            print(f"  {point['calculated_at']}: {point['total_score']:.1f} (rank #{point['rank_position']})")


def recalculate_only():
    """Recalculate rankings from existing certificates (no scraping)"""
    print("Recalculating rankings from existing data...")
    
    manager = JanoshikManager(db_path="data/production/peptide_management.db")
    
    rankings_df = manager.recalculate_rankings()
    
    print(f"✓ Calculated rankings for {len(rankings_df)} suppliers")
    print("\nTop 5:")
    print(rankings_df[['supplier_name', 'total_score', 'rank_position']].head())


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Janoshik Manager Demo")
    parser.add_argument('--supplier', type=str, help='Show detail for specific supplier')
    parser.add_argument('--recalculate', action='store_true', help='Recalculate rankings only')
    args = parser.parse_args()
    
    if args.supplier:
        show_supplier_detail(args.supplier)
    elif args.recalculate:
        recalculate_only()
    else:
        main()
