"""
Unit tests for TreatmentPlan model and TreatmentPlanRepository.
"""

import unittest
import sqlite3
import tempfile
import os
from datetime import date, timedelta
from decimal import Decimal

from peptide_manager.models.treatment_plan import TreatmentPlan, TreatmentPlanRepository


class TestTreatmentPlanModel(unittest.TestCase):
    """Tests for the TreatmentPlan dataclass."""

    def _make_plan(self, **kwargs):
        defaults = dict(name="Test Plan", start_date=date.today())
        defaults.update(kwargs)
        return TreatmentPlan(**defaults)

    def test_create_valid(self):
        plan = self._make_plan()
        self.assertEqual(plan.name, "Test Plan")
        self.assertEqual(plan.status, 'active')
        self.assertEqual(plan.days_completed, 0)
        self.assertEqual(plan.adherence_percentage, Decimal('100.0'))

    def test_empty_name_raises(self):
        with self.assertRaises(ValueError):
            TreatmentPlan(name="", start_date=date.today())

    def test_whitespace_name_raises(self):
        with self.assertRaises(ValueError):
            TreatmentPlan(name="   ", start_date=date.today())

    def test_missing_start_date_raises(self):
        with self.assertRaises(ValueError):
            TreatmentPlan(name="Plan", start_date=None)

    def test_invalid_status_raises(self):
        with self.assertRaises(ValueError):
            TreatmentPlan(name="Plan", start_date=date.today(), status='invalid')

    def test_adherence_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            self._make_plan(adherence_percentage=Decimal('101'))
        with self.assertRaises(ValueError):
            self._make_plan(adherence_percentage=Decimal('-1'))

    def test_negative_days_completed_raises(self):
        with self.assertRaises(ValueError):
            self._make_plan(days_completed=-1)

    def test_date_string_conversion(self):
        plan = self._make_plan(start_date='2025-06-01')
        self.assertEqual(plan.start_date, date(2025, 6, 1))

    def test_decimal_adherence_conversion(self):
        plan = self._make_plan(adherence_percentage=95.5)
        self.assertIsInstance(plan.adherence_percentage, Decimal)
        self.assertEqual(plan.adherence_percentage, Decimal('95.5'))

    def test_bool_is_multi_phase_conversion(self):
        plan = self._make_plan(is_multi_phase=1)
        self.assertIs(plan.is_multi_phase, True)

    # Status properties
    def test_is_active(self):
        plan = self._make_plan(status='active')
        self.assertTrue(plan.is_active())
        self.assertFalse(plan.is_completed())

    def test_is_completed(self):
        plan = self._make_plan(status='completed')
        self.assertTrue(plan.is_completed())
        self.assertFalse(plan.is_active())

    def test_is_paused(self):
        self.assertTrue(self._make_plan(status='paused').is_paused())

    def test_is_planned(self):
        self.assertTrue(self._make_plan(status='planned').is_planned())

    def test_is_deleted(self):
        plan = self._make_plan()
        self.assertFalse(plan.is_deleted())

    # Computed methods
    def test_calculate_progress_normal(self):
        plan = self._make_plan(total_planned_days=100, days_completed=50)
        self.assertEqual(plan.calculate_progress_percentage(), Decimal('50.0'))

    def test_calculate_progress_zero_planned(self):
        plan = self._make_plan(total_planned_days=0, days_completed=5)
        self.assertEqual(plan.calculate_progress_percentage(), Decimal('0.0'))

    def test_calculate_progress_overcomplete(self):
        plan = self._make_plan(total_planned_days=10, days_completed=15)
        self.assertEqual(plan.calculate_progress_percentage(), Decimal('100.0'))

    def test_get_remaining_days_normal(self):
        plan = self._make_plan(total_planned_days=30, days_completed=10)
        self.assertEqual(plan.get_remaining_days(), 20)

    def test_get_remaining_days_none_when_no_total(self):
        plan = self._make_plan()
        self.assertIsNone(plan.get_remaining_days())

    def test_get_remaining_days_past_end(self):
        plan = self._make_plan(total_planned_days=10, days_completed=15)
        self.assertEqual(plan.get_remaining_days(), 0)

    def test_calculate_estimated_end_date_no_progress(self):
        plan = self._make_plan(total_planned_days=30)
        # days_completed = 0 → returns planned_end_date
        result = plan.calculate_estimated_end_date()
        self.assertIsNone(result)  # planned_end_date is None


