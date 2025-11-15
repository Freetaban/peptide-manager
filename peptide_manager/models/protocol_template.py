"""
ProtocolTemplate model - gestisce i template di protocolli riutilizzabili.

Un ProtocolTemplate è uno schema di dosaggio teorico che può essere riutilizzato
per creare multipli TreatmentPlan (cicli di trattamento).
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict
from datetime import datetime
from decimal import Decimal

from .base import BaseModel, Repository


@dataclass
class ProtocolTemplate(BaseModel):
    """Rappresenta un template di protocollo riutilizzabile."""
    
    # Campi obbligatori
    name: str = field(default="")
    
    # Campi opzionali
    description: Optional[str] = None
    dose_ml: Optional[Decimal] = None
    frequency_per_day: int = 1
    days_on: Optional[int] = None
    days_off: int = 0
    cycle_duration_weeks: Optional[int] = None
    notes: Optional[str] = None
    tags: Optional[str] = None  # Comma-separated tags
    is_active: bool = True
    deleted_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Validazione e conversioni dopo inizializzazione."""
        # Conversione dose_ml
        if self.dose_ml and isinstance(self.dose_ml, (int, float, str)):
            self.dose_ml = Decimal(str(self.dose_ml))
        
        # Conversione deleted_at
        if self.deleted_at and isinstance(self.deleted_at, str):
            self.deleted_at = datetime.fromisoformat(self.deleted_at)
        
        # Conversione is_active da int a bool
        if isinstance(self.is_active, int):
            self.is_active = bool(self.is_active)
        
        # Gestione NULL
        if self.frequency_per_day is None:
            self.frequency_per_day = 1
        if self.days_off is None:
            self.days_off = 0
        if self.is_active is None:
            self.is_active = True
        
        # Validazioni
        if not self.name or not self.name.strip():
            raise ValueError("Nome template obbligatorio")
        
        if self.dose_ml is not None and self.dose_ml <= 0:
            raise ValueError("Dose deve essere > 0")
        
        if self.frequency_per_day < 1:
            raise ValueError("Frequenza deve essere >= 1")
        
        if self.days_on is not None and self.days_on < 1:
            raise ValueError("Days ON deve essere >= 1")
        
        if self.days_off < 0:
            raise ValueError("Days OFF deve essere >= 0")
        
        if self.cycle_duration_weeks is not None and self.cycle_duration_weeks < 1:
            raise ValueError("Durata ciclo deve essere >= 1 settimana")
    
    def is_deleted(self) -> bool:
        """Verifica se eliminato (soft delete)."""
        return self.deleted_at is not None
    
    def has_cycle(self) -> bool:
        """Verifica se il template ha un ciclo on/off."""
        return self.days_on is not None and self.days_on > 0
    
    def calculate_daily_dose_ml(self) -> Optional[Decimal]:
        """
        Calcola dose giornaliera totale in ml.
        
        Returns:
            Dose giornaliera o None se dose_ml non definita
        """
        if self.dose_ml is None:
            return None
        return self.dose_ml * self.frequency_per_day
    
    def calculate_cycle_total_dose_ml(self) -> Optional[Decimal]:
        """
        Calcola dose totale per un ciclo completo.
        
        Returns:
            Dose totale ml per ciclo o None se non calcolabile
        """
        if not self.has_cycle() or self.dose_ml is None:
            return None
        
        return self.dose_ml * self.frequency_per_day * self.days_on
    
    def get_tags_list(self) -> List[str]:
        """
        Ottiene lista di tags.
        
        Returns:
            Lista di tags (vuota se non presenti)
        """
        if not self.tags:
            return []
        return [tag.strip() for tag in self.tags.split(',') if tag.strip()]
    
    def add_tag(self, tag: str):
        """
        Aggiunge un tag.
        
        Args:
            tag: Tag da aggiungere
        """
        tags = self.get_tags_list()
        if tag not in tags:
            tags.append(tag)
            self.tags = ', '.join(tags)
    
    def remove_tag(self, tag: str):
        """
        Rimuove un tag.
        
        Args:
            tag: Tag da rimuovere
        """
        tags = self.get_tags_list()
        if tag in tags:
            tags.remove(tag)
            self.tags = ', '.join(tags) if tags else None


@dataclass
class ProtocolTemplatePeptide(BaseModel):
    """Associazione tra ProtocolTemplate e Peptide con dosaggio target."""
    
    # Campi obbligatori
    template_id: int = field(default=None)
    peptide_id: int = field(default=None)
    target_dose_mcg: Decimal = field(default=None)
    
    # Campi opzionali
    frequency: Optional[str] = None  # e.g., "1x/day", "2x/day"
    notes: Optional[str] = None
    
    def __post_init__(self):
        """Validazione e conversioni."""
        # Conversione target_dose_mcg
        if isinstance(self.target_dose_mcg, (int, float, str)):
            self.target_dose_mcg = Decimal(str(self.target_dose_mcg))
        
        # Validazioni
        if self.template_id is None:
            raise ValueError("template_id obbligatorio")
        if self.peptide_id is None:
            raise ValueError("peptide_id obbligatorio")
        if self.target_dose_mcg is None or self.target_dose_mcg <= 0:
            raise ValueError("target_dose_mcg deve essere > 0")


