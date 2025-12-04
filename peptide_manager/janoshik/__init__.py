"""
Janoshik Supplier Ranking System

Modulo per monitoraggio e ranking automatico dei supplier basato
sui certificati pubblici di analisi Janoshik.

Features:
- Scraping automatico certificati da janoshik.com/public/
- Estrazione dati con LLM multi-provider (GPT-4o, Claude, Gemini, Ollama)
- Algoritmo scoring per ranking supplier
- Integrazione con database suppliers
- Visualizzazione ranking in GUI
"""

from .scraper import JanoshikScraper
from .extractor import JanoshikExtractor
from .scorer import SupplierScorer
from .llm_providers import LLMProvider, get_llm_extractor
from .models import JanoshikCertificate, SupplierRanking
from .repositories import JanoshikCertificateRepository, SupplierRankingRepository
from .manager import JanoshikManager

__all__ = [
    'JanoshikScraper',
    'JanoshikExtractor',
    'SupplierScorer',
    'LLMProvider',
    'get_llm_extractor',
    'JanoshikCertificate',
    'SupplierRanking',
    'JanoshikCertificateRepository',
    'SupplierRankingRepository',
    'JanoshikManager',
]

__version__ = '0.3.0'
