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
        
        # Carica tutti i certificati
        query = """
        SELECT 
            supplier_name,
            test_date,
            purity_percentage,
            product_name as peptide_name,
            purity_mg_per_vial as quantity_tested_mg,
            endotoxin_eu_per_mg as endotoxin_level
        FROM janoshik_certificates
        WHERE supplier_name IS NOT NULL
          AND supplier_name != ''
          AND purity_percentage IS NOT NULL
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
        
        # Query con CTE per evitare bug SQLite GROUP BY con CASE complesso
        query = f"""
        WITH normalized AS (
            SELECT 
                CASE 
                    -- GLP-1 Agonisti
                    WHEN product_name LIKE '%Tirzepatide%' OR product_name LIKE '%Tirze%' THEN 'Tirzepatide'
                    WHEN product_name LIKE '%Semaglutide%' OR product_name LIKE '%Sema%' THEN 'Semaglutide'
                    WHEN product_name LIKE '%Retatrutide%' OR product_name LIKE '%Reta%' THEN 'Retatrutide'
                    WHEN product_name LIKE '%Liraglutide%' THEN 'Liraglutide'
                    WHEN product_name LIKE '%Dulaglutide%' THEN 'Dulaglutide'
                    
                    -- Peptidi riparativi
                    WHEN product_name LIKE '%BPC%' OR product_name LIKE '%BPC-157%' OR product_name LIKE '%BPC157%' THEN 'BPC-157'
                    WHEN product_name LIKE '%TB-500%' OR product_name LIKE '%TB500%' OR product_name LIKE '%Thymosin%' THEN 'TB-500'
                    WHEN product_name LIKE '%KPV%' THEN 'KPV'
                    WHEN product_name LIKE '%GHK-Cu%' OR product_name LIKE '%GHK%' THEN 'GHK-Cu'
                    
                    -- Growth Hormone Secretagogues
                    WHEN product_name LIKE '%Ipamorelin%' OR product_name LIKE '%Ipam%' THEN 'Ipamorelin'
                    WHEN product_name LIKE '%CJC-1295%' OR product_name LIKE '%CJC%' THEN 'CJC-1295'
                    WHEN product_name LIKE '%Tesamorelin%' OR product_name LIKE '%Tesam%' THEN 'Tesamorelin'
                    WHEN product_name LIKE '%Sermorelin%' THEN 'Sermorelin'
                    WHEN product_name LIKE '%Hexarelin%' THEN 'Hexarelin'
                    WHEN product_name LIKE '%GHRP-2%' THEN 'GHRP-2'
                    WHEN product_name LIKE '%GHRP-6%' THEN 'GHRP-6'
                    WHEN product_name LIKE '%MK-677%' OR product_name LIKE '%Ibutamoren%' THEN 'MK-677'
                    
                    -- HGH/Somatropin
                    WHEN product_name LIKE '%HGH%' OR product_name LIKE '%Somatropin%' OR product_name LIKE '%Qitrope%' THEN 'HGH'
                    
                    -- Peptidi nootropici/cognitivi
                    WHEN product_name LIKE '%Selank%' THEN 'Selank'
                    WHEN product_name LIKE '%Semax%' THEN 'Semax'
                    WHEN product_name LIKE '%Cerebrolysin%' THEN 'Cerebrolysin'
                    WHEN product_name LIKE '%Noopept%' THEN 'Noopept'
                    WHEN product_name LIKE '%P21%' THEN 'P21'
                    
                    -- Anti-aging/longevità
                    WHEN product_name LIKE '%Epithalon%' OR product_name LIKE '%Epitalon%' THEN 'Epithalon'
                    WHEN product_name LIKE '%NAD%' THEN 'NAD+'
                    WHEN product_name LIKE '%NMN%' THEN 'NMN'
                    WHEN product_name LIKE '%MOTS-C%' OR product_name LIKE '%MOTS%' THEN 'MOTS-C'
                    WHEN product_name LIKE '%Humanin%' THEN 'Humanin'
                    WHEN product_name LIKE '%SS-31%' OR product_name LIKE '%Elamipretide%' THEN 'SS-31'
                    
                    -- Peptidi metabolici
                    WHEN product_name LIKE '%AOD-9604%' OR product_name LIKE '%AOD%' THEN 'AOD-9604'
                    WHEN product_name LIKE '%5-Amino-1MQ%' OR product_name LIKE '%5-Amino%' THEN '5-Amino-1MQ'
                    WHEN product_name LIKE '%Tesofensine%' THEN 'Tesofensine'
                    
                    -- Peptidi immunitari
                    WHEN product_name LIKE '%Thymosin Alpha%' OR product_name LIKE '%TA1%' THEN 'Thymosin Alpha-1'
                    WHEN product_name LIKE '%LL-37%' THEN 'LL-37'
                    
                    -- Peptidi sessuali
                    WHEN product_name LIKE '%PT-141%' OR product_name LIKE '%Bremelanotide%' THEN 'PT-141'
                    WHEN product_name LIKE '%Melanotan%' OR product_name LIKE '%MT-2%' THEN 'Melanotan II'
                    WHEN product_name LIKE '%Kisspeptin%' THEN 'Kisspeptin'
                    
                    -- Fallback: prima parola (rimuove dosaggio)
                    ELSE RTRIM(SUBSTR(product_name, 1, INSTR(product_name || ' ', ' ') - 1), '0123456789')
                END as peptide_name,
                supplier_name,
                test_date,
                purity_percentage
            FROM janoshik_certificates
            WHERE product_name IS NOT NULL
              {date_filter}
        )
        SELECT 
            peptide_name,
            COUNT(*) as test_count,
            COUNT(DISTINCT supplier_name) as vendor_count,
            AVG(purity_percentage) as avg_purity,
            MAX(test_date) as most_recent
        FROM normalized
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
