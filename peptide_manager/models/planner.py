"""
Treatment Planner Models - Modelli per pianificazione multi-fase trattamenti.

Gestisce:
- PlanPhase: Singola fase di un piano multi-fase
- ResourceRequirement: Requisiti risorse calcolati per fase/piano
- PlanSimulation: Simulazioni what-if salvate
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from decimal import Decimal
import json

from .base import BaseModel, Repository


@dataclass
class PlanPhase(BaseModel):
    """Rappresenta una fase di un piano di trattamento multi-fase."""
    
    # Campi obbligatori
    treatment_plan_id: int = 0
    phase_number: int = 0  # 1, 2, 3, 4
    phase_name: str = ""  # "Foundation", "Intensification", "Consolidation", "Transition"
    duration_weeks: int = 0
    peptides_config: str = ""  # JSON array
    daily_frequency: int = 1
    
    # Campi opzionali
    description: Optional[str] = None
    start_week: Optional[int] = None  # Settimana di inizio relativa (1-based)
    five_two_protocol: bool = False
    ramp_schedule: Optional[str] = None  # JSON per ramp-up/down
    status: str = 'planned'  # 'planned', 'active', 'completed', 'skipped'
    cycle_id: Optional[int] = None
    actual_start_date: Optional[date] = None
    actual_end_date: Optional[date] = None
    notes: Optional[str] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    
    # Enhanced timing fields (migration 015)
    administration_times: Optional[str] = None  # JSON: ["morning", "evening"] or ["08:00", "20:00"]
    peptide_timing: Optional[str] = None  # JSON: {"peptide_id": "morning", ...}
    weekday_pattern: Optional[str] = None  # JSON: [1,2,3,4,5] for Mon-Fri
    dose_adjustments: Optional[str] = None  # JSON: {"peptide_id": {"dose_mcg": 150, "reason": "..."}}
    
    def __post_init__(self):
        """Validazione e conversioni."""
        # Conversione date
        if self.actual_start_date and isinstance(self.actual_start_date, str):
            self.actual_start_date = date.fromisoformat(self.actual_start_date)
        if self.actual_end_date and isinstance(self.actual_end_date, str):
            self.actual_end_date = date.fromisoformat(self.actual_end_date)
        
        # Conversione datetime
        if self.updated_at and isinstance(self.updated_at, str):
            self.updated_at = datetime.fromisoformat(self.updated_at)
        if self.deleted_at and isinstance(self.deleted_at, str):
            self.deleted_at = datetime.fromisoformat(self.deleted_at)
        
        # Conversione bool
        if isinstance(self.five_two_protocol, int):
            self.five_two_protocol = bool(self.five_two_protocol)
        
        # Validazioni
        if self.treatment_plan_id <= 0:
            raise ValueError("treatment_plan_id deve essere > 0")
        
        if self.phase_number <= 0:
            raise ValueError("phase_number deve essere > 0")
        
        if not self.phase_name or not self.phase_name.strip():
            raise ValueError("phase_name obbligatorio")
        
        if self.duration_weeks <= 0:
            raise ValueError("duration_weeks deve essere > 0")
        
        if self.daily_frequency <= 0:
            raise ValueError("daily_frequency deve essere > 0")
        
        valid_statuses = ['planned', 'active', 'completed', 'skipped']
        if self.status not in valid_statuses:
            raise ValueError(f"Status deve essere uno di: {', '.join(valid_statuses)}")
        
        # Valida JSON peptides_config
        if self.peptides_config:
            try:
                peptides = json.loads(self.peptides_config)
                if not isinstance(peptides, list):
                    raise ValueError("peptides_config deve essere un array JSON")
            except json.JSONDecodeError as e:
                raise ValueError(f"peptides_config JSON non valido: {e}")
    
    def get_peptides(self) -> List[Dict[str, Any]]:
        """
        Parse peptides_config JSON.
        
        Returns:
            Lista di dict: [{'peptide_id': 1, 'dose_mcg': 100, 'peptide_name': 'CJC-1295'}, ...]
        """
        if not self.peptides_config:
            return []
        return json.loads(self.peptides_config)
    
    def set_peptides(self, peptides: List[Dict[str, Any]]):
        """Imposta peptides_config da lista di dict."""
        self.peptides_config = json.dumps(peptides)
    
    def get_ramp(self) -> Optional[Dict[str, Any]]:
        """Parse ramp_schedule JSON se presente."""
        if not self.ramp_schedule:
            return None
        return json.loads(self.ramp_schedule)
    
    def is_active(self) -> bool:
        """Verifica se fase attualmente attiva."""
        return self.status == 'active' and self.deleted_at is None
    
    def is_completed(self) -> bool:
        """Verifica se fase completata."""
        return self.status == 'completed'
    
    def total_administrations(self) -> int:
        """
        Calcola numero totale amministrazioni previste.
        
        Returns:
            Numero totale iniezioni per questa fase
        """
        days = self.duration_weeks * 7
        
        if self.five_two_protocol:
            # 5 giorni on, 2 off per settimana
            full_weeks = self.duration_weeks
            on_days = full_weeks * 5
        elif self.weekday_pattern:
            # Pattern personalizzato giorni settimana
            weekdays = self.get_weekday_pattern()
            on_days = self.duration_weeks * len(weekdays)
        else:
            on_days = days
        
        return on_days * self.daily_frequency
    
    def get_administration_times(self) -> List[str]:
        """
        Parse administration_times JSON.
        
        Returns:
            Lista di orari: ["morning", "evening"] or ["08:00", "20:00"]
        """
        if not self.administration_times:
            return []
        return json.loads(self.administration_times)
    
    def set_administration_times(self, times: List[str]):
        """Imposta administration_times da lista."""
        self.administration_times = json.dumps(times)
    
    def get_peptide_timing(self) -> Dict[str, str]:
        """
        Parse peptide_timing JSON.
        
        Returns:
            Dict: {peptide_id: "morning"|"evening"|"both", ...}
        """
        if not self.peptide_timing:
            return {}
        return json.loads(self.peptide_timing)
    
    def set_peptide_timing(self, timing: Dict[str, str]):
        """Imposta peptide_timing da dict."""
        self.peptide_timing = json.dumps(timing)
    
    def get_weekday_pattern(self) -> List[int]:
        """
        Parse weekday_pattern JSON.
        
        Returns:
            Lista di giorni settimana: [1,2,3,4,5] for Mon-Fri (1=Mon, 7=Sun)
        """
        if not self.weekday_pattern:
            return []
        return json.loads(self.weekday_pattern)
    
    def set_weekday_pattern(self, weekdays: List[int]):
        """Imposta weekday_pattern da lista."""
        self.weekday_pattern = json.dumps(weekdays)
    
    def get_dose_adjustments(self) -> Dict[str, Dict[str, Any]]:
        """
        Parse dose_adjustments JSON.
        
        Returns:
            Dict: {peptide_id: {"dose_mcg": 150, "reason": "..."}, ...}
        """
        if not self.dose_adjustments:
            return {}
        return json.loads(self.dose_adjustments)
    
    def set_dose_adjustments(self, adjustments: Dict[str, Dict[str, Any]]):
        """Imposta dose_adjustments da dict."""
        self.dose_adjustments = json.dumps(adjustments)
    
    def get_effective_dose(self, peptide_id: int, base_dose_mcg: float) -> float:
        """
        Calcola dose effettiva considerando eventuali aggiustamenti.
        
        Args:
            peptide_id: ID del peptide
            base_dose_mcg: Dose base da template
            
        Returns:
            Dose effettiva in mcg
        """
        adjustments = self.get_dose_adjustments()
        key = str(peptide_id)
        
        if key in adjustments and 'dose_mcg' in adjustments[key]:
            return float(adjustments[key]['dose_mcg'])
        
        return base_dose_mcg


@dataclass
class ResourceRequirement(BaseModel):
    """Rappresenta requisiti di risorse calcolati per una fase o piano."""
    
    # Campi obbligatori
    treatment_plan_id: int = 0
    resource_type: str = ""  # 'peptide', 'syringe', 'needle', 'consumable'
    resource_name: str = ""
    quantity_needed: Decimal = Decimal('0')
    quantity_unit: str = ""  # 'vials', 'mg', 'ml', 'units'
    
    # Campi opzionali
    plan_phase_id: Optional[int] = None  # NULL = per intero piano
    resource_id: Optional[int] = None  # peptide_id o altro
    quantity_available: Decimal = Decimal('0')
    quantity_gap: Optional[Decimal] = None
    needs_ordering: bool = False
    order_by_week: Optional[int] = None
    estimated_cost: Optional[Decimal] = None
    currency: str = 'EUR'
    calculation_date: Optional[datetime] = None
    calculation_params: Optional[str] = None  # JSON
    notes: Optional[str] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Validazione e conversioni."""
        # Conversione Decimal
        if isinstance(self.quantity_needed, (int, float, str)):
            self.quantity_needed = Decimal(str(self.quantity_needed))
        if isinstance(self.quantity_available, (int, float, str)):
            self.quantity_available = Decimal(str(self.quantity_available))
        if self.quantity_gap and isinstance(self.quantity_gap, (int, float, str)):
            self.quantity_gap = Decimal(str(self.quantity_gap))
        if self.estimated_cost and isinstance(self.estimated_cost, (int, float, str)):
            self.estimated_cost = Decimal(str(self.estimated_cost))
        
        # Conversione datetime
        if self.calculation_date and isinstance(self.calculation_date, str):
            self.calculation_date = datetime.fromisoformat(self.calculation_date)
        if self.updated_at and isinstance(self.updated_at, str):
            self.updated_at = datetime.fromisoformat(self.updated_at)
        
        # Conversione bool
        if isinstance(self.needs_ordering, int):
            self.needs_ordering = bool(self.needs_ordering)
        
        # Validazioni
        if self.treatment_plan_id <= 0:
            raise ValueError("treatment_plan_id deve essere > 0")
        
        valid_types = ['peptide', 'syringe', 'needle', 'consumable', 'diluent']
        if self.resource_type not in valid_types:
            raise ValueError(f"resource_type deve essere uno di: {', '.join(valid_types)}")
        
        if not self.resource_name or not self.resource_name.strip():
            raise ValueError("resource_name obbligatorio")
        
        if self.quantity_needed < 0:
            raise ValueError("quantity_needed deve essere >= 0")
        
        if not self.quantity_unit or not self.quantity_unit.strip():
            raise ValueError("quantity_unit obbligatorio")
        
        # Calcola gap se non impostato
        if self.quantity_gap is None:
            self.quantity_gap = self.quantity_needed - self.quantity_available
        
        # Imposta needs_ordering se gap positivo
        if self.quantity_gap > 0 and not self.needs_ordering:
            self.needs_ordering = True
    
    def get_calculation_params(self) -> Optional[Dict[str, Any]]:
        """Parse calculation_params JSON."""
        if not self.calculation_params:
            return None
        return json.loads(self.calculation_params)
    
    def has_gap(self) -> bool:
        """Verifica se c'è gap da colmare."""
        return self.quantity_gap and self.quantity_gap > 0


