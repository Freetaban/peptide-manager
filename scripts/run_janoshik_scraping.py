"""
Script per scaricare certificati Janoshik e popolare il database

Usage:
    python run_janoshik_scraping.py [--max-pages N] [--max-certs N]
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from peptide_manager.janoshik.scraper import JanoshikScraper
from peptide_manager.janoshik.repositories.certificate_repository import JanoshikCertificateRepository
from peptide_manager.janoshik.models.janoshik_certificate import JanoshikCertificate


def main():
    parser = argparse.ArgumentParser(description="Scarica certificati Janoshik")
    parser.add_argument("--max-pages", type=int, help="Max pagine da scaricare")
    parser.add_argument("--max-certs", type=int, help="Max certificati da scaricare")
    parser.add_argument("--db", default="data/development/peptide_management.db", help="Path database")
    args = parser.parse_args()
    
    print("=" * 60)
    print("🌐 JANOSHIK CERTIFICATE SCRAPER")
    print("=" * 60)
    print()
    
    # Initialize scraper
    scraper = JanoshikScraper(
        storage_dir="data/janoshik/images",
        rate_limit_delay=0.5
    )
    
    # Initialize repository
    repo = JanoshikCertificateRepository(args.db)
    
    # Progress callback
    def progress(page_num, total_certs):
        print(f"📄 Pagina {page_num} - Certificati raccolti: {total_certs}")
    
    # Scrape certificates
    print(f"🔍 Inizio scraping (max_pages={args.max_pages or 'tutte'}, max_certs={args.max_certs or 'tutti'})")
    print()
    
    certificates_data = scraper.scrape_certificates(
        max_pages=args.max_pages,
        max_certificates=args.max_certs,
        progress_callback=progress
    )
    
    print()
    print(f"✅ Scraping completato: {len(certificates_data)} certificati")
    print()
    
    # Save to database
    print("💾 Salvataggio certificati nel database...")
    saved = 0
    skipped = 0
    
    for cert_data in certificates_data:
        try:
            # Create JanoshikCertificate object
            cert = JanoshikCertificate(
                task_number=cert_data['task_number'],
                image_url=cert_data['image_url'],
                image_hash=cert_data.get('image_hash'),
                local_image_path=cert_data.get('local_image_path'),
                supplier_name=None,  # Will be extracted later
                product_name=None,
                test_date=None,
                purity_percentage=None,
                created_at=datetime.now().isoformat()
            )
            
            repo.insert(cert)
            saved += 1
            
        except Exception as e:
            if "UNIQUE constraint" in str(e):
                skipped += 1
            else:
                print(f"  ⚠️  Errore salvando {cert_data['task_number']}: {e}")
    
    print(f"  ✅ Salvati: {saved}")
    print(f"  ⏭️  Skipped (duplicati): {skipped}")
    print()
    
    # Summary
    print("=" * 60)
    print("📊 RIEPILOGO")
    print("=" * 60)
    print(f"Certificati scaricati: {len(certificates_data)}")
    print(f"Certificati salvati nel DB: {saved}")
    print(f"Immagini PNG: {scraper.storage_dir}")
    print()
    print("⏭️  Prossimo step: Esegui estrazione dati con LLM")
    print("   python scripts/run_janoshik_extraction.py")
    print()


if __name__ == "__main__":
    from datetime import datetime
    main()
