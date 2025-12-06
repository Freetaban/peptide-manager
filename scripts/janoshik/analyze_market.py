"""
Script di esempio per analisi mercato Janoshik.

Usage:
    python scripts/janoshik/analyze_market.py [--days 30] [--peptide Tirzepatide]
"""

import argparse
from peptide_manager.janoshik.analytics import JanoshikAnalytics
import pandas as pd

pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', 50)


def main():
    parser = argparse.ArgumentParser(description="Analisi mercato Janoshik")
    parser.add_argument('--days', type=int, help='Finestra temporale (giorni)')
    parser.add_argument('--peptide', type=str, help='Peptide specifico da analizzare')
    parser.add_argument('--db', default='data/development/peptide_management.db', help='Path database')
    args = parser.parse_args()
    
    analytics = JanoshikAnalytics(args.db)
    
    print("\n" + "=" * 80)
    print("📊 JANOSHIK MARKET ANALYTICS")
    print("=" * 80)
    
    # Market Overview
    print("\n🌍 MARKET OVERVIEW")
    if args.days:
        print(f"   (Ultimi {args.days} giorni)")
    overview = analytics.get_market_overview(time_window_days=args.days)
    print(f"   Total Certificates: {overview['total_certificates']}")
    print(f"   Unique Vendors: {overview['unique_vendors']}")
    print(f"   Unique Products: {overview['unique_products']}")
    print(f"   Market Avg Purity: {overview['market_avg_purity']:.2f}%")
    print(f"   Best Purity: {overview['best_purity']:.2f}%")
    print(f"   Worst Purity: {overview['worst_purity']:.2f}%")
    
    # Quality Distribution
    print("\n📈 QUALITY DISTRIBUTION")
    quality_dist = analytics.get_quality_distribution()
    for tier, count in quality_dist.items():
        print(f"   {tier}: {count} certificates")
    
    # Hottest Peptides
    print("\n🔥 HOTTEST PEPTIDES")
    if args.days:
        print(f"   (Ultimi {args.days} giorni)")
    hot_peptides = analytics.get_hottest_peptides(
        time_window_days=args.days or 30,
        limit=10
    )
    print(hot_peptides.to_string(index=False))
    
    # Top Vendors
    print("\n🏆 TOP VENDORS BY QUALITY")
    if args.days:
        print(f"   (Ultimi {args.days} giorni)")
    top_vendors = analytics.get_top_vendors(
        time_window_days=args.days,
        limit=15
    )
    print(top_vendors[['supplier_name', 'total_certificates', 'avg_purity', 'days_since_last_test']].to_string(index=False))
    
    # Peptide-specific analysis
    if args.peptide:
        print(f"\n🔬 ANALYSIS FOR: {args.peptide}")
        
        # Best vendor for this peptide
        best = analytics.get_best_vendor_for_peptide(
            peptide_name=args.peptide,
            time_window_days=args.days
        )
        if best:
            print(f"\n   🥇 BEST VENDOR:")
            print(f"      {best['supplier_name']}")
            print(f"      Certificates: {best['certificates']}")
            print(f"      Avg Purity: {best['avg_purity']:.2f}%")
            print(f"      Most Recent: {best['most_recent_test']}")
        else:
            print(f"   ❌ No data found for {args.peptide}")
        
        # All vendors for this peptide
        print(f"\n   📊 ALL VENDORS FOR {args.peptide}:")
        vendors = analytics.get_peptide_vendors(
            peptide_name=args.peptide,
            time_window_days=args.days
        )
        print(vendors[['supplier_name', 'certificates', 'avg_purity', 'last_test']].to_string(index=False))
    
    # Vendor-Peptide Matrix
    print("\n📋 VENDOR-PEPTIDE MATRIX (top products)")
    matrix = analytics.get_vendor_peptide_matrix(time_window_days=args.days)
    if not matrix.empty:
        # Show only top 10 vendors and top 8 peptides
        top_vendors_list = matrix.sum(axis=1).nlargest(10).index
        top_peptides = matrix.sum(axis=0).nlargest(8).index
        print(matrix.loc[top_vendors_list, top_peptides].to_string())
    else:
        print("   No data available")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
