"""
TreatmentPlan model - gestisce i piani di trattamento (cicli di somministrazione).

Un TreatmentPlan rappresenta un ciclo di trattamento specifico, basato opzionalmente
su un ProtocolTemplate, con tracking di aderenza, inventario e statistiche.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict
from datetime import date, datetime
from decimal import Decimal

from .base import BaseModel, Repository


@dataclass
class TreatmentPlan(BaseModel):
    """Rappresenta un piano di trattamento (ciclo)."""
    
    # Campi obbligatori
    name: str = field(default="")
    start_date: date = field(default=None)
    
    # Campi opzionali
    protocol_template_id: Optional[int] = None
    description: Optional[str] = None
    reason: Optional[str] = None
    planned_end_date: Optional[date] = None
    actual_end_date: Optional[date] = None
    status: str = 'active'  # active, paused, completed, abandoned, planned
    total_planned_days: Optional[int] = None
    days_completed: int = 0
    adherence_percentage: Decimal = Decimal('100.0')
    notes: Optional[str] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Validazione e conversioni dopo inizializzazione."""
        # Conversione date
        if self.start_date and isinstance(self.start_date, str):
            self.start_date = date.fromisoformat(self.start_date)
        if self.planned_end_date and isinstance(self.planned_end_date, str):
            self.planned_end_date = date.fromisoformat(self.planned_end_date)
        if self.actual_end_date and isinstance(self.actual_end_date, str):
            self.actual_end_date = date.fromisoformat(self.actual_end_date)
        
        # Conversione datetime
        if self.updated_at and isinstance(self.updated_at, str):
            self.updated_at = datetime.fromisoformat(self.updated_at)
        if self.deleted_at and isinstance(self.deleted_at, str):
            self.deleted_at = datetime.fromisoformat(self.deleted_at)
        
        # Conversione adherence
        if isinstance(self.adherence_percentage, (int, float, str)):
            self.adherence_percentage = Decimal(str(self.adherence_percentage))
        
        # Gestione NULL
        if self.days_completed is None:
            self.days_completed = 0
        if self.adherence_percentage is None:
            self.adherence_percentage = Decimal('100.0')
        if self.status is None:
            self.status = 'active'
        
        # Validazioni
        if not self.name or not self.name.strip():
            raise ValueError("Nome piano obbligatorio")
        
        if self.start_date is None:
            raise ValueError("Data inizio obbligatoria")
        
        valid_statuses = ['active', 'paused', 'completed', 'abandoned', 'planned']
        if self.status not in valid_statuses:
            raise ValueError(f"Status deve essere uno di: {', '.join(valid_statuses)}")
        
        if self.adherence_percentage < 0 or self.adherence_percentage > 100:
            raise ValueError("Aderenza deve essere tra 0 e 100")
        
        if self.days_completed < 0:
            raise ValueError("Giorni completati deve essere >= 0")
    
    def is_deleted(self) -> bool:
        """Verifica se eliminato (soft delete)."""
        return self.deleted_at is not None
    
    def is_active(self) -> bool:
        """Verifica se piano attivo."""
        return self.status == 'active' and not self.is_deleted()
    
    def is_completed(self) -> bool:
        """Verifica se piano completato."""
        return self.status == 'completed'
    
    def is_paused(self) -> bool:
        """Verifica se piano in pausa."""
        return self.status == 'paused'
    
    def is_planned(self) -> bool:
        """Verifica se piano futuro (non ancora iniziato)."""
        return self.status == 'planned'
    
    def calculate_progress_percentage(self) -> Decimal:
        """
        Calcola percentuale di progresso del piano.
        
        Returns:
            Percentuale di completamento (0-100)
        """
        if not self.total_planned_days or self.total_planned_days <= 0:
            return Decimal('0.0')
        
        progress = (Decimal(str(self.days_completed)) / Decimal(str(self.total_planned_days))) * 100
        return min(progress, Decimal('100.0'))
    
    def get_remaining_days(self) -> Optional[int]:
        """
        Calcola giorni rimanenti del piano.
        
        Returns:
            Giorni rimanenti o None se non calcolabile
        """
        if not self.total_planned_days:
            return None
        
        remaining = self.total_planned_days - self.days_completed
        return max(0, remaining)
    
    def calculate_estimated_end_date(self) -> Optional[date]:
        """
        Stima data fine basata su progresso attuale.
        
        Returns:
            Data fine stimata o None
        """
        if not self.total_planned_days or self.days_completed <= 0:
            return self.planned_end_date
        
        # Calcola giorni trascorsi dall'inizio
        from datetime import timedelta
        today = date.today()
        days_since_start = (today - self.start_date).days
        
        if days_since_start <= 0:
            return self.planned_end_date
        
        # Calcola velocità media (giorni completati / giorni trascorsi)
        completion_rate = self.days_completed / days_since_start
        
        if completion_rate <= 0:
            return self.planned_end_date
        
        # Stima giorni totali necessari
        estimated_total_days = self.total_planned_days / completion_rate
        estimated_end = self.start_date + timedelta(days=int(estimated_total_days))
        
        return estimated_end


