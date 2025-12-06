"""
Debug script to understand Janoshik certificate URL structure
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Prendi una pagina certificato di esempio
test_url = "https://janoshik.com/tests/82282-Peptide-Name"

print("=" * 80)
print("JANOSHIK URL STRUCTURE DEBUG")
print("=" * 80)
print(f"\nTesting URL: {test_url}\n")

try:
    response = requests.get(test_url, timeout=10)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Cerca download link
        print("\n--- DOWNLOAD LINKS ---")
        download_links = soup.select('a[download]')
        for link in download_links:
            href = link.get('href')
            download_attr = link.get('download')
            full_url = urljoin(test_url, href) if href else None
            print(f"Download: {download_attr}")
            print(f"  href: {href}")
            print(f"  full URL: {full_url}")
        
        # Cerca tutte le immagini
        print("\n--- ALL IMAGES ---")
        images = soup.find_all('img')
        for i, img in enumerate(images, 1):
            src = img.get('src')
            alt = img.get('alt', '')
            full_url = urljoin(test_url, src) if src else None
            print(f"{i}. src: {src}")
            print(f"   alt: {alt}")
            print(f"   full: {full_url}")
            
            # Test se l'URL funziona
            if full_url and full_url.endswith('.png'):
                try:
                    test_resp = requests.head(full_url, timeout=5)
                    print(f"   → Test: {test_resp.status_code}")
                except Exception as e:
                    print(f"   → Test failed: {e}")
        
        # Cerca pattern ./img/
        print("\n--- PATTERN SEARCH ---")
        html_text = response.text
        import re
        img_patterns = re.findall(r'["\'](\./img/[A-Z0-9]+\.png)["\']', html_text)
        print(f"Found {len(img_patterns)} './img/*.png' patterns:")
        for pattern in img_patterns[:5]:  # Prime 5
            full_url = urljoin(test_url, pattern)
            print(f"  {pattern} → {full_url}")
            
            # Test
            try:
                test_resp = requests.head(full_url, timeout=5)
                print(f"    Status: {test_resp.status_code}")
            except Exception as e:
                print(f"    Error: {e}")
                
except Exception as e:
    print(f"ERROR: {e}")

print("\n" + "=" * 80)
