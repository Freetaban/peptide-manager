"""
Cycle model and repository.

Provides a minimal dataclass for Cycle and a repository with basic CRUD
and administration assignment helpers. This is intentionally lightweight
as a first scaffold to integrate with the GUI and the existing DB.
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import date, datetime
import json


@dataclass
class Cycle:
    id: Optional[int] = None
    protocol_id: int = 0
    name: str = ""
    description: Optional[str] = None
    start_date: Optional[date] = None
    planned_end_date: Optional[date] = None
    actual_end_date: Optional[date] = None
    days_on: Optional[int] = None
    days_off: int = 0
    cycle_duration_weeks: Optional[int] = None
    protocol_snapshot: Optional[Dict[str, Any]] = None
    ramp_schedule: Optional[List[Dict[str, Any]]] = None
    status: str = 'active'
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_row(self) -> Dict:
        return {
            'id': self.id,
            'protocol_id': self.protocol_id,
            'name': self.name,
            'description': self.description,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'planned_end_date': self.planned_end_date.isoformat() if self.planned_end_date else None,
            'actual_end_date': self.actual_end_date.isoformat() if self.actual_end_date else None,
            'days_on': self.days_on,
            'days_off': self.days_off,
            'cycle_duration_weeks': self.cycle_duration_weeks,
            'protocol_snapshot': json.dumps(self.protocol_snapshot) if self.protocol_snapshot else None,
            'ramp_schedule': json.dumps(self.ramp_schedule) if self.ramp_schedule else None,
            'status': self.status,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }


class CycleRepository:
    def __init__(self, conn):
        self.conn = conn

    def create(self, cycle: Cycle) -> int:
        query = '''
            INSERT INTO cycles (
                protocol_id, name, description, start_date, planned_end_date,
                actual_end_date, days_on, days_off, cycle_duration_weeks,
                protocol_snapshot, ramp_schedule, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''

        cur = self.conn.cursor()
        cur.execute(query, (
            cycle.protocol_id,
            cycle.name,
            cycle.description,
            cycle.start_date.isoformat() if cycle.start_date else None,
            cycle.planned_end_date.isoformat() if cycle.planned_end_date else None,
            cycle.actual_end_date.isoformat() if cycle.actual_end_date else None,
            cycle.days_on,
            cycle.days_off,
            cycle.cycle_duration_weeks,
            json.dumps(cycle.protocol_snapshot, default=str) if cycle.protocol_snapshot else None,
            json.dumps(cycle.ramp_schedule, default=str) if cycle.ramp_schedule else None,
            cycle.status,
        ))
        self.conn.commit()
        return cur.lastrowid

    def get_all(self, active_only: bool = True) -> List[Dict]:
        q = 'SELECT * FROM cycles WHERE 1=1'
        params = []
        if active_only:
            q += ' AND deleted_at IS NULL AND status = ?'
            params.append('active')

        q += ' ORDER BY created_at DESC'
        cur = self.conn.cursor()
        cur.execute(q, tuple(params))
        rows = cur.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            if d.get('protocol_snapshot'):
                d['protocol_snapshot'] = json.loads(d['protocol_snapshot'])
            if d.get('ramp_schedule'):
                d['ramp_schedule'] = json.loads(d['ramp_schedule'])
            result.append(d)
        return result

    def get_by_id(self, cycle_id: int) -> Optional[Dict]:
        cur = self.conn.cursor()
        cur.execute('SELECT * FROM cycles WHERE id = ?', (cycle_id,))
        row = cur.fetchone()
        if not row:
            return None
        d = dict(row)
        if d.get('protocol_snapshot'):
            d['protocol_snapshot'] = json.loads(d['protocol_snapshot'])
        if d.get('ramp_schedule'):
            d['ramp_schedule'] = json.loads(d['ramp_schedule'])
        return d

    def record_administration(self, cycle_id: int, administration_id: int) -> bool:
        """Associate an existing administration (from administrations table) to a cycle.

        This performs an update on `administrations` table setting protocol_id and
        a new column `cycle_id` if present. If `cycle_id` column is not present,
        it will only set protocol_id.
        """
        cur = self.conn.cursor()
        # Ensure we don't reassign an administration already linked to a different cycle
        try:
            cur.execute('SELECT cycle_id FROM administrations WHERE id = ?', (administration_id,))
            row = cur.fetchone()
            if row:
                existing_cycle = row['cycle_id'] if isinstance(row, dict) else row[0]
            else:
                existing_cycle = None
        except Exception:
            existing_cycle = None

        # If already linked to another cycle, do not overwrite
        if existing_cycle is not None and existing_cycle != cycle_id:
            return False

        # Try to update cycle_id if column exists (will set even if equal)
        try:
            cur.execute('UPDATE administrations SET cycle_id = ? WHERE id = ?', (cycle_id, administration_id))
        except Exception:
            # If column doesn't exist, ignore and fallback
            pass

        # Also link protocol_id to the administration using the cycle's protocol
        cycle = self.get_by_id(cycle_id)
        if not cycle:
            return False

        protocol_id = cycle.get('protocol_id')
        if protocol_id:
            cur.execute('UPDATE administrations SET protocol_id = ? WHERE id = ?', (protocol_id, administration_id))

        self.conn.commit()
        return True

    def assign_administrations(self, admin_ids: List[int], cycle_id: int) -> int:
        count = 0
        for aid in admin_ids:
            if self.record_administration(cycle_id, aid):
                count += 1
        return count

    def update_ramp_schedule(self, cycle_id: int, ramp_schedule: List[Dict]) -> bool:
        """Aggiorna il campo `ramp_schedule` di un ciclo con una struttura serializzabile in JSON."""
        cur = self.conn.cursor()
        try:
            cur.execute('UPDATE cycles SET ramp_schedule = ? WHERE id = ?', (json.dumps(ramp_schedule, default=str), cycle_id))
            self.conn.commit()
            return True
        except Exception:
            return False
