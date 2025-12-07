#!/usr/bin/env python3
"""
Full Janoshik Update - Scrape all available certificates and populate database.

This will:
1. Scrape all public certificates from janoshik.com/public/
2. Extract data using LLM (GPT-4o with new enhanced prompt)
3. Save to database with new test_category fields
4. Calculate supplier rankings with testing_completeness_score
"""

from peptide_manager.janoshik.manager import JanoshikManager
from peptide_manager.janoshik.llm_providers import LLMProvider
import time

def main():
    print("=" * 80)
    print("🚀 FULL JANOSHIK DATABASE UPDATE")
    print("=" * 80)
    print()
    print("This will scrape ALL available certificates from Janoshik.")
    print("Using GPT-4o for extraction (cost: ~$0.01-0.02 per certificate)")
    print()
    
    # Estimate
    estimated_certs = 200  # Rough estimate
    estimated_cost = estimated_certs * 0.0125
    print(f"📊 Estimated: ~{estimated_certs} certificates")
    print(f"💰 Estimated cost: ~${estimated_cost:.2f} USD")
    print()
    
    response = input("Proceed? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("❌ Cancelled.")
        return
    
    print("\n" + "=" * 80)
    print("Starting full update...")
    print("=" * 80 + "\n")
    
    manager = JanoshikManager(
        db_path="data/development/peptide_management.db",
        llm_provider=LLMProvider.GPT4O
    )
    
    def progress(stage, message):
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] [{stage.upper()}] {message}")
    
    try:
        stats = manager.run_full_update(
            max_pages=None,  # All pages
            max_certificates=None,  # All certificates
            progress_callback=progress
        )
        
        print("\n" + "=" * 80)
        print("✅ UPDATE COMPLETED")
        print("=" * 80)
        print(f"📥 Certificates scraped: {stats['certificates_scraped']}")
        print(f"🆕 New certificates: {stats['certificates_new']}")
        print(f"🔬 Certificates extracted: {stats['certificates_extracted']}")
        print(f"📊 Rankings calculated: {stats['rankings_calculated']}")
        print(f"🏆 Top supplier: {stats['top_supplier']}")
        print()
        
        # Show top 10 with testing completeness
        print("=" * 80)
        print("TOP 10 SUPPLIERS (with testing completeness)")
        print("=" * 80)
        
        top_suppliers = manager.get_latest_rankings(limit=10)
        for i, supplier in enumerate(top_suppliers, 1):
            print(f"\n{i}. {supplier.supplier_name}")
            print(f"   Total Score: {supplier.total_score:.2f}")
            print(f"   Purity: {supplier.avg_purity:.2f}%")
            print(f"   Testing Completeness: {supplier.testing_completeness_score:.1f}/100")
            print(f"   Batches Fully Tested: {supplier.batches_fully_tested}/{supplier.total_batches_tracked}")
            print(f"   Avg Tests per Batch: {supplier.avg_tests_per_batch:.1f}")
        
        # Export to CSV
        print("\n" + "=" * 80)
        print("Exporting rankings to CSV...")
        csv_path = manager.export_rankings_to_csv(
            "data/exports/janoshik_full_rankings.csv"
        )
        print(f"✅ Exported to: {csv_path}")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise

if __name__ == "__main__":
    main()
