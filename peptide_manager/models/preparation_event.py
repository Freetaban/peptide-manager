"""
Modulo PreparationEvents - Storico eventi di una preparazione.

Ogni spreco (wastage) registrato su una preparazione e' un record autonomo con
identita' propria, quindi correggibile e cancellabile. Le colonne wastage_* su
`preparations` restano come cache derivata, ricalcolata da questi eventi.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Tuple
from datetime import date, datetime
from decimal import Decimal

from .base import BaseModel, Repository


VALID_REASONS = ('measurement_error', 'spillage', 'contamination', 'other')
VALID_EVENT_TYPES = ('wastage', 'depletion')

# Tolleranza pratica per residui float/Decimal, coerente con Preparation
TOLERANCE = Decimal('0.01')


@dataclass
class PreparationEvent(BaseModel):
    """Un singolo episodio di spreco/esaurimento su una preparazione."""

    preparation_id: int = field(default=None)
    volume_ml: Decimal = field(default=None)

    event_type: str = 'wastage'
    event_date: Optional[date] = None
    reason: Optional[str] = None
    notes: Optional[str] = None

    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None

    def __post_init__(self):
        if self.preparation_id is None:
            raise ValueError("Preparation ID obbligatorio")
        if self.volume_ml is None:
            raise ValueError("Volume obbligatorio")

        if self.event_type not in VALID_EVENT_TYPES:
            raise ValueError(
                f"Event type deve essere uno di: {', '.join(VALID_EVENT_TYPES)}"
            )

        if self.reason is not None and self.reason not in VALID_REASONS:
            raise ValueError(
                f"Reason deve essere uno di: {', '.join(VALID_REASONS)}"
            )

        if isinstance(self.volume_ml, (int, float, str)):
            self.volume_ml = Decimal(str(self.volume_ml))

        if self.volume_ml <= 0:
            raise ValueError("Volume deve essere > 0")

        if self.event_date is None:
            self.event_date = date.today()
        elif isinstance(self.event_date, str):
            self.event_date = date.fromisoformat(self.event_date)

        if self.updated_at and isinstance(self.updated_at, str):
            self.updated_at = datetime.fromisoformat(self.updated_at)
        if self.deleted_at and isinstance(self.deleted_at, str):
            self.deleted_at = datetime.fromisoformat(self.deleted_at)

    def is_deleted(self) -> bool:
        return self.deleted_at is not None


class PreparationEventRepository(Repository):
    """Repository per gli eventi di una preparazione."""

    def get_by_preparation(
        self,
        prep_id: int,
        include_deleted: bool = False
    ) -> List[PreparationEvent]:
        """Recupera gli eventi di una preparazione, dal piu' vecchio al piu' recente."""
        query = 'SELECT * FROM preparation_events WHERE preparation_id = ?'
        if not include_deleted:
            query += ' AND deleted_at IS NULL'
        query += ' ORDER BY event_date ASC, id ASC'

        rows = self._fetch_all(query, (prep_id,))
        return [PreparationEvent.from_row(row) for row in rows]

    def get_by_id(
        self,
        event_id: int,
        include_deleted: bool = False
    ) -> Optional[PreparationEvent]:
        query = 'SELECT * FROM preparation_events WHERE id = ?'
        if not include_deleted:
            query += ' AND deleted_at IS NULL'
        row = self._fetch_one(query, (event_id,))
        return PreparationEvent.from_row(row) if row else None

    def total_wastage(self, prep_id: int) -> Decimal:
        """Somma degli sprechi non cancellati di una preparazione."""
        query = '''
            SELECT COALESCE(SUM(volume_ml), 0)
            FROM preparation_events
            WHERE preparation_id = ? AND deleted_at IS NULL
        '''
        row = self._fetch_one(query, (prep_id,))
        return Decimal(str(row[0])) if row else Decimal('0')

    def create(self, event: PreparationEvent) -> int:
        """Inserisce un evento. Non ricalcola: usa PreparationRepository."""
        query = '''
            INSERT INTO preparation_events
                (preparation_id, event_type, volume_ml, event_date, reason, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        '''
        cursor = self._execute(query, (
            event.preparation_id,
            event.event_type,
            float(event.volume_ml),
            event.event_date.isoformat(),
            event.reason,
            event.notes,
        ))
        self._commit()
        return cursor.lastrowid

    def update(self, event: PreparationEvent) -> bool:
        """Aggiorna un evento. Non ricalcola: usa PreparationRepository."""
        if event.id is None:
            raise ValueError("ID evento necessario per update")

        query = '''
            UPDATE preparation_events
            SET volume_ml = ?,
                event_date = ?,
                reason = ?,
                notes = ?,
                updated_at = ?
            WHERE id = ? AND deleted_at IS NULL
        '''
        self._execute(query, (
            float(event.volume_ml),
            event.event_date.isoformat(),
            event.reason,
            event.notes,
            datetime.now().isoformat(),
            event.id,
        ))
        self._commit()
        return True

    def delete(self, event_id: int) -> Tuple[bool, str]:
        """Soft delete di un evento. Non ricalcola: usa PreparationRepository."""
        event = self.get_by_id(event_id)
        if not event:
            return False, f"Evento #{event_id} non trovato"

        query = 'UPDATE preparation_events SET deleted_at = ? WHERE id = ?'
        self._execute(query, (datetime.now().isoformat(), event_id))
        self._commit()
        return True, f"Evento #{event_id} eliminato"
