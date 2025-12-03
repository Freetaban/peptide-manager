"""
Data Models - Janoshik Certificate

Rappresenta un certificato di analisi Janoshik.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict


@dataclass
class JanoshikCertificate:
    """Certificato di analisi Janoshik"""
    
    # Required fields
    task_number: str
    supplier_name: str
    peptide_name: str
    test_date: datetime
    
    # Optional fields
    supplier_website: Optional[str] = None
    batch_number: Optional[str] = None
    testing_ordered: Optional[datetime] = None
    sample_received: Optional[datetime] = None
    analysis_conducted: Optional[datetime] = None
    
    # Analytical results
    purity_percentage: Optional[float] = None
    quantity_tested_mg: Optional[float] = None
    endotoxin_level: Optional[float] = None  # EU/mg
    
    # Metadata
    test_type: Optional[str] = None
    comments: Optional[str] = None
    verification_key: Optional[str] = None
    raw_data: Optional[str] = None  # JSON string
    
    # File tracking
    image_file: Optional[str] = None
    image_hash: Optional[str] = None
    
    # Processing
    scraped_at: datetime = field(default_factory=datetime.now)
    processed: bool = False
    
    # Database ID (set after insert)
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        """Converte a dict per database insert"""
        return {
            'task_number': self.task_number,
            'supplier_name': self.supplier_name,
            'supplier_website': self.supplier_website,
            'peptide_name': self.peptide_name,
            'batch_number': self.batch_number,
            'test_date': self.test_date.isoformat() if isinstance(self.test_date, datetime) else self.test_date,
            'testing_ordered': self.testing_ordered.isoformat() if isinstance(self.testing_ordered, datetime) else self.testing_ordered,
            'sample_received': self.sample_received.isoformat() if isinstance(self.sample_received, datetime) else self.sample_received,
            'analysis_conducted': self.analysis_conducted.isoformat() if isinstance(self.analysis_conducted, datetime) else self.analysis_conducted,
            'purity_percentage': self.purity_percentage,
            'quantity_tested_mg': self.quantity_tested_mg,
            'endotoxin_level': self.endotoxin_level,
            'test_type': self.test_type,
            'comments': self.comments,
            'verification_key': self.verification_key,
            'raw_data': self.raw_data,
            'image_file': self.image_file,
            'image_hash': self.image_hash,
            'scraped_at': self.scraped_at.isoformat() if isinstance(self.scraped_at, datetime) else self.scraped_at,
            'processed': int(self.processed),
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'JanoshikCertificate':
        """Crea istanza da dict (database row)"""
        # Parse date strings
        for date_field in ['test_date', 'testing_ordered', 'sample_received', 
                          'analysis_conducted', 'scraped_at', 'created_at']:
            if data.get(date_field) and isinstance(data[date_field], str):
                try:
                    data[date_field] = datetime.fromisoformat(data[date_field])
                except ValueError:
                    data[date_field] = None
        
        # Parse boolean
        if 'processed' in data:
            data['processed'] = bool(data['processed'])
        
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    @classmethod
    def from_extracted_data(cls, extracted: Dict, image_file: str, image_hash: str) -> 'JanoshikCertificate':
        """
        Crea istanza da dati estratti da LLM.
        
        Args:
            extracted: Dict con dati estratti da LLM
            image_file: Path file immagine
            image_hash: Hash immagine
            
        Returns:
            JanoshikCertificate instance
        """
        import json
        from dateutil import parser
        
        # Parse dates
        def parse_date(date_str: Optional[str]) -> Optional[datetime]:
            if not date_str:
                return None
            try:
                return parser.parse(date_str)
            except (ValueError, TypeError):
                return None
        
        # Estrai purity e endotoxin da results
        purity = None
        endotoxin = None
        quantity = None
        
        results = extracted.get('results', {})
        if isinstance(results, dict):
            for key, value in results.items():
                key_lower = key.lower()
                value_str = str(value).replace('%', '').replace('EU/mg', '').replace('<', '').strip()
                
                try:
                    if 'purity' in key_lower:
                        purity = float(value_str)
                    elif 'endotoxin' in key_lower:
                        endotoxin = float(value_str)
                    elif 'mg' in str(value).lower() and not 'eu/mg' in str(value).lower():
                        # Quantity (es: "44.33 mg")
                        quantity = float(value_str.replace('mg', '').strip())
                except (ValueError, AttributeError):
                    pass
        
        # Fallback per purity_percentage
        if not purity and 'purity_percentage' in extracted:
            purity = extracted.get('purity_percentage')
        
        return cls(
            task_number=extracted.get('task_number', 'unknown'),
            supplier_name=extracted.get('client') or extracted.get('manufacturer') or 'unknown',
            supplier_website=extracted.get('manufacturer'),
            peptide_name=extracted.get('sample', 'unknown'),
            batch_number=extracted.get('batch'),
            test_date=parse_date(extracted.get('analysis_conducted')) or datetime.now(),
            testing_ordered=parse_date(extracted.get('testing_ordered')),
            sample_received=parse_date(extracted.get('sample_received')),
            analysis_conducted=parse_date(extracted.get('analysis_conducted')),
            purity_percentage=purity,
            quantity_tested_mg=quantity,
            endotoxin_level=endotoxin,
            test_type=extracted.get('test_type'),
            comments=extracted.get('comments'),
            verification_key=extracted.get('verification_key'),
            raw_data=json.dumps(extracted),
            image_file=image_file,
            image_hash=image_hash,
            processed=True
        )
    
    def __repr__(self) -> str:
        return f"<JanoshikCertificate {self.task_number}: {self.supplier_name} - {self.peptide_name} ({self.purity_percentage}%)>"
