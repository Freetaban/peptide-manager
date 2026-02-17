"""
Test per database e schema.
"""

import unittest
import sqlite3
import tempfile
import os
from peptide_manager.database import init_database


class TestDatabase(unittest.TestCase):

    def setUp(self):
        """Setup database di test with unique temp file."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.test_db = self.temp_db.name
        self.conn = init_database(self.test_db)

    def tearDown(self):
        """Cleanup."""
        self.conn.close()
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def test_tables_exist(self):
        """Verifica che tutte le tabelle siano create."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        # Tabelle essenziali del sistema
        expected_tables = [
            'suppliers', 'peptides', 'batches', 'batch_composition',
            'certificates', 'certificate_details', 'preparations',
            'protocols', 'protocol_peptides', 'administrations',
            'cycles'
        ]

        for table in expected_tables:
            self.assertIn(table, tables, f"Tabella '{table}' mancante nel database")

    def test_foreign_keys_enabled(self):
        """Verify PRAGMA foreign_keys = ON."""
        cursor = self.conn.cursor()
        cursor.execute('PRAGMA foreign_keys')
        result = cursor.fetchone()
        self.assertEqual(result[0], 1, "foreign_keys PRAGMA should be ON (1)")

    def test_row_factory_set(self):
        """Verify row_factory is sqlite3.Row for dict-like access."""
        self.assertEqual(self.conn.row_factory, sqlite3.Row)

        # Verify it works in practice: insert and read back
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO suppliers (name) VALUES (?)", ("TestRow",))
        self.conn.commit()

        cursor.execute("SELECT * FROM suppliers WHERE name = ?", ("TestRow",))
        row = cursor.fetchone()
        # sqlite3.Row supports key-based access
        self.assertEqual(row['name'], "TestRow")


if __name__ == '__main__':
    unittest.main()