@dataclass
class TreatmentPlanPreparation(BaseModel):
    """Associazione tra TreatmentPlan e Preparation."""
    
    # Campi obbligatori
    plan_id: int = field(default=None)
    preparation_id: int = field(default=None)
    
    # Campi opzionali
    peptide_id: Optional[int] = None
    actual_dose_mcg: Optional[Decimal] = None
    actual_dose_ml: Optional[Decimal] = None
    frequency: Optional[str] = None
    phase_name: Optional[str] = None
    phase_start_date: Optional[date] = None
    phase_end_date: Optional[date] = None
    is_active: bool = True
    notes: Optional[str] = None
    
    def __post_init__(self):
        """Validazione e conversioni."""
        # Conversione decimals
        if self.actual_dose_mcg and isinstance(self.actual_dose_mcg, (int, float, str)):
            self.actual_dose_mcg = Decimal(str(self.actual_dose_mcg))
        if self.actual_dose_ml and isinstance(self.actual_dose_ml, (int, float, str)):
            self.actual_dose_ml = Decimal(str(self.actual_dose_ml))
        
        # Conversione date
        if self.phase_start_date and isinstance(self.phase_start_date, str):
            self.phase_start_date = date.fromisoformat(self.phase_start_date)
        if self.phase_end_date and isinstance(self.phase_end_date, str):
            self.phase_end_date = date.fromisoformat(self.phase_end_date)
        
        # Conversione bool
        if isinstance(self.is_active, int):
            self.is_active = bool(self.is_active)
        
        # Validazioni
        if self.plan_id is None:
            raise ValueError("plan_id obbligatorio")
        if self.preparation_id is None:
            raise ValueError("preparation_id obbligatorio")


