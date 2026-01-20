"""
TreatmentPlanTemplate model - Template completi multi-fase per treatment plans.

Questi template rappresentano i "protocolli" del libro (GH Secretagogue, Metabolic
Restoration, Age-Related Decline) come strutture riutilizzabili per creare
treatment plans concreti.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
import json

from .base import BaseModel, Repository


@dataclass
class TreatmentPlanTemplate(BaseModel):
    """
    Template completo per un treatment plan multi-fase.
    
    Rappresenta un protocollo del libro con tutte le fasi pre-configurate,
    candidate profile, e outcomes attesi.
    """
    
    # Campi obbligatori
    name: str = ""
    phases_config: str = ""  # JSON completo delle fasi
    total_duration_weeks: int = 0
    total_phases: int = 0
    
    # Identificazione
    short_name: Optional[str] = None  # Es. "GH-Recomp", "MetRestore"
    category: Optional[str] = None  # "weight_loss", "body_recomposition", "metabolic", "anti_aging"
    
    # Profilo candidato (JSON)
    candidate_profile: Optional[str] = None
    
    # Outcomes attesi (JSON)
    expected_outcomes: Optional[str] = None
    
    # Metadata
    source: Optional[str] = None  # Es. "Peptide Weight Loss Book"
    is_system_template: bool = False  # Template di sistema non modificabili
    is_active: bool = True
    notes: Optional[str] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Validazione e conversioni."""
        # Conversione datetime
        if self.updated_at and isinstance(self.updated_at, str):
            self.updated_at = datetime.fromisoformat(self.updated_at)
        
        # Conversione bool
        if isinstance(self.is_system_template, int):
            self.is_system_template = bool(self.is_system_template)
        if isinstance(self.is_active, int):
            self.is_active = bool(self.is_active)
        
        # Validazioni
        if not self.name or not self.name.strip():
            raise ValueError("name obbligatorio")
        
        if not self.phases_config or not self.phases_config.strip():
            raise ValueError("phases_config obbligatorio")
        
        # Valida JSON phases_config
        try:
            phases = json.loads(self.phases_config)
            if not isinstance(phases, list):
                raise ValueError("phases_config deve essere un array JSON")
        except json.JSONDecodeError as e:
            raise ValueError(f"phases_config JSON non valido: {e}")
        
        if self.total_duration_weeks <= 0:
            raise ValueError("total_duration_weeks deve essere > 0")
        
        if self.total_phases <= 0:
            raise ValueError("total_phases deve essere > 0")
    
    def get_phases(self) -> List[Dict[str, Any]]:
        """
        Parse phases_config JSON.
        
        Returns:
            Lista di dict con configurazione fasi
        """
        return json.loads(self.phases_config)
    
    def set_phases(self, phases: List[Dict[str, Any]]):
        """Imposta phases_config da lista di dict."""
        self.phases_config = json.dumps(phases, ensure_ascii=False)
        self.total_phases = len(phases)
        self.total_duration_weeks = sum(p.get('duration_weeks', 0) for p in phases)
    
    def get_candidate_profile(self) -> Dict[str, Any]:
        """Parse candidate_profile JSON."""
        if not self.candidate_profile:
            return {}
        return json.loads(self.candidate_profile)
    
    def set_candidate_profile(self, profile: Dict[str, Any]):
        """Imposta candidate_profile da dict."""
        self.candidate_profile = json.dumps(profile, ensure_ascii=False)
    
    def get_expected_outcomes(self) -> List[str]:
        """Parse expected_outcomes JSON."""
        if not self.expected_outcomes:
            return []
        return json.loads(self.expected_outcomes)
    
    def set_expected_outcomes(self, outcomes: List[str]):
        """Imposta expected_outcomes da lista."""
        self.expected_outcomes = json.dumps(outcomes, ensure_ascii=False)
    
    def get_all_peptides(self) -> List[Dict[str, Any]]:
        """
        Estrae tutti i peptidi unici da tutte le fasi.
        
        Returns:
            Lista di peptidi unici con dose range
        """
        peptides_map = {}
        
        for phase in self.get_phases():
            for peptide in phase.get('peptides', []):
                pid = peptide.get('peptide_id') or peptide.get('peptide_name')
                if pid not in peptides_map:
                    peptides_map[pid] = {
                        'peptide_id': peptide.get('peptide_id'),
                        'peptide_name': peptide.get('peptide_name'),
                        'min_dose_mcg': peptide.get('dose_mcg'),
                        'max_dose_mcg': peptide.get('dose_mcg'),
                        'phases': [phase.get('phase_number', 1)]
                    }
                else:
                    dose = peptide.get('dose_mcg', 0)
                    peptides_map[pid]['min_dose_mcg'] = min(
                        peptides_map[pid]['min_dose_mcg'] or dose, dose
                    )
                    peptides_map[pid]['max_dose_mcg'] = max(
                        peptides_map[pid]['max_dose_mcg'] or dose, dose
                    )
                    peptides_map[pid]['phases'].append(phase.get('phase_number', 1))
        
        return list(peptides_map.values())
    
    def estimate_total_peptide_needs(self) -> Dict[str, Decimal]:
        """
        Stima quantità totale di ogni peptide per l'intero template.
        
        Returns:
            Dict: {peptide_name: total_mg_needed}
        """
        needs = {}
        
        for phase in self.get_phases():
            duration_weeks = phase.get('duration_weeks', 4)
            daily_frequency = phase.get('daily_frequency', 1)
            five_two = phase.get('five_two_protocol', False)
            
            # Calcola giorni effettivi
            if five_two:
                on_days = duration_weeks * 5
            else:
                on_days = duration_weeks * 7
            
            total_doses = on_days * daily_frequency
            
            for peptide in phase.get('peptides', []):
                name = peptide.get('peptide_name', f"Peptide_{peptide.get('peptide_id')}")
                dose_mcg = Decimal(str(peptide.get('dose_mcg', 0)))
                total_mcg = dose_mcg * total_doses
                total_mg = total_mcg / Decimal('1000')
                
                if name in needs:
                    needs[name] += total_mg
                else:
                    needs[name] = total_mg
        
        return needs


