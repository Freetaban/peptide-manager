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
    
    # Standardized peptide fields (NEW)
    peptide_name_std: Optional[str] = None  # Standardized name (es. "BPC157", "Tirzepatide")
    quantity_nominal: Optional[float] = None  # Declared quantity (es. 5, 10, 30)
    unit_of_measure: Optional[str] = None  # Unit ("mg", "IU", "mcg")
    
    # Analytical results
    purity_percentage: Optional[float] = None
    quantity_tested_mg: Optional[float] = None
    endotoxin_level: Optional[float] = None  # EU/mg
    heavy_metals_result: Optional[str] = None  # JSON: {"Pb": 0.5, "Cd": 0.1, "Hg": 0.05, "As": 0.2}
    microbiology_tamc: Optional[int] = None  # Total Aerobic Microbial Count (CFU/g)
    microbiology_tymc: Optional[int] = None  # Total Yeast/Mold Count (CFU/g)
    
    # Metadata
    test_type: Optional[str] = None
    test_category: Optional[str] = None  # 'purity', 'endotoxin', 'heavy_metals', 'microbiology'
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
            'image_url': '',  # Non usato per ora
            'image_hash': self.image_hash,
            'local_image_path': self.image_file,
            'supplier_name': self.supplier_name,
            'product_name': self.peptide_name,  # DB usa product_name
            'test_date': self.test_date.isoformat() if isinstance(self.test_date, datetime) else self.test_date,
            'purity_percentage': self.purity_percentage,
            'purity_mg_per_vial': self.quantity_tested_mg,  # DB usa purity_mg_per_vial
            'endotoxin_eu_per_mg': self.endotoxin_level,
            'testing_lab': 'Janoshik Analytical',
            'raw_llm_response': self.raw_data,
            'extraction_timestamp': datetime.now().isoformat(),
            # Standardized fields (NEW)
            'peptide_name_std': self.peptide_name_std,
            'quantity_nominal': self.quantity_nominal,
            'unit_of_measure': self.unit_of_measure,
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
        quantities = []  # Per multi-peptide
        purities = []    # Per valori multipli
        heavy_metals = None
        tamc = None
        tymc = None
        
        # Estrai test_category (nuovo campo)
        test_category = extracted.get('test_category', 'purity')  # default purity
        
        # Estrai heavy metals se presente (JSON object)
        if 'heavy_metals' in extracted and extracted['heavy_metals']:
            hm = extracted['heavy_metals']
            # Se tutti i metalli sono None o "not detected", converti a 0.0
            if isinstance(hm, dict):
                cleaned_hm = {}
                for metal, value in hm.items():
                    if value is None or (isinstance(value, str) and 'not detected' in value.lower()):
                        cleaned_hm[metal] = 0.0
                    else:
                        try:
                            cleaned_hm[metal] = float(value)
                        except (ValueError, TypeError):
                            cleaned_hm[metal] = 0.0
                heavy_metals = json.dumps(cleaned_hm)
        
        # Estrai microbiology se presente
        if 'microbiology_tamc' in extracted:
            val = extracted['microbiology_tamc']
            # "Pass" = 0 (no contamination), altrimenti numero
            if isinstance(val, str) and val.lower() == 'pass':
                tamc = 0
            elif val is not None:
                try:
                    tamc = int(val)
                except (ValueError, TypeError):
                    tamc = None
        
        if 'microbiology_tymc' in extracted:
            val = extracted['microbiology_tymc']
            # "Pass" = 0 (no contamination), altrimenti numero
            if isinstance(val, str) and val.lower() == 'pass':
                tymc = 0
            elif val is not None:
                try:
                    tymc = int(val)
                except (ValueError, TypeError):
                    tymc = None
        
        # Fallback: controlla results per TAMC/TYMC "Pass"
        results = extracted.get('results', {})
        if isinstance(results, dict) and (tamc is None or tymc is None):
            for key, value in results.items():
                key_lower = key.lower()
                value_str = str(value).lower()
                
                if 'tamc' in key_lower and tamc is None:
                    if 'pass' in value_str:
                        tamc = 0
                    elif 'fail' in value_str:
                        tamc = -1  # Marker per contaminazione rilevata ma valore sconosciuto
                    else:
                        try:
                            tamc = int(value_str.split()[0])
                        except:
                            pass
                
                if 'tymc' in key_lower and tymc is None:
                    if 'pass' in value_str:
                        tymc = 0
                    elif 'fail' in value_str:
                        tymc = -1  # Marker per contaminazione rilevata
                    else:
                        try:
                            tymc = int(value_str.split()[0])
                        except:
                            pass
        
        # Estrai endotoxin level direttamente se presente
        if 'endotoxin_level' in extracted and extracted['endotoxin_level']:
            try:
                endotoxin = float(extracted['endotoxin_level'])
            except (ValueError, TypeError):
                pass
        
        # Parse results per valori aggiuntivi
        if isinstance(results, dict):
            for key, value in results.items():
                key_lower = key.lower()
                value_str = str(value)
                
                try:
                    if 'purity' in key_lower:
                        # Gestisci valori multipli separati da ";" (es: "99.798%; 99.782%")
                        if ';' in value_str:
                            for part in value_str.split(';'):
                                clean = part.replace('%', '').strip()
                                purities.append(float(clean))
                        else:
                            clean = value_str.replace('%', '').strip()
                            purities.append(float(clean))
                    
                    elif 'endotoxin' in key_lower:
                        clean = value_str.replace('EU/mg', '').replace('<', '').replace('>', '').strip()
                        endotoxin = float(clean)
                    
                    elif 'mg' in value_str.lower() and 'eu/mg' not in value_str.lower():
                        # Quantity (es: "44.33 mg" o "25.41 mg; 24.98 mg")
                        if ';' in value_str:
                            for part in value_str.split(';'):
                                clean = part.replace('mg', '').strip()
                                quantities.append(float(clean))
                        else:
                            clean = value_str.replace('mg', '').strip()
                            quantities.append(float(clean))
                
                except (ValueError, AttributeError):
                    pass
        
        # Conta peptidi distinti (escludi 'Purity' e 'Endotoxin')
        peptide_keys = [k for k in results.keys() 
                       if k.lower() not in ['purity', 'endotoxin'] 
                       and 'mg' in str(results[k]).lower()]
        num_distinct_peptides = len(peptide_keys)
        
        # Calcola purity: 
        # - Se multi-peptide MIX (>1 peptide diverso) -> purity = None (non applicabile)
        # - Se multi-vial (stesso peptide) -> media delle purezze
        # - Se single -> singolo valore
        if num_distinct_peptides > 1:
            # Multi-peptide mix: purity non è applicabile
            purity = None
        elif purities:
            # Single peptide o multi-vial: calcola media
            purity = sum(purities) / len(purities)
        
        # Quantity: sempre somma (per multi-peptide o multi-vial)
        if quantities:
            quantity = sum(quantities)
        
        # Fallback per purity_percentage (solo se non è multi-peptide)
        if not purity and num_distinct_peptides <= 1 and 'purity_percentage' in extracted:
            purity = extracted.get('purity_percentage')
        
        # Extract standardized peptide fields from LLM (NEW)
        peptide_name_std = extracted.get('peptide_name')  # LLM now provides standardized name
        quantity_nominal = extracted.get('quantity_nominal')  # Declared quantity (numeric)
        unit_of_measure = extracted.get('unit_of_measure')  # Unit (mg, IU, mcg)
        
        # Apply normalizers to ensure consistency
        from peptide_manager.janoshik.supplier_normalizer import SupplierNormalizer
        from peptide_manager.janoshik.peptide_normalizer import PeptideNormalizer
        
        # Normalize supplier name (handle various formats)
        raw_supplier = extracted.get('manufacturer') or extracted.get('client') or 'unknown'
        normalized_supplier = SupplierNormalizer.normalize(raw_supplier)
        
        # Normalize peptide name_std (handle spelling variants)
        if peptide_name_std:
            normalized_peptide = PeptideNormalizer.normalize(peptide_name_std)
        else:
            # Fallback: try to normalize from sample name
            normalized_peptide = PeptideNormalizer.normalize(extracted.get('sample', 'unknown'))
        
        return cls(
            task_number=extracted.get('task_number', 'unknown'),
            supplier_name=normalized_supplier,  # Use normalized name
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
            heavy_metals_result=heavy_metals,
            microbiology_tamc=tamc,
            microbiology_tymc=tymc,
            test_type=extracted.get('test_type'),
            test_category=test_category,
            comments=extracted.get('comments'),
            verification_key=extracted.get('verification_key'),
            raw_data=json.dumps(extracted),
            image_file=image_file,
            image_hash=image_hash,
            processed=True,
            # Standardized fields (NEW) - use normalized values
            peptide_name_std=normalized_peptide,
            quantity_nominal=quantity_nominal,
            unit_of_measure=unit_of_measure,
        )
    
    def __repr__(self) -> str:
        return f"<JanoshikCertificate {self.task_number}: {self.supplier_name} - {self.peptide_name} ({self.purity_percentage}%)>"