class TreatmentPlanRepository(Repository):
    """Repository per operazioni CRUD sui piani di trattamento."""
    
    def __init__(self, db):
        super().__init__(db, 'treatment_plans', TreatmentPlan)
    
    def get_active_plans(self) -> List[TreatmentPlan]:
        """
        Recupera tutti i piani attivi.
        
        Returns:
            Lista di piani con status='active'
        """
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT * FROM treatment_plans 
            WHERE status = 'active' AND deleted_at IS NULL
            ORDER BY start_date DESC
        """)
        
        rows = cursor.fetchall()
        return [self._row_to_entity(dict(row)) for row in rows]
    
    def get_planned_plans(self) -> List[TreatmentPlan]:
        """
        Recupera tutti i piani futuri.
        
        Returns:
            Lista di piani con status='planned'
        """
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT * FROM treatment_plans 
            WHERE status = 'planned' AND deleted_at IS NULL
            ORDER BY start_date ASC
        """)
        
        rows = cursor.fetchall()
        return [self._row_to_entity(dict(row)) for row in rows]
    
    def get_completed_plans(self, limit: int = 10) -> List[TreatmentPlan]:
        """
        Recupera piani completati recenti.
        
        Args:
            limit: Numero massimo di risultati
            
        Returns:
            Lista di piani completati
        """
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT * FROM treatment_plans 
            WHERE status = 'completed' AND deleted_at IS NULL
            ORDER BY actual_end_date DESC, updated_at DESC
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        return [self._row_to_entity(dict(row)) for row in rows]
    
    def get_by_template(self, template_id: int) -> List[TreatmentPlan]:
        """
        Recupera tutti i piani basati su un template.
        
        Args:
            template_id: ID del protocol template
            
        Returns:
            Lista di piani
        """
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT * FROM treatment_plans 
            WHERE protocol_template_id = ? AND deleted_at IS NULL
            ORDER BY start_date DESC
        """, (template_id,))
        
        rows = cursor.fetchall()
        return [self._row_to_entity(dict(row)) for row in rows]
    
    def update_adherence(self, plan_id: int, adherence: Decimal) -> bool:
        """
        Aggiorna percentuale di aderenza.
        
        Args:
            plan_id: ID del piano
            adherence: Nuova percentuale (0-100)
            
        Returns:
            True se successo
        """
        cursor = self.db.conn.cursor()
        cursor.execute("""
            UPDATE treatment_plans 
            SET adherence_percentage = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (float(adherence), plan_id))
        
        self.db.conn.commit()
        return cursor.rowcount > 0
    
    def increment_days_completed(self, plan_id: int) -> bool:
        """
        Incrementa contatore giorni completati.
        
        Args:
            plan_id: ID del piano
            
        Returns:
            True se successo
        """
        cursor = self.db.conn.cursor()
        cursor.execute("""
            UPDATE treatment_plans 
            SET days_completed = days_completed + 1, 
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (plan_id,))
        
        self.db.conn.commit()
        return cursor.rowcount > 0
    
    def change_status(self, plan_id: int, new_status: str) -> bool:
        """
        Cambia status del piano.
        
        Args:
            plan_id: ID del piano
            new_status: Nuovo status
            
        Returns:
            True se successo
        """
        valid_statuses = ['active', 'paused', 'completed', 'abandoned', 'planned']
        if new_status not in valid_statuses:
            raise ValueError(f"Status non valido: {new_status}")
        
        cursor = self.db.conn.cursor()
        
        # Se completato, registra actual_end_date
        if new_status == 'completed':
            cursor.execute("""
                UPDATE treatment_plans 
                SET status = ?, 
                    actual_end_date = CURRENT_DATE,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (new_status, plan_id))
        else:
            cursor.execute("""
                UPDATE treatment_plans 
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (new_status, plan_id))
        
        self.db.conn.commit()
        return cursor.rowcount > 0


class TreatmentPlanPreparationRepository(Repository):
    """Repository per associazioni piano-preparazione."""
    
    def __init__(self, db):
        super().__init__(db, 'treatment_plan_preparations', TreatmentPlanPreparation)
    
    def get_by_plan(self, plan_id: int) -> List[TreatmentPlanPreparation]:
        """
        Recupera tutte le preparazioni di un piano.
        
        Args:
            plan_id: ID del piano
            
        Returns:
            Lista di associazioni
        """
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT * FROM treatment_plan_preparations 
            WHERE plan_id = ?
            ORDER BY created_at DESC
        """, (plan_id,))
        
        rows = cursor.fetchall()
        return [self._row_to_entity(dict(row)) for row in rows]
    
    def get_active_preparations(self, plan_id: int) -> List[TreatmentPlanPreparation]:
        """
        Recupera preparazioni attive di un piano.
        
        Args:
            plan_id: ID del piano
            
        Returns:
            Lista di preparazioni attive
        """
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT * FROM treatment_plan_preparations 
            WHERE plan_id = ? AND is_active = 1
            ORDER BY phase_start_date DESC
        """, (plan_id,))
        
        rows = cursor.fetchall()
        return [self._row_to_entity(dict(row)) for row in rows]
