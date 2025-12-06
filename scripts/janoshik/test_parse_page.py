"""
Test how many certificates _parse_certificate_page finds on the public page
"""

import requests
from bs4 import BeautifulSoup
import re

url = "https://janoshik.com/public/"
print("=" * 80)
print(f"Testing: {url}")
print("=" * 80)

response = requests.get(url, timeout=10)
soup = BeautifulSoup(response.content, 'html.parser')

# Method from scraper.py
cert_links = soup.select('a[href*="/tests/"]')
print(f"\nFound {len(cert_links)} links with '/tests/' in href")

# Extract task numbers
certificates = []
for link in cert_links:
    href = link.get('href', '')
    match = re.search(r'/tests/(\d+)-', href)
    if match:
        task_number = match.group(1)
        title = link.get_text(strip=True)
        certificates.append({
            'task': task_number,
            'title': title,
            'href': href
        })

print(f"Certificates with task numbers: {len(certificates)}")

# Deduplicate
unique = {}
for cert in certificates:
    if cert['task'] not in unique:
        unique[cert['task']] = cert

print(f"Unique certificates: {len(unique)}")

# Show first 10
print("\nFirst 10:")
for i, cert in enumerate(list(unique.values())[:10], 1):
    print(f"{i:2}. Task {cert['task']}: {cert['title'][:60]}")

# Check pagination
print("\n--- PAGINATION ---")
next_link = soup.select_one('a[rel="next"]')
print(f"rel='next' link: {next_link is not None}")

pagination = soup.select('.pagination a, nav a, [class*="page"] a')
print(f"Pagination links found: {len(pagination)}")
for p in pagination[:5]:
    print(f"  - {p.get('href', 'no href')}: {p.get_text(strip=True)}")
