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
    protocol_id: Optional[int] = None  # Made optional for planner-generated cycles
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
    plan_phase_id: Optional[int] = None  # Link to plan_phases table
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def get_current_week(self, target_date: Optional[date] = None) -> int:
        """Calculate current week of cycle (1-indexed)."""
        if not self.start_date:
            return 1
        
        if target_date is None:
            target_date = date.today()
        
        days_elapsed = (target_date - self.start_date).days
        return (days_elapsed // 7) + 1
    
    def get_ramp_dose(self, peptide_id: int, target_date: Optional[date] = None) -> Optional[float]:
        """Get exact ramp-up dose in mcg for specific peptide and week.
        
        Args:
            peptide_id: ID of the peptide
            target_date: Target date (default: today)
            
        Returns:
            Dose in mcg if defined in ramp_schedule, None otherwise
        """
        if not self.ramp_schedule:
            return None
        
        current_week = self.get_current_week(target_date)
        
        # Format: [{'week': 1, 'doses': [{'peptide_id': 1, 'dose_mcg': 250}, ...]}, ...]
        # OR legacy format: [{'week': 1, 'percentage': 50}, ...] (fallback)
        for entry in self.ramp_schedule:
            if entry.get('week') == current_week:
                # New format: exact doses per peptide
                if 'doses' in entry:
                    for dose_entry in entry.get('doses', []):
                        if dose_entry.get('peptide_id') == peptide_id:
                            return dose_entry.get('dose_mcg')
                # Legacy format: percentage (deprecated but supported)
                elif 'percentage' in entry:
                    # Return None to signal "use percentage" in caller
                    return None
        
        return None
    
    def get_ramp_percentage(self, target_date: Optional[date] = None) -> float:
        """Get ramp-up percentage for current week (legacy compatibility).
        
        DEPRECATED: Use get_ramp_dose() for exact doses.
        """
        if not self.ramp_schedule:
            return 1.0  # No ramp = full dose
        
        current_week = self.get_current_week(target_date)
        
        # Find matching week in ramp_schedule
        # Format: [{'week': 1, 'percentage': 50}, {'week': 2, 'percentage': 75}, ...]
        for entry in self.ramp_schedule:
            if entry.get('week') == current_week:
                # New format with exact doses - return 1.0 (caller should use get_ramp_dose)
                if 'doses' in entry:
                    return 1.0
                # Legacy format with percentage
                return entry.get('percentage', 100) / 100.0
        
        # If week not in schedule, check if we're past all defined weeks
        max_week = max((e.get('week', 0) for e in self.ramp_schedule), default=0)
        if current_week > max_week:
            # Past ramp period, use 100%
            return 1.0
        
        # Before ramp starts or between gaps, use previous week's percentage
        sorted_schedule = sorted(self.ramp_schedule, key=lambda x: x.get('week', 0))
        for i, entry in enumerate(sorted_schedule):
            if entry.get('week', 0) > current_week:
                if i > 0:
                    return sorted_schedule[i-1].get('percentage', 100) / 100.0
                else:
                    return sorted_schedule[0].get('percentage', 100) / 100.0
        
        return 1.0

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
    def __init__(self, db):
        # Support both sqlite3.Connection and DatabaseManager
        if hasattr(db, 'conn'):
            self.db = db
            self.conn = db.conn
        else:
            self.db = None
            self.conn = db

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

    def update(self, cycle_id: int, **kwargs) -> bool:
        """
        Update cycle fields.
        
        Args:
            cycle_id: ID of cycle to update
            **kwargs: Fields to update (name, description, start_date, planned_end_date,
                     days_on, days_off, cycle_duration_weeks, ramp_schedule, status)
        
        Returns:
            True if successful
        """
        # Allowed fields
        allowed_fields = {
            'name', 'description', 'start_date', 'planned_end_date',
            'days_on', 'days_off', 'cycle_duration_weeks', 'ramp_schedule', 'status'
        }
        
        # Filter valid fields
        updates = {}
        for key, value in kwargs.items():
            if key in allowed_fields:
                # Convert dates to ISO format
                if key in ('start_date', 'planned_end_date') and value:
                    if isinstance(value, date):
                        updates[key] = value.isoformat()
                    else:
                        updates[key] = value
                # Convert ramp_schedule to JSON
                elif key == 'ramp_schedule' and value:
                    updates[key] = json.dumps(value, default=str)
                else:
                    updates[key] = value
        
        if not updates:
            return False
        
        # Build query
        set_clause = ', '.join([f'{field} = ?' for field in updates.keys()])
        query = f'UPDATE cycles SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?'
        
        cur = self.conn.cursor()
        try:
            cur.execute(query, (*updates.values(), cycle_id))
            self.conn.commit()
            return cur.rowcount > 0
        except Exception:
            return False
    
    def update_ramp_schedule(self, cycle_id: int, ramp_schedule: List[Dict]) -> bool:
        """Aggiorna il campo `ramp_schedule` di un ciclo con una struttura serializzabile in JSON."""
        return self.update(cycle_id, ramp_schedule=ramp_schedule)
    
    def update_status(self, cycle_id: int, new_status: str) -> bool:
        """Update cycle status."""
        valid_statuses = ['planned', 'active', 'paused', 'completed', 'cancelled']
        if new_status not in valid_statuses:
            return False
        
        cur = self.conn.cursor()
        try:
            cur.execute(
                'UPDATE cycles SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                (new_status, cycle_id)
            )
            self.conn.commit()
            return True
        except Exception:
            return False
    
    def complete_cycle(self, cycle_id: int) -> bool:
        """Mark cycle as completed with actual end date."""
        cur = self.conn.cursor()
        try:
            cur.execute(
                '''UPDATE cycles 
                   SET status = 'completed', 
                       actual_end_date = DATE('now'),
                       updated_at = CURRENT_TIMESTAMP 
                   WHERE id = ?''',
                (cycle_id,)
            )
            self.conn.commit()
            return True
        except Exception:
            return False
    
    def check_and_complete_expired_cycles(self) -> int:
        """
        Auto-complete cycles that have reached their planned_end_date.
        Returns number of cycles completed.
        """
        cur = self.conn.cursor()
        try:
            # Find active cycles past their planned end date
            cur.execute('''
                SELECT id, name, planned_end_date 
                FROM cycles 
                WHERE status = 'active' 
                  AND planned_end_date IS NOT NULL 
                  AND DATE(planned_end_date) <= DATE('now')
            ''')
            
            expired = cur.fetchall()
            count = 0
            
            for row in expired:
                cycle_id = row[0] if not isinstance(row, dict) else row['id']
                if self.complete_cycle(cycle_id):
                    count += 1
            
            return count
        except Exception:
            return 0
