"""
Test basico per Treatment Planner — isolated, in-memory SQLite.

Verifica il lifecycle di un TreatmentPlan via repository:
create → activate → increment days → complete.
"""

import unittest
import sqlite3
import tempfile
import os
from datetime import date
from decimal import Decimal

from peptide_manager.models.treatment_plan import TreatmentPlan, TreatmentPlanRepository


class TestTreatmentPlannerLifecycle(unittest.TestCase):
    """Integration test for TreatmentPlan lifecycle via repository."""

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.conn = sqlite3.connect(self.temp_db.name)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute('PRAGMA foreign_keys = ON')
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
        self.repo = TreatmentPlanRepository(self.conn)

    def tearDown(self):
        self.conn.close()
        os.unlink(self.temp_db.name)

    def test_full_lifecycle(self):
        """Create plan → verify active → increment days → mark completed."""
        # 1. Create plan
        plan = TreatmentPlan(
            name="GH Secretagogue Protocol",
            start_date=date.today(),
            description="Growth hormone secretagogue for body recomposition",
            total_planned_days=84,
            status='planned',
        )
        plan_id = self.repo.create(plan)
        self.assertGreater(plan_id, 0)

        # 2. Activate
        self.assertTrue(self.repo.change_status(plan_id, 'active'))
        active_plan = self.repo.get_by_id(plan_id)
        self.assertEqual(active_plan.status, 'active')
        self.assertTrue(active_plan.is_active())

        # 3. Simulate daily progress
        for _ in range(5):
            self.repo.increment_days_completed(plan_id)
        plan = self.repo.get_by_id(plan_id)
        self.assertEqual(plan.days_completed, 5)

        # 4. Update adherence
        self.repo.update_adherence(plan_id, Decimal('90.0'))
        plan = self.repo.get_by_id(plan_id)
        self.assertAlmostEqual(float(plan.adherence_percentage), 90.0, places=1)

        # 5. Complete
        self.assertTrue(self.repo.change_status(plan_id, 'completed'))
        completed = self.repo.get_by_id(plan_id)
        self.assertEqual(completed.status, 'completed')
        self.assertTrue(completed.is_completed())
        self.assertIsNotNone(completed.actual_end_date)

    def test_pause_and_resume(self):
        """Pause and resume a plan."""
        plan_id = self.repo.create(
            TreatmentPlan(name="Pausable Plan", start_date=date.today())
        )

        self.repo.change_status(plan_id, 'paused')
        self.assertTrue(self.repo.get_by_id(plan_id).is_paused())

        self.repo.change_status(plan_id, 'active')
        self.assertTrue(self.repo.get_by_id(plan_id).is_active())

    def test_soft_delete_hides_plan(self):
        """Soft-deleted plans are excluded from get_all."""
        pid1 = self.repo.create(
            TreatmentPlan(name="Keep", start_date=date.today())
        )
        pid2 = self.repo.create(
            TreatmentPlan(name="Delete", start_date=date.today())
        )

        self.repo.delete(pid2, soft=True)
        all_plans = self.repo.get_all()
        self.assertEqual(len(all_plans), 1)
        self.assertEqual(all_plans[0].name, "Keep")


if __name__ == '__main__':
    unittest.main()
