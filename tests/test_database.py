"""
Test per database e schema.
"""

import unittest
import sqlite3
import os
from peptide_manager.database import init_database


class TestDatabase(unittest.TestCase):
    
    def setUp(self):
        """Setup database di test."""
        self.test_db = 'test_peptide.db'
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
            'cycles'  # Aggiunta tabella cycles
        ]
        
        for table in expected_tables:
            self.assertIn(table, tables, f"Tabella '{table}' mancante nel database")


if __name__ == '__main__':
    unittest.main()
