"""
Count total certificates available on Janoshik public page
"""

import requests
from bs4 import BeautifulSoup
import re

BASE_URL = "https://janoshik.com/public/"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

print("=" * 80)
print("JANOSHIK CERTIFICATE COUNT")
print("=" * 80)

total_certs = []
page = 1
max_pages = 20  # Safety limit

while page <= max_pages:
    url = BASE_URL if page == 1 else f"{BASE_URL}?page={page}"
    print(f"\nPage {page}: {url}")
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"  Status {response.status_code}, stopping")
            break
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Trova link a certificati
        cert_links = soup.select('a[href*="/tests/"]')
        
        page_certs = []
        for link in cert_links:
            href = link.get('href', '')
            # Pattern: /tests/12345-Name
            match = re.search(r'/tests/(\d+)-', href)
            if match:
                task_num = match.group(1)
                title = link.get_text(strip=True)
                page_certs.append({
                    'task': task_num,
                    'title': title,
                    'href': href
                })
        
        # Deduplica per task number
        unique_tasks = {c['task']: c for c in page_certs}
        page_count = len(unique_tasks)
        
        print(f"  Found: {page_count} unique certificates")
        
        if page_count == 0:
            print("  No certificates, stopping")
            break
        
        total_certs.extend(unique_tasks.values())
        
        # Check pagination
        next_link = soup.select_one('a[rel="next"]')
        if not next_link:
            print("  No next page link, stopping")
            break
        
        page += 1
        
    except Exception as e:
        print(f"  ERROR: {e}")
        break

print("\n" + "=" * 80)
print(f"TOTAL: {len(total_certs)} unique certificates found across {page-1} pages")
print("=" * 80)

# Show first 5 and last 5
print("\nFirst 5:")
for cert in total_certs[:5]:
    print(f"  {cert['task']}: {cert['title'][:50]}")

print("\nLast 5:")
for cert in total_certs[-5:]:
    print(f"  {cert['task']}: {cert['title'][:50]}")
