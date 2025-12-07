"""
Find certificates that are on the public page but NOT in our database
Then test if they're actually accessible
"""

import requests
from bs4 import BeautifulSoup
import re
from peptide_manager.janoshik.repositories import JanoshikCertificateRepository

print("=" * 80)
print("FINDING MISSING CERTIFICATES")
print("=" * 80)

# Get what we have in DB
repo = JanoshikCertificateRepository('data/development/peptide_management.db')
db_certs = repo.get_all()
db_tasks = {c.task_number for c in db_certs}
print(f"\nIn database: {len(db_tasks)} certificates")

# Get what's on the public page
url = "https://janoshik.com/public/"
response = requests.get(url, timeout=10)
soup = BeautifulSoup(response.content, 'html.parser')

public_tasks = set()
cert_links = soup.select('a[href*="/tests/"]')
for link in cert_links:
    href = link.get('href', '')
    match = re.search(r'/tests/(\d+)-', href)
    if match:
        public_tasks.add(match.group(1))

print(f"On public page: {len(public_tasks)} certificates")

# Find missing
missing = public_tasks - db_tasks
print(f"\nMissing from DB: {len(missing)} certificates")

# Test first 5 missing ones
print("\n" + "=" * 80)
print("TESTING FIRST 5 MISSING CERTIFICATES")
print("=" * 80)

for i, task_num in enumerate(sorted(missing)[:5], 1):
    cert_url = f"https://janoshik.com/tests/{task_num}"
    print(f"\n{i}. Task #{task_num}")
    print(f"   URL: {cert_url}")
    
    try:
        # Try to fetch the page
        resp = requests.get(cert_url, timeout=10)
        print(f"   Page status: {resp.status_code}")
        
        if resp.status_code == 200:
            # Try to find image URL
            page_soup = BeautifulSoup(resp.content, 'html.parser')
            download_link = page_soup.select_one('a[download*="Test Report"]')
            
            if download_link:
                img_href = download_link.get('href')
                if img_href:
                    from urllib.parse import urljoin
                    img_url = urljoin(cert_url, img_href)
                    print(f"   Image URL: {img_url}")
                    
                    # Test image
                    img_resp = requests.head(img_url, timeout=5)
                    print(f"   Image status: {img_resp.status_code}")
                    
                    if img_resp.status_code != 200:
                        print(f"   ❌ IMAGE NOT ACCESSIBLE")
                    else:
                        print(f"   ✅ CERTIFICATE IS FULLY ACCESSIBLE")
            else:
                print(f"   ⚠️  No download link found")
        else:
            print(f"   ❌ PAGE NOT ACCESSIBLE")
            
    except Exception as e:
        print(f"   ❌ ERROR: {e}")

print("\n" + "=" * 80)
