"""
Unit tests for Cycle model and CycleRepository.
"""

import unittest
import sqlite3
import tempfile
import os
import json
from datetime import date, timedelta

from peptide_manager.models.cycle import Cycle, CycleRepository


class TestCycleModel(unittest.TestCase):
    """Tests for Cycle dataclass."""

    def test_create_cycle_defaults(self):
        """Cycle with defaults is valid."""
        cycle = Cycle(name="Test Cycle")
        self.assertEqual(cycle.name, "Test Cycle")
        self.assertIsNone(cycle.id)
        self.assertIsNone(cycle.protocol_id)
        self.assertEqual(cycle.status, 'active')
        self.assertEqual(cycle.days_off, 0)

    def test_create_cycle_complete(self):
        """Cycle with all fields set."""
        today = date.today()
        cycle = Cycle(
            id=1,
            protocol_id=5,
            name="Full Cycle",
            description="Test desc",
            start_date=today,
            planned_end_date=today + timedelta(weeks=4),
            days_on=5,
            days_off=2,
            cycle_duration_weeks=4,
            status='active',
        )
        self.assertEqual(cycle.protocol_id, 5)
        self.assertEqual(cycle.days_on, 5)
        self.assertEqual(cycle.cycle_duration_weeks, 4)

    def test_get_current_week_today(self):
        """Week 1 when start_date is today."""
        cycle = Cycle(name="C", start_date=date.today())
        self.assertEqual(cycle.get_current_week(), 1)

    def test_get_current_week_past(self):
        """Correct week calculation for past start_date."""
        start = date.today() - timedelta(days=14)  # 14 days ago
        cycle = Cycle(name="C", start_date=start)
        self.assertEqual(cycle.get_current_week(), 3)  # (14 // 7) + 1

    def test_get_current_week_future(self):
        """Week before start results in 0 or negative via formula."""
        start = date.today() + timedelta(days=7)
        cycle = Cycle(name="C", start_date=start)
        # (-7 // 7) + 1 = -1 + 1 = 0
        self.assertEqual(cycle.get_current_week(), 0)

    def test_get_current_week_no_start_date(self):
        """Returns 1 when no start_date."""
        cycle = Cycle(name="C")
        self.assertEqual(cycle.get_current_week(), 1)

    def test_get_ramp_dose_new_format(self):
        """Ramp dose with new format returns exact dose per peptide."""
        schedule = [
            {'week': 1, 'doses': [{'peptide_id': 1, 'dose_mcg': 250}]},
            {'week': 2, 'doses': [{'peptide_id': 1, 'dose_mcg': 500}]},
        ]
        cycle = Cycle(
            name="C",
            start_date=date.today(),
            ramp_schedule=schedule,
        )
        # Week 1 (today)
        dose = cycle.get_ramp_dose(1, target_date=cycle.start_date)
        self.assertEqual(dose, 250)

    def test_get_ramp_dose_legacy_format(self):
        """Legacy percentage format returns None (caller handles)."""
        schedule = [{'week': 1, 'percentage': 50}]
        cycle = Cycle(
            name="C",
            start_date=date.today(),
            ramp_schedule=schedule,
        )
        dose = cycle.get_ramp_dose(1, target_date=cycle.start_date)
        self.assertIsNone(dose)

    def test_get_ramp_dose_no_schedule(self):
        """No ramp schedule returns None."""
        cycle = Cycle(name="C", start_date=date.today())
        self.assertIsNone(cycle.get_ramp_dose(1))

    def test_get_ramp_percentage_legacy(self):
        """Legacy schedule returns correct percentage."""
        schedule = [
            {'week': 1, 'percentage': 50},
            {'week': 2, 'percentage': 75},
        ]
        cycle = Cycle(
            name="C",
            start_date=date.today(),
            ramp_schedule=schedule,
        )
        pct = cycle.get_ramp_percentage(target_date=cycle.start_date)
        self.assertEqual(pct, 0.5)

    def test_get_ramp_percentage_past_ramp(self):
        """After ramp period, returns 1.0."""
        schedule = [{'week': 1, 'percentage': 50}]
        cycle = Cycle(
            name="C",
            start_date=date.today() - timedelta(days=14),  # week 3
            ramp_schedule=schedule,
        )
        pct = cycle.get_ramp_percentage()
        self.assertEqual(pct, 1.0)

    def test_get_ramp_percentage_no_schedule(self):
        """No ramp schedule returns 1.0 (full dose)."""
        cycle = Cycle(name="C", start_date=date.today())
        self.assertEqual(cycle.get_ramp_percentage(), 1.0)

    def test_to_row_serialization(self):
        """to_row serializes dates and JSON fields."""
        today = date.today()
        snapshot = {'protocol': 'test'}
        schedule = [{'week': 1, 'percentage': 50}]
        cycle = Cycle(
            id=1,
            name="C",
            start_date=today,
            protocol_snapshot=snapshot,
            ramp_schedule=schedule,
        )
        row = cycle.to_row()
        self.assertEqual(row['start_date'], today.isoformat())
        self.assertEqual(json.loads(row['protocol_snapshot']), snapshot)
        self.assertEqual(json.loads(row['ramp_schedule']), schedule)

    def test_to_row_none_dates(self):
        """to_row handles None dates/JSON gracefully."""
        cycle = Cycle(name="C")
        row = cycle.to_row()
        self.assertIsNone(row['start_date'])
        self.assertIsNone(row['protocol_snapshot'])
        self.assertIsNone(row['ramp_schedule'])


