"""
Data Models - Supplier Ranking

Rappresenta un ranking snapshot di un supplier.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict
import json


@dataclass
class SupplierRanking:
    """Ranking snapshot di un supplier"""
    
    # Identification
    supplier_name: str
    supplier_website: Optional[str] = None
    
    # Metrics
    total_certificates: int = 0
    recent_certificates: int = 0  # Last 90 days
    certs_last_30d: int = 0
    
    # Purity metrics
    avg_purity: float = 0.0
    min_purity: float = 0.0
    max_purity: float = 0.0
    std_purity: float = 0.0
    
    # Accuracy metrics (quantity declared vs tested)
    avg_accuracy: Optional[float] = None
    certs_with_accuracy: int = 0
    
    # Endotoxin metrics
    avg_endotoxin_level: Optional[float] = None
    certs_with_endotoxin: int = 0
    
    # Testing completeness metrics
    testing_completeness_score: float = 50.0  # Default neutral
    batches_fully_tested: int = 0  # Batches with all 4 test types
    total_batches_tracked: int = 0
    avg_tests_per_batch: float = 1.0
    
    # Score components (0-100)
    volume_score: float = 0.0
    quality_score: float = 0.0
    accuracy_score: float = 50.0  # Default neutral
    consistency_score: float = 0.0
    recency_score: float = 0.0
    
    # Final score
    total_score: float = 0.0
    rank_position: Optional[int] = None
    
    # Metadata
    days_since_last_cert: int = 999
    avg_date_gap: float = 0.0
    peptides_tested: List[str] = field(default_factory=list)
    calculated_at: datetime = field(default_factory=datetime.now)
    data_snapshot: Optional[str] = None  # JSON
    
    # Database ID (set after insert)
    id: Optional[int] = None
    
    def to_dict(self) -> Dict:
        """Converte a dict per database insert (solo colonne esistenti)"""
        return {
            'supplier_name': self.supplier_name,
            'total_score': self.total_score,
            'volume_score': self.volume_score,
            'quality_score': self.quality_score,
            'consistency_score': self.consistency_score,
            'recency_score': self.recency_score,
            'endotoxin_score': self.accuracy_score,  # DB usa endotoxin_score per accuracy
            'cert_count': self.total_certificates,
            'avg_purity': self.avg_purity,
            'min_purity': self.min_purity,
            'purity_std_dev': self.std_purity,
            'recent_cert_count': self.recent_certificates,
            'last_cert_date': '',  # Non disponibile ora
            'avg_endotoxin': self.avg_endotoxin_level or 0.0,
            'has_endotoxin_tests': int(self.certs_with_endotoxin > 0),
            'rank_position': self.rank_position,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'SupplierRanking':
        """Crea istanza da dict (database row)"""
        # Parse datetime
        if data.get('calculated_at') and isinstance(data['calculated_at'], str):
            try:
                data['calculated_at'] = datetime.fromisoformat(data['calculated_at'])
            except ValueError:
                data['calculated_at'] = datetime.now()
        
        # Parse JSON fields
        if data.get('peptides_tested') and isinstance(data['peptides_tested'], str):
            try:
                data['peptides_tested'] = json.loads(data['peptides_tested'])
            except json.JSONDecodeError:
                data['peptides_tested'] = []
        
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    @classmethod
    def from_scorer_output(cls, scorer_data: Dict) -> 'SupplierRanking':
        """
        Crea istanza da output SupplierScorer.
        
        Args:
            scorer_data: Dict da SupplierScorer._calculate_supplier_metrics()
            
        Returns:
            SupplierRanking instance
        """
        return cls(
            supplier_name=scorer_data.get('supplier_name', 'unknown'),
            supplier_website=None,  # Da inferire dai certificati
            total_certificates=scorer_data.get('total_certificates', 0),
            recent_certificates=scorer_data.get('recent_certificates', 0),
            certs_last_30d=scorer_data.get('certs_last_30d', 0),
            avg_purity=scorer_data.get('avg_purity', 0.0),
            min_purity=scorer_data.get('min_purity', 0.0),
            max_purity=scorer_data.get('max_purity', 0.0),
            std_purity=scorer_data.get('std_purity', 0.0),
            avg_accuracy=scorer_data.get('avg_accuracy'),
            certs_with_accuracy=scorer_data.get('certs_with_accuracy', 0),
            avg_endotoxin_level=scorer_data.get('avg_endotoxin_level'),
            certs_with_endotoxin=scorer_data.get('certs_with_endotoxin', 0),
            testing_completeness_score=scorer_data.get('testing_completeness_score', 50.0),
            batches_fully_tested=scorer_data.get('batches_fully_tested', 0),
            total_batches_tracked=scorer_data.get('total_batches_tracked', 0),
            avg_tests_per_batch=scorer_data.get('avg_tests_per_batch', 1.0),
            volume_score=scorer_data.get('volume_score', 0.0),
            quality_score=scorer_data.get('quality_score', 0.0),
            accuracy_score=scorer_data.get('accuracy_score', 50.0),
            consistency_score=scorer_data.get('consistency_score', 0.0),
            recency_score=scorer_data.get('recency_score', 0.0),
            total_score=scorer_data.get('total_score', 0.0),
            rank_position=scorer_data.get('rank_position'),
            days_since_last_cert=scorer_data.get('days_since_last_cert', 999),
            avg_date_gap=scorer_data.get('avg_date_gap', 0.0),
            peptides_tested=scorer_data.get('peptides_tested', []),
            data_snapshot=json.dumps(scorer_data)
        )
    
    def get_quality_badge(self) -> str:
        """Ritorna emoji badge basato su total_score"""
        if self.total_score >= 80:
            return "🔥"  # HOT
        elif self.total_score >= 60:
            return "✅"  # Good
        elif self.total_score >= 40:
            return "⚠️"   # Mediocre
        else:
            return "❌"  # Poor
    
    def get_quality_label(self) -> str:
        """Ritorna label testuale basato su total_score"""
        if self.total_score >= 80:
            return "HOT (Top tier)"
        elif self.total_score >= 60:
            return "Buono (Affidabile)"
        elif self.total_score >= 40:
            return "Mediocre (Da valutare)"
        else:
            return "Scarso (Red flag)"
    
    def __repr__(self) -> str:
        badge = self.get_quality_badge()
        return f"<SupplierRanking #{self.rank_position} {badge} {self.supplier_name}: {self.total_score:.1f}>"