class ProtocolTemplateRepository(Repository):
    """Repository per operazioni CRUD sui template di protocolli."""
    
    def __init__(self, db):
        super().__init__(db, 'protocol_templates', ProtocolTemplate)
    
    def get_active_templates(self) -> List[ProtocolTemplate]:
        """
        Recupera tutti i template attivi.
        
        Returns:
            Lista di template attivi
        """
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT * FROM protocol_templates 
            WHERE is_active = 1 AND deleted_at IS NULL
            ORDER BY name
        """)
        
        rows = cursor.fetchall()
        return [self._row_to_entity(dict(row)) for row in rows]
    
    def search_by_name(self, query: str) -> List[ProtocolTemplate]:
        """
        Cerca template per nome.
        
        Args:
            query: Stringa di ricerca
            
        Returns:
            Lista di template che matchano
        """
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT * FROM protocol_templates 
            WHERE name LIKE ? AND deleted_at IS NULL
            ORDER BY name
        """, (f'%{query}%',))
        
        rows = cursor.fetchall()
        return [self._row_to_entity(dict(row)) for row in rows]
    
    def search_by_tag(self, tag: str) -> List[ProtocolTemplate]:
        """
        Cerca template per tag.
        
        Args:
            tag: Tag da cercare
            
        Returns:
            Lista di template con quel tag
        """
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT * FROM protocol_templates 
            WHERE tags LIKE ? AND deleted_at IS NULL
            ORDER BY name
        """, (f'%{tag}%',))
        
        rows = cursor.fetchall()
        return [self._row_to_entity(dict(row)) for row in rows]
    
    def get_most_used(self, limit: int = 10) -> List[Dict]:
        """
        Recupera i template più utilizzati.
        
        Args:
            limit: Numero massimo di risultati
            
        Returns:
            Lista di dict con template e conteggio utilizzi
        """
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT 
                pt.*,
                COUNT(tp.id) as usage_count
            FROM protocol_templates pt
            LEFT JOIN treatment_plans tp ON tp.protocol_template_id = pt.id
            WHERE pt.deleted_at IS NULL
            GROUP BY pt.id
            ORDER BY usage_count DESC, pt.name
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        results = []
        for row in rows:
            row_dict = dict(row)
            usage_count = row_dict.pop('usage_count')
            template = self._row_to_entity(row_dict)
            results.append({
                'template': template,
                'usage_count': usage_count
            })
        return results
    
    def deactivate(self, template_id: int) -> bool:
        """
        Disattiva un template (non elimina).
        
        Args:
            template_id: ID del template
            
        Returns:
            True se successo
        """
        cursor = self.db.conn.cursor()
        cursor.execute("""
            UPDATE protocol_templates 
            SET is_active = 0
            WHERE id = ?
        """, (template_id,))
        
        self.db.conn.commit()
        return cursor.rowcount > 0
    
    def activate(self, template_id: int) -> bool:
        """
        Riattiva un template.
        
        Args:
            template_id: ID del template
            
        Returns:
            True se successo
        """
        cursor = self.db.conn.cursor()
        cursor.execute("""
            UPDATE protocol_templates 
            SET is_active = 1
            WHERE id = ?
        """, (template_id,))
        
        self.db.conn.commit()
        return cursor.rowcount > 0


class ProtocolTemplatePeptideRepository(Repository):
    """Repository per associazioni template-peptide."""
    
    def __init__(self, db):
        super().__init__(db, 'protocol_template_peptides', ProtocolTemplatePeptide)
    
    def get_by_template(self, template_id: int) -> List[ProtocolTemplatePeptide]:
        """
        Recupera tutti i peptidi di un template.
        
        Args:
            template_id: ID del template
            
        Returns:
            Lista di associazioni
        """
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT * FROM protocol_template_peptides 
            WHERE template_id = ?
            ORDER BY id
        """, (template_id,))
        
        rows = cursor.fetchall()
        return [self._row_to_entity(dict(row)) for row in rows]
    
    def get_template_peptides_details(self, template_id: int) -> List[Dict]:
        """
        Recupera peptidi con dettagli completi.
        
        Args:
            template_id: ID del template
            
        Returns:
            Lista di dict con info peptide e dosaggio
        """
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT 
                ptp.*,
                p.name as peptide_name,
                p.description as peptide_description
            FROM protocol_template_peptides ptp
            JOIN peptides p ON p.id = ptp.peptide_id
            WHERE ptp.template_id = ?
            ORDER BY p.name
        """, (template_id,))
        
        rows = cursor.fetchall()
        results = []
        for row in rows:
            row_dict = dict(row)
            peptide_name = row_dict.pop('peptide_name')
            peptide_description = row_dict.pop('peptide_description')
            
            assoc = self._row_to_entity(row_dict)
            results.append({
                'association': assoc,
                'peptide_name': peptide_name,
                'peptide_description': peptide_description
            })
        return results
    
    def delete_by_template(self, template_id: int) -> int:
        """
        Elimina tutte le associazioni di un template.
        
        Args:
            template_id: ID del template
            
        Returns:
            Numero di righe eliminate
        """
        cursor = self.db.conn.cursor()
        cursor.execute("""
            DELETE FROM protocol_template_peptides 
            WHERE template_id = ?
        """, (template_id,))
        
        self.db.conn.commit()
        return cursor.rowcount
