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
    WEIGHT_VOLUME = 0.20          # Numero certificati
    WEIGHT_QUALITY = 0.25         # Purezza media
    WEIGHT_ACCURACY = 0.20        # Accuratezza quantità (dichiarato vs testato)
    WEIGHT_CONSISTENCY = 0.15     # Variabilità purezza
    WEIGHT_RECENCY = 0.10         # Attività recente
    WEIGHT_TESTING_COMPLETENESS = 0.10  # Completezza test (purity + endotoxin + heavy_metals + microbiology)
    
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
        # Priorità: supplier_name (già manufacturer), client, manufacturer
        supplier = row.get('supplier_name') or row.get('manufacturer') or row.get('client')
        
        if not supplier:
            return None
        
        # Normalizza (lowercase, trim)
        supplier = str(supplier).strip().lower()
        
        # Rimuovi protocolli web
        for prefix in ['https://', 'http://']:
            if supplier.startswith(prefix):
                supplier = supplier[len(prefix):]
        
        # Rimuovi www. se presente
        if supplier.startswith('www.'):
            supplier = supplier[4:]
        
        # Rimuovi trailing slash
        if supplier.endswith('/'):
            supplier = supplier[:-1]
        
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
        
        # Usa fillna per gestire Series pandas correttamente
        date_col = certs['analysis_conducted'].fillna(certs['test_date']) if 'analysis_conducted' in certs.columns else certs.get('test_date', pd.Series())
        certs['test_date'] = pd.to_datetime(date_col, errors='coerce')
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
        
        # Accuracy quantità (dichiarato vs testato)
        accuracies = self._calculate_quantity_accuracies(certs)
        avg_accuracy = statistics.mean(accuracies) if accuracies else None
        certs_with_accuracy = len(accuracies)
        
        # Testing completeness (raggruppa per batch e controlla test opzionali)
        testing_completeness_metrics = self._calculate_testing_completeness(certs)
        
        # Date gaps
        sorted_dates = certs['test_date'].sort_values()
        gaps = sorted_dates.diff().dt.days.dropna()
        avg_gap = gaps.mean() if len(gaps) > 0 else 0
        
        # Days since last cert
        days_since_last = (reference_date - certs['test_date'].max()).days
        
        # Calcola score components
        volume_score = self._calculate_volume_score(total_certs, certs_last_30d)
        quality_score = self._calculate_quality_score(avg_purity, min_purity)
        accuracy_score = self._calculate_accuracy_score(avg_accuracy, certs_with_accuracy)
        consistency_score = self._calculate_consistency_score(std_purity, avg_gap)
        recency_score = self._calculate_recency_score(days_since_last, certs_last_30d)
        testing_completeness_score = testing_completeness_metrics['score']
        
        # Score totale
        total_score = (
            volume_score * self.WEIGHT_VOLUME +
            quality_score * self.WEIGHT_QUALITY +
            accuracy_score * self.WEIGHT_ACCURACY +
            consistency_score * self.WEIGHT_CONSISTENCY +
            recency_score * self.WEIGHT_RECENCY +
            testing_completeness_score * self.WEIGHT_TESTING_COMPLETENESS
        )
        
        # Peptidi testati (usa 'peptide_name' se 'sample' non esiste)
        sample_col = 'sample' if 'sample' in certs.columns else 'peptide_name'
        peptides = certs[sample_col].dropna().unique().tolist() if sample_col in certs.columns else []
        
        return {
            'total_certificates': total_certs,
            'recent_certificates': recent_certs,
            'certs_last_30d': certs_last_30d,
            'avg_purity': round(avg_purity, 3),
            'min_purity': round(min_purity, 3),
            'max_purity': round(max_purity, 3),
            'std_purity': round(std_purity, 3),
            'avg_accuracy': round(avg_accuracy, 2) if avg_accuracy else None,
            'certs_with_accuracy': certs_with_accuracy,
            'avg_endotoxin_level': round(avg_endotoxin, 3) if avg_endotoxin else None,
            'certs_with_endotoxin': certs_with_endotoxin,
            'testing_completeness_score': round(testing_completeness_score, 2),
            'batches_fully_tested': testing_completeness_metrics['fully_tested'],
            'total_batches_tracked': testing_completeness_metrics['total_batches'],
            'avg_tests_per_batch': round(testing_completeness_metrics['avg_tests'], 2),
            'days_since_last_cert': int(days_since_last),
            'avg_date_gap': round(avg_gap, 1),
            'peptides_tested': peptides[:10],  # Top 10
            'volume_score': round(volume_score, 2),
            'quality_score': round(quality_score, 2),
            'accuracy_score': round(accuracy_score, 2),
            'consistency_score': round(consistency_score, 2),
            'recency_score': round(recency_score, 2),
            'total_score': round(total_score, 2)
        }
    
    def _extract_purities(self, certs: pd.DataFrame) -> List[float]:
        """
        Estrae valori purezza/quality dai certificati.
        Priorità: effective_quality_score > purity_percentage > results dict
        """
        purities = []
        
        for _, cert in certs.iterrows():
            # Prima priorità: effective_quality_score (include IU accuracy)
            if 'effective_quality_score' in cert and pd.notna(cert['effective_quality_score']):
                purities.append(float(cert['effective_quality_score']))
                continue
            
            # Seconda priorità: purity_percentage
            if 'purity_percentage' in cert and pd.notna(cert['purity_percentage']):
                purities.append(float(cert['purity_percentage']))
                continue
            
            # Terza priorità: cerca in results dict
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
    
    def _calculate_quantity_accuracies(self, certs: pd.DataFrame) -> List[float]:
        """
        Calcola accuracy quantità (dichiarato vs testato) per ogni certificato.
        
        Logica:
        1. Outliers detection: scostamenti > ±50% esclusi (probabili mislabeling)
        2. Scostamenti negativi penalizzati > positivi (meno mg è peggio)
        3. Range ottimale: -5% / +15%
        
        Uses:
        - quantity_nominal: Declared quantity from DB (standardized)
        - quantity_tested_mg: Actual tested quantity
        - unit_of_measure: Unit verification (only compare same units)
        
        Returns:
            Lista di accuracy scores (0-100)
        """
        accuracies = []
        
        for _, cert in certs.iterrows():
            # Quantità testata
            qty_tested = cert.get('quantity_tested_mg')
            if not qty_tested or pd.isna(qty_tested):
                continue
            
            # Quantità dichiarata (da DB standardizzato)
            qty_declared = cert.get('quantity_nominal')
            if not qty_declared or pd.isna(qty_declared):
                # Fallback: estrai dal nome se quantity_nominal non disponibile
                import re
                sample = cert.get('sample') or cert.get('peptide_name', '')
                match = re.search(r'(\d+(?:\.\d+)?)\s*mg', str(sample), re.IGNORECASE)
                if not match:
                    continue
                qty_declared = float(match.group(1))
            else:
                qty_declared = float(qty_declared)
            
            # Verifica unità di misura
            unit = cert.get('unit_of_measure', 'mg')
            unit_str = str(unit).lower() if unit else 'mg'
            
            # Accetta mg e IU (stessa logica di confronto)
            # IU (International Units) usate per HCG, HGH, etc.
            if unit_str not in ['mg', 'iu']:
                # Skip mcg, g, etc - non confrontabili
                continue
            
            # Scostamento percentuale
            deviation_pct = ((qty_tested - qty_declared) / qty_declared) * 100
            
            # OUTLIER DETECTION: escludi scostamenti > ±50% (probabili mislabeling)
            if abs(deviation_pct) > 50:
                # Non considerare questi certificati nel calcolo accuracy
                continue
            
            # CALCOLO ACCURACY come metrica continua
            # Baseline: 100 se perfettamente uguale (0% deviation)
            # Negative deviations: penalità crescente (meno mg = peggio)
            # Positive deviations: bonus crescente (più mg = meglio)
            
            if deviation_pct == 0:
                # Perfetto
                accuracy = 100.0
            elif deviation_pct < 0:
                # NEGATIVO (meno mg del dichiarato) - PEGGIO
                # Penalità: -2 punti per ogni 1% di scostamento
                # -5% → 90, -10% → 80, -20% → 60, -25% → 50, -50% → 0
                penalty = abs(deviation_pct) * 2
                accuracy = max(0, 100 - penalty)
            else:
                # POSITIVO (più mg del dichiarato) - MEGLIO
                # Bonus: +1 punto per ogni 1% di scostamento (fino a max 120)
                # +5% → 105, +10% → 110, +20% → 120, +30% → 120 (cap)
                bonus = deviation_pct * 1
                accuracy = min(120, 100 + bonus)
            
            accuracies.append(accuracy)
        
        return accuracies
    
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
    
    def _calculate_accuracy_score(self, avg_accuracy: Optional[float], certs_with_accuracy: int) -> float:
        """
        Score basato su accuracy quantità (0-100).
        
        Args:
            avg_accuracy: Media accuracy % (0-100)
            certs_with_accuracy: Numero certificati con dato quantità
        
        Formula:
        - Se nessun dato disponibile → 50 (neutro)
        - avg >= 95% → 90-100
        - avg >= 90% → 80-89
        - avg >= 80% → 60-79
        - avg < 80% → 0-59
        Bonus +5 se > 3 certificati con dato quantità
        """
        if avg_accuracy is None or certs_with_accuracy == 0:
            return 50.0  # Score neutro se dato non disponibile
        
        if avg_accuracy >= 95:
            base = 90 + (avg_accuracy - 95) * 2
        elif avg_accuracy >= 90:
            base = 80 + (avg_accuracy - 90) * 2
        elif avg_accuracy >= 80:
            base = 60 + (avg_accuracy - 80) * 2
        else:
            base = (avg_accuracy / 80) * 60
        
        bonus = 5 if certs_with_accuracy > 3 else 0
        return min(100, base + bonus)
    
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
    
    def _calculate_testing_completeness(self, certs: pd.DataFrame) -> Dict:
        """
        Calcola score completezza testing per supplier (0-100).
        
        Raggruppa per (peptide_name, batch_number) e verifica presenza di 4 tipi test:
        1. Purity (sempre presente)
        2. Endotoxin
        3. Heavy Metals
        4. Microbiology (TAMC/TYMC)
        
        Score per batch:
        - Solo purity → 50 punti (base)
        - + endotoxin → +15 punti
        - + heavy metals → +15 punti
        - + microbiology → +15 punti
        - Tutti e 4 → +5 bonus = 100 punti
        
        Score finale supplier = media dei batch
        
        Returns:
            Dict con score, batches_fully_tested, total_batches, avg_tests_per_batch
        """
        if certs.empty:
            return {
                'score': 50.0,
                'fully_tested': 0,
                'total_batches': 0,
                'avg_tests': 1.0
            }
        
        # Raggruppa per (peptide_name, batch_number)
        # Se batch_number è None, usa task_number come fallback
        certs_copy = certs.copy()
        certs_copy['batch_key'] = certs_copy.apply(
            lambda row: f"{row.get('peptide_name', 'unknown')}_{row.get('batch_number') or row.get('task_number', 'unknown')}",
            axis=1
        )
        
        batch_scores = []
        fully_tested = 0
        total_tests_count = 0
        
        for batch_key, batch_certs in certs_copy.groupby('batch_key'):
            # Conta test types presenti
            has_purity = False
            has_endotoxin = False
            has_heavy_metals = False
            has_microbiology = False
            
            for _, cert in batch_certs.iterrows():
                test_cat = cert.get('test_category', 'purity')
                
                if test_cat == 'purity' or pd.notna(cert.get('purity_percentage')):
                    has_purity = True
                if test_cat == 'endotoxin' or pd.notna(cert.get('endotoxin_level')):
                    has_endotoxin = True
                if test_cat == 'heavy_metals' or pd.notna(cert.get('heavy_metals_result')):
                    has_heavy_metals = True
                if test_cat == 'microbiology' or (pd.notna(cert.get('microbiology_tamc')) or pd.notna(cert.get('microbiology_tymc'))):
                    has_microbiology = True
            
            # Calcola score batch
            score = 50.0  # Base
            tests_count = 1  # Purity sempre presente
            
            if has_endotoxin:
                score += 15
                tests_count += 1
            if has_heavy_metals:
                score += 15
                tests_count += 1
            if has_microbiology:
                score += 15
                tests_count += 1
            
            # Bonus se tutti e 4 test presenti
            if has_purity and has_endotoxin and has_heavy_metals and has_microbiology:
                score += 5  # Bonus completezza
                fully_tested += 1
            
            batch_scores.append(score)
            total_tests_count += tests_count
        
        # Media score
        avg_score = statistics.mean(batch_scores) if batch_scores else 50.0
        avg_tests = total_tests_count / len(batch_scores) if batch_scores else 1.0
        
        return {
            'score': avg_score,
            'fully_tested': fully_tested,
            'total_batches': len(batch_scores),
            'avg_tests': avg_tests
        }
    
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
            'testing_completeness_score': 50.0,
            'batches_fully_tested': 0,
            'total_batches_tracked': 0,
            'avg_tests_per_batch': 1.0,
            'days_since_last_cert': 999,
            'avg_date_gap': 0.0,
            'peptides_tested': [],
            'volume_score': 0.0,
            'quality_score': 0.0,
            'consistency_score': 0.0,
            'recency_score': 0.0,
            'total_score': 0.0
        }
