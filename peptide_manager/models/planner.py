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
        else:
            on_days = days
        
        return on_days * self.daily_frequency


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
        super().__init__(db, 'plan_phases', PlanPhase)
    
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
        super().__init__(db, 'plan_resources', ResourceRequirement)
    
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
        super().__init__(db, 'plan_simulations', PlanSimulation)
    
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
