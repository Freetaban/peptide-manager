"""
Janoshik Manager - Orchestrator

Coordina l'intero workflow Janoshik: scraping, extraction, scoring, storage.
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable, List, Dict
import pandas as pd
from dotenv import load_dotenv

# Load environment variables from .env.development or .env
env_file = Path(__file__).parent.parent.parent / '.env.development'
if not env_file.exists():
    env_file = Path(__file__).parent.parent.parent / '.env'
load_dotenv(env_file)

from .scraper import JanoshikScraper
from .extractor import JanoshikExtractor
from .scorer import SupplierScorer
from .llm_providers import LLMProvider, get_llm_extractor
from .models import JanoshikCertificate, SupplierRanking
from .repositories import JanoshikCertificateRepository, SupplierRankingRepository


logger = logging.getLogger(__name__)


class JanoshikManager:
    """Manager per orchestrare workflow Janoshik completo"""
    
    def __init__(
        self,
        db_path: str,
        llm_provider: LLMProvider = LLMProvider.GEMINI_FLASH,
        llm_api_key: Optional[str] = None,
        storage_dir: str = "data/janoshik/images",
        cache_dir: str = "data/janoshik/cache"
    ):
        """
        Inizializza manager.
        
        Args:
            db_path: Path al database
            llm_provider: Provider LLM da usare
            llm_api_key: API key per LLM (se None, carica da .env)
            storage_dir: Directory immagini certificati
            cache_dir: Directory cache
        """
        self.db_path = db_path
        
        # Auto-load API key from environment if not provided
        if llm_api_key is None:
            llm_api_key = self._get_api_key_from_env(llm_provider)
        
        # Load Janoshik URL from user preferences
        janoshik_url = self._get_janoshik_url_from_preferences()
        
        # Initialize components
        self.scraper = JanoshikScraper(
            storage_dir=storage_dir,
            cache_dir=cache_dir,
            base_url=janoshik_url
        )
        
        llm_extractor = get_llm_extractor(llm_provider, api_key=llm_api_key)
        self.extractor = JanoshikExtractor(llm_extractor)
        self.scorer = SupplierScorer()
        
        # Repositories
        self.cert_repo = JanoshikCertificateRepository(db_path)
        self.ranking_repo = SupplierRankingRepository(db_path)
    
    def _get_janoshik_url_from_preferences(self) -> str:
        """Load Janoshik URL from user_preferences table"""
        import sqlite3
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT preference_value FROM user_preferences WHERE preference_key = 'janoshik_base_url'"
            )
            row = cursor.fetchone()
            conn.close()
            return row[0] if row else "https://public.janoshik.com/"
        except Exception:
            return "https://public.janoshik.com/"
    
    def _get_api_key_from_env(self, provider: LLMProvider) -> Optional[str]:
        """
        Carica API key da environment variables.
        
        Args:
            provider: LLM provider
            
        Returns:
            API key o None
        """
        env_key_map = {
            LLMProvider.GPT4O: 'OPENAI_API_KEY',
            LLMProvider.CLAUDE_SONNET: 'ANTHROPIC_API_KEY',
            LLMProvider.GEMINI_FLASH: 'GOOGLE_API_KEY',
            LLMProvider.OLLAMA_LLAMA: None  # Non richiede API key
        }
        
        env_key = env_key_map.get(provider)
        if not env_key:
            return None
        
        api_key = os.getenv(env_key)
        
        if not api_key:
            logger.warning(f"API key {env_key} not found in environment for {provider.value}")
        
        return api_key
    
    def run_full_update(
        self,
        max_pages: Optional[int] = None,
        max_certificates: Optional[int] = None,
        progress_callback: Optional[Callable[[str, str], None]] = None
    ) -> Dict:
        """
        Esegue aggiornamento completo: scraping → extraction → scoring → storage.
        
        Args:
            max_pages: Numero massimo pagine da scrapare
            max_certificates: Numero massimo certificati da processare
            progress_callback: Callback(stage, message)
            
        Returns:
            Dict con statistiche: {
                'certificates_scraped': int,
                'certificates_new': int,
                'certificates_extracted': int,
                'rankings_calculated': int,
                'top_supplier': str
            }
        """
        stats = {
            'certificates_scraped': 0,
            'certificates_new': 0,
            'certificates_extracted': 0,
            'rankings_calculated': 0,
            'top_supplier': None
        }
        
        try:
            # STEP 1: Scraping - Solo metadata (NO download)
            if progress_callback:
                progress_callback('scraping', 'Scraping certificate list from Janoshik...')
            
            certificates_metadata = self.scraper.scrape_certificates(
                max_pages=max_pages,
                max_certificates=max_certificates
            )
            stats['certificates_scraped'] = len(certificates_metadata)
            
            if not certificates_metadata:
                logger.warning("No certificates scraped")
                return stats
            
            # STEP 2: Filtro PRIMA del download - Controlla quali già esistono
            if progress_callback:
                progress_callback('filtering', f'Filtering {len(certificates_metadata)} certificates against database...')
            
            new_certificates = []
            for cert_meta in certificates_metadata:
                task_number = cert_meta.get('task_number')
                if task_number and not self.cert_repo.exists_by_task_number(task_number):
                    new_certificates.append(cert_meta)
            
            stats['certificates_new'] = len(new_certificates)
            skipped = len(certificates_metadata) - len(new_certificates)
            logger.info(f"Filtered: {len(new_certificates)} new, {skipped} already in DB")
            
            if not new_certificates:
                if progress_callback:
                    progress_callback('complete', f'All {len(certificates_metadata)} certificates already in database - no update needed!')
                logger.info("No new certificates to process")
                # Ricalcola comunque rankings con dati esistenti
                if progress_callback:
                    progress_callback('scoring', 'Recalculating supplier rankings with existing data...')
                all_certs = self.cert_repo.get_all_as_dicts()
                rankings_df = self.scorer.calculate_rankings(all_certs)
                ranking_objects = []
                for _, row in rankings_df.iterrows():
                    ranking_obj = SupplierRanking.from_scorer_output(row.to_dict())
                    ranking_objects.append(ranking_obj)
                rankings_saved = self.ranking_repo.insert_many(ranking_objects)
                stats['rankings_calculated'] = rankings_saved
                return stats
            
            # STEP 3: Download - SOLO i nuovi
            if progress_callback:
                progress_callback('downloading', f'Downloading {len(new_certificates)} NEW certificate images...')
            
            downloaded_certificates = []
            for i, cert_meta in enumerate(new_certificates, 1):
                # Fetch image URL
                image_url = self.scraper._fetch_certificate_image_url(
                    cert_meta['certificate_url'],
                    cert_meta['task_number']
                )
                
                if not image_url:
                    logger.warning(f"Could not get image URL for task {cert_meta['task_number']}")
                    continue
                
                # Download image
                download_result = self.scraper.download_certificate_image(
                    image_url,
                    cert_meta.get('task_number')
                )
                
                if download_result:
                    cert_meta.update(download_result)
                    downloaded_certificates.append(cert_meta)
                
                if i % 10 == 0 and progress_callback:
                    progress_callback('downloading', f'Downloaded {i}/{len(new_certificates)} images...')
            
            if not downloaded_certificates:
                logger.error("Failed to download any certificate images")
                return stats
            
            # STEP 4: Extraction - SOLO i nuovi scaricati
            if progress_callback:
                progress_callback('extraction', f'Extracting data from {len(downloaded_certificates)} certificates with LLM...')
            
            image_paths = [cert['file_path'] for cert in downloaded_certificates]
            extracted_data = self.extractor.process_certificates(image_paths)
            stats['certificates_extracted'] = len(extracted_data)
            
            # STEP 5: Storage - Save certificates to DB
            if progress_callback:
                progress_callback('storage', 'Saving new certificates to database...')
            
            cert_objects = []
            for data, cert_meta in zip(extracted_data, downloaded_certificates):
                try:
                    cert_obj = JanoshikCertificate.from_extracted_data(
                        data,
                        cert_meta['file_path'],
                        cert_meta['image_hash']
                    )
                    cert_objects.append(cert_obj)
                except Exception as e:
                    logger.error(f"Failed to create certificate object: {e}")
                    continue
            
            new_certs = self.cert_repo.insert_many(cert_objects)
            logger.info(f"Saved {new_certs} new certificates to database")
            
            # STEP 6: Scoring
            if progress_callback:
                progress_callback('scoring', 'Calculating supplier rankings...')
            
            all_certs = self.cert_repo.get_all_as_dicts()
            rankings_df = self.scorer.calculate_rankings(all_certs)
            
            # STEP 7: Storage - Save rankings to DB
            if progress_callback:
                progress_callback('storage', 'Saving rankings to database...')
            
            ranking_objects = []
            for _, row in rankings_df.iterrows():
                ranking_obj = SupplierRanking.from_scorer_output(row.to_dict())
                ranking_objects.append(ranking_obj)
            
            rankings_saved = self.ranking_repo.insert_many(ranking_objects)
            stats['rankings_calculated'] = rankings_saved
            
            # Top supplier
            if not rankings_df.empty:
                stats['top_supplier'] = rankings_df.iloc[0]['supplier_name']
            
            if progress_callback:
                progress_callback('complete', 'Update completed successfully!')
            
            return stats
            
        except Exception as e:
            logger.error(f"Full update failed: {e}")
            if progress_callback:
                progress_callback('error', f'Error: {str(e)}')
            raise
    
    def get_latest_rankings(self, top_n: int = 10, limit: int = None) -> List[SupplierRanking]:
        """
        Recupera latest ranking.
        
        Args:
            top_n: Numero top supplier da ritornare (deprecato, usa limit)
            limit: Numero supplier da ritornare (preferito)
            
        Returns:
            Lista SupplierRanking
        """
        n = limit if limit is not None else top_n
        return self.ranking_repo.get_top_suppliers(n)
    
    def get_supplier_certificates(self, supplier_name: str) -> List[JanoshikCertificate]:
        """
        Recupera certificati di un supplier.
        
        Args:
            supplier_name: Nome supplier
            
        Returns:
            Lista JanoshikCertificate
        """
        return self.cert_repo.get_by_supplier(supplier_name)
    
    def get_supplier_trend(self, supplier_name: str) -> List[Dict]:
        """
        Recupera trend score supplier nel tempo.
        
        Args:
            supplier_name: Nome supplier
            
        Returns:
            Lista dict con {calculated_at, total_score, rank_position}
        """
        return self.ranking_repo.get_supplier_trend(supplier_name)
    
    def get_statistics(self) -> Dict:
        """
        Ritorna statistiche generali.
        
        Returns:
            Dict con statistiche
        """
        return {
            'total_certificates': self.cert_repo.count(),
            'unique_suppliers': len(self.cert_repo.get_unique_suppliers()),
            'total_rankings': self.ranking_repo.count(),
            'calculations_performed': self.ranking_repo.count_calculations(),
        }
    
    def cleanup_old_rankings(self, keep_last_n: int = 10) -> int:
        """
        Elimina vecchi ranking mantenendo ultimi N.
        
        Args:
            keep_last_n: Numero calcoli da mantenere
            
        Returns:
            Numero record eliminati
        """
        return self.ranking_repo.delete_old_rankings(keep_last_n)
    
    def recalculate_rankings(self) -> pd.DataFrame:
        """
        Ricalcola ranking da certificati esistenti.
        
        Returns:
            DataFrame con nuovi ranking
        """
        all_certs = self.cert_repo.get_all_as_dicts()
        
        if not all_certs:
            logger.warning("No certificates found for ranking calculation")
            return pd.DataFrame()
        
        rankings_df = self.scorer.calculate_rankings(all_certs)
        
        # Save to DB
        ranking_objects = []
        for _, row in rankings_df.iterrows():
            ranking_obj = SupplierRanking.from_scorer_output(row.to_dict())
            ranking_objects.append(ranking_obj)
        
        self.ranking_repo.insert_many(ranking_objects)
        
        return rankings_df
    
    def export_rankings_to_csv(self, output_path: str) -> str:
        """
        Esporta latest ranking in CSV.
        
        Args:
            output_path: Path file output
            
        Returns:
            Path file creato
        """
        rankings = self.get_latest_rankings(top_n=1000)
        
        if not rankings:
            raise ValueError("No rankings found")
        
        # Convert to DataFrame
        data = [r.to_dict() for r in rankings]
        df = pd.DataFrame(data)
        
        # Export
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_file, index=False)
        
        return str(output_file)
    
    def get_cost_estimate(self, num_certificates: int) -> Dict[str, float]:
        """
        Stima costo per processare N certificati.
        
        Args:
            num_certificates: Numero certificati
            
        Returns:
            Dict con costo per provider
        """
        return self.extractor.get_estimated_cost(num_certificates)
