"""
Protocol model - gestisce i protocolli di dosaggio.

Un protocollo definisce uno schema di somministrazione con dosi, frequenza, 
cicli on/off e peptidi target con dosaggi specifici.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple
from datetime import date, datetime
from decimal import Decimal

from .base import BaseModel, Repository


@dataclass
class Protocol(BaseModel):
    """Rappresenta un protocollo di dosaggio."""
    
    # Campi obbligatori
    name: str = field(default="")
    dose_ml: Optional[Decimal] = field(default=None)
    
    # Campi opzionali
    description: Optional[str] = None
    frequency_per_day: int = 1
    days_on: Optional[int] = None
    days_off: int = 0
    cycle_duration_weeks: Optional[int] = None
    notes: Optional[str] = None
    active: bool = True
    deleted_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Validazione e conversioni dopo inizializzazione."""
        # Conversioni PRIMA delle validazioni
        if self.dose_ml and isinstance(self.dose_ml, (int, float, str)):
            self.dose_ml = Decimal(str(self.dose_ml))
        
        # Conversione deleted_at
        if self.deleted_at and isinstance(self.deleted_at, str):
            self.deleted_at = datetime.fromisoformat(self.deleted_at)
        
        # Conversione active da int a bool (SQLite restituisce 0/1)
        if isinstance(self.active, int):
            self.active = bool(self.active)
        
        # Gestione NULL dal database - imposta default
        if self.frequency_per_day is None:
            self.frequency_per_day = 1
        if self.days_off is None:
            self.days_off = 0
        
        # Validazioni
        if not self.name or not self.name.strip():
            raise ValueError("Nome protocollo obbligatorio")
        
        if self.dose_ml is not None and self.dose_ml <= 0:
            raise ValueError("Dose deve essere > 0")
        
        if self.frequency_per_day < 1:
            raise ValueError("Frequenza deve essere >= 1")
        
        if self.days_on is not None and self.days_on < 1:
            raise ValueError("Days ON deve essere >= 1")
        
        if self.days_off < 0:
            raise ValueError("Days OFF deve essere >= 0")
    
    def is_deleted(self) -> bool:
        """Verifica se eliminato (soft delete)."""
        return self.deleted_at is not None
    
    def is_active(self) -> bool:
        """Verifica se protocollo attivo."""
        return self.active and not self.is_deleted()
    
    def has_cycle(self) -> bool:
        """Verifica se il protocollo ha un ciclo on/off."""
        return self.days_on is not None and self.days_on > 0
    
    def calculate_daily_dose_ml(self) -> Decimal:
        """Calcola dose giornaliera totale in ml."""
        return self.dose_ml * self.frequency_per_day
    
    def calculate_cycle_total_dose_ml(self) -> Optional[Decimal]:
        """
        Calcola dose totale per un ciclo completo (se applicabile).
        
        Returns:
            Dose totale ml per ciclo o None se non ha ciclo
        """
        if not self.has_cycle():
            return None
        
        return self.dose_ml * self.frequency_per_day * self.days_on