class TreatmentPlanTemplateRepository(Repository):
    """Repository per operazioni CRUD sui template di treatment plan."""
    
    def __init__(self, db):
        super().__init__(db, 'treatment_plan_templates', TreatmentPlanTemplate)
    
    def get_active_templates(self) -> List[TreatmentPlanTemplate]:
        """Recupera tutti i template attivi."""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT * FROM treatment_plan_templates 
            WHERE is_active = 1
            ORDER BY category, name
        """)
        
        return [self._row_to_entity(dict(row)) for row in cursor.fetchall()]
    
    def get_by_category(self, category: str) -> List[TreatmentPlanTemplate]:
        """Recupera template per categoria."""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT * FROM treatment_plan_templates 
            WHERE category = ? AND is_active = 1
            ORDER BY name
        """, (category,))
        
        return [self._row_to_entity(dict(row)) for row in cursor.fetchall()]
    
    def get_system_templates(self) -> List[TreatmentPlanTemplate]:
        """Recupera template di sistema."""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT * FROM treatment_plan_templates 
            WHERE is_system_template = 1 AND is_active = 1
            ORDER BY name
        """)
        
        return [self._row_to_entity(dict(row)) for row in cursor.fetchall()]
    
    def search_by_name(self, query: str) -> List[TreatmentPlanTemplate]:
        """Cerca template per nome."""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT * FROM treatment_plan_templates 
            WHERE (name LIKE ? OR short_name LIKE ?) AND is_active = 1
            ORDER BY name
        """, (f'%{query}%', f'%{query}%'))
        
        return [self._row_to_entity(dict(row)) for row in cursor.fetchall()]


# =============================================================================
# Classe helper per costruire template programmaticamente
# =============================================================================

class TemplateBuilder:
    """Builder per creare TreatmentPlanTemplate in modo fluente."""
    
    def __init__(self, name: str):
        self.name = name
        self.short_name = None
        self.category = None
        self.source = None
        self.phases = []
        self.candidate_profile = {}
        self.expected_outcomes = []
        self.notes = None
        self.is_system = False
    
    def with_short_name(self, short_name: str) -> 'TemplateBuilder':
        self.short_name = short_name
        return self
    
    def with_category(self, category: str) -> 'TemplateBuilder':
        self.category = category
        return self
    
    def with_source(self, source: str) -> 'TemplateBuilder':
        self.source = source
        return self
    
    def as_system_template(self) -> 'TemplateBuilder':
        self.is_system = True
        return self
    
    def with_candidate_profile(self, **kwargs) -> 'TemplateBuilder':
        self.candidate_profile = kwargs
        return self
    
    def with_expected_outcomes(self, *outcomes) -> 'TemplateBuilder':
        self.expected_outcomes = list(outcomes)
        return self
    
    def add_phase(
        self,
        phase_number: int,
        phase_name: str,
        duration_weeks: int,
        peptides: List[Dict[str, Any]],
        daily_frequency: int = 1,
        five_two_protocol: bool = False,
        administration_times: List[str] = None,
        description: str = None
    ) -> 'TemplateBuilder':
        """
        Aggiunge una fase al template.
        
        Args:
            phase_number: Numero fase (1, 2, 3, 4)
            phase_name: Nome fase (Foundation, Intensification, etc.)
            duration_weeks: Durata in settimane
            peptides: Lista peptidi [{"peptide_name": "X", "dose_mcg": 100}, ...]
            daily_frequency: Frequenza giornaliera (1, 2)
            five_two_protocol: Se usare pattern 5on/2off
            administration_times: Orari ["morning", "evening"]
            description: Descrizione fase
        """
        phase = {
            'phase_number': phase_number,
            'phase_name': phase_name,
            'duration_weeks': duration_weeks,
            'peptides': peptides,
            'daily_frequency': daily_frequency,
            'five_two_protocol': five_two_protocol
        }
        
        if administration_times:
            phase['administration_times'] = administration_times
        
        if description:
            phase['description'] = description
        
        self.phases.append(phase)
        return self
    
    def with_notes(self, notes: str) -> 'TemplateBuilder':
        self.notes = notes
        return self
    
    def build(self) -> TreatmentPlanTemplate:
        """Costruisce il template."""
        if not self.phases:
            raise ValueError("Almeno una fase richiesta")
        
        # Ordina fasi per phase_number
        self.phases.sort(key=lambda p: p['phase_number'])
        
        total_weeks = sum(p['duration_weeks'] for p in self.phases)
        
        template = TreatmentPlanTemplate(
            name=self.name,
            short_name=self.short_name,
            category=self.category,
            phases_config=json.dumps(self.phases, ensure_ascii=False),
            total_duration_weeks=total_weeks,
            total_phases=len(self.phases),
            candidate_profile=json.dumps(self.candidate_profile, ensure_ascii=False) if self.candidate_profile else None,
            expected_outcomes=json.dumps(self.expected_outcomes, ensure_ascii=False) if self.expected_outcomes else None,
            source=self.source,
            is_system_template=self.is_system,
            is_active=True,
            notes=self.notes
        )
        
        return template
