"""
Janoshik Views Logic

Business logic per viste dinamiche GUI.
Separa logica da presentazione (pattern MVC).
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Literal
from enum import Enum
import pandas as pd
from .analytics import JanoshikAnalytics


class TimeWindow(Enum):
    """Finestre temporali disponibili"""
    MONTH = ("Ultimo Mese", 30)
    QUARTER = ("Ultimi 3 Mesi", 90)
    YEAR = ("Ultimo Anno", 365)
    ALL = ("Tutti i Dati", None)
    
    def __init__(self, label: str, days: Optional[int]):
        self.label = label
        self.days = days


@dataclass
class SupplierRankingItem:
    """Item singolo ranking supplier"""
    rank: int
    supplier_name: str
    total_certificates: int
    avg_purity: float
    min_purity: float
    max_purity: float
    days_since_last_test: int
    endotoxin_tests: int
    products_tested: str  # Comma-separated
    
    @property
    def quality_badge(self) -> str:
        """Badge qualità basato su avg_purity"""
        if self.avg_purity >= 99.5:
            return "🥇 Eccellente"
        elif self.avg_purity >= 99.0:
            return "🥈 Ottimo"
        elif self.avg_purity >= 98.0:
            return "🥉 Buono"
        else:
            return "⚠️ Sufficiente"
    
    @property
    def activity_badge(self) -> str:
        """Badge attività basato su last test"""
        if self.days_since_last_test <= 7:
            return "🔥 Attivo"
        elif self.days_since_last_test <= 30:
            return "✅ Recente"
        elif self.days_since_last_test <= 90:
            return "⏰ Moderato"
        else:
            return "💤 Inattivo"


@dataclass
class PeptideRankingItem:
    """Item singolo ranking peptide"""
    rank: int
    peptide_name: str
    test_count: int
    vendor_count: int
    avg_purity: float
    most_recent: str
    
    @property
    def popularity_badge(self) -> str:
        """Badge popolarità basato su test_count"""
        if self.test_count >= 20:
            return "🔥🔥🔥 Hot"
        elif self.test_count >= 10:
            return "🔥🔥 Trending"
        elif self.test_count >= 5:
            return "🔥 Popolare"
        else:
            return "📊 Normale"


@dataclass
class VendorForPeptideItem:
    """Vendor specifico per un peptide"""
    rank: int
    supplier_name: str
    certificates: int
    avg_purity: float
    min_purity: float
    max_purity: float
    last_test: str
    
    @property
    def recommendation_score(self) -> float:
        """Score 0-100 per raccomandazione"""
        # 60% qualità, 30% volume, 10% recency
        quality_score = min(100, (self.avg_purity - 95) * 20)  # 95%=0, 100%=100
        volume_score = min(100, self.certificates * 10)  # 10 certs = 100
        
        days_ago = (datetime.now() - datetime.fromisoformat(self.last_test)).days
        recency_score = max(0, 100 - days_ago)  # 0 days=100, 100+ days=0
        
        return (quality_score * 0.6 + volume_score * 0.3 + recency_score * 0.1)


class JanoshikViewsLogic:
    """Logica per viste dinamiche Janoshik"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.analytics = JanoshikAnalytics(db_path)
    
    # ==================== VIEW 1: SUPPLIER RANKINGS ====================
    
    def get_supplier_rankings(
        self,
        time_window: TimeWindow = TimeWindow.QUARTER,
        min_certificates: int = 3,
        limit: int = 50
    ) -> List[SupplierRankingItem]:
        """
        Ranking suppliers per finestra temporale.
        
        Args:
            time_window: Finestra temporale (enum)
            min_certificates: Minimo certificati per qualificarsi
            limit: Numero massimo risultati
            
        Returns:
            Lista SupplierRankingItem ordinata per qualità
        """
        df = self.analytics.get_top_vendors(
            time_window_days=time_window.days,
            min_certificates=min_certificates,
            limit=limit
        )
        
        if df.empty:
            return []
        
        items = []
        for idx, row in df.iterrows():
            item = SupplierRankingItem(
                rank=idx + 1,
                supplier_name=row['supplier_name'],
                total_certificates=int(row['total_certificates']),
                avg_purity=float(row['avg_purity']),
                min_purity=float(row['min_purity']),
                max_purity=float(row['max_purity']),
                days_since_last_test=int(row['days_since_last_test']),
                endotoxin_tests=int(row['endotoxin_tests']),
                products_tested=row['products_tested'][:100] if row['products_tested'] else ""
            )
            items.append(item)
        
        return items
    
    def get_supplier_ranking_stats(
        self,
        time_window: TimeWindow
    ) -> Dict:
        """
        Statistiche aggregate ranking suppliers.
        
        Returns:
            Dict con totali, medie, etc.
        """
        overview = self.analytics.get_market_overview(time_window.days)
        quality_dist = self.analytics.get_quality_distribution()
        
        return {
            'total_vendors': overview['unique_vendors'],
            'total_certificates': overview['total_certificates'],
            'market_avg_purity': overview['market_avg_purity'],
            'quality_distribution': quality_dist,
            'time_window_label': time_window.label
        }
    
    # ==================== VIEW 2: PEPTIDE RANKINGS ====================
    
    def get_peptide_rankings(
        self,
        time_window: TimeWindow = TimeWindow.MONTH,
        min_certificates: int = 2,
        limit: int = 30
    ) -> List[PeptideRankingItem]:
        """
        Ranking peptidi più testati (trending).
        
        Args:
            time_window: Finestra temporale
            min_certificates: Minimo certificati
            limit: Numero massimo risultati
            
        Returns:
            Lista PeptideRankingItem ordinata per popolarità
        """
        # Default 30 giorni se TimeWindow.ALL (non ha senso "trending" su tutto)
        days = time_window.days if time_window.days else 30
        
        df = self.analytics.get_hottest_peptides(
            time_window_days=days,
            min_certificates=min_certificates,
            limit=limit
        )
        
        if df.empty:
            return []
        
        items = []
        for idx, row in df.iterrows():
            item = PeptideRankingItem(
                rank=idx + 1,
                peptide_name=row['peptide_name'],
                test_count=int(row['test_count']),
                vendor_count=int(row['vendor_count']),
                avg_purity=float(row['avg_purity']),
                most_recent=row['most_recent']
            )
            items.append(item)
        
        return items
    
    def get_peptide_ranking_stats(
        self,
        time_window: TimeWindow
    ) -> Dict:
        """
        Statistiche aggregate ranking peptidi.
        
        Returns:
            Dict con totali, trend, etc.
        """
        days = time_window.days if time_window.days else 30
        overview = self.analytics.get_market_overview(days)
        
        return {
            'unique_peptides': overview['unique_products'],
            'total_tests': overview['total_certificates'],
            'avg_tests_per_peptide': overview['total_certificates'] / max(1, overview['unique_products']),
            'time_window_label': time_window.label
        }
    
    # ==================== VIEW 3: VENDOR SEARCH PER PEPTIDE ====================
    
    def search_vendors_for_peptide(
        self,
        peptide_name: str,
        time_window: TimeWindow = TimeWindow.QUARTER,
        limit: int = 20
    ) -> Dict:
        """
        Cerca migliori vendors per un peptide specifico.
        
        Args:
            peptide_name: Nome peptide (es. "Tirzepatide")
            time_window: Finestra temporale
            limit: Numero massimo risultati
            
        Returns:
            Dict con:
                - best_vendor: Miglior vendor
                - all_vendors: Lista VendorForPeptideItem
                - peptide_name: Nome peptide cercato
                - stats: Statistiche
        """
        # Best vendor
        best_dict = self.analytics.get_best_vendor_for_peptide(
            peptide_name=peptide_name,
            time_window_days=time_window.days
        )
        
        # Converti in VendorForPeptideItem
        best_vendor = None
        if best_dict:
            best_vendor = VendorForPeptideItem(
                rank=1,
                supplier_name=best_dict['supplier_name'],
                certificates=int(best_dict['certificates']),
                avg_purity=float(best_dict['avg_purity']),
                min_purity=float(best_dict['avg_purity']),  # Single source, use avg
                max_purity=float(best_dict['avg_purity']),  # Single source, use avg
                last_test=best_dict['most_recent_test']
            )
        
        # All vendors
        df = self.analytics.get_peptide_vendors(
            peptide_name=peptide_name,
            time_window_days=time_window.days
        )
        
        vendors = []
        if not df.empty:
            for idx, row in df.iterrows():
                item = VendorForPeptideItem(
                    rank=idx + 1,
                    supplier_name=row['supplier_name'],
                    certificates=int(row['certificates']),
                    avg_purity=float(row['avg_purity']),
                    min_purity=float(row['min_purity']),
                    max_purity=float(row['max_purity']),
                    last_test=row['last_test']
                )
                vendors.append(item)
        
        # Stats
        total_certs = df['certificates'].sum() if not df.empty else 0
        avg_purity_market = df['avg_purity'].mean() if not df.empty else 0
        
        return {
            'peptide_name': peptide_name,
            'best_vendor': best_vendor,
            'all_vendors': vendors,
            'stats': {
                'total_vendors': len(vendors),
                'total_certificates': int(total_certs),
                'market_avg_purity': float(avg_purity_market),
                'time_window_label': time_window.label
            }
        }
    
    def get_peptide_suggestions(self, partial: str, limit: int = 10) -> List[str]:
        """
        Suggerimenti peptidi per autocomplete.
        
        Args:
            partial: Testo parziale
            limit: Numero suggerimenti
            
        Returns:
            Lista nomi peptidi che matchano
        """
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        
        query = f"""
        WITH extracted AS (
            SELECT DISTINCT
                CASE 
                    WHEN product_name LIKE '%Tirzepatide%' THEN 'Tirzepatide'
                    WHEN product_name LIKE '%Semaglutide%' THEN 'Semaglutide'
                    WHEN product_name LIKE '%Retatrutide%' THEN 'Retatrutide'
                    WHEN product_name LIKE '%BPC%' THEN 'BPC-157'
                    WHEN product_name LIKE '%TB-500%' THEN 'TB-500'
                    WHEN product_name LIKE '%Ipamorelin%' THEN 'Ipamorelin'
                    WHEN product_name LIKE '%CJC%' THEN 'CJC-1295'
                    ELSE SUBSTR(product_name, 1, INSTR(product_name || ' ', ' ') - 1)
                END as peptide_name
            FROM janoshik_certificates
            WHERE product_name IS NOT NULL
        )
        SELECT peptide_name
        FROM extracted
        WHERE peptide_name LIKE '%{partial}%'
        ORDER BY 
            CASE WHEN peptide_name LIKE '{partial}%' THEN 0 ELSE 1 END,
            LENGTH(peptide_name)
        LIMIT {limit}
        """
        
        cursor = conn.execute(query)
        suggestions = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return suggestions
    
    # ==================== UTILITY METHODS ====================
    
    @staticmethod
    def format_purity(purity: float) -> str:
        """Formatta purezza con colore"""
        return f"{purity:.2f}%"
    
    @staticmethod
    def format_date_ago(date_str: str) -> str:
        """Formatta data come 'X giorni fa'"""
        try:
            date = datetime.fromisoformat(date_str)
            days = (datetime.now() - date).days
            
            if days == 0:
                return "Oggi"
            elif days == 1:
                return "Ieri"
            elif days < 7:
                return f"{days} giorni fa"
            elif days < 30:
                weeks = days // 7
                return f"{weeks} settiman{'a' if weeks == 1 else 'e'} fa"
            elif days < 365:
                months = days // 30
                return f"{months} mes{'e' if months == 1 else 'i'} fa"
            else:
                years = days // 365
                return f"{years} ann{'o' if years == 1 else 'i'} fa"
        except:
            return date_str
    
    @staticmethod
    def get_time_window_options() -> List[TimeWindow]:
        """Ritorna tutte le opzioni finestra temporale"""
        return [TimeWindow.MONTH, TimeWindow.QUARTER, TimeWindow.YEAR, TimeWindow.ALL]
