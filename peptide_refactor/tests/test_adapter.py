"""
Test di integrazione per l'adapter PeptideManager.

Verifica che la vecchia interfaccia continui a funzionare
usando la nuova architettura sotto.
"""

import unittest
import sqlite3
import tempfile
import os
from pathlib import Path

# Import dal modulo refactored
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from peptide_manager import PeptideManager


class TestPeptideManagerAdapter(unittest.TestCase):
    """Test per verificare che l'adapter mantiene retrocompatibilità."""
    
    def setUp(self):
        """Setup: crea database temporaneo."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        # Crea schema
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE suppliers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                country TEXT,
                website TEXT,
                email TEXT,
                notes TEXT,
                reliability_rating INTEGER CHECK(reliability_rating >= 1 AND reliability_rating <= 5),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE batches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                supplier_id INTEGER NOT NULL,
                product_name TEXT NOT NULL,
                vials_count INTEGER NOT NULL,
                mg_per_vial REAL NOT NULL,
                total_price REAL NOT NULL,
                purchase_date DATE NOT NULL,
                vials_remaining INTEGER NOT NULL,
                FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
            )
        ''')
        conn.commit()
        conn.close()
        
        # Crea manager
        self.manager = PeptideManager(self.temp_db.name)
    
    def tearDown(self):
        """Cleanup."""
        self.manager.close()
        os.unlink(self.temp_db.name)
    
    def test_add_supplier_old_interface(self):
        """Test che vecchia interfaccia add_supplier funziona."""
        # Usa vecchia interfaccia (positional + keyword args)
        supplier_id = self.manager.add_supplier(
            "Test Supplier",
            country="IT",
            rating=5
        )
        
        self.assertIsNotNone(supplier_id)
        self.assertGreater(supplier_id, 0)
    
    def test_get_suppliers_returns_dict(self):
        """Test che get_suppliers restituisce dict (non Supplier objects)."""
        # Aggiungi alcuni suppliers
        self.manager.add_supplier("Supplier A", country="IT")
        self.manager.add_supplier("Supplier B", country="US")
        
        # Recupera
        suppliers = self.manager.get_suppliers()
        
        # Verifica che sono dict (vecchia interfaccia)
        self.assertIsInstance(suppliers, list)
        self.assertEqual(len(suppliers), 2)
        self.assertIsInstance(suppliers[0], dict)
        self.assertIn('name', suppliers[0])
        self.assertIn('country', suppliers[0])
    
    def test_get_suppliers_with_search(self):
        """Test ricerca suppliers (vecchia interfaccia)."""
        self.manager.add_supplier("Italian Supplier", country="IT")
        self.manager.add_supplier("American Supplier", country="US")
        
        # Cerca
        results = self.manager.get_suppliers(search="Italian")
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['name'], "Italian Supplier")
    
    def test_update_supplier_old_interface(self):
        """Test update con vecchia interfaccia (**kwargs)."""
        # Crea
        supplier_id = self.manager.add_supplier("Original Name")
        
        # Update con kwargs (vecchia interfaccia)
        success = self.manager.update_supplier(
            supplier_id,
            name="Updated Name",
            rating=4
        )
        
        self.assertTrue(success)
        
        # Verifica
        suppliers = self.manager.get_suppliers()
        updated = next(s for s in suppliers if s['id'] == supplier_id)
        self.assertEqual(updated['name'], "Updated Name")
        self.assertEqual(updated['reliability_rating'], 4)
    
    def test_delete_supplier(self):
        """Test eliminazione (vecchia interfaccia)."""
        # Crea
        supplier_id = self.manager.add_supplier("To Delete")
        
        # Elimina
        success = self.manager.delete_supplier(supplier_id)
        
        self.assertTrue(success)
        
        # Verifica
        suppliers = self.manager.get_suppliers()
        self.assertEqual(len(suppliers), 0)
    
    def test_conn_attribute_exists(self):
        """Test che attributo conn esiste (retrocompatibilità)."""
        # Vecchio codice potrebbe accedere direttamente a self.manager.conn
        self.assertIsNotNone(self.manager.conn)
        self.assertIsInstance(self.manager.conn, sqlite3.Connection)


if __name__ == '__main__':
    unittest.main()
