"""
Test fetching image URL from a specific certificate page
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import sys

if len(sys.argv) > 1:
    task_num = sys.argv[1]
else:
    # Default: use a task number that gave 404
    # We need to extract the actual task number from the scraping log
    # Let's try a few from the public page
    task_num = "82282"  # Known good one

cert_url = f"https://janoshik.com/tests/{task_num}"

print("=" * 80)
print(f"Testing certificate page: {cert_url}")
print("=" * 80)

try:
    response = requests.get(cert_url, timeout=10)
    print(f"\nPage status: {response.status_code}")
    
    if response.status_code != 200:
        print(f"ERROR: Page not accessible")
        sys.exit(1)
    
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Method 1: Look for download link
    print("\n--- Method 1: Download link ---")
    download_link = soup.select_one('a[download*="Test Report"]')
    if download_link:
        img_url = download_link.get('href')
        full_url = urljoin(cert_url, img_url) if img_url else None
        print(f"Found: {img_url}")
        print(f"Full URL: {full_url}")
        
        # Test if accessible
        if full_url:
            test_resp = requests.head(full_url, timeout=5)
            print(f"Image status: {test_resp.status_code}")
    else:
        print("No download link found")
    
    # Method 2: Look for img tags
    print("\n--- Method 2: IMG tags ---")
    for img in soup.find_all('img'):
        src = img.get('src', '')
        if './img/' in src and src.endswith('.png'):
            full_url = urljoin(cert_url, src)
            print(f"Found: {src}")
            print(f"Full URL: {full_url}")
            
            # Test
            test_resp = requests.head(full_url, timeout=5)
            print(f"Image status: {test_resp.status_code}")
            break
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
