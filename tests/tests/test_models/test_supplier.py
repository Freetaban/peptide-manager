"""
Unit tests per Supplier model e repository.
"""

import unittest
import sqlite3
import tempfile
import os
from pathlib import Path

# Import dal modulo refactored
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from peptide_manager.models import Supplier, SupplierRepository


class TestSupplierModel(unittest.TestCase):
    """Test per la dataclass Supplier."""
    
    def test_create_supplier_minimal(self):
        """Test creazione supplier con dati minimi."""
        supplier = Supplier(name="Test Supplier")
        
        self.assertEqual(supplier.name, "Test Supplier")
        self.assertIsNone(supplier.id)
        self.assertIsNone(supplier.country)
    
    def test_create_supplier_complete(self):
        """Test creazione supplier con tutti i dati."""
        supplier = Supplier(
            id=1,
            name="Test Supplier",
            country="IT",
            website="https://test.com",
            email="test@test.com",
            notes="Test notes",
            reliability_rating=5
        )
        
        self.assertEqual(supplier.id, 1)
        self.assertEqual(supplier.name, "Test Supplier")
        self.assertEqual(supplier.country, "IT")
        self.assertEqual(supplier.reliability_rating, 5)
    
    def test_rating_validation(self):
        """Test validazione rating (1-5)."""
        # Rating validi
        for rating in [1, 2, 3, 4, 5]:
            supplier = Supplier(name="Test", reliability_rating=rating)
            self.assertEqual(supplier.reliability_rating, rating)
        
        # Rating non validi
        with self.assertRaises(ValueError):
            Supplier(name="Test", reliability_rating=0)
        
        with self.assertRaises(ValueError):
            Supplier(name="Test", reliability_rating=6)