class ProtocolRepository(Repository):
    """Repository per operazioni CRUD sui protocolli."""
    
    def get_all(
        self,
        active_only: bool = False,
        include_deleted: bool = False
    ) -> List[Protocol]:
        """
        Recupera protocolli con filtri opzionali.
        
        Args:
            active_only: Solo protocolli attivi
            include_deleted: Include protocolli eliminati
        
        Returns:
            Lista di protocolli
        """
        query = 'SELECT * FROM protocols WHERE 1=1'
        params = []
        
        if not include_deleted:
            query += ' AND deleted_at IS NULL'
        
        if active_only:
            query += ' AND active = 1'
        
        query += ' ORDER BY created_at DESC'
        
        rows = self._fetch_all(query, tuple(params))
        return [Protocol.from_row(row) for row in rows]
    
    def get_by_id(
        self,
        protocol_id: int,
        include_deleted: bool = False
    ) -> Optional[Protocol]:
        """
        Recupera protocollo per ID.
        
        Args:
            protocol_id: ID protocollo
            include_deleted: Include anche se eliminato
        
        Returns:
            Protocol o None se non trovato
        """
        query = 'SELECT * FROM protocols WHERE id = ?'
        
        if not include_deleted:
            query += ' AND deleted_at IS NULL'
        
        row = self._fetch_one(query, (protocol_id,))
        return Protocol.from_row(row) if row else None
    
    def create(self, protocol: Protocol) -> int:
        """
        Crea nuovo protocollo.
        
        Args:
            protocol: Oggetto Protocol da creare
        
        Returns:
            ID protocollo creato
        
        Raises:
            ValueError: Se dati non validi
        """
        # Validazione
        if not protocol.name or not protocol.name.strip():
            raise ValueError("Nome protocollo obbligatorio")
        
        # Inserimento
        query = '''
            INSERT INTO protocols (
                name, description, frequency_per_day,
                days_on, days_off, cycle_duration_weeks,
                notes, active
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        '''
        
        cursor = self._execute(query, (
            protocol.name,
            protocol.description,
            protocol.frequency_per_day,
            protocol.days_on,
            protocol.days_off,
            protocol.cycle_duration_weeks,
            protocol.notes,
            1 if protocol.active else 0
        ))
        
        self._commit()
        return cursor.lastrowid
    
    def update(self, protocol: Protocol) -> bool:
        """
        Aggiorna protocollo esistente.
        
        Args:
            protocol: Oggetto Protocol con dati aggiornati (deve avere id)
        
        Returns:
            True se aggiornato
        
        Raises:
            ValueError: Se id non specificato o dati non validi
        """
        if protocol.id is None:
            raise ValueError("ID necessario per update")
        
        # Validazione
        if not protocol.name or not protocol.name.strip():
            raise ValueError("Nome protocollo obbligatorio")
        
        if protocol.dose_ml <= 0:
            raise ValueError("Dose deve essere > 0")
        
        query = '''
            UPDATE protocols
            SET name = ?, description = ?, dose_ml = ?,
                frequency_per_day = ?, days_on = ?, days_off = ?,
                cycle_duration_weeks = ?, notes = ?, active = ?
            WHERE id = ?
        '''
        
        self._execute(query, (
            protocol.name,
            protocol.description,
            float(protocol.dose_ml),
            protocol.frequency_per_day,
            protocol.days_on,
            protocol.days_off,
            protocol.cycle_duration_weeks,
            protocol.notes,
            1 if protocol.active else 0,
            protocol.id
        ))
        
        self._commit()
        return True
    
    def delete(
        self,
        protocol_id: int,
        force: bool = False,
        unlink_administrations: bool = True
    ) -> Tuple[bool, str]:
        """
        Elimina protocollo (soft delete di default).
        
        Args:
            protocol_id: ID protocollo
            force: Se True, elimina fisicamente (hard delete)
            unlink_administrations: Se True, scollega amministrazioni prima di eliminare
        
        Returns:
            (success: bool, message: str)
        """
        # Verifica esistenza
        protocol = self.get_by_id(protocol_id, include_deleted=True)
        if not protocol:
            return False, f"Protocollo #{protocol_id} non trovato"
        
        if protocol.is_deleted() and not force:
            return False, "Protocollo già eliminato"
        
        # Controlla amministrazioni collegate
        admin_query = 'SELECT COUNT(*) FROM administrations WHERE protocol_id = ? AND deleted_at IS NULL'
        admin_row = self._fetch_one(admin_query, (protocol_id,))
        admin_count = admin_row[0] if admin_row else 0
        
        if admin_count > 0:
            if unlink_administrations:
                # Scollega amministrazioni (setta protocol_id a NULL)
                unlink_query = 'UPDATE administrations SET protocol_id = NULL WHERE protocol_id = ?'
                self._execute(unlink_query, (protocol_id,))
            elif not force:
                return False, (
                    f"Impossibile eliminare: {admin_count} somministrazione(i) collegata(e). "
                    f"Usa unlink_administrations=True o force=True"
                )
        
        if force:
            # Hard delete
            # Prima elimina record in protocol_peptides (CASCADE dovrebbe farlo automaticamente)
            query = 'DELETE FROM protocols WHERE id = ?'
            self._execute(query, (protocol_id,))
            self._commit()
            return True, "Protocollo eliminato definitivamente"
        else:
            # Soft delete
            query = 'UPDATE protocols SET deleted_at = CURRENT_TIMESTAMP, active = 0 WHERE id = ?'
            self._execute(query, (protocol_id,))
            self._commit()
            return True, "Protocollo archiviato (soft delete)"
    
    def activate(self, protocol_id: int) -> Tuple[bool, str]:
        """
        Attiva un protocollo.
        
        Args:
            protocol_id: ID protocollo
        
        Returns:
            (success: bool, message: str)
        """
        protocol = self.get_by_id(protocol_id, include_deleted=False)
        if not protocol:
            return False, f"Protocollo #{protocol_id} non trovato"
        
        if protocol.active:
            return False, "Protocollo già attivo"
        
        query = 'UPDATE protocols SET active = 1 WHERE id = ?'
        self._execute(query, (protocol_id,))
        self._commit()
        
        return True, "Protocollo attivato"
    
    def deactivate(self, protocol_id: int) -> Tuple[bool, str]:
        """
        Disattiva un protocollo.
        
        Args:
            protocol_id: ID protocollo
        
        Returns:
            (success: bool, message: str)
        """
        protocol = self.get_by_id(protocol_id, include_deleted=False)
        if not protocol:
            return False, f"Protocollo #{protocol_id} non trovato"
        
        if not protocol.active:
            return False, "Protocollo già disattivo"
        
        query = 'UPDATE protocols SET active = 0 WHERE id = ?'
        self._execute(query, (protocol_id,))
        self._commit()
        
        return True, "Protocollo disattivato"
    
    def get_peptides_for_protocol(self, protocol_id: int) -> List[Dict]:
        """
        Recupera peptidi associati al protocollo con dosaggi target.
        
        Args:
            protocol_id: ID protocollo
        
        Returns:
            Lista di dict con id, peptide_id, name, target_dose_mcg
        """
        query = '''
            SELECT p.id as id, p.id as peptide_id, p.name, pp.target_dose_mcg
            FROM protocol_peptides pp
            JOIN peptides p ON pp.peptide_id = p.id
            WHERE pp.protocol_id = ?
            ORDER BY p.name
        '''
        
        rows = self._fetch_all(query, (protocol_id,))
        return [dict(row) for row in rows]
    
    def add_peptide_to_protocol(
        self,
        protocol_id: int,
        peptide_id: int,
        target_dose_mcg: float
    ) -> Tuple[bool, str]:
        """
        Aggiungi peptide al protocollo.
        
        Args:
            protocol_id: ID protocollo
            peptide_id: ID peptide
            target_dose_mcg: Dosaggio target in mcg
        
        Returns:
            (success: bool, message: str)
        """
        # Verifica protocollo esiste
        if not self.get_by_id(protocol_id):
            return False, f"Protocollo #{protocol_id} non trovato"
        
        # Verifica peptide esiste
        peptide_query = 'SELECT id FROM peptides WHERE id = ?'
        if not self._fetch_one(peptide_query, (peptide_id,)):
            return False, f"Peptide #{peptide_id} non trovato"
        
        # Verifica non esiste già
        check_query = '''
            SELECT id FROM protocol_peptides 
            WHERE protocol_id = ? AND peptide_id = ?
        '''
        if self._fetch_one(check_query, (protocol_id, peptide_id)):
            return False, "Peptide già associato al protocollo"
        
        # Inserisci
        query = '''
            INSERT INTO protocol_peptides (protocol_id, peptide_id, target_dose_mcg)
            VALUES (?, ?, ?)
        '''
        self._execute(query, (protocol_id, peptide_id, target_dose_mcg))
        self._commit()
        
        return True, "Peptide aggiunto al protocollo"
    
    def remove_peptide_from_protocol(
        self,
        protocol_id: int,
        peptide_id: int
    ) -> Tuple[bool, str]:
        """
        Rimuovi peptide dal protocollo.
        
        Args:
            protocol_id: ID protocollo
            peptide_id: ID peptide
        
        Returns:
            (success: bool, message: str)
        """
        query = '''
            DELETE FROM protocol_peptides
            WHERE protocol_id = ? AND peptide_id = ?
        '''
        cursor = self._execute(query, (protocol_id, peptide_id))
        self._commit()
        
        if cursor.rowcount == 0:
            return False, "Associazione non trovata"
        
        return True, "Peptide rimosso dal protocollo"
    
    def get_statistics(self, protocol_id: int) -> Optional[Dict]:
        """
        Recupera statistiche somministrazioni per protocollo.
        
        Args:
            protocol_id: ID protocollo
        
        Returns:
            Dict con count, first_date, last_date, total_ml o None
        """
        protocol = self.get_by_id(protocol_id)
        if not protocol:
            return None
        
        query = '''
            SELECT 
                COUNT(*) as count,
                MIN(administration_datetime) as first_date,
                MAX(administration_datetime) as last_date,
                SUM(dose_ml) as total_ml
            FROM administrations
            WHERE protocol_id = ? AND deleted_at IS NULL
        '''
        
        row = self._fetch_one(query, (protocol_id,))
        if not row:
            return {
                'count': 0,
                'first_date': None,
                'last_date': None,
                'total_ml': 0
            }
        
        return {
            'count': row[0] or 0,
            'first_date': row[1],
            'last_date': row[2],
            'total_ml': float(row[3]) if row[3] else 0.0
        }
    
    def count(
        self,
        active_only: bool = False,
        include_deleted: bool = False
    ) -> int:
        """
        Conta protocolli totali.
        
        Args:
            active_only: Conta solo protocolli attivi
            include_deleted: Include protocolli eliminati
        
        Returns:
            Numero protocolli
        """
        query = 'SELECT COUNT(*) FROM protocols WHERE 1=1'
        
        if not include_deleted:
            query += ' AND deleted_at IS NULL'
        
        if active_only:
            query += ' AND active = 1'
        
        row = self._fetch_one(query)
        return row[0] if row else 0
