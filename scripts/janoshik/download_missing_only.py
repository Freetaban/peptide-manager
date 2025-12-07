"""
Download only missing certificates (those on public page but not in DB)
WITHOUT re-analyzing existing ones
"""

import logging
from peptide_manager.janoshik.scraper import JanoshikScraper
from peptide_manager.janoshik.repositories import JanoshikCertificateRepository
from peptide_manager.janoshik.models import JanoshikCertificate
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

def main():
    print("=" * 80)
    print("📥 DOWNLOAD MISSING CERTIFICATES ONLY")
    print("=" * 80)
    
    # Get what we already have
    repo = JanoshikCertificateRepository('data/development/peptide_management.db')
    existing = repo.get_all()
    existing_tasks = {c.task_number for c in existing}
    print(f"\n✓ Already in DB: {len(existing_tasks)} certificates")
    
    # Get all from public page
    url = "https://janoshik.com/public/"
    response = requests.get(url, timeout=10)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    all_certs = []
    for link in soup.select('a[href*="/tests/"]'):
        href = link.get('href', '')
        match = re.search(r'/tests/(\d+)-', href)
        if match:
            task_num = match.group(1)
            if task_num not in existing_tasks:
                from urllib.parse import urljoin
                cert_url = urljoin(url, href)
                all_certs.append({
                    'task_number': task_num,
                    'certificate_url': cert_url,
                    'title': link.get_text(strip=True)
                })
    
    # Deduplicate
    unique_certs = {c['task_number']: c for c in all_certs}
    missing = list(unique_certs.values())
    
    print(f"📊 On public page: {len(existing_tasks) + len(missing)} total")
    print(f"🔍 Missing from DB: {len(missing)} certificates")
    
    if not missing:
        print("\n✅ Database is complete! Nothing to download.")
        return
    
    proceed = input(f"\nDownload {len(missing)} missing certificates? (yes/no): ")
    if proceed.lower() != 'yes':
        print("Cancelled.")
        return
    
    # Initialize scraper
    scraper = JanoshikScraper()
    
    # Download missing ones
    print(f"\n{'=' * 80}")
    print(f"Starting download of {len(missing)} certificates...")
    print(f"{'=' * 80}\n")
    
    downloaded = []
    failed = []
    
    for i, cert in enumerate(missing, 1):
        task_num = cert['task_number']
        
        try:
            # Fetch image URL
            image_url = None
            for attempt in range(2):
                try:
                    image_url = scraper._fetch_certificate_image_url(
                        cert['certificate_url'],
                        task_num
                    )
                    if image_url:
                        break
                except Exception as e:
                    if attempt == 0:
                        logger.warning(f"Task {task_num}: Retry after error: {e}")
                        import time
                        time.sleep(1)
            
            if not image_url:
                logger.warning(f"[{i}/{len(missing)}] Task {task_num}: No image URL found")
                failed.append(task_num)
                continue
            
            # Download image
            download_result = scraper.download_certificate_image(image_url, task_num)
            
            if download_result:
                # Save minimal record with placeholders (no extraction yet)
                import sqlite3
                conn = sqlite3.connect('data/development/peptide_management.db')
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO janoshik_certificates 
                    (task_number, supplier_name, peptide_name, test_date, 
                     image_file, image_hash, scraped_at, processed)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    task_num,
                    'PENDING_EXTRACTION',  # Placeholder
                    'PENDING_EXTRACTION',  # Placeholder
                    '2020-01-01',  # Placeholder date
                    download_result['file_path'],
                    download_result['image_hash'],
                    datetime.now().isoformat(),
                    0  # Not processed yet
                ))
                
                conn.commit()
                conn.close()
                
                downloaded.append(task_num)
                logger.info(f"[{i}/{len(missing)}] ✓ Task {task_num} saved (pending extraction)")
            else:
                logger.warning(f"[{i}/{len(missing)}] Task {task_num}: Download failed")
                failed.append(task_num)
        
        except Exception as e:
            logger.error(f"[{i}/{len(missing)}] Task {task_num}: ERROR - {e}")
            failed.append(task_num)
        
        # Progress every 25
        if i % 25 == 0:
            success_rate = (len(downloaded) / i) * 100
            print(f"\nProgress: {i}/{len(missing)} processed ({len(downloaded)} OK, {len(failed)} failed, {success_rate:.1f}%)\n")
    
    print(f"\n{'=' * 80}")
    print(f"✅ DOWNLOAD COMPLETE")
    print(f"{'=' * 80}")
    print(f"Downloaded: {len(downloaded)}")
    print(f"Failed: {len(failed)}")
    print(f"Total in DB: {len(existing_tasks) + len(downloaded)}")
    
    if failed:
        print(f"\nFailed tasks (first 20): {failed[:20]}")

if __name__ == '__main__':
    main()
