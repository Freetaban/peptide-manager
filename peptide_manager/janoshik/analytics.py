"""
Janoshik Analytics Module

Query analitiche avanzate per analisi mercato peptidi.
"""

import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import pandas as pd
from .scorer import SupplierScorer


class JanoshikAnalytics:
    """Analisi avanzate su dati Janoshik"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.scorer = SupplierScorer()
    
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
        Top vendors con scoring completo (6 componenti).
        
        Componenti score:
        - Volume (20%): Numero certificati + attività recente
        - Quality (25%): Purezza media e minima
        - Accuracy (20%): Accuratezza quantità dichiarata vs testata
        - Consistency (15%): Variabilità purezza
        - Recency (10%): Attività recente
        - Testing Completeness (10%): Test completi (endotossine, metalli, micro)
        
        Args:
            time_window_days: Ultimi N giorni (None = tutti)
            min_certificates: Minimo certificati per qualificarsi
            limit: Numero risultati
            
        Returns:
            DataFrame con ranking vendors (ordinato per total_score)
        """
        conn = self._get_connection()
        
        # Carica tutti i certificati (con campi standardizzati)
        # Includiamo certificati IU (hormones) anche se purity è NULL
        query = """
        SELECT 
            supplier_name,
            test_date,
            purity_percentage,
            product_name as peptide_name,
            purity_mg_per_vial as quantity_tested_mg,
            endotoxin_eu_per_mg as endotoxin_level,
            peptide_name_std,
            quantity_nominal,
            unit_of_measure,
            CASE 
                WHEN purity_percentage IS NOT NULL AND purity_percentage > 0 THEN purity_percentage
                WHEN unit_of_measure IN ('mg', 'IU') AND quantity_tested_mg IS NOT NULL AND quantity_nominal IS NOT NULL AND quantity_nominal > 0 
                THEN (quantity_tested_mg * 100.0 / quantity_nominal)
                ELSE NULL
            END as effective_quality_score
        FROM janoshik_certificates
        WHERE supplier_name IS NOT NULL
          AND supplier_name != ''
          AND (
              (purity_percentage IS NOT NULL AND purity_percentage > 0)
              OR 
              (unit_of_measure IN ('mg', 'IU') AND quantity_tested_mg IS NOT NULL AND quantity_nominal > 0)
          )
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if df.empty:
            return pd.DataFrame()
        
        # Filtra per time window se specificato
        if time_window_days:
            cutoff = (datetime.now() - timedelta(days=time_window_days)).strftime('%Y-%m-%d')
            df['test_date'] = pd.to_datetime(df['test_date'])
            df = df[df['test_date'] >= cutoff]
        
        # Converti in dict per scorer
        certificates = df.to_dict('records')
        
        # Calcola rankings con scorer completo
        rankings = self.scorer.calculate_rankings(certificates)
        
        if rankings.empty:
            return pd.DataFrame()
        
        # Filtra per min_certificates
        rankings = rankings[rankings['total_certificates'] >= min_certificates]
        
        # Prendi top N
        rankings = rankings.head(limit)
        
        # Calcola days_since_last_test per compatibilità
        rankings['days_since_last_test'] = rankings['days_since_last_cert']
        
        # Rinomina colonne per compatibilità con views_logic
        rankings['total_certificates'] = rankings['total_certificates']
        rankings['avg_purity'] = rankings['avg_purity']
        rankings['min_purity'] = rankings['min_purity']
        rankings['max_purity'] = rankings['max_purity']
        rankings['endotoxin_tests'] = rankings['certs_with_endotoxin']
        rankings['last_test_date'] = ''  # Non disponibile dal scorer
        rankings['products_tested'] = rankings['peptides_tested'].apply(
            lambda x: ', '.join(x) if isinstance(x, list) else ''
        )
        rankings['composite_score'] = rankings['total_score']
        
        return rankings
    
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
        
        # Usa peptide_name_std per match esatto (più accurato del LIKE)
        # Includiamo certificati IU (hormones) anche se purity è NULL
        query = f"""
        SELECT 
            supplier_name,
            COUNT(*) as certificates,
            AVG(CASE 
                WHEN purity_percentage IS NOT NULL AND purity_percentage > 0 THEN purity_percentage
                WHEN unit_of_measure IN ('mg', 'IU') AND quantity_tested_mg IS NOT NULL AND quantity_nominal IS NOT NULL AND quantity_nominal > 0 
                THEN (quantity_tested_mg * 100.0 / quantity_nominal)
                ELSE NULL
            END) as avg_purity,
            MAX(test_date) as most_recent_test,
            AVG(quantity_nominal) as avg_quantity_declared,
            GROUP_CONCAT(DISTINCT unit_of_measure) as units_available,
            GROUP_CONCAT(product_name || ' (' || COALESCE(CAST(purity_percentage AS TEXT), 'N/A') || '%)') as products
        FROM janoshik_certificates
        WHERE peptide_name_std = '{peptide_name}'
          {date_filter}
          AND supplier_name IS NOT NULL
          AND (
              (purity_percentage IS NOT NULL AND purity_percentage > 0)
              OR 
              (unit_of_measure IN ('mg', 'IU') AND quantity_tested_mg IS NOT NULL AND quantity_nominal > 0)
          )
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
        time_window_days: Optional[int] = None,
        min_certificates: int = 2,
        limit: int = 20
    ) -> pd.DataFrame:
        """
        Peptidi più testati nel periodo (trending).
        
        Args:
            time_window_days: Finestra temporale (None = tutti i tempi)
            min_certificates: Minimo certificati
            limit: Numero risultati
            
        Returns:
            DataFrame con peptidi trending
        """
        conn = self._get_connection()
        
        # Filtro temporale (None = tutti i certificati)
        date_filter = ""
        if time_window_days:
            cutoff = (datetime.now() - timedelta(days=time_window_days)).strftime('%Y-%m-%d')
            date_filter = f"AND test_date >= '{cutoff}'"
        
        # Query semplificata usando peptide_name_std (no parsing runtime)
        # Filtra peptidi sospetti: 
        # - nomi <3 caratteri sempre
        # - nomi 3-4 caratteri con <=3 certificati
        # Includiamo certificati IU (hormones) anche se purity è NULL
        query = f"""
        SELECT 
            peptide_name_std as peptide_name,
            COUNT(*) as test_count,
            COUNT(DISTINCT supplier_name) as vendor_count,
            AVG(CASE 
                WHEN purity_percentage IS NOT NULL AND purity_percentage > 0 THEN purity_percentage
                WHEN unit_of_measure IN ('mg', 'IU') AND quantity_tested_mg IS NOT NULL AND quantity_nominal IS NOT NULL AND quantity_nominal > 0 
                THEN (quantity_tested_mg * 100.0 / quantity_nominal)
                ELSE NULL
            END) as avg_purity,
            MIN(CASE 
                WHEN purity_percentage IS NOT NULL AND purity_percentage > 0 THEN purity_percentage
                WHEN unit_of_measure IN ('mg', 'IU') AND quantity_tested_mg IS NOT NULL AND quantity_nominal IS NOT NULL AND quantity_nominal > 0 
                THEN (quantity_tested_mg * 100.0 / quantity_nominal)
                ELSE NULL
            END) as min_purity,
            MAX(CASE 
                WHEN purity_percentage IS NOT NULL AND purity_percentage > 0 THEN purity_percentage
                WHEN unit_of_measure IN ('mg', 'IU') AND quantity_tested_mg IS NOT NULL AND quantity_nominal IS NOT NULL AND quantity_nominal > 0 
                THEN (quantity_tested_mg * 100.0 / quantity_nominal)
                ELSE NULL
            END) as max_purity,
            MAX(test_date) as most_recent,
            GROUP_CONCAT(DISTINCT unit_of_measure) as units_tested,
            LENGTH(peptide_name_std) as name_length
        FROM janoshik_certificates
        WHERE peptide_name_std IS NOT NULL
          AND peptide_name_std != ''
          AND (
              (purity_percentage IS NOT NULL AND purity_percentage > 0)
              OR 
              (unit_of_measure IN ('mg', 'IU') AND quantity_tested_mg IS NOT NULL AND quantity_nominal > 0)
          )
          {date_filter}
        GROUP BY peptide_name_std
        HAVING test_count >= {min_certificates}
           AND name_length >= 3
           AND NOT (name_length <= 4 AND test_count <= 3)
        ORDER BY test_count DESC, most_recent DESC
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
        
        # Usa peptide_name_std per match esatto
        # Includiamo certificati IU (hormones) anche se purity è NULL
        query = f"""
        SELECT 
            supplier_name,
            COUNT(*) as certificates,
            AVG(CASE 
                WHEN purity_percentage IS NOT NULL AND purity_percentage > 0 THEN purity_percentage
                WHEN unit_of_measure IN ('mg', 'IU') AND quantity_tested_mg IS NOT NULL AND quantity_nominal IS NOT NULL AND quantity_nominal > 0 
                THEN (quantity_tested_mg * 100.0 / quantity_nominal)
                ELSE NULL
            END) as avg_purity,
            MIN(CASE 
                WHEN purity_percentage IS NOT NULL AND purity_percentage > 0 THEN purity_percentage
                WHEN unit_of_measure IN ('mg', 'IU') AND quantity_tested_mg IS NOT NULL AND quantity_nominal IS NOT NULL AND quantity_nominal > 0 
                THEN (quantity_tested_mg * 100.0 / quantity_nominal)
                ELSE NULL
            END) as min_purity,
            MAX(CASE 
                WHEN purity_percentage IS NOT NULL AND purity_percentage > 0 THEN purity_percentage
                WHEN unit_of_measure IN ('mg', 'IU') AND quantity_tested_mg IS NOT NULL AND quantity_nominal IS NOT NULL AND quantity_nominal > 0 
                THEN (quantity_tested_mg * 100.0 / quantity_nominal)
                ELSE NULL
            END) as max_purity,
            MAX(test_date) as last_test,
            AVG(quantity_nominal) as avg_quantity_declared,
            GROUP_CONCAT(DISTINCT unit_of_measure) as units_available,
            GROUP_CONCAT(task_number) as task_numbers
        FROM janoshik_certificates
        WHERE peptide_name_std = '{peptide_name}'
          {date_filter}
          AND supplier_name IS NOT NULL
          AND (
              (purity_percentage IS NOT NULL AND purity_percentage > 0)
              OR 
              (unit_of_measure IN ('mg', 'IU') AND quantity_tested_mg IS NOT NULL AND quantity_nominal > 0)
          )
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
        WHERE purity_percentage IS NOT NULL
          AND purity_percentage > 0
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
        
        # Usa peptide_name_std per matrice (no parsing runtime)
        query = f"""
        SELECT 
            supplier_name,
            peptide_name_std as peptide,
            COUNT(*) as count
        FROM janoshik_certificates
        WHERE supplier_name IS NOT NULL
          AND peptide_name_std IS NOT NULL
          AND peptide_name_std != ''
          {date_filter}
        GROUP BY supplier_name, peptide_name_std
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
