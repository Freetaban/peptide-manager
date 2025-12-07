"""
Debug scraper - Ispeziona struttura HTML di janoshik.com/public/
"""

import requests
from bs4 import BeautifulSoup

url = "https://janoshik.com/public/"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

print(f"🌐 Fetching {url}...")
try:
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    
    print(f"✓ Status: {response.status_code}")
    print(f"✓ Content-Type: {response.headers.get('Content-Type')}")
    print(f"✓ Content Length: {len(response.content)} bytes\n")
    
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Salva HTML per ispezione
    with open('janoshik_page.html', 'w', encoding='utf-8') as f:
        f.write(soup.prettify())
    print("✓ HTML salvato in: janoshik_page.html\n")
    
    # Cerca possibili selettori
    print("🔍 Analisi struttura pagina:")
    print(f"   <title>: {soup.title.string if soup.title else 'N/A'}")
    
    # Cerca elementi comuni
    selectors_to_try = [
        'article',
        '.certificate',
        '.cert',
        '[class*="certificate"]',
        '[class*="cert"]',
        'img[src*="certificate"]',
        'img[src*="cert"]',
        'a[href*="certificate"]',
        'a[href*="cert"]',
    ]
    
    for selector in selectors_to_try:
        elements = soup.select(selector)
        if elements:
            print(f"   ✓ {selector}: {len(elements)} elementi")
            if len(elements) > 0:
                print(f"      Primo elemento: {elements[0].name} {elements[0].get('class', [])}")
    
    # Mostra primi 20 link
    print("\n📎 Primi 20 link trovati:")
    links = soup.find_all('a', href=True)[:20]
    for i, link in enumerate(links, 1):
        href = link.get('href')
        text = link.get_text(strip=True)[:50]
        print(f"   {i}. {href} - '{text}'")
    
    # Mostra primi 10 immagini
    print("\n🖼️ Prime 10 immagini trovate:")
    images = soup.find_all('img', src=True)[:10]
    for i, img in enumerate(images, 1):
        src = img.get('src')
        alt = img.get('alt', '')
        print(f"   {i}. {src} - '{alt}'")
    
except requests.RequestException as e:
    print(f"❌ Errore: {e}")
except Exception as e:
    print(f"❌ Errore: {e}")
    import traceback
    traceback.print_exc()
