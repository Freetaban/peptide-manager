"""
Janoshik Web Scraper

Scraping certificati pubblici da https://janoshik.com/public/
"""

import hashlib
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Callable
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from PIL import Image


logger = logging.getLogger(__name__)


class JanoshikScraper:
    """Web scraper per certificati Janoshik pubblici"""
    
    BASE_URL = "https://public.janoshik.com/"
    DEFAULT_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    def __init__(
        self,
        storage_dir: str = "data/janoshik/images",
        cache_dir: str = "data/janoshik/cache",
        rate_limit_delay: float = 0.5,
        base_url: Optional[str] = None
    ):
        """
        Inizializza scraper.
        
        Args:
            storage_dir: Directory per salvataggio immagini PNG certificati
            cache_dir: Directory per cache dati
            rate_limit_delay: Delay tra richieste (secondi)
            base_url: URL base personalizzato (opzionale, default: BASE_URL)
        """
        self.storage_dir = Path(storage_dir)
        self.cache_dir = Path(cache_dir)
        self.rate_limit_delay = rate_limit_delay
        self.base_url = base_url if base_url else self.BASE_URL
        
        # Crea directory se non esistono
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.session = requests.Session()
        self.session.headers.update(self.DEFAULT_HEADERS)
        
        self._last_request_time = 0
    
    def scrape_certificates(
        self,
        max_pages: Optional[int] = None,
        max_certificates: Optional[int] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[Dict]:
        """
        Scrape certificati da janoshik.com/public/.
        
        Args:
            max_pages: Numero massimo pagine da scaricare (None = tutte)
            max_certificates: Numero massimo certificati da raccogliere (None = tutti)
            progress_callback: Callback(page_num, total_certs) per progress
            
        Returns:
            Lista dict con metadata certificati
        """
        logger.info("Starting Janoshik scraping...")
        certificates = []
        page = 1
        
        while True:
            if max_pages and page > max_pages:
                break
            
            if max_certificates and len(certificates) >= max_certificates:
                logger.info(f"Reached max_certificates limit: {max_certificates}")
                break
            
            logger.info(f"Scraping page {page}...")
            page_url = self.base_url if page == 1 else f"{self.base_url}?page={page}"
            
            try:
                # Rate limiting
                self._wait_for_rate_limit()
                
                # Fetch page
                response = self.session.get(page_url, timeout=30)
                response.raise_for_status()
                
                # Parse HTML
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Trova certificati sulla pagina
                page_certs = self._parse_certificate_page(soup)
                
                if not page_certs:
                    logger.info(f"No certificates found on page {page}, stopping.")
                    break
                
                # Limita se necessario
                if max_certificates:
                    remaining = max_certificates - len(certificates)
                    if remaining <= 0:
                        break
                    page_certs = page_certs[:remaining]
                
                certificates.extend(page_certs)
                
                if progress_callback:
                    progress_callback(page, len(certificates))
                
                # Check se c'è prossima pagina
                if not self._has_next_page(soup):
                    break
                
                page += 1
                
            except requests.RequestException as e:
                logger.error(f"Error scraping page {page}: {e}")
                break
        
        logger.info(f"Scraping completed: {len(certificates)} certificates found")
        return certificates
    
    def _parse_certificate_page(self, soup: BeautifulSoup) -> List[Dict]:
        """
        Parse pagina certificati e estrae metadata.
        
        Args:
            soup: BeautifulSoup object della pagina
            
        Returns:
            Lista certificati trovati
        """
        certificates = []
        
        # Cerca link a certificati nel formato /tests/{id}-{name}
        cert_links = soup.select('a[href*="/tests/"]')
        
        for link in cert_links:
            try:
                href = link.get('href', '')
                if not href or '/tests/' not in href:
                    continue
                
                cert_data = self._extract_certificate_metadata(link)
                if cert_data:
                    certificates.append(cert_data)
            except Exception as e:
                logger.warning(f"Failed to parse certificate link: {e}")
                continue
        
        return certificates
    
    def _extract_certificate_metadata(self, element) -> Optional[Dict]:
        """
        Estrae metadata da link certificato.
        
        Args:
            element: BeautifulSoup <a> element
            
        Returns:
            Dict con metadata o None
        """
        href = element.get('href', '')
        if not href:
            return None
        
        # Assicura URL completo
        if not href.startswith('http'):
            href = urljoin(self.base_url, href)
        
        # Estrai task number da URL: /tests/82282-Name → 82282
        import re
        match = re.search(r'/tests/(\d+)-', href)
        if not match:
            return None
        
        task_number = match.group(1)
        
        # Estrai titolo
        title = element.get_text(strip=True)
        
        # Metadata
        metadata = {
            'certificate_url': href,
            'task_number': task_number,
            'title': title,
            'scraped_at': datetime.now().isoformat(),
        }
        
        return metadata
    
    def _extract_task_number_from_url(self, url: str) -> Optional[str]:
        """Estrae task number da URL certificato"""
        # Pattern comuni: /certificates/12345.jpg, /cert/12345, etc.
        import re
        match = re.search(r'/certificates?/(\d+)', url)
        if match:
            return match.group(1)
        
        # Fallback: nome file senza estensione
        filename = url.split('/')[-1].split('.')[0]
        if filename.isdigit():
            return filename
        
        return None
    
    def download_certificate_image(
        self,
        image_url: str,
        task_number: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Download immagine certificato.
        
        Args:
            image_url: URL immagine
            task_number: Task number certificato (per naming)
            
        Returns:
            Dict con file_path, image_hash, file_size o None
        """
        try:
            # Rate limiting
            self._wait_for_rate_limit()
            
            # Download
            response = self.session.get(image_url, timeout=30)
            response.raise_for_status()
            
            # Hash immagine (SHA256)
            image_data = response.content
            image_hash = self._hash_image_data(image_data)
            
            # Check se già esiste (deduplicazione)
            existing_file = self._find_existing_by_hash(image_hash)
            if existing_file:
                logger.info(f"Image already exists: {existing_file}")
                return {
                    'file_path': str(existing_file),
                    'image_hash': image_hash,
                    'file_size': existing_file.stat().st_size,
                    'already_exists': True
                }
            
            # Salva file
            if not task_number:
                task_number = self._extract_task_number_from_url(image_url) or 'unknown'
            
            filename = f"{task_number}_{image_hash[:8]}.png"
            file_path = self.storage_dir / filename
            
            with open(file_path, 'wb') as f:
                f.write(image_data)
            
            # Verifica sia immagine valida
            try:
                img = Image.open(file_path)
                img.verify()
            except Exception as e:
                logger.error(f"Invalid image file: {e}")
                file_path.unlink()  # Elimina file corrotto
                return None
            
            logger.info(f"Downloaded certificate: {filename}")
            
            return {
                'file_path': str(file_path),
                'image_hash': image_hash,
                'file_size': file_path.stat().st_size,
                'already_exists': False
            }
            
        except requests.RequestException as e:
            logger.error(f"Failed to download {image_url}: {e}")
            return None
    
    def _hash_image_data(self, data: bytes) -> str:
        """Calcola SHA256 hash di immagine"""
        return hashlib.sha256(data).hexdigest()
    
    def _find_existing_by_hash(self, image_hash: str) -> Optional[Path]:
        """Cerca file esistente con stesso hash"""
        # Cerca file con hash nel nome
        for file_path in self.storage_dir.glob(f"*{image_hash[:8]}*"):
            return file_path
        return None
    
    def _has_next_page(self, soup: BeautifulSoup) -> bool:
        """Controlla se esiste prossima pagina"""
        # Cerca link pagination
        next_link = soup.select_one('a.next, a[rel="next"], .pagination .next')
        return next_link is not None
    
    def _wait_for_rate_limit(self):
        """Rate limiting tra richieste"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self._last_request_time = time.time()
    
    def scrape_and_download_all(
        self,
        max_pages: Optional[int] = None,
        max_certificates: Optional[int] = None,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> List[Dict]:
        """
        Scrape e download completo: trova certificati e scarica immagini.
        
        Args:
            max_pages: Numero massimo pagine
            max_certificates: Numero massimo certificati (None = tutti)
            progress_callback: Callback(stage, current, total)
                stage: 'scraping', 'fetching', o 'downloading'
            
        Returns:
            Lista certificati con file_path e image_hash
        """
        # Stage 1: Scraping lista certificati
        def scrape_progress(page, total):
            if progress_callback:
                progress_callback('scraping', page, total)
        
        certificates = self.scrape_certificates(max_pages, max_certificates, scrape_progress)
        
        if not certificates:
            logger.warning("No certificates found")
            return []
        
        # Stage 2: Visita pagina certificato e estrai immagine
        logger.info(f"Fetching certificate images from {len(certificates)} pages...")
        certs_with_images = []
        failed_fetches = []
        
        for i, cert in enumerate(certificates, 1):
            if progress_callback:
                progress_callback('fetching', i, len(certificates))
            
            # Visita pagina certificato ed estrai URL PNG (with retry)
            image_url = None
            for attempt in range(3):  # 3 attempts
                try:
                    image_url = self._fetch_certificate_image_url(
                        cert['certificate_url'],
                        cert['task_number']
                    )
                    if image_url:
                        break
                    if attempt == 0:
                        break  # No image found, don't retry
                except Exception as e:
                    if attempt < 2:
                        logger.warning(f"Task {cert['task_number']}: Attempt {attempt+1} failed, retrying...")
                        time.sleep(1)
                    else:
                        logger.error(f"Task {cert['task_number']}: All attempts failed")
            
            if image_url:
                cert['image_url'] = image_url
                certs_with_images.append(cert)
            else:
                failed_fetches.append(cert['task_number'])
            
            # Progress logging
            if i % 50 == 0:
                success_rate = (len(certs_with_images) / i) * 100
                logger.info(f"Progress: {i}/{len(certificates)} ({len(certs_with_images)} OK, {len(failed_fetches)} failed, {success_rate:.1f}%)")
        
        if not certs_with_images:
            logger.error(f"No certificate images found! Failed: {len(failed_fetches)}")
            return []
        
        logger.info(f"Fetched {len(certs_with_images)} URLs ({len(failed_fetches)} failed)")
        
        # Stage 3: Download immagini
        logger.info(f"Downloading {len(certs_with_images)} certificate images...")
        downloaded = []
        
        for i, cert in enumerate(certs_with_images, 1):
            if progress_callback:
                progress_callback('downloading', i, len(certs_with_images))
            
            download_result = self.download_certificate_image(
                cert['image_url'],
                cert.get('task_number')
            )
            
            if download_result:
                cert.update(download_result)
                downloaded.append(cert)
            
            # Progress logging every 10 certificates
            if i % 10 == 0:
                logger.info(f"Progress: {i}/{len(certs_with_images)} processed ({len(downloaded)} downloaded)")
        
        logger.info(f"Download completed: {len(downloaded)} certificates")
        return downloaded
    
    def _fetch_certificate_image_url(self, certificate_url: str, task_number: str) -> Optional[str]:
        """
        Visita pagina certificato ed estrae URL immagine PNG del certificato.
        
        Args:
            certificate_url: URL pagina certificato
            task_number: Task number (non usato, mantenuto per compatibilità)
            
        Returns:
            URL immagine certificato PNG o None
        """
        try:
            self._wait_for_rate_limit()
            response = self.session.get(certificate_url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Cerca link download PNG certificato: <a download="Test Report #82282" href="./img/XXX.png">
            download_link = soup.select_one('a[download*="Test Report"]')
            if download_link:
                img_url = download_link.get('href')
                if img_url:
                    # URL relativo: ./img/XXX.png
                    if not img_url.startswith('http'):
                        img_url = urljoin(certificate_url, img_url)
                    logger.info(f"Found certificate PNG: {img_url}")
                    return img_url
            
            # Fallback: cerca img con src="./img/*.png" (evita foto prodotto jas.janoshik.com/images/)
            for img in soup.find_all('img'):
                src = img.get('src', '')
                # Skip foto prodotto (URL assoluto jas.janoshik.com)
                if 'jas.janoshik.com/images/' in src:
                    continue
                # Skip logo/icon
                if any(x in src.lower() for x in ['logo', 'icon', 'avatar']):
                    continue
                # Preferisci ./img/*.png
                if './img/' in src and src.endswith('.png'):
                    if not src.startswith('http'):
                        src = urljoin(certificate_url, src)
                    logger.info(f"Found certificate PNG (fallback): {src}")
                    return src
            
            logger.debug(f"Task {task_number}: No PNG in {certificate_url}")
            return None
            
        except Exception as e:
            logger.warning(f"Task {task_number}: Error fetching {certificate_url}: {e}")
            raise  # Re-raise for retry logic
    
    def get_cached_certificates(self) -> List[str]:
        """
        Ritorna lista file certificati già scaricati.
        
        Returns:
            Lista file paths
        """
        return [str(f) for f in self.storage_dir.glob("*.png")]
