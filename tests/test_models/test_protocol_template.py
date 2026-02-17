"""
Unit tests for ProtocolTemplate model and ProtocolTemplateRepository.
"""

import unittest
import sqlite3
import tempfile
import os
from decimal import Decimal

from peptide_manager.models.protocol_template import (
    ProtocolTemplate,
    ProtocolTemplateRepository,
)


class TestProtocolTemplateModel(unittest.TestCase):
    """Tests for ProtocolTemplate dataclass."""

    def _make_template(self, **kwargs):
        defaults = dict(name="Test Template")
        defaults.update(kwargs)
        return ProtocolTemplate(**defaults)

    def test_create_valid(self):
        t = self._make_template()
        self.assertEqual(t.name, "Test Template")
        self.assertTrue(t.is_active)
        self.assertEqual(t.frequency_per_day, 1)
        self.assertEqual(t.days_off, 0)

    def test_empty_name_raises(self):
        with self.assertRaises(ValueError):
            ProtocolTemplate(name="")

    def test_whitespace_name_raises(self):
        with self.assertRaises(ValueError):
            ProtocolTemplate(name="   ")

    def test_negative_dose_raises(self):
        with self.assertRaises(ValueError):
            self._make_template(dose_ml=Decimal('-1'))

    def test_zero_dose_raises(self):
        with self.assertRaises(ValueError):
            self._make_template(dose_ml=Decimal('0'))

    def test_frequency_less_than_1_raises(self):
        with self.assertRaises(ValueError):
            self._make_template(frequency_per_day=0)

    def test_days_on_less_than_1_raises(self):
        with self.assertRaises(ValueError):
            self._make_template(days_on=0)

    def test_days_off_negative_raises(self):
        with self.assertRaises(ValueError):
            self._make_template(days_off=-1)

    def test_cycle_duration_less_than_1_raises(self):
        with self.assertRaises(ValueError):
            self._make_template(cycle_duration_weeks=0)

    def test_decimal_dose_conversion(self):
        t = self._make_template(dose_ml=0.3)
        self.assertIsInstance(t.dose_ml, Decimal)
        self.assertEqual(t.dose_ml, Decimal('0.3'))

    def test_bool_is_active_conversion(self):
        t = self._make_template(is_active=0)
        self.assertIs(t.is_active, False)
        t2 = self._make_template(is_active=1)
        self.assertIs(t2.is_active, True)

    def test_is_deleted(self):
        t = self._make_template()
        self.assertFalse(t.is_deleted())

    def test_has_cycle_true(self):
        t = self._make_template(days_on=5)
        self.assertTrue(t.has_cycle())

    def test_has_cycle_false(self):
        t = self._make_template()
        self.assertFalse(t.has_cycle())

    def test_calculate_daily_dose_ml_with_dose(self):
        t = self._make_template(dose_ml=Decimal('0.2'), frequency_per_day=2)
        self.assertEqual(t.calculate_daily_dose_ml(), Decimal('0.4'))

    def test_calculate_daily_dose_ml_without_dose(self):
        t = self._make_template()
        self.assertIsNone(t.calculate_daily_dose_ml())

    def test_calculate_cycle_total_dose_with_cycle(self):
        t = self._make_template(dose_ml=Decimal('0.2'), frequency_per_day=2, days_on=5)
        # 0.2 * 2 * 5 = 2.0
        self.assertEqual(t.calculate_cycle_total_dose_ml(), Decimal('2.0'))

    def test_calculate_cycle_total_dose_without_cycle(self):
        t = self._make_template(dose_ml=Decimal('0.2'))
        self.assertIsNone(t.calculate_cycle_total_dose_ml())

    def test_get_tags_list_empty(self):
        t = self._make_template()
        self.assertEqual(t.get_tags_list(), [])

    def test_get_tags_list_single(self):
        t = self._make_template(tags="GH")
        self.assertEqual(t.get_tags_list(), ["GH"])

    def test_get_tags_list_multiple(self):
        t = self._make_template(tags="GH, weight-loss, recomp")
        self.assertEqual(t.get_tags_list(), ["GH", "weight-loss", "recomp"])

    def test_add_tag(self):
        t = self._make_template(tags="GH")
        t.add_tag("recomp")
        self.assertIn("recomp", t.get_tags_list())
        self.assertEqual(len(t.get_tags_list()), 2)

    def test_add_tag_duplicate(self):
        t = self._make_template(tags="GH")
        t.add_tag("GH")
        self.assertEqual(len(t.get_tags_list()), 1)

    def test_remove_tag(self):
        t = self._make_template(tags="GH, recomp")
        t.remove_tag("GH")
        self.assertEqual(t.get_tags_list(), ["recomp"])

    def test_remove_last_tag(self):
        t = self._make_template(tags="GH")
        t.remove_tag("GH")
        self.assertIsNone(t.tags)
        self.assertEqual(t.get_tags_list(), [])


