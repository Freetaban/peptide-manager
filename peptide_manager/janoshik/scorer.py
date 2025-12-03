"""
Supplier Scoring & Ranking Algorithm

Calcola score e ranking supplier basato su certificati Janoshik.
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import statistics


class SupplierScorer:
    """Calcola score e ranking supplier da certificati"""
    
    # Pesi algoritmo scoring (totale = 1.0)
    WEIGHT_VOLUME = 0.25       # Numero certificati
    WEIGHT_QUALITY = 0.35      # Purezza media
    WEIGHT_CONSISTENCY = 0.15  # Variabilità purezza
    WEIGHT_RECENCY = 0.15      # Attività recente
    WEIGHT_ENDOTOXIN = 0.10    # Livello endotossine (quando disponibile)
    
    def calculate_rankings(
        self,
        certificates: List[Dict],
        reference_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        Calcola ranking supplier da certificati.
        
        Args:
            certificates: Lista certificati estratti
            reference_date: Data riferimento (default: oggi)
            
        Returns:
            DataFrame con ranking supplier
        """
        if not reference_date:
            reference_date = datetime.now()
        
        # Converti in DataFrame
        df = pd.DataFrame(certificates)
        
        # Estrai supplier_name e normalizza
        df['supplier_name'] = df.apply(self._extract_supplier_name, axis=1)
        df = df[df['supplier_name'].notna()]
        
        if df.empty:
            return pd.DataFrame()
        
        # Group by supplier e calcola metriche
        supplier_stats = []
        for supplier, group in df.groupby('supplier_name'):
            stats = self._calculate_supplier_metrics(group, reference_date)
            stats['supplier_name'] = supplier
            supplier_stats.append(stats)
        
        # Crea DataFrame ranking
        rankings = pd.DataFrame(supplier_stats)
        rankings = rankings.sort_values('total_score', ascending=False)
        rankings['rank_position'] = range(1, len(rankings) + 1)
        
        return rankings
    
    def _extract_supplier_name(self, row: pd.Series) -> Optional[str]:
        """Estrae nome supplier standardizzato"""
        # Priorità: client, manufacturer, website
        supplier = row.get('client') or row.get('manufacturer') or row.get('supplier_name')
        
        if not supplier:
            return None
        
        # Normalizza (lowercase, trim)
        supplier = str(supplier).strip().lower()
        
        # Rimuovi www. se presente
        if supplier.startswith('www.'):
            supplier = supplier[4:]
        
        return supplier
    
    def _calculate_supplier_metrics(
        self,
        certs: pd.DataFrame,
        reference_date: datetime
    ) -> Dict:
        """
        Calcola metriche per singolo supplier.
        
        Args:
            certs: DataFrame certificati del supplier
            reference_date: Data riferimento
            
        Returns:
            Dict con metriche e score
        """
        # Parsing date
        certs = certs.copy()
        certs['test_date'] = pd.to_datetime(
            certs.get('analysis_conducted') or certs.get('test_date'),
            errors='coerce'
        )
        certs = certs[certs['test_date'].notna()]
        
        if certs.empty:
            return self._empty_metrics()
        
        # Metriche base
        total_certs = len(certs)
        recent_certs = len(certs[certs['test_date'] > reference_date - timedelta(days=90)])
        certs_last_30d = len(certs[certs['test_date'] > reference_date - timedelta(days=30)])
        
        # Purezza
        purities = self._extract_purities(certs)
        avg_purity = statistics.mean(purities) if purities else 0
        min_purity = min(purities) if purities else 0
        max_purity = max(purities) if purities else 0
        std_purity = statistics.stdev(purities) if len(purities) > 1 else 0
        
        # Endotossine
        endotoxins = self._extract_endotoxins(certs)
        avg_endotoxin = statistics.mean(endotoxins) if endotoxins else None
        certs_with_endotoxin = len(endotoxins)
        
        # Date gaps
        sorted_dates = certs['test_date'].sort_values()
        gaps = sorted_dates.diff().dt.days.dropna()
        avg_gap = gaps.mean() if len(gaps) > 0 else 0
        
        # Days since last cert
        days_since_last = (reference_date - certs['test_date'].max()).days
        
        # Calcola score components
        volume_score = self._calculate_volume_score(total_certs, certs_last_30d)
        quality_score = self._calculate_quality_score(avg_purity, min_purity)
        consistency_score = self._calculate_consistency_score(std_purity, avg_gap)
        recency_score = self._calculate_recency_score(days_since_last, certs_last_30d)
        endotoxin_score = self._calculate_endotoxin_score(avg_endotoxin, certs_with_endotoxin)
        
        # Score totale
        total_score = (
            volume_score * self.WEIGHT_VOLUME +
            quality_score * self.WEIGHT_QUALITY +
            consistency_score * self.WEIGHT_CONSISTENCY +
            recency_score * self.WEIGHT_RECENCY +
            endotoxin_score * self.WEIGHT_ENDOTOXIN
        )
        
        # Peptidi testati
        peptides = certs['sample'].dropna().unique().tolist()
        
        return {
            'total_certificates': total_certs,
            'recent_certificates': recent_certs,
            'certs_last_30d': certs_last_30d,
            'avg_purity': round(avg_purity, 3),
            'min_purity': round(min_purity, 3),
            'max_purity': round(max_purity, 3),
            'std_purity': round(std_purity, 3),
            'avg_endotoxin_level': round(avg_endotoxin, 3) if avg_endotoxin else None,
            'certs_with_endotoxin': certs_with_endotoxin,
            'days_since_last_cert': int(days_since_last),
            'avg_date_gap': round(avg_gap, 1),
            'peptides_tested': peptides[:10],  # Top 10
            'volume_score': round(volume_score, 2),
            'quality_score': round(quality_score, 2),
            'consistency_score': round(consistency_score, 2),
            'recency_score': round(recency_score, 2),
            'endotoxin_score': round(endotoxin_score, 2),
            'total_score': round(total_score, 2)
        }
    
    def _extract_purities(self, certs: pd.DataFrame) -> List[float]:
        """Estrae valori purezza dai certificati"""
        purities = []
        
        for _, cert in certs.iterrows():
            # Cerca in purity_percentage
            if 'purity_percentage' in cert and pd.notna(cert['purity_percentage']):
                purities.append(float(cert['purity_percentage']))
                continue
            
            # Cerca in results dict
            results = cert.get('results', {})
            if isinstance(results, dict):
                for key, value in results.items():
                    if 'purity' in key.lower():
                        # Parse "99.720%" -> 99.720
                        purity_str = str(value).replace('%', '').strip()
                        try:
                            purities.append(float(purity_str))
                            break
                        except ValueError:
                            pass
        
        return purities
    
    def _extract_endotoxins(self, certs: pd.DataFrame) -> List[float]:
        """Estrae valori endotossine dai certificati (EU/mg)"""
        endotoxins = []
        
        for _, cert in certs.iterrows():
            # Cerca in endotoxin_level
            if 'endotoxin_level' in cert and pd.notna(cert['endotoxin_level']):
                endotoxins.append(float(cert['endotoxin_level']))
                continue
            
            # Cerca in results dict
            results = cert.get('results', {})
            if isinstance(results, dict):
                for key, value in results.items():
                    if 'endotoxin' in key.lower():
                        # Parse "<50 EU/mg" -> 50.0 or "45.3 EU/mg" -> 45.3
                        endotox_str = str(value).replace('<', '').replace('EU/mg', '').strip()
                        try:
                            endotoxins.append(float(endotox_str))
                            break
                        except ValueError:
                            pass
        
        return endotoxins
    
    def _calculate_volume_score(self, total_certs: int, certs_last_30d: int) -> float:
        """
        Score basato su volume certificati (0-100).
        
        Formula:
        - 0 certs → 0
        - 1-5 certs → 20-40
        - 6-15 certs → 41-70
        - 16-30 certs → 71-90
        - 30+ certs → 91-100
        Bonus +10 se >= 3 cert negli ultimi 30 giorni
        """
        base_score = min(100, (total_certs / 30) * 100)
        recent_bonus = 10 if certs_last_30d >= 3 else 0
        return min(100, base_score + recent_bonus)
    
    def _calculate_quality_score(self, avg_purity: float, min_purity: float) -> float:
        """
        Score basato su purezza (0-100).
        
        Formula:
        - avg >= 99% → 90-100
        - avg >= 98% → 70-89
        - avg >= 95% → 50-69
        - avg < 95% → 0-49
        Penalty -20 se min < 95%
        """
        if avg_purity >= 99:
            base = 90 + (avg_purity - 99) * 10
        elif avg_purity >= 98:
            base = 70 + (avg_purity - 98) * 20
        elif avg_purity >= 95:
            base = 50 + (avg_purity - 95) * 6.67
        else:
            base = (avg_purity / 95) * 50
        
        penalty = 20 if min_purity < 95 else 0
        return max(0, min(100, base - penalty))
    
    def _calculate_consistency_score(self, std_purity: float, avg_gap: float) -> float:
        """
        Score basato su consistenza (0-100).
        
        Formula:
        - std < 0.5% → 90-100
        - std < 1.0% → 70-89
        - std < 2.0% → 50-69
        - std >= 2.0% → 0-49
        Bonus +10 se testing regolare (avg gap < 60 giorni)
        """
        if std_purity < 0.5:
            base = 95
        elif std_purity < 1.0:
            base = 80
        elif std_purity < 2.0:
            base = 60
        else:
            base = max(0, 50 - (std_purity - 2) * 10)
        
        regular_bonus = 10 if avg_gap < 60 else 0
        return min(100, base + regular_bonus)
    
    def _calculate_recency_score(self, days_since_last: int, certs_last_30d: int) -> float:
        """
        Score basato su attività recente (0-100).
        
        Formula:
        - < 7 giorni → 100
        - < 30 giorni → 70-99
        - < 90 giorni → 40-69
        - < 180 giorni → 10-39
        - >= 180 giorni → 0-9
        Bonus +15 se >= 2 cert negli ultimi 30 giorni
        """
        if days_since_last < 7:
            base = 100
        elif days_since_last < 30:
            base = 70 + (30 - days_since_last) / 23 * 29
        elif days_since_last < 90:
            base = 40 + (90 - days_since_last) / 60 * 30
        elif days_since_last < 180:
            base = 10 + (180 - days_since_last) / 90 * 30
        else:
            base = max(0, 10 - (days_since_last - 180) / 365 * 10)
        
        active_bonus = 15 if certs_last_30d >= 2 else 0
        return min(100, base + active_bonus)
    
    def _calculate_endotoxin_score(self, avg_endotoxin: Optional[float], certs_with_endotoxin: int) -> float:
        """
        Score basato su livello endotossine (0-100).
        
        Formula:
        - Nessun dato → 50 (neutro)
        - < 10 EU/mg → 100 (eccellente)
        - < 50 EU/mg → 80-99 (buono)
        - < 100 EU/mg → 60-79 (accettabile)
        - < 200 EU/mg → 40-59 (mediocre)
        - >= 200 EU/mg → 0-39 (scarso)
        
        Note: FDA limit per peptidi iniettabili è tipicamente 5-10 EU/mg
        """
        # Se non ci sono dati endotossine, score neutro
        if avg_endotoxin is None or certs_with_endotoxin == 0:
            return 50.0
        
        # Calcola score base su livello medio
        if avg_endotoxin < 10:
            score = 100
        elif avg_endotoxin < 50:
            score = 80 + (50 - avg_endotoxin) / 40 * 19
        elif avg_endotoxin < 100:
            score = 60 + (100 - avg_endotoxin) / 50 * 20
        elif avg_endotoxin < 200:
            score = 40 + (200 - avg_endotoxin) / 100 * 20
        else:
            score = max(0, 40 - (avg_endotoxin - 200) / 100 * 10)
        
        # Bonus se molti certificati hanno test endotossine (indica trasparenza)
        if certs_with_endotoxin >= 5:
            score = min(100, score + 5)
        
        return score
    
    def _empty_metrics(self) -> Dict:
        """Ritorna metriche vuote"""
        return {
            'total_certificates': 0,
            'recent_certificates': 0,
            'certs_last_30d': 0,
            'avg_purity': 0.0,
            'min_purity': 0.0,
            'max_purity': 0.0,
            'std_purity': 0.0,
            'avg_endotoxin_level': None,
            'certs_with_endotoxin': 0,
            'days_since_last_cert': 999,
            'avg_date_gap': 0.0,
            'peptides_tested': [],
            'volume_score': 0.0,
            'quality_score': 0.0,
            'consistency_score': 0.0,
            'recency_score': 0.0,
            'endotoxin_score': 50.0,
            'total_score': 0.0
        }