class TestTreatmentPlanRepository(unittest.TestCase):
    """Tests for TreatmentPlanRepository."""

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.conn = sqlite3.connect(self.temp_db.name)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute('PRAGMA foreign_keys = ON')
        self._create_schema()
        # TreatmentPlanRepository expects an object with .conn attribute
        # Repository.__init__ sets self.db = self and self.conn = connection
        # So passing raw conn works: self.db.conn == self.conn == raw conn
        self.repo = TreatmentPlanRepository(self.conn)

    def tearDown(self):
        self.conn.close()
        os.unlink(self.temp_db.name)

    def _create_schema(self):
        self.conn.executescript('''
            CREATE TABLE treatment_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                start_date DATE NOT NULL,
                protocol_template_id INTEGER,
                description TEXT,
                reason TEXT,
                planned_end_date DATE,
                actual_end_date DATE,
                status TEXT DEFAULT 'active',
                total_planned_days INTEGER,
                days_completed INTEGER DEFAULT 0,
                adherence_percentage REAL DEFAULT 100.0,
                notes TEXT,
                is_multi_phase INTEGER DEFAULT 0,
                simulation_id INTEGER,
                current_phase_id INTEGER,
                total_phases INTEGER DEFAULT 1,
                resources_summary TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP
            );
        ''')

    def _make_plan(self, **kwargs):
        defaults = dict(name="Test Plan", start_date=date.today())
        defaults.update(kwargs)
        return TreatmentPlan(**defaults)

    def test_create(self):
        plan = self._make_plan()
        pid = self.repo.create(plan)
        self.assertIsNotNone(pid)
        self.assertGreater(pid, 0)

    def test_get_by_id(self):
        pid = self.repo.create(self._make_plan(description="Desc"))
        retrieved = self.repo.get_by_id(pid)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, "Test Plan")
        self.assertEqual(retrieved.description, "Desc")

    def test_get_by_id_not_found(self):
        self.assertIsNone(self.repo.get_by_id(999))

    def test_get_all(self):
        self.repo.create(self._make_plan(name="Plan A"))
        self.repo.create(self._make_plan(name="Plan B"))
        plans = self.repo.get_all()
        self.assertEqual(len(plans), 2)

    def test_get_all_excludes_deleted(self):
        pid = self.repo.create(self._make_plan())
        self.repo.delete(pid, soft=True)
        plans = self.repo.get_all()
        self.assertEqual(len(plans), 0)

    def test_update(self):
        plan = self._make_plan()
        pid = self.repo.create(plan)
        plan = self.repo.get_by_id(pid)
        plan.name = "Updated"
        plan.days_completed = 5
        self.assertTrue(self.repo.update(plan))
        updated = self.repo.get_by_id(pid)
        self.assertEqual(updated.name, "Updated")
        self.assertEqual(updated.days_completed, 5)

    def test_update_no_id_raises(self):
        plan = self._make_plan()
        with self.assertRaises(ValueError):
            self.repo.update(plan)

    def test_delete_soft(self):
        pid = self.repo.create(self._make_plan())
        self.assertTrue(self.repo.delete(pid, soft=True))
        # Soft deleted — not returned by get_by_id
        self.assertIsNone(self.repo.get_by_id(pid))

    def test_delete_hard(self):
        pid = self.repo.create(self._make_plan())
        self.assertTrue(self.repo.delete(pid, soft=False))
        self.assertIsNone(self.repo.get_by_id(pid))

    def test_change_status(self):
        pid = self.repo.create(self._make_plan())
        self.assertTrue(self.repo.change_status(pid, 'paused'))
        plan = self.repo.get_by_id(pid)
        self.assertEqual(plan.status, 'paused')

    def test_change_status_completed_sets_end_date(self):
        pid = self.repo.create(self._make_plan())
        self.repo.change_status(pid, 'completed')
        plan = self.repo.get_by_id(pid)
        self.assertEqual(plan.status, 'completed')
        self.assertIsNotNone(plan.actual_end_date)

    def test_change_status_invalid_raises(self):
        pid = self.repo.create(self._make_plan())
        with self.assertRaises(ValueError):
            self.repo.change_status(pid, 'invalid_status')

    def test_update_adherence(self):
        pid = self.repo.create(self._make_plan())
        self.assertTrue(self.repo.update_adherence(pid, Decimal('85.5')))
        plan = self.repo.get_by_id(pid)
        self.assertAlmostEqual(float(plan.adherence_percentage), 85.5, places=1)

    def test_increment_days_completed(self):
        pid = self.repo.create(self._make_plan())
        self.repo.increment_days_completed(pid)
        self.repo.increment_days_completed(pid)
        plan = self.repo.get_by_id(pid)
        self.assertEqual(plan.days_completed, 2)

    def test_update_resources_summary(self):
        pid = self.repo.create(self._make_plan())
        json_str = '{"total_injections": 100}'
        self.assertTrue(self.repo.update_resources_summary(pid, json_str))
        # Verify via raw SQL since model may not expose resources_summary easily
        cur = self.conn.cursor()
        cur.execute("SELECT resources_summary FROM treatment_plans WHERE id = ?", (pid,))
        self.assertEqual(cur.fetchone()[0], json_str)


if __name__ == '__main__':
    unittest.main()