class TestCycleRepository(unittest.TestCase):
    """Tests for CycleRepository."""

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.conn = sqlite3.connect(self.temp_db.name)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute('PRAGMA foreign_keys = ON')
        self._create_schema()
        self.repo = CycleRepository(self.conn)

    def tearDown(self):
        self.conn.close()
        os.unlink(self.temp_db.name)

    def _create_schema(self):
        self.conn.executescript('''
            CREATE TABLE protocols (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                dose_ml REAL,
                frequency_per_day INTEGER DEFAULT 1,
                days_on INTEGER,
                days_off INTEGER DEFAULT 0,
                cycle_duration_weeks INTEGER,
                active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP
            );
            CREATE TABLE cycles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                protocol_id INTEGER,
                name TEXT NOT NULL,
                description TEXT,
                start_date DATE,
                planned_end_date DATE,
                actual_end_date DATE,
                days_on INTEGER DEFAULT 7,
                days_off INTEGER DEFAULT 0,
                cycle_duration_weeks INTEGER,
                protocol_snapshot TEXT,
                ramp_schedule TEXT,
                status TEXT DEFAULT 'active',
                plan_phase_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP
            );
            CREATE TABLE administrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                preparation_id INTEGER,
                protocol_id INTEGER,
                administration_datetime TIMESTAMP NOT NULL,
                dose_ml REAL NOT NULL,
                injection_site TEXT,
                notes TEXT,
                cycle_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP
            );
        ''')

    def _make_cycle(self, **kwargs):
        defaults = dict(
            name="Test Cycle",
            start_date=date.today(),
            status='active',
        )
        defaults.update(kwargs)
        return Cycle(**defaults)

    def _insert_protocol(self, name="Proto"):
        cur = self.conn.cursor()
        cur.execute("INSERT INTO protocols (name) VALUES (?)", (name,))
        self.conn.commit()
        return cur.lastrowid

    def _insert_administration(self, dose_ml=0.1):
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO administrations (administration_datetime, dose_ml) VALUES (?, ?)",
            ('2025-06-01 08:00:00', dose_ml),
        )
        self.conn.commit()
        return cur.lastrowid

    def test_create_and_get(self):
        """Create a cycle and retrieve by id."""
        cycle = self._make_cycle()
        cid = self.repo.create(cycle)
        self.assertIsNotNone(cid)
        retrieved = self.repo.get_by_id(cid)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved['name'], "Test Cycle")
        self.assertEqual(retrieved['status'], 'active')

    def test_get_by_id_not_found(self):
        """Returns None for nonexistent id."""
        self.assertIsNone(self.repo.get_by_id(999))

    def test_get_all_active_only(self):
        """get_all with active_only filters by status."""
        self.repo.create(self._make_cycle(name="Active"))
        self.repo.create(self._make_cycle(name="Done", status='completed'))
        results = self.repo.get_all(active_only=True)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['name'], "Active")

    def test_get_all_include_inactive(self):
        """get_all with active_only=False returns all."""
        self.repo.create(self._make_cycle(name="Active"))
        self.repo.create(self._make_cycle(name="Done", status='completed'))
        results = self.repo.get_all(active_only=False)
        self.assertEqual(len(results), 2)

    def test_update_fields(self):
        """Update name, description, and JSON fields."""
        cid = self.repo.create(self._make_cycle())
        success = self.repo.update(cid, name="Updated", description="desc")
        self.assertTrue(success)
        retrieved = self.repo.get_by_id(cid)
        self.assertEqual(retrieved['name'], "Updated")
        self.assertEqual(retrieved['description'], "desc")

    def test_update_json_fields(self):
        """Update ramp_schedule and protocol_snapshot serializes JSON."""
        cid = self.repo.create(self._make_cycle())
        schedule = [{'week': 1, 'percentage': 50}]
        snapshot = {'protocol': 'data'}
        self.repo.update(cid, ramp_schedule=schedule, protocol_snapshot=snapshot)
        retrieved = self.repo.get_by_id(cid)
        self.assertEqual(retrieved['ramp_schedule'], schedule)
        self.assertEqual(retrieved['protocol_snapshot'], snapshot)

    def test_update_no_valid_fields(self):
        """Update with no recognized fields returns False."""
        cid = self.repo.create(self._make_cycle())
        self.assertFalse(self.repo.update(cid, bogus_field="x"))

    def test_delete(self):
        """Delete removes cycle and unlinks administrations."""
        cid = self.repo.create(self._make_cycle())
        aid = self._insert_administration()
        # Link administration to cycle
        self.conn.execute("UPDATE administrations SET cycle_id = ? WHERE id = ?", (cid, aid))
        self.conn.commit()

        success = self.repo.delete(cid)
        self.assertTrue(success)
        self.assertIsNone(self.repo.get_by_id(cid))
        # Administration's cycle_id should be cleared
        row = self.conn.execute("SELECT cycle_id FROM administrations WHERE id = ?", (aid,)).fetchone()
        self.assertIsNone(row['cycle_id'])

    def test_update_status_valid(self):
        """update_status accepts valid statuses."""
        cid = self.repo.create(self._make_cycle())
        for status in ['planned', 'paused', 'completed', 'cancelled']:
            self.assertTrue(self.repo.update_status(cid, status))
            self.assertEqual(self.repo.get_by_id(cid)['status'], status)

    def test_update_status_invalid(self):
        """update_status rejects invalid status."""
        cid = self.repo.create(self._make_cycle())
        self.assertFalse(self.repo.update_status(cid, 'invalid'))

    def test_complete_cycle(self):
        """complete_cycle sets status and actual_end_date."""
        cid = self.repo.create(self._make_cycle())
        self.assertTrue(self.repo.complete_cycle(cid))
        retrieved = self.repo.get_by_id(cid)
        self.assertEqual(retrieved['status'], 'completed')
        self.assertIsNotNone(retrieved['actual_end_date'])

    def test_record_administration(self):
        """Link an administration to a cycle."""
        proto_id = self._insert_protocol()
        cid = self.repo.create(self._make_cycle(protocol_id=proto_id))
        aid = self._insert_administration()

        self.assertTrue(self.repo.record_administration(cid, aid))
        row = self.conn.execute("SELECT cycle_id FROM administrations WHERE id = ?", (aid,)).fetchone()
        self.assertEqual(row['cycle_id'], cid)

    def test_record_administration_rejects_different_cycle(self):
        """Cannot reassign administration to a different cycle."""
        proto_id = self._insert_protocol()
        cid1 = self.repo.create(self._make_cycle(name="C1", protocol_id=proto_id))
        cid2 = self.repo.create(self._make_cycle(name="C2", protocol_id=proto_id))
        aid = self._insert_administration()

        # Link to first cycle
        self.repo.record_administration(cid1, aid)
        # Try to re-link to second cycle — should fail
        self.assertFalse(self.repo.record_administration(cid2, aid))

    def test_assign_administrations_bulk(self):
        """assign_administrations links multiple at once."""
        proto_id = self._insert_protocol()
        cid = self.repo.create(self._make_cycle(protocol_id=proto_id))
        aids = [self._insert_administration() for _ in range(3)]

        count = self.repo.assign_administrations(aids, cid)
        self.assertEqual(count, 3)

    def test_check_and_complete_expired_cycles(self):
        """Auto-completes cycles past planned_end_date."""
        yesterday = date.today() - timedelta(days=1)
        cid = self.repo.create(self._make_cycle(planned_end_date=yesterday))

        completed = self.repo.check_and_complete_expired_cycles()
        self.assertEqual(completed, 1)
        self.assertEqual(self.repo.get_by_id(cid)['status'], 'completed')

    def test_check_expired_skips_future(self):
        """Does not complete cycles with future end dates."""
        future = date.today() + timedelta(days=7)
        self.repo.create(self._make_cycle(planned_end_date=future))

        completed = self.repo.check_and_complete_expired_cycles()
        self.assertEqual(completed, 0)


if __name__ == '__main__':
    unittest.main()
