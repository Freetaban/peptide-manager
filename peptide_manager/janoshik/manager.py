"""
Janoshik Manager - Orchestrator

Coordina l'intero workflow Janoshik: scraping, extraction, scoring, storage.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable, List, Dict
import pandas as pd

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
            llm_api_key: API key per LLM (se richiesta)
            storage_dir: Directory immagini certificati
            cache_dir: Directory cache
        """
        self.db_path = db_path
        
        # Initialize components
        self.scraper = JanoshikScraper(
            storage_dir=storage_dir,
            cache_dir=cache_dir
        )
        
        llm_extractor = get_llm_extractor(llm_provider, api_key=llm_api_key)
        self.extractor = JanoshikExtractor(llm_provider=llm_extractor)
        
        self.scorer = SupplierScorer()
        
        # Repositories
        self.cert_repo = JanoshikCertificateRepository(db_path)
        self.ranking_repo = SupplierRankingRepository(db_path)
    
    def run_full_update(
        self,
        max_pages: Optional[int] = None,
        progress_callback: Optional[Callable[[str, str], None]] = None
    ) -> Dict:
        """
        Esegue aggiornamento completo: scraping → extraction → scoring → storage.
        
        Args:
            max_pages: Numero massimo pagine da scrapare
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
            # STEP 1: Scraping
            if progress_callback:
                progress_callback('scraping', 'Scraping certificates from Janoshik...')
            
            certificates = self.scraper.scrape_and_download_all(max_pages=max_pages)
            stats['certificates_scraped'] = len(certificates)
            
            if not certificates:
                logger.warning("No certificates scraped")
                return stats
            
            # STEP 2: Extraction
            if progress_callback:
                progress_callback('extraction', f'Extracting data from {len(certificates)} certificates...')
            
            image_paths = [cert['file_path'] for cert in certificates]
            extracted_data = self.extractor.process_certificates(image_paths)
            stats['certificates_extracted'] = len(extracted_data)
            
            # STEP 3: Storage - Save certificates to DB
            if progress_callback:
                progress_callback('storage', 'Saving certificates to database...')
            
            cert_objects = []
            for data, cert_meta in zip(extracted_data, certificates):
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
            stats['certificates_new'] = new_certs
            
            # STEP 4: Scoring
            if progress_callback:
                progress_callback('scoring', 'Calculating supplier rankings...')
            
            all_certs = self.cert_repo.get_all_as_dicts()
            rankings_df = self.scorer.calculate_rankings(all_certs)
            
            # STEP 5: Storage - Save rankings to DB
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
    
    def get_latest_rankings(self, top_n: int = 10) -> List[SupplierRanking]:
        """
        Recupera latest ranking.
        
        Args:
            top_n: Numero top supplier da ritornare
            
        Returns:
            Lista SupplierRanking
        """
        return self.ranking_repo.get_top_suppliers(top_n)
    
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
