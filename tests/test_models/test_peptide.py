"""
Unit tests per Peptide model e repository.
"""

import unittest
import sqlite3
import tempfile
import os
from pathlib import Path

# Import dal modulo refactored
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from peptide_manager.models import Peptide, PeptideRepository


class TestPeptideModel(unittest.TestCase):
    """Test per la dataclass Peptide."""
    
    def test_create_peptide_minimal(self):
        """Test creazione peptide con dati minimi."""
        peptide = Peptide(name="BPC-157")
        
        self.assertEqual(peptide.name, "BPC-157")
        self.assertIsNone(peptide.id)
        self.assertIsNone(peptide.description)
    
    def test_create_peptide_complete(self):
        """Test creazione peptide con tutti i dati."""
        peptide = Peptide(
            id=1,
            name="BPC-157",
            description="Body Protection Compound",
            common_uses="Healing, Recovery",
            notes="Very effective"
        )
        
        self.assertEqual(peptide.id, 1)
        self.assertEqual(peptide.name, "BPC-157")
        self.assertEqual(peptide.description, "Body Protection Compound")
        self.assertEqual(peptide.common_uses, "Healing, Recovery")
    
    def test_empty_name_validation(self):
        """Test validazione nome vuoto."""
        with self.assertRaises(ValueError):
            Peptide(name="")
        
        with self.assertRaises(ValueError):
            Peptide(name="   ")  # Solo spazi


