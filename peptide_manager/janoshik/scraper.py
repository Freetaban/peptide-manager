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
    
    BASE_URL = "https://janoshik.com/public/"
    DEFAULT_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    def __init__(
        self,
        storage_dir: str = "data/janoshik/images",
        cache_dir: str = "data/janoshik/cache",
        rate_limit_delay: float = 1.0
    ):
        """
        Inizializza scraper.
        
        Args:
            storage_dir: Directory per salvataggio immagini
            cache_dir: Directory per cache dati
            rate_limit_delay: Delay tra richieste (secondi)
        """
        self.storage_dir = Path(storage_dir)
        self.cache_dir = Path(cache_dir)
        self.rate_limit_delay = rate_limit_delay
        
        # Crea directory se non esistono
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.session = requests.Session()
        self.session.headers.update(self.DEFAULT_HEADERS)
        
        self._last_request_time = 0
    
    def scrape_certificates(
        self,
        max_pages: Optional[int] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[Dict]:
        """
        Scrape certificati da janoshik.com/public/.
        
        Args:
            max_pages: Numero massimo pagine da scaricare (None = tutte)
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
            
            logger.info(f"Scraping page {page}...")
            page_url = self.BASE_URL if page == 1 else f"{self.BASE_URL}?page={page}"
            
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
        
        # Cerca card/elementi certificati
        # NOTA: Selettori CSS da adattare alla struttura reale del sito
        cert_elements = soup.select('.certificate-card, .cert-item, article.certificate')
        
        if not cert_elements:
            # Fallback: cerca link a immagini certificati
            cert_elements = soup.select('a[href*="/certificates/"], img[src*="/certificates/"]')
        
        for elem in cert_elements:
            try:
                cert_data = self._extract_certificate_metadata(elem)
                if cert_data:
                    certificates.append(cert_data)
            except Exception as e:
                logger.warning(f"Failed to parse certificate element: {e}")
                continue
        
        return certificates
    
    def _extract_certificate_metadata(self, element) -> Optional[Dict]:
        """
        Estrae metadata da elemento certificato.
        
        Args:
            element: BeautifulSoup element
            
        Returns:
            Dict con metadata o None
        """
        # Cerca immagine certificato
        img_elem = element.find('img') if element.name != 'img' else element
        if not img_elem:
            return None
        
        img_url = img_elem.get('src') or img_elem.get('data-src')
        if not img_url:
            return None
        
        # URL completo
        if not img_url.startswith('http'):
            img_url = urljoin(self.BASE_URL, img_url)
        
        # Estrai task number da URL (esempio: /certificates/12345.jpg)
        task_number = self._extract_task_number_from_url(img_url)
        
        # Estrai altre info se disponibili
        metadata = {
            'image_url': img_url,
            'task_number': task_number,
            'scraped_at': datetime.now().isoformat(),
        }
        
        # Cerca testo associato (supplier, peptide, etc)
        if element.name != 'img':
            # Cerca testo nel parent container
            text_content = element.get_text(strip=True)
            if text_content:
                metadata['page_text'] = text_content
        
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
            
            filename = f"{task_number}_{image_hash[:8]}.jpg"
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
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> List[Dict]:
        """
        Scrape e download completo: trova certificati e scarica immagini.
        
        Args:
            max_pages: Numero massimo pagine
            progress_callback: Callback(stage, current, total)
                stage: 'scraping' o 'downloading'
            
        Returns:
            Lista certificati con file_path e image_hash
        """
        # Stage 1: Scraping
        def scrape_progress(page, total):
            if progress_callback:
                progress_callback('scraping', page, total)
        
        certificates = self.scrape_certificates(max_pages, scrape_progress)
        
        if not certificates:
            logger.warning("No certificates found")
            return []
        
        # Stage 2: Download immagini
        logger.info(f"Downloading {len(certificates)} certificate images...")
        downloaded = []
        
        for i, cert in enumerate(certificates, 1):
            if progress_callback:
                progress_callback('downloading', i, len(certificates))
            
            download_result = self.download_certificate_image(
                cert['image_url'],
                cert.get('task_number')
            )
            
            if download_result:
                cert.update(download_result)
                downloaded.append(cert)
        
        logger.info(f"Download completed: {len(downloaded)} certificates")
        return downloaded
    
    def get_cached_certificates(self) -> List[str]:
        """
        Ritorna lista file certificati già scaricati.
        
        Returns:
            Lista file paths
        """
        return [str(f) for f in self.storage_dir.glob("*.jpg")]