class TestSupplierRepository(unittest.TestCase):
    """Test per SupplierRepository."""
    
    def setUp(self):
        """Setup: crea database temporaneo per ogni test."""
        # Crea file temporaneo
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        # Crea connessione e schema
        self.conn = sqlite3.connect(self.temp_db.name)
        self.conn.row_factory = sqlite3.Row
        self._create_schema()
        
        # Crea repository
        self.repo = SupplierRepository(self.conn)
    
    def tearDown(self):
        """Cleanup: chiude connessione e elimina file temporaneo."""
        self.conn.close()
        os.unlink(self.temp_db.name)
    
    def _create_schema(self):
        """Crea schema suppliers nel database di test."""
        cursor = self.conn.cursor()
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
        
        # Crea anche tabella batches per testare foreign key
        cursor.execute('''
            CREATE TABLE batches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                supplier_id INTEGER NOT NULL,
                product_name TEXT NOT NULL,
                batch_number TEXT,
                vials_count INTEGER NOT NULL,
                mg_per_vial REAL NOT NULL,
                total_price REAL NOT NULL,
                currency TEXT DEFAULT 'EUR',
                purchase_date DATE NOT NULL,
                vials_remaining INTEGER NOT NULL,
                FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
            )
        ''')
        
        self.conn.commit()
    
    def test_create_supplier(self):
        """Test creazione supplier."""
        supplier = Supplier(
            name="Test Supplier",
            country="IT",
            reliability_rating=5
        )
        
        supplier_id = self.repo.create(supplier)
        
        self.assertIsNotNone(supplier_id)
        self.assertGreater(supplier_id, 0)
    
    def test_create_supplier_validation(self):
        """Test validazione durante creazione."""
        # Nome vuoto
        with self.assertRaises(ValueError):
            supplier = Supplier(name="")
            self.repo.create(supplier)
        
        # Rating non valido
        with self.assertRaises(ValueError):
            supplier = Supplier(name="Test", reliability_rating=10)
            self.repo.create(supplier)
    
    def test_get_by_id(self):
        """Test recupero supplier per ID."""
        # Crea supplier
        supplier = Supplier(name="Test Supplier", country="IT")
        supplier_id = self.repo.create(supplier)
        
        # Recupera
        retrieved = self.repo.get_by_id(supplier_id)
        
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.id, supplier_id)
        self.assertEqual(retrieved.name, "Test Supplier")
        self.assertEqual(retrieved.country, "IT")
    
    def test_get_by_id_not_found(self):
        """Test recupero supplier inesistente."""
        retrieved = self.repo.get_by_id(999)
        self.assertIsNone(retrieved)
    
    def test_get_all(self):
        """Test recupero tutti i suppliers."""
        # Crea alcuni suppliers
        suppliers = [
            Supplier(name="Supplier A", country="IT"),
            Supplier(name="Supplier B", country="US"),
            Supplier(name="Supplier C", country="UK"),
        ]
        
        for s in suppliers:
            self.repo.create(s)
        
        # Recupera tutti
        all_suppliers = self.repo.get_all()
        
        self.assertEqual(len(all_suppliers), 3)
        self.assertEqual(all_suppliers[0].name, "Supplier A")  # Ordinati per nome
    
    def test_get_all_with_search(self):
        """Test ricerca suppliers."""
        # Crea suppliers
        self.repo.create(Supplier(name="Italian Supplier", country="IT"))
        self.repo.create(Supplier(name="American Supplier", country="US"))
        self.repo.create(Supplier(name="British Supplier", country="UK"))
        
        # Cerca per nome
        results = self.repo.get_all(search="Italian")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "Italian Supplier")
        
        # Cerca per paese
        results = self.repo.get_all(search="US")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].country, "US")
    
    def test_update_supplier(self):
        """Test aggiornamento supplier."""
        # Crea
        supplier = Supplier(name="Original Name", country="IT")
        supplier_id = self.repo.create(supplier)
        
        # Recupera e modifica
        supplier = self.repo.get_by_id(supplier_id)
        supplier.name = "Updated Name"
        supplier.country = "US"
        supplier.reliability_rating = 4
        
        # Update
        success = self.repo.update(supplier)
        self.assertTrue(success)
        
        # Verifica
        updated = self.repo.get_by_id(supplier_id)
        self.assertEqual(updated.name, "Updated Name")
        self.assertEqual(updated.country, "US")
        self.assertEqual(updated.reliability_rating, 4)
    
    def test_update_validation(self):
        """Test validazione durante update."""
        # Crea supplier
        supplier = Supplier(name="Test")
        supplier_id = self.repo.create(supplier)
        
        # Update senza ID
        supplier_no_id = Supplier(name="Test")
        with self.assertRaises(ValueError):
            self.repo.update(supplier_no_id)
        
        # Update con nome vuoto
        supplier = self.repo.get_by_id(supplier_id)
        supplier.name = ""
        with self.assertRaises(ValueError):
            self.repo.update(supplier)
    
    def test_delete_supplier(self):
        """Test eliminazione supplier."""
        # Crea
        supplier = Supplier(name="To Delete")
        supplier_id = self.repo.create(supplier)
        
        # Elimina
        success, message = self.repo.delete(supplier_id)
        
        self.assertTrue(success)
        self.assertIn("eliminato", message)
        
        # Verifica che non esiste più
        retrieved = self.repo.get_by_id(supplier_id)
        self.assertIsNone(retrieved)
    
    def test_delete_with_batches_fails(self):
        """Test che non puoi eliminare supplier con batches."""
        # Crea supplier
        supplier = Supplier(name="Supplier with Batches")
        supplier_id = self.repo.create(supplier)
        
        # Crea batch associato
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO batches 
            (supplier_id, product_name, vials_count, mg_per_vial, 
             total_price, purchase_date, vials_remaining)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (supplier_id, "Test Product", 5, 10.0, 100.0, "2025-01-01", 5))
        self.conn.commit()
        
        # Prova a eliminare (senza force)
        success, message = self.repo.delete(supplier_id, force=False)
        
        self.assertFalse(success)
        self.assertIn("batch", message.lower())
    
    def test_delete_with_batches_force(self):
        """Test eliminazione forzata supplier con batches."""
        # Crea supplier e batch
        supplier = Supplier(name="Supplier with Batches")
        supplier_id = self.repo.create(supplier)
        
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO batches 
            (supplier_id, product_name, vials_count, mg_per_vial, 
             total_price, purchase_date, vials_remaining)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (supplier_id, "Test Product", 5, 10.0, 100.0, "2025-01-01", 5))
        self.conn.commit()
        
        # Elimina con force=True
        success, message = self.repo.delete(supplier_id, force=True)
        
        self.assertTrue(success)
        
        # Verifica eliminazione
        retrieved = self.repo.get_by_id(supplier_id)
        self.assertIsNone(retrieved)
    
    def test_count(self):
        """Test conteggio suppliers."""
        self.assertEqual(self.repo.count(), 0)
        
        self.repo.create(Supplier(name="Supplier 1"))
        self.assertEqual(self.repo.count(), 1)
        
        self.repo.create(Supplier(name="Supplier 2"))
        self.assertEqual(self.repo.count(), 2)
    
    def test_get_with_batch_count(self):
        """Test recupero suppliers con conteggio batches."""
        # Crea suppliers
        s1_id = self.repo.create(Supplier(name="Supplier 1"))
        s2_id = self.repo.create(Supplier(name="Supplier 2"))
        
        # Aggiungi batches a s1
        cursor = self.conn.cursor()
        for i in range(3):
            cursor.execute('''
                INSERT INTO batches 
                (supplier_id, product_name, vials_count, mg_per_vial, 
                 total_price, purchase_date, vials_remaining)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (s1_id, f"Product {i}", 5, 10.0, 100.0, "2025-01-01", 5))
        self.conn.commit()
        
        # Recupera con conteggio
        results = self.repo.get_with_batch_count()
        
        self.assertEqual(len(results), 2)
        
        # Supplier 1 ha 3 batches
        s1_result = next(r for r in results if r['supplier'].id == s1_id)
        self.assertEqual(s1_result['batch_count'], 3)
        
        # Supplier 2 ha 0 batches
        s2_result = next(r for r in results if r['supplier'].id == s2_id)
        self.assertEqual(s2_result['batch_count'], 0)


if __name__ == '__main__':
    unittest.main()