@dataclass
class PlanSimulation(BaseModel):
    """Rappresenta una simulazione what-if salvata."""
    
    # Campi obbligatori
    name: str = ""
    simulation_config: str = ""  # JSON completo
    
    # Campi opzionali
    description: Optional[str] = None
    base_plan_id: Optional[int] = None
    results_summary: Optional[str] = None  # JSON
    comparison_notes: Optional[str] = None
    is_archived: bool = False
    converted_to_plan: bool = False
    converted_plan_id: Optional[int] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Validazione e conversioni."""
        # Conversione datetime
        if self.updated_at and isinstance(self.updated_at, str):
            self.updated_at = datetime.fromisoformat(self.updated_at)
        if self.deleted_at and isinstance(self.deleted_at, str):
            self.deleted_at = datetime.fromisoformat(self.deleted_at)
        
        # Conversione bool
        if isinstance(self.is_archived, int):
            self.is_archived = bool(self.is_archived)
        if isinstance(self.converted_to_plan, int):
            self.converted_to_plan = bool(self.converted_to_plan)
        
        # Validazioni
        if not self.name or not self.name.strip():
            raise ValueError("name obbligatorio")
        
        if not self.simulation_config or not self.simulation_config.strip():
            raise ValueError("simulation_config obbligatorio")
        
        # Valida JSON
        try:
            json.loads(self.simulation_config)
        except json.JSONDecodeError as e:
            raise ValueError(f"simulation_config JSON non valido: {e}")
    
    def get_config(self) -> Dict[str, Any]:
        """Parse simulation_config JSON."""
        return json.loads(self.simulation_config)
    
    def get_results(self) -> Optional[Dict[str, Any]]:
        """Parse results_summary JSON."""
        if not self.results_summary:
            return None
        return json.loads(self.results_summary)


# =============================================================================
# REPOSITORIES
# =============================================================================

class PlanPhaseRepository(Repository):
    """Repository per operazioni CRUD su fasi piano."""
    
    def __init__(self, db):
        self.db = db
        super().__init__(db.conn if hasattr(db, 'conn') else db)
    
    def _row_to_entity(self, row_dict: dict) -> 'PlanPhase':
        """Converte una riga del database in entità PlanPhase."""
        from .planner import PlanPhase
        return PlanPhase.from_row(row_dict)
    
    def create(self, phase: PlanPhase) -> int:
        """
        Crea una nuova fase.
        
        Args:
            phase: PlanPhase da creare
            
        Returns:
            ID della fase creata
        """
        cursor = self.db.conn.cursor()
        cursor.execute("""
            INSERT INTO plan_phases (
                treatment_plan_id, phase_number, phase_name, description,
                duration_weeks, start_week, peptides_config, daily_frequency,
                five_two_protocol, ramp_schedule, status, notes,
                administration_times, peptide_timing, weekday_pattern, dose_adjustments
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            phase.treatment_plan_id,
            phase.phase_number,
            phase.phase_name,
            phase.description,
            phase.duration_weeks,
            phase.start_week,
            phase.peptides_config,
            phase.daily_frequency,
            1 if phase.five_two_protocol else 0,
            phase.ramp_schedule,
            phase.status,
            phase.notes,
            phase.administration_times,
            phase.peptide_timing,
            phase.weekday_pattern,
            phase.dose_adjustments
        ))
        
        self.db.conn.commit()
        return cursor.lastrowid
    
    def get_by_plan(self, treatment_plan_id: int) -> List[PlanPhase]:
        """
        Recupera tutte le fasi di un piano.
        
        Args:
            treatment_plan_id: ID del piano
            
        Returns:
            Lista fasi ordinate per phase_number
        """
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT * FROM plan_phases
            WHERE treatment_plan_id = ? AND deleted_at IS NULL
            ORDER BY phase_number ASC
        """, (treatment_plan_id,))
        
        rows = cursor.fetchall()
        return [self._row_to_entity(dict(row)) for row in rows]
    
    def get_active_phases(self) -> List[PlanPhase]:
        """Recupera tutte le fasi attive."""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT * FROM plan_phases
            WHERE status = 'active' AND deleted_at IS NULL
            ORDER BY treatment_plan_id, phase_number
        """)
        
        rows = cursor.fetchall()
        return [self._row_to_entity(dict(row)) for row in rows]
    
    def update(self, phase: PlanPhase) -> bool:
        """
        Aggiorna una fase esistente.
        
        Args:
            phase: PlanPhase con dati aggiornati
            
        Returns:
            True se successo
        """
        cursor = self.db.conn.cursor()
        cursor.execute("""
            UPDATE plan_phases
            SET phase_name = ?,
                description = ?,
                duration_weeks = ?,
                start_week = ?,
                peptides_config = ?,
                daily_frequency = ?,
                five_two_protocol = ?,
                ramp_schedule = ?,
                status = ?,
                cycle_id = ?,
                actual_start_date = ?,
                actual_end_date = ?,
                notes = ?,
                administration_times = ?,
                peptide_timing = ?,
                weekday_pattern = ?,
                dose_adjustments = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            phase.phase_name,
            phase.description,
            phase.duration_weeks,
            phase.start_week,
            phase.peptides_config,
            phase.daily_frequency,
            1 if phase.five_two_protocol else 0,
            phase.ramp_schedule,
            phase.status,
            phase.cycle_id,
            phase.actual_start_date.isoformat() if phase.actual_start_date else None,
            phase.actual_end_date.isoformat() if phase.actual_end_date else None,
            phase.notes,
            phase.administration_times,
            phase.peptide_timing,
            phase.weekday_pattern,
            phase.dose_adjustments,
            phase.id
        ))
        
        self.db.conn.commit()
        return cursor.rowcount > 0
    
    def link_to_cycle(self, phase_id: int, cycle_id: int) -> bool:
        """
        Collega una fase a un ciclo attivato.
        
        Args:
            phase_id: ID della fase
            cycle_id: ID del ciclo
            
        Returns:
            True se successo
        """
        cursor = self.db.conn.cursor()
        cursor.execute("""
            UPDATE plan_phases
            SET cycle_id = ?, 
                status = 'active',
                actual_start_date = CASE WHEN actual_start_date IS NULL THEN DATE('now') ELSE actual_start_date END,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (cycle_id, phase_id))
        
        self.db.conn.commit()
        return cursor.rowcount > 0
    
    def complete_phase(self, phase_id: int) -> bool:
        """
        Marca una fase come completata.
        
        Args:
            phase_id: ID della fase
            
        Returns:
            True se successo
        """
        cursor = self.db.conn.cursor()
        cursor.execute("""
            UPDATE plan_phases
            SET status = 'completed',
                actual_end_date = CASE WHEN actual_end_date IS NULL THEN DATE('now') ELSE actual_end_date END,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (phase_id,))
        
        self.db.conn.commit()
        return cursor.rowcount > 0


class ResourceRequirementRepository(Repository):
    """Repository per requisiti risorse."""
    
    def __init__(self, db):
        self.db = db
        super().__init__(db.conn if hasattr(db, 'conn') else db)
    
    def _row_to_entity(self, row_dict: dict) -> 'ResourceRequirement':
        """Converte una riga del database in entità ResourceRequirement."""
        from .planner import ResourceRequirement
        return ResourceRequirement.from_row(row_dict)
    
    def create(self, requirement: ResourceRequirement) -> int:
        """
        Crea un nuovo requisito risorsa.
        
        Args:
            requirement: ResourceRequirement da creare
            
        Returns:
            ID del requisito creato
        """
        cursor = self.db.conn.cursor()
        cursor.execute("""
            INSERT INTO plan_resources (
                treatment_plan_id, plan_phase_id, resource_type, resource_id,
                resource_name, quantity_needed, quantity_unit, quantity_available,
                quantity_gap, needs_ordering, order_by_week, estimated_cost,
                currency, calculation_params, notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            requirement.treatment_plan_id,
            requirement.plan_phase_id,
            requirement.resource_type,
            requirement.resource_id,
            requirement.resource_name,
            float(requirement.quantity_needed),
            requirement.quantity_unit,
            float(requirement.quantity_available),
            float(requirement.quantity_gap) if requirement.quantity_gap is not None else None,
            1 if requirement.needs_ordering else 0,
            requirement.order_by_week,
            float(requirement.estimated_cost) if requirement.estimated_cost is not None else None,
            requirement.currency,
            requirement.calculation_params,
            requirement.notes
        ))
        
        self.db.conn.commit()
        return cursor.lastrowid
    
    def get_by_plan(self, treatment_plan_id: int) -> List[ResourceRequirement]:
        """
        Recupera tutti i requisiti di un piano.
        
        Args:
            treatment_plan_id: ID del piano
            
        Returns:
            Lista requisiti
        """
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT * FROM plan_resources
            WHERE treatment_plan_id = ?
            ORDER BY resource_type, resource_name
        """, (treatment_plan_id,))
        
        rows = cursor.fetchall()
        return [self._row_to_entity(dict(row)) for row in rows]
    
    def get_by_phase(self, plan_phase_id: int) -> List[ResourceRequirement]:
        """Recupera requisiti di una fase specifica."""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT * FROM plan_resources
            WHERE plan_phase_id = ?
            ORDER BY resource_type, resource_name
        """, (plan_phase_id,))
        
        rows = cursor.fetchall()
        return [self._row_to_entity(dict(row)) for row in rows]
    
    def get_needs_ordering(self, treatment_plan_id: int) -> List[ResourceRequirement]:
        """
        Recupera risorse che necessitano ordine.
        
        Args:
            treatment_plan_id: ID del piano
            
        Returns:
            Lista risorse con gap > 0
        """
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT * FROM plan_resources
            WHERE treatment_plan_id = ? AND needs_ordering = 1
            ORDER BY order_by_week ASC, resource_type, resource_name
        """, (treatment_plan_id,))
        
        rows = cursor.fetchall()
        return [self._row_to_entity(dict(row)) for row in rows]
    
    def delete_by_plan(self, treatment_plan_id: int) -> bool:
        """
        Elimina tutti i requisiti di un piano.
        
        Args:
            treatment_plan_id: ID del piano
            
        Returns:
            True se successo
        """
        cursor = self.db.conn.cursor()
        cursor.execute("""
            DELETE FROM plan_resources
            WHERE treatment_plan_id = ?
        """, (treatment_plan_id,))
        
        self.db.conn.commit()
        return True


class PlanSimulationRepository(Repository):
    """Repository per simulazioni."""
    
    def __init__(self, db):
        self.db = db
        super().__init__(db.conn if hasattr(db, 'conn') else db)
    
    def _row_to_entity(self, row_dict: dict) -> 'PlanSimulation':
        """Converte una riga del database in entità PlanSimulation."""
        from .planner import PlanSimulation
        return PlanSimulation.from_row(row_dict)
    
    def get_all_active(self) -> List[PlanSimulation]:
        """Recupera tutte le simulazioni non archiviate."""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT * FROM plan_simulations
            WHERE is_archived = 0 AND deleted_at IS NULL
            ORDER BY created_at DESC
        """)
        
        rows = cursor.fetchall()
        return [self._row_to_entity(dict(row)) for row in rows]
    
    def get_by_base_plan(self, base_plan_id: int) -> List[PlanSimulation]:
        """Recupera simulazioni derivate da un piano."""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT * FROM plan_simulations
            WHERE base_plan_id = ? AND deleted_at IS NULL
            ORDER BY created_at DESC
        """, (base_plan_id,))
        
        rows = cursor.fetchall()
        return [self._row_to_entity(dict(row)) for row in rows]
    
    def archive_simulation(self, simulation_id: int) -> bool:
        """Archivia una simulazione."""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            UPDATE plan_simulations
            SET is_archived = 1, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (simulation_id,))
        
        self.db.conn.commit()
        return cursor.rowcount > 0
