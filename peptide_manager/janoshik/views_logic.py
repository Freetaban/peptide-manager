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
    composite_score: float = 0.0  # Score composito 0-100
    
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
    recommendation_score: int = 0  # Score generale vendor (0-100) dal ranking globale


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
                products_tested=row['products_tested'][:100] if row['products_tested'] else "",
                composite_score=float(row['composite_score']) if 'composite_score' in row else 0.0
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
        # TimeWindow.ALL = None (tutti i certificati)
        days = time_window.days
        
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
        time_window: TimeWindow = TimeWindow.ALL,
        limit: int = 20
    ) -> Dict:
        """
        Cerca migliori vendors per un peptide specifico.
        
        Usa lo SCORE GENERALE del vendor (da get_supplier_rankings) per classificare,
        anche se il vendor ha pochi certificati per questo peptide specifico.
        
        Args:
            peptide_name: Nome peptide (es. "Tirzepatide")
            time_window: Finestra temporale (default: ALL per cercare in tutto lo storico)
            limit: Numero massimo risultati
            
        Returns:
            Dict con:
                - best_vendor: Miglior vendor (basato su score generale)
                - all_vendors: Lista VendorForPeptideItem (ordinata per score)
                - peptide_name: Nome peptide cercato
                - stats: Statistiche
        """
        # Ottieni ranking generale vendors (per score globale)
        # Usa metodo interno per avere accesso ai VendorRankingItem con score
        rankings = self.get_supplier_rankings(
            time_window=time_window,
            min_certificates=1,  # Include tutti, anche con pochi certificati
            limit=100  # Prendi top 100 per avere coverage
        )
        
        # Crea mappa supplier -> score generale
        vendor_scores = {item.supplier_name: item.composite_score for item in rankings}
        
        # All vendors che hanno testato questo peptide
        df = self.analytics.get_peptide_vendors(
            peptide_name=peptide_name,
            time_window_days=time_window.days
        )
        
        vendors = []
        if not df.empty:
            # Aggiungi score generale a ogni vendor
            df['vendor_score'] = df['supplier_name'].map(vendor_scores).fillna(0)
            
            # Ordina per score generale (non per avg_purity del peptide)
            df = df.sort_values('vendor_score', ascending=False)
            
            for idx, row in df.iterrows():
                item = VendorForPeptideItem(
                    rank=idx + 1,
                    supplier_name=row['supplier_name'],
                    certificates=int(row['certificates']),
                    avg_purity=float(row['avg_purity']) if row.get('avg_purity') is not None and not pd.isna(row['avg_purity']) else 0.0,
                    min_purity=float(row['min_purity']) if row.get('min_purity') is not None and not pd.isna(row['min_purity']) else 0.0,
                    max_purity=float(row['max_purity']) if row.get('max_purity') is not None and not pd.isna(row['max_purity']) else 0.0,
                    last_test=row['last_test'],
                    recommendation_score=int(row['vendor_score'])  # Score generale vendor
                )
                vendors.append(item)
        
        # Best vendor = primo della lista (score generale più alto)
        best_vendor = vendors[0] if vendors else None
        
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
            Lista nomi peptidi che matchano (usa peptide_name_std dal DB)
        """
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        
        # Usa peptide_name_std dal database (standardizzato)
        # Filtra peptidi sospetti:
        # - Nomi molto corti (<3 caratteri) sempre
        # - Nomi corti (3-4 caratteri) con pochi certificati (<=3)
        # Includiamo certificati IU (hormones) anche se purity è NULL
        query = f"""
        WITH peptide_stats AS (
            SELECT 
                peptide_name_std,
                COUNT(*) as cert_count,
                LENGTH(peptide_name_std) as name_length
            FROM janoshik_certificates
            WHERE peptide_name_std IS NOT NULL
              AND peptide_name_std != ''
              AND (
                  (purity_percentage IS NOT NULL AND purity_percentage > 0)
                  OR 
                  (unit_of_measure IN ('mg', 'IU') AND quantity_tested_mg IS NOT NULL AND quantity_nominal > 0)
              )
            GROUP BY peptide_name_std
        )
        SELECT peptide_name_std
        FROM peptide_stats
        WHERE peptide_name_std LIKE '%{partial}%'
          AND name_length >= 3
          AND NOT (name_length <= 4 AND cert_count <= 3)
        ORDER BY 
            CASE WHEN peptide_name_std LIKE '{partial}%' THEN 0 ELSE 1 END,
            cert_count DESC,
            name_length,
            peptide_name_std
        LIMIT {limit}
        """
        
        cursor = conn.execute(query)
        suggestions = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return suggestions
    
    # ==================== VIEW 4: VENDOR DETAILS ====================
    
    def get_all_vendor_names(self) -> List[str]:
        """
        Recupera lista di tutti i vendor unici nel database.
        
        Returns:
            Lista nomi vendor ordinati alfabeticamente
        """
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT DISTINCT supplier_name
            FROM janoshik_certificates
            WHERE supplier_name IS NOT NULL
              AND supplier_name != ''
            ORDER BY supplier_name ASC
        ''')
        
        vendors = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return vendors
    
    def get_vendor_certificates(self, vendor_name: str) -> List[Dict]:
        """
        Recupera tutti i certificati di un vendor specifico.
        
        Args:
            vendor_name: Nome vendor (es: "QSC", "Amo", "Nexaph")
        
        Returns:
            Lista di dict con info certificati ordinati per data (più recenti prima):
            - certificate_id: ID certificato
            - test_date: Data test
            - peptide_name: Nome peptide
            - purity_percent: Purezza %
            - supplier_name: Nome vendor
            - image_url: URL immagine certificato (se disponibile)
        """
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                jc.id as certificate_id,
                jc.test_date,
                jc.peptide_name_std as peptide_name,
                jc.purity_percentage as purity_percent,
                jc.supplier_name,
                jc.image_url
            FROM janoshik_certificates jc
            WHERE LOWER(jc.supplier_name) = LOWER(?)
            ORDER BY jc.test_date DESC
        ''', (vendor_name,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                'certificate_id': row[0],
                'test_date': row[1],
                'peptide_name': row[2],
                'purity_percent': row[3] if row[3] is not None else 0.0,
                'supplier_name': row[4],
                'image_url': row[5],
            }
            for row in rows
        ]
    
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
