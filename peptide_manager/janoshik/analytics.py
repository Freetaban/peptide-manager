"""
Janoshik Analytics Module

Query analitiche avanzate per analisi mercato peptidi.
"""

import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import pandas as pd


class JanoshikAnalytics:
    """Analisi avanzate su dati Janoshik"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def _get_connection(self) -> sqlite3.Connection:
        """Connessione DB con row_factory"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    # ==================== VENDOR RANKINGS ====================
    
    def get_top_vendors(
        self,
        time_window_days: Optional[int] = None,
        min_certificates: int = 3,
        limit: int = 20
    ) -> pd.DataFrame:
        """
        Top vendors per score totale.
        
        Args:
            time_window_days: Ultimi N giorni (None = tutti)
            min_certificates: Minimo certificati per qualificarsi
            limit: Numero risultati
            
        Returns:
            DataFrame con ranking vendors
        """
        conn = self._get_connection()
        
        # Time filter
        date_filter = ""
        if time_window_days:
            cutoff = (datetime.now() - timedelta(days=time_window_days)).strftime('%Y-%m-%d')
            date_filter = f"AND test_date >= '{cutoff}'"
        
        query = f"""
        SELECT 
            supplier_name,
            COUNT(*) as total_certificates,
            AVG(purity_percentage) as avg_purity,
            MIN(purity_percentage) as min_purity,
            MAX(purity_percentage) as max_purity,
            COUNT(CASE WHEN endotoxin_eu_per_mg IS NOT NULL THEN 1 END) as endotoxin_tests,
            MAX(test_date) as last_test_date,
            GROUP_CONCAT(DISTINCT product_name) as products_tested
        FROM janoshik_certificates
        WHERE supplier_name IS NOT NULL
          AND purity_percentage IS NOT NULL
          {date_filter}
        GROUP BY supplier_name
        HAVING COUNT(*) >= {min_certificates}
        ORDER BY avg_purity DESC, total_certificates DESC
        LIMIT {limit}
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        # Calcola days since last test
        df['days_since_last_test'] = df['last_test_date'].apply(
            lambda x: (datetime.now() - datetime.fromisoformat(x)).days if x else 999
        )
        
        return df
    
    def get_best_vendor_for_peptide(
        self,
        peptide_name: str,
        time_window_days: Optional[int] = 90
    ) -> Dict:
        """
        Miglior vendor per un peptide specifico.
        
        Args:
            peptide_name: Nome peptide (es. "Tirzepatide")
            time_window_days: Finestra temporale (None = tutti)
            
        Returns:
            Dict con vendor info
        """
        conn = self._get_connection()
        
        date_filter = ""
        if time_window_days:
            cutoff = (datetime.now() - timedelta(days=time_window_days)).strftime('%Y-%m-%d')
            date_filter = f"AND test_date >= '{cutoff}'"
        
        query = f"""
        SELECT 
            supplier_name,
            COUNT(*) as certificates,
            AVG(purity_percentage) as avg_purity,
            MAX(test_date) as most_recent_test,
            GROUP_CONCAT(product_name || ' (' || purity_percentage || '%)') as products
        FROM janoshik_certificates
        WHERE product_name LIKE '%{peptide_name}%'
          {date_filter}
          AND supplier_name IS NOT NULL
        GROUP BY supplier_name
        ORDER BY avg_purity DESC, most_recent_test DESC
        LIMIT 1
        """
        
        cursor = conn.execute(query)
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return dict(row)
    
    # ==================== PEPTIDE TRENDS ====================
    
    def get_hottest_peptides(
        self,
        time_window_days: int = 30,
        min_certificates: int = 2,
        limit: int = 20
    ) -> pd.DataFrame:
        """
        Peptidi più testati nel periodo (trending).
        
        Args:
            time_window_days: Finestra temporale
            min_certificates: Minimo certificati
            limit: Numero risultati
            
        Returns:
            DataFrame con peptidi trending
        """
        conn = self._get_connection()
        
        cutoff = (datetime.now() - timedelta(days=time_window_days)).strftime('%Y-%m-%d')
        
        query = f"""
        SELECT 
            CASE 
                WHEN product_name LIKE '%Tirzepatide%' THEN 'Tirzepatide'
                WHEN product_name LIKE '%Semaglutide%' THEN 'Semaglutide'
                WHEN product_name LIKE '%Retatrutide%' THEN 'Retatrutide'
                WHEN product_name LIKE '%BPC%' THEN 'BPC-157'
                WHEN product_name LIKE '%TB-500%' THEN 'TB-500'
                WHEN product_name LIKE '%Ipamorelin%' THEN 'Ipamorelin'
                WHEN product_name LIKE '%CJC%' THEN 'CJC-1295'
                ELSE SUBSTR(product_name, 1, INSTR(product_name || ' ', ' ') - 1)
            END as peptide_name,
            COUNT(*) as test_count,
            COUNT(DISTINCT supplier_name) as vendor_count,
            AVG(purity_percentage) as avg_purity,
            MAX(test_date) as most_recent
        FROM janoshik_certificates
        WHERE test_date >= '{cutoff}'
          AND product_name IS NOT NULL
          AND purity_percentage IS NOT NULL
        GROUP BY peptide_name
        HAVING COUNT(*) >= {min_certificates}
        ORDER BY test_count DESC
        LIMIT {limit}
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        return df
    
    def get_peptide_vendors(
        self,
        peptide_name: str,
        time_window_days: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Tutti i vendors che testano un peptide specifico.
        
        Args:
            peptide_name: Nome peptide
            time_window_days: Finestra temporale (None = tutti)
            
        Returns:
            DataFrame con vendors ordinati per qualità
        """
        conn = self._get_connection()
        
        date_filter = ""
        if time_window_days:
            cutoff = (datetime.now() - timedelta(days=time_window_days)).strftime('%Y-%m-%d')
            date_filter = f"AND test_date >= '{cutoff}'"
        
        query = f"""
        SELECT 
            supplier_name,
            COUNT(*) as certificates,
            AVG(purity_percentage) as avg_purity,
            MIN(purity_percentage) as min_purity,
            MAX(purity_percentage) as max_purity,
            MAX(test_date) as last_test,
            GROUP_CONCAT(task_number) as task_numbers
        FROM janoshik_certificates
        WHERE product_name LIKE '%{peptide_name}%'
          {date_filter}
          AND supplier_name IS NOT NULL
        GROUP BY supplier_name
        ORDER BY avg_purity DESC, last_test DESC
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        return df
    
    # ==================== MARKET INSIGHTS ====================
    
    def get_market_overview(
        self,
        time_window_days: Optional[int] = 90
    ) -> Dict:
        """
        Overview mercato peptidi.
        
        Args:
            time_window_days: Finestra temporale
            
        Returns:
            Dict con statistiche globali
        """
        conn = self._get_connection()
        
        date_filter = ""
        if time_window_days:
            cutoff = (datetime.now() - timedelta(days=time_window_days)).strftime('%Y-%m-%d')
            date_filter = f"WHERE test_date >= '{cutoff}'"
        
        query = f"""
        SELECT 
            COUNT(*) as total_certificates,
            COUNT(DISTINCT supplier_name) as unique_vendors,
            COUNT(DISTINCT product_name) as unique_products,
            AVG(purity_percentage) as market_avg_purity,
            MIN(purity_percentage) as worst_purity,
            MAX(purity_percentage) as best_purity
        FROM janoshik_certificates
        {date_filter}
        """
        
        cursor = conn.execute(query)
        stats = dict(cursor.fetchone())
        conn.close()
        
        return stats
    
    def get_vendor_peptide_matrix(
        self,
        time_window_days: Optional[int] = 90
    ) -> pd.DataFrame:
        """
        Matrice vendor x peptide con conteggio certificati.
        
        Returns:
            DataFrame pivot con vendors come righe, peptidi come colonne
        """
        conn = self._get_connection()
        
        date_filter = ""
        if time_window_days:
            cutoff = (datetime.now() - timedelta(days=time_window_days)).strftime('%Y-%m-%d')
            date_filter = f"AND test_date >= '{cutoff}'"
        
        query = f"""
        SELECT 
            supplier_name,
            CASE 
                WHEN product_name LIKE '%Tirzepatide%' THEN 'Tirzepatide'
                WHEN product_name LIKE '%Semaglutide%' THEN 'Semaglutide'
                WHEN product_name LIKE '%Retatrutide%' THEN 'Retatrutide'
                ELSE SUBSTR(product_name, 1, INSTR(product_name || ' ', ' ') - 1)
            END as peptide,
            COUNT(*) as count
        FROM janoshik_certificates
        WHERE supplier_name IS NOT NULL
          AND product_name IS NOT NULL
          {date_filter}
        GROUP BY supplier_name, peptide
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        # Pivot
        if not df.empty:
            matrix = df.pivot(index='supplier_name', columns='peptide', values='count').fillna(0)
            return matrix
        
        return pd.DataFrame()
    
    # ==================== QUALITY ANALYSIS ====================
    
    def get_quality_distribution(self) -> Dict[str, int]:
        """
        Distribuzione qualità certificati.
        
        Returns:
            Dict con conteggi per fasce qualità
        """
        conn = self._get_connection()
        
        query = """
        SELECT 
            CASE 
                WHEN purity_percentage >= 99.5 THEN 'Excellent (>99.5%)'
                WHEN purity_percentage >= 99.0 THEN 'Very Good (99-99.5%)'
                WHEN purity_percentage >= 98.0 THEN 'Good (98-99%)'
                WHEN purity_percentage >= 95.0 THEN 'Acceptable (95-98%)'
                ELSE 'Below Standard (<95%)'
            END as quality_tier,
            COUNT(*) as count
        FROM janoshik_certificates
        WHERE purity_percentage IS NOT NULL
        GROUP BY quality_tier
        ORDER BY MIN(purity_percentage) DESC
        """
        
        cursor = conn.execute(query)
        distribution = {row['quality_tier']: row['count'] for row in cursor.fetchall()}
        conn.close()
        
        return distribution
