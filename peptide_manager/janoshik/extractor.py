"""
Janoshik Certificate Data Extractor

Gestisce l'estrazione dati dai certificati usando LLM.
"""

import time
from pathlib import Path
from typing import List, Dict, Optional, Callable
from .llm_providers import LLMProvider, get_llm_extractor


class JanoshikExtractor:
    """Estrattore dati certificati Janoshik con LLM"""
    
    def __init__(
        self,
        provider: LLMProvider = LLMProvider.GEMINI_FLASH,
        api_key: Optional[str] = None,
        rate_limit_rpm: int = 10,
        **provider_kwargs
    ):
        """
        Inizializza estrattore.
        
        Args:
            provider: Provider LLM (enum) o istanza extractor già creata
            api_key: API key (opzionale se in env)
            rate_limit_rpm: Requests per minute (rate limiting)
            **provider_kwargs: Parametri aggiuntivi per provider
        """
        # Se provider è già un'istanza di extractor, usala direttamente
        if hasattr(provider, 'extract_certificate_data'):
            self.llm = provider
            self.provider = None
        else:
            # Altrimenti crea l'extractor dal provider enum
            self.llm = get_llm_extractor(provider, api_key, **provider_kwargs)
            self.provider = provider
        
        self.rate_limit_rpm = rate_limit_rpm
        self.last_request_time = 0
    
    def process_certificates(
        self,
        image_paths: List[Path],
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[Dict]:
        """
        Processa batch di certificati.
        
        Args:
            image_paths: Lista percorsi immagini
            progress_callback: Callback(current, total) per progress
            
        Returns:
            Lista dati certificati estratti
        """
        results = []
        total = len(image_paths)
        errors = []
        
        for idx, image_path in enumerate(image_paths):
            # Converti a Path se stringa
            if isinstance(image_path, str):
                image_path = Path(image_path)
            
            try:
                # Rate limiting
                self._wait_for_rate_limit()
                
                # Estrai dati
                cert_data = self.llm.extract_certificate_data(str(image_path))
                cert_data['image_file'] = image_path.name
                cert_data['extraction_provider'] = self.provider.value if self.provider else 'unknown'
                
                results.append(cert_data)
                
                # Progress callback
                if progress_callback:
                    progress_callback(idx + 1, total)
            
            except Exception as e:
                error_msg = f"Error {image_path.name if hasattr(image_path, 'name') else image_path}: {str(e)}"
                errors.append(error_msg)
                print(f"❌ {error_msg}")
        
        if errors:
            print(f"\n⚠️  Errori totali: {len(errors)}/{total}")
        
        return results
    
    def process_single_certificate(self, image_path: Path) -> Dict:
        """
        Processa singolo certificato.
        
        Args:
            image_path: Percorso immagine
            
        Returns:
            Dati certificato estratti
        """
        self._wait_for_rate_limit()
        
        cert_data = self.llm.extract_certificate_data(str(image_path))
        cert_data['image_file'] = image_path.name if hasattr(image_path, 'name') else str(image_path)
        cert_data['extraction_provider'] = self.provider.value if self.provider else 'unknown'
        
        return cert_data
    
    def get_estimated_cost(self, num_images: int) -> float:
        """
        Stima costo per elaborazione.
        
        Args:
            num_images: Numero immagini da processare
            
        Returns:
            Costo stimato in USD
        """
        cost_per_image = self.llm.get_cost_per_image()
        return num_images * cost_per_image
    
    def _wait_for_rate_limit(self):
        """Implementa rate limiting"""
        if self.rate_limit_rpm <= 0:
            return
        
        seconds_per_request = 60.0 / self.rate_limit_rpm
        elapsed = time.time() - self.last_request_time
        
        if elapsed < seconds_per_request:
            wait_time = seconds_per_request - elapsed
            time.sleep(wait_time)
        
        self.last_request_time = time.time()