class TestProtocolTemplateRepository(unittest.TestCase):
    """Tests for ProtocolTemplateRepository."""

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.conn = sqlite3.connect(self.temp_db.name)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute('PRAGMA foreign_keys = ON')
        self._create_schema()
        self.repo = ProtocolTemplateRepository(self.conn)

    def tearDown(self):
        self.conn.close()
        os.unlink(self.temp_db.name)

    def _create_schema(self):
        self.conn.executescript('''
            CREATE TABLE protocol_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                dose_ml REAL,
                frequency_per_day INTEGER DEFAULT 1,
                days_on INTEGER,
                days_off INTEGER DEFAULT 0,
                cycle_duration_weeks INTEGER,
                notes TEXT,
                tags TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP
            );
            CREATE TABLE treatment_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                start_date DATE NOT NULL,
                protocol_template_id INTEGER,
                status TEXT DEFAULT 'active',
                total_planned_days INTEGER,
                days_completed INTEGER DEFAULT 0,
                adherence_percentage REAL DEFAULT 100.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP
            );
        ''')

    def _insert_template(self, name="Template", **extras):
        """Insert directly via SQL, bypassing model validation."""
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO protocol_templates (name, is_active, tags) VALUES (?, ?, ?)",
            (name, extras.get('is_active', 1), extras.get('tags', None)),
        )
        self.conn.commit()
        return cur.lastrowid

    def test_get_active_templates(self):
        self._insert_template("Active1")
        self._insert_template("Active2")
        self._insert_template("Inactive", is_active=0)
        results = self.repo.get_active_templates()
        self.assertEqual(len(results), 2)

    def test_search_by_name(self):
        self._insert_template("GH Secretagogue Protocol")
        self._insert_template("Weight Loss Protocol")
        results = self.repo.search_by_name("Weight")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "Weight Loss Protocol")

    def test_search_by_name_no_match(self):
        self._insert_template("GH Protocol")
        results = self.repo.search_by_name("zzzzz")
        self.assertEqual(len(results), 0)

    def test_search_by_tag(self):
        self._insert_template("T1", tags="recomp, cutting")
        self._insert_template("T2", tags="bulking")
        self._insert_template("T3", tags="recomp, anti-aging")
        results = self.repo.search_by_tag("recomp")
        self.assertEqual(len(results), 2)

    def test_deactivate(self):
        tid = self._insert_template("T1")
        self.assertTrue(self.repo.deactivate(tid))
        results = self.repo.get_active_templates()
        self.assertEqual(len(results), 0)

    def test_activate(self):
        tid = self._insert_template("T1", is_active=0)
        self.assertTrue(self.repo.activate(tid))
        results = self.repo.get_active_templates()
        self.assertEqual(len(results), 1)

    def test_deactivate_nonexistent(self):
        self.assertFalse(self.repo.deactivate(999))

    def test_activate_nonexistent(self):
        self.assertFalse(self.repo.activate(999))


if __name__ == '__main__':
    unittest.main()
