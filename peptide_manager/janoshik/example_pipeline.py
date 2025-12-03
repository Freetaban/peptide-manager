"""
Example: End-to-End Janoshik Ranking Pipeline

Dimostra workflow completo:
1. Scraping certificati
2. Estrazione dati con LLM
3. Calcolo ranking supplier
4. Salvataggio risultati
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from peptide_manager.janoshik import (
    JanoshikScraper,
    JanoshikExtractor,
    SupplierScorer,
    LLMProvider,
    get_llm_extractor
)


def main():
    """Run complete pipeline"""
    
    print("=" * 60)
    print("Janoshik Supplier Ranking - End-to-End Demo")
    print("=" * 60)
    
    # ========================================
    # STEP 1: Scraping
    # ========================================
    print("\n[1/4] Scraping certificates from janoshik.com/public/...")
    
    scraper = JanoshikScraper(
        storage_dir="data/janoshik/images",
        rate_limit_delay=1.0
    )
    
    # Scrape first 2 pages for demo
    certificates = scraper.scrape_and_download_all(
        max_pages=2,
        progress_callback=lambda stage, current, total: 
            print(f"  {stage.capitalize()}: {current}/{total}")
    )
    
    print(f"✓ Found and downloaded {len(certificates)} certificates")
    
    if not certificates:
        print("No certificates found. Exiting.")
        return
    
    # ========================================
    # STEP 2: LLM Extraction
    # ========================================
    print("\n[2/4] Extracting data from certificates with LLM...")
    
    # Use Gemini Flash (free) for demo
    # For production, set API key in environment or pass directly
    llm_provider = get_llm_extractor(
        LLMProvider.GEMINI_FLASH,
        api_key="YOUR_API_KEY_HERE"  # Replace with real key
    )
    
    extractor = JanoshikExtractor(
        llm_provider=llm_provider,
        rate_limit_rpm=10
    )
    
    # Extract data from images
    image_paths = [cert['file_path'] for cert in certificates]
    
    extracted_data = extractor.process_certificates(
        image_paths,
        progress_callback=lambda current, total, success, failed:
            print(f"  Processing: {current}/{total} (✓{success} ✗{failed})")
    )
    
    print(f"✓ Extracted data from {len(extracted_data)} certificates")
    
    # Show sample
    if extracted_data:
        sample = extracted_data[0]
        print(f"\n  Sample certificate:")
        print(f"    Task: {sample.get('task_number')}")
        print(f"    Client: {sample.get('client')}")
        print(f"    Sample: {sample.get('sample')}")
        print(f"    Purity: {sample.get('results', {}).get('Purity', 'N/A')}")
    
    # ========================================
    # STEP 3: Scoring & Ranking
    # ========================================
    print("\n[3/4] Calculating supplier rankings...")
    
    scorer = SupplierScorer()
    rankings = scorer.calculate_rankings(extracted_data)
    
    print(f"✓ Calculated rankings for {len(rankings)} suppliers")
    
    # ========================================
    # STEP 4: Display Results
    # ========================================
    print("\n[4/4] Supplier Rankings:")
    print("=" * 60)
    
    for _, row in rankings.iterrows():
        badge = "🔥" if row['total_score'] >= 80 else "✅" if row['total_score'] >= 60 else "⚠️"
        
        print(f"\n#{row['rank_position']} {badge} {row['supplier_name']}")
        print(f"  Total Score: {row['total_score']:.1f}/100")
        print(f"  Certificates: {row['total_certificates']} total, {row['certs_last_30d']} last 30d")
        print(f"  Purity: {row['avg_purity']:.2f}% avg (min {row['min_purity']:.2f}%, std {row['std_purity']:.2f}%)")
        
        if row['avg_endotoxin_level']:
            print(f"  Endotoxins: {row['avg_endotoxin_level']:.1f} EU/mg avg ({row['certs_with_endotoxin']} certs)")
        
        print(f"  Score Breakdown:")
        print(f"    Volume:      {row['volume_score']:.0f}/100 (25%)")
        print(f"    Quality:     {row['quality_score']:.0f}/100 (35%)")
        print(f"    Consistency: {row['consistency_score']:.0f}/100 (15%)")
        print(f"    Recency:     {row['recency_score']:.0f}/100 (15%)")
        print(f"    Endotoxin:   {row['endotoxin_score']:.0f}/100 (10%)")
    
    # ========================================
    # Optional: Export to CSV
    # ========================================
    output_file = "data/janoshik/rankings/supplier_rankings_demo.csv"
    rankings.to_csv(output_file, index=False)
    print(f"\n✓ Rankings exported to: {output_file}")
    
    print("\n" + "=" * 60)
    print("Demo completed successfully!")
    print("=" * 60)


def quick_test_scraper():
    """Quick test: only scraping (no LLM needed)"""
    print("Quick Test: Scraper Only")
    print("-" * 40)
    
    scraper = JanoshikScraper()
    
    # Check cached certificates
    cached = scraper.get_cached_certificates()
    print(f"Cached certificates: {len(cached)}")
    
    if cached:
        print(f"Sample: {cached[0]}")


def quick_test_scorer():
    """Quick test: scoring with dummy data"""
    print("Quick Test: Scorer Only")
    print("-" * 40)
    
    # Dummy certificate data
    dummy_certs = [
        {
            'client': 'www.supplier-a.com',
            'sample': 'BPC-157 5mg',
            'analysis_conducted': '2025-11-15',
            'results': {'Purity': '99.5%', 'Endotoxins': '<10 EU/mg'}
        },
        {
            'client': 'www.supplier-a.com',
            'sample': 'TB-500 5mg',
            'analysis_conducted': '2025-11-20',
            'results': {'Purity': '99.7%', 'Endotoxins': '8.5 EU/mg'}
        },
        {
            'client': 'www.supplier-b.com',
            'sample': 'Semaglutide 2mg',
            'analysis_conducted': '2025-10-01',
            'results': {'Purity': '97.2%'}
        }
    ]
    
    scorer = SupplierScorer()
    rankings = scorer.calculate_rankings(dummy_certs)
    
    print(f"\nRankings:\n{rankings[['supplier_name', 'total_score', 'rank_position']]}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Janoshik Ranking Demo")
    parser.add_argument('--quick-scraper', action='store_true', help='Test scraper only')
    parser.add_argument('--quick-scorer', action='store_true', help='Test scorer only')
    args = parser.parse_args()
    
    if args.quick_scraper:
        quick_test_scraper()
    elif args.quick_scorer:
        quick_test_scorer()
    else:
        main()