class TestPeptideRepository(unittest.TestCase):
    """Test per PeptideRepository."""
    
    def setUp(self):
        """Setup: crea database temporaneo per ogni test."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        # Crea connessione e schema
        self.conn = sqlite3.connect(self.temp_db.name)
        self.conn.row_factory = sqlite3.Row
        self._create_schema()
        
        # Crea repository
        self.repo = PeptideRepository(self.conn)
    
    def tearDown(self):
        """Cleanup: chiude connessione e elimina file temporaneo."""
        self.conn.close()
        os.unlink(self.temp_db.name)
    
    def _create_schema(self):
        """Crea schema peptides nel database di test."""
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE peptides (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                common_uses TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Crea tabelle correlate per testare foreign keys
        cursor.execute('''
            CREATE TABLE batch_composition (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id INTEGER NOT NULL,
                peptide_id INTEGER NOT NULL,
                mg_per_vial REAL NOT NULL,
                FOREIGN KEY (peptide_id) REFERENCES peptides(id) ON DELETE CASCADE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE protocol_peptides (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                protocol_id INTEGER NOT NULL,
                peptide_id INTEGER NOT NULL,
                target_dose_mcg REAL NOT NULL,
                FOREIGN KEY (peptide_id) REFERENCES peptides(id) ON DELETE CASCADE
            )
        ''')
        
        self.conn.commit()
    
    def test_create_peptide(self):
        """Test creazione peptide."""
        peptide = Peptide(
            name="BPC-157",
            description="Body Protection Compound",
            common_uses="Healing"
        )
        
        peptide_id = self.repo.create(peptide)
        
        self.assertIsNotNone(peptide_id)
        self.assertGreater(peptide_id, 0)
    
    def test_create_peptide_validation(self):
        """Test validazione durante creazione."""
        # Nome vuoto
        with self.assertRaises(ValueError):
            peptide = Peptide(name="")
            self.repo.create(peptide)
        
        # Nome duplicato
        peptide1 = Peptide(name="BPC-157")
        self.repo.create(peptide1)
        
        peptide2 = Peptide(name="BPC-157")
        with self.assertRaises(ValueError):
            self.repo.create(peptide2)
    
    def test_get_by_id(self):
        """Test recupero peptide per ID."""
        # Crea peptide
        peptide = Peptide(name="BPC-157", description="Test peptide")
        peptide_id = self.repo.create(peptide)
        
        # Recupera
        retrieved = self.repo.get_by_id(peptide_id)
        
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.id, peptide_id)
        self.assertEqual(retrieved.name, "BPC-157")
        self.assertEqual(retrieved.description, "Test peptide")
    
    def test_get_by_id_not_found(self):
        """Test recupero peptide inesistente."""
        retrieved = self.repo.get_by_id(999)
        self.assertIsNone(retrieved)
    
    def test_get_by_name(self):
        """Test recupero peptide per nome."""
        # Crea peptide
        peptide = Peptide(name="BPC-157")
        self.repo.create(peptide)
        
        # Recupera per nome
        retrieved = self.repo.get_by_name("BPC-157")
        
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, "BPC-157")
    
    def test_get_by_name_not_found(self):
        """Test recupero peptide inesistente per nome."""
        retrieved = self.repo.get_by_name("NonExistent")
        self.assertIsNone(retrieved)
    
    def test_get_all(self):
        """Test recupero tutti i peptidi."""
        # Crea alcuni peptidi
        peptides = [
            Peptide(name="BPC-157", description="Healing"),
            Peptide(name="TB-500", description="Recovery"),
            Peptide(name="CJC-1295", description="Growth"),
        ]
        
        for p in peptides:
            self.repo.create(p)
        
        # Recupera tutti
        all_peptides = self.repo.get_all()
        
        self.assertEqual(len(all_peptides), 3)
        self.assertEqual(all_peptides[0].name, "BPC-157")  # Ordinati per nome
    
    def test_get_all_with_search(self):
        """Test ricerca peptidi."""
        # Crea peptidi
        self.repo.create(Peptide(name="BPC-157", description="Healing peptide"))
        self.repo.create(Peptide(name="TB-500", description="Recovery peptide"))
        self.repo.create(Peptide(name="CJC-1295", description="Growth hormone"))
        
        # Cerca per nome
        results = self.repo.get_all(search="BPC")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "BPC-157")
        
        # Cerca per descrizione
        results = self.repo.get_all(search="peptide")
        self.assertEqual(len(results), 2)  # BPC-157 e TB-500
    
    def test_update_peptide(self):
        """Test aggiornamento peptide."""
        # Crea
        peptide = Peptide(name="BPC-157", description="Original")
        peptide_id = self.repo.create(peptide)
        
        # Recupera e modifica
        peptide = self.repo.get_by_id(peptide_id)
        peptide.description = "Updated description"
        peptide.common_uses = "Healing, Recovery"
        
        # Update
        success = self.repo.update(peptide)
        self.assertTrue(success)
        
        # Verifica
        updated = self.repo.get_by_id(peptide_id)
        self.assertEqual(updated.description, "Updated description")
        self.assertEqual(updated.common_uses, "Healing, Recovery")
    
    def test_update_validation(self):
        """Test validazione durante update."""
        # Crea peptide
        peptide = Peptide(name="BPC-157")
        peptide_id = self.repo.create(peptide)
        
        # Update senza ID
        peptide_no_id = Peptide(name="BPC-157")
        with self.assertRaises(ValueError):
            self.repo.update(peptide_no_id)
        
        # Update con nome vuoto
        peptide = self.repo.get_by_id(peptide_id)
        peptide.name = ""
        with self.assertRaises(ValueError):
            self.repo.update(peptide)
        
        # Update con nome duplicato
        self.repo.create(Peptide(name="TB-500"))
        peptide = self.repo.get_by_id(peptide_id)
        peptide.name = "TB-500"
        with self.assertRaises(ValueError):
            self.repo.update(peptide)
    
    def test_delete_peptide(self):
        """Test eliminazione peptide."""
        # Crea
        peptide = Peptide(name="BPC-157")
        peptide_id = self.repo.create(peptide)
        
        # Elimina
        success, message = self.repo.delete(peptide_id)
        
        self.assertTrue(success)
        self.assertIn("eliminato", message)
        
        # Verifica che non esiste più
        retrieved = self.repo.get_by_id(peptide_id)
        self.assertIsNone(retrieved)
    
    def test_delete_with_batch_refs_fails(self):
        """Test che non puoi eliminare peptide con riferimenti batch."""
        # Crea peptide
        peptide = Peptide(name="BPC-157")
        peptide_id = self.repo.create(peptide)
        
        # Aggiungi riferimento in batch_composition
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO batch_composition (batch_id, peptide_id, mg_per_vial)
            VALUES (?, ?, ?)
        ''', (1, peptide_id, 5.0))
        self.conn.commit()
        
        # Prova a eliminare (senza force)
        success, message = self.repo.delete(peptide_id, force=False)
        
        self.assertFalse(success)
        self.assertIn("batch", message.lower())
    
    def test_delete_with_protocol_refs_fails(self):
        """Test che non puoi eliminare peptide con riferimenti protocollo."""
        # Crea peptide
        peptide = Peptide(name="BPC-157")
        peptide_id = self.repo.create(peptide)
        
        # Aggiungi riferimento in protocol_peptides
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO protocol_peptides (protocol_id, peptide_id, target_dose_mcg)
            VALUES (?, ?, ?)
        ''', (1, peptide_id, 250.0))
        self.conn.commit()
        
        # Prova a eliminare (senza force)
        success, message = self.repo.delete(peptide_id, force=False)
        
        self.assertFalse(success)
        self.assertIn("protocollo", message.lower())
    
    def test_delete_with_refs_force(self):
        """Test eliminazione forzata peptide con riferimenti."""
        # Crea peptide
        peptide = Peptide(name="BPC-157")
        peptide_id = self.repo.create(peptide)
        
        # Aggiungi riferimenti
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO batch_composition (batch_id, peptide_id, mg_per_vial)
            VALUES (?, ?, ?)
        ''', (1, peptide_id, 5.0))
        cursor.execute('''
            INSERT INTO protocol_peptides (protocol_id, peptide_id, target_dose_mcg)
            VALUES (?, ?, ?)
        ''', (1, peptide_id, 250.0))
        self.conn.commit()
        
        # Elimina con force=True
        success, message = self.repo.delete(peptide_id, force=True)
        
        self.assertTrue(success)
        
        # Verifica eliminazione
        retrieved = self.repo.get_by_id(peptide_id)
        self.assertIsNone(retrieved)
    
    def test_count(self):
        """Test conteggio peptidi."""
        self.assertEqual(self.repo.count(), 0)
        
        self.repo.create(Peptide(name="BPC-157"))
        self.assertEqual(self.repo.count(), 1)
        
        self.repo.create(Peptide(name="TB-500"))
        self.assertEqual(self.repo.count(), 2)
    
    def test_get_with_usage_count(self):
        """Test recupero peptidi con conteggio utilizzi."""
        # Crea peptidi
        p1_id = self.repo.create(Peptide(name="BPC-157"))
        p2_id = self.repo.create(Peptide(name="TB-500"))
        
        # Aggiungi utilizzi a BPC-157
        cursor = self.conn.cursor()
        
        # 2 batch
        cursor.execute('''
            INSERT INTO batch_composition (batch_id, peptide_id, mg_per_vial)
            VALUES (?, ?, ?)
        ''', (1, p1_id, 5.0))
        cursor.execute('''
            INSERT INTO batch_composition (batch_id, peptide_id, mg_per_vial)
            VALUES (?, ?, ?)
        ''', (2, p1_id, 5.0))
        
        # 1 protocollo
        cursor.execute('''
            INSERT INTO protocol_peptides (protocol_id, peptide_id, target_dose_mcg)
            VALUES (?, ?, ?)
        ''', (1, p1_id, 250.0))
        
        self.conn.commit()
        
        # Recupera con conteggio
        results = self.repo.get_with_usage_count()
        
        self.assertEqual(len(results), 2)
        
        # BPC-157 ha 2 batch + 1 protocollo = 3 total
        p1_result = next(r for r in results if r['peptide'].id == p1_id)
        self.assertEqual(p1_result['batch_count'], 2)
        self.assertEqual(p1_result['protocol_count'], 1)
        self.assertEqual(p1_result['total_usage'], 3)
        
        # TB-500 ha 0 utilizzi
        p2_result = next(r for r in results if r['peptide'].id == p2_id)
        self.assertEqual(p2_result['total_usage'], 0)
    
    def test_get_most_used(self):
        """Test recupero peptidi più usati."""
        # Crea peptidi
        p1_id = self.repo.create(Peptide(name="BPC-157"))
        p2_id = self.repo.create(Peptide(name="TB-500"))
        p3_id = self.repo.create(Peptide(name="CJC-1295"))
        
        # Aggiungi utilizzi
        cursor = self.conn.cursor()
        
        # BPC-157: 3 utilizzi
        for i in range(3):
            cursor.execute('''
                INSERT INTO batch_composition (batch_id, peptide_id, mg_per_vial)
                VALUES (?, ?, ?)
            ''', (i+1, p1_id, 5.0))
        
        # TB-500: 1 utilizzo
        cursor.execute('''
            INSERT INTO batch_composition (batch_id, peptide_id, mg_per_vial)
            VALUES (?, ?, ?)
        ''', (10, p2_id, 5.0))
        
        # CJC-1295: 0 utilizzi
        
        self.conn.commit()
        
        # Get most used (top 2)
        most_used = self.repo.get_most_used(limit=2)
        
        self.assertEqual(len(most_used), 2)
        self.assertEqual(most_used[0]['peptide'].name, "BPC-157")  # Più usato
        self.assertEqual(most_used[0]['total_usage'], 3)
        self.assertEqual(most_used[1]['peptide'].name, "TB-500")
        self.assertEqual(most_used[1]['total_usage'], 1)
    
    def test_search_by_use(self):
        """Test ricerca per uso comune."""
        # Crea peptidi
        self.repo.create(Peptide(
            name="BPC-157",
            common_uses="Healing, Gut health"
        ))
        self.repo.create(Peptide(
            name="TB-500",
            common_uses="Recovery, Inflammation"
        ))
        self.repo.create(Peptide(
            name="CJC-1295",
            common_uses="Growth, Anti-aging"
        ))
        
        # Cerca per "Healing"
        results = self.repo.search_by_use("Healing")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "BPC-157")
        
        # Cerca per "Growth"
        results = self.repo.search_by_use("Growth")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "CJC-1295")


if __name__ == '__main__':
    unittest.main()
