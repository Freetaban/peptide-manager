#!/usr/bin/env python3
"""
Esempio pratico della nuova architettura modulare.

Questo script dimostra come usare il nuovo sistema rispetto al vecchio.
"""

import sys
from pathlib import Path
import tempfile

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from peptide_manager.database import DatabaseManager
from peptide_manager.models import Supplier
from peptide_manager import PeptideManager


def demo_old_interface():
    """Dimostra vecchia interfaccia (ancora funzionante)."""
    print("=" * 60)
    print("DEMO: Vecchia Interfaccia (Adapter)")
    print("=" * 60)
    
    # Crea database temporaneo
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    # Setup schema
    import sqlite3
    conn = sqlite3.connect(db_path)
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
    
    # Usa vecchia interfaccia
    print("\n📦 Vecchia interfaccia PeptideManager (compatibilità):\n")
    
    manager = PeptideManager(db_path)
    
    # Aggiungi suppliers
    print("1. Aggiungo fornitori...")
    id1 = manager.add_supplier("Peptide Sciences", country="US", rating=5)
    id2 = manager.add_supplier("Swiss Peptides", country="CH", rating=4)
    id3 = manager.add_supplier("Italian Peptides", country="IT", rating=5)
    
    # Recupera tutti
    print("\n2. Recupero tutti i fornitori:")
    suppliers = manager.get_suppliers()
    for s in suppliers:
        print(f"   - {s['name']} ({s['country']}) - Rating: {s['reliability_rating']}/5")
    
    # Cerca
    print("\n3. Cerco fornitori in USA:")
    us_suppliers = manager.get_suppliers(search="US")
    for s in us_suppliers:
        print(f"   - {s['name']}")
    
    # Aggiorna
    print("\n4. Aggiorno rating Swiss Peptides a 5:")
    manager.update_supplier(id2, reliability_rating=5)
    updated = manager.get_suppliers(search="Swiss")[0]
    print(f"   Nuovo rating: {updated['reliability_rating']}/5")
    
    # Elimina
    print("\n5. Elimino Italian Peptides:")
    manager.delete_supplier(id3)
    remaining = manager.get_suppliers()
    print(f"   Fornitori rimasti: {len(remaining)}")
    
    manager.close()
    
    # Cleanup
    import os
    os.unlink(db_path)
    
    print("\n✅ Vecchia interfaccia funziona perfettamente!")


def demo_new_interface():
    """Dimostra nuova interfaccia (raccomandata)."""
    print("\n\n" + "=" * 60)
    print("DEMO: Nuova Interfaccia (Modulare)")
    print("=" * 60)
    
    # Crea database temporaneo
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    # Setup schema
    import sqlite3
    conn = sqlite3.connect(db_path)
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
    
    print("\n📦 Nuova interfaccia modulare:\n")
    
    # Context manager (chiude automaticamente)
    with DatabaseManager(db_path) as db:
        
        # 1. Crea con dataclass (type-safe)
        print("1. Creo fornitori con dataclass:")
        
        supplier1 = Supplier(
            name="Peptide Sciences",
            country="US",
            website="https://peptidesciences.com",
            email="info@peptidesciences.com",
            reliability_rating=5,
            notes="Fornitore principale USA"
        )
        
        supplier2 = Supplier(
            name="Swiss Peptides",
            country="CH",
            website="https://swisspeptides.ch",
            reliability_rating=4
        )
        
        id1 = db.suppliers.create(supplier1)
        id2 = db.suppliers.create(supplier2)
        
        print(f"   ✓ {supplier1.name} (ID: {id1})")
        print(f"   ✓ {supplier2.name} (ID: {id2})")
        
        # 2. Query avanzate
        print("\n2. Query avanzate:")
        
        # Get by ID
        retrieved = db.suppliers.get_by_id(id1)
        print(f"   - Get by ID: {retrieved.name}")
        
        # Count
        total = db.suppliers.count()
        print(f"   - Totale fornitori: {total}")
        
        # Get all
        all_suppliers = db.suppliers.get_all()
        print(f"   - Get all: {[s.name for s in all_suppliers]}")
        
        # Search
        us_suppliers = db.suppliers.get_all(search="Sciences")
        print(f"   - Search 'Sciences': {[s.name for s in us_suppliers]}")
        
        # 3. Update (type-safe)
        print("\n3. Aggiorno fornitore:")
        supplier = db.suppliers.get_by_id(id2)
        print(f"   Prima: {supplier.name} - Rating {supplier.reliability_rating}/5")
        
        supplier.reliability_rating = 5
        supplier.notes = "Aggiornato a rating 5!"
        db.suppliers.update(supplier)
        
        updated = db.suppliers.get_by_id(id2)
        print(f"   Dopo: {updated.name} - Rating {updated.reliability_rating}/5")
        
        # 4. Query con join
        print("\n4. Get con batch count:")
        
        # Aggiungi batch al supplier 1
        cursor = db.conn.cursor()
        cursor.execute('''
            INSERT INTO batches 
            (supplier_id, product_name, vials_count, mg_per_vial, 
             total_price, purchase_date, vials_remaining)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (id1, "BPC-157", 10, 5.0, 100.0, "2025-01-01", 10))
        db.conn.commit()
        
        results = db.suppliers.get_with_batch_count()
        for result in results:
            supplier = result['supplier']
            count = result['batch_count']
            print(f"   - {supplier.name}: {count} batch(es)")
        
        # 5. Validazione automatica
        print("\n5. Validazione automatica:")
        
        try:
            # Prova a creare con nome vuoto
            invalid_supplier = Supplier(name="")
            db.suppliers.create(invalid_supplier)
        except ValueError as e:
            print(f"   ✓ Validazione funziona: {e}")
        
        try:
            # Prova rating invalido
            invalid_supplier = Supplier(name="Test", reliability_rating=10)
        except ValueError as e:
            print(f"   ✓ Validazione funziona: {e}")
        
        # 6. Delete con protezione
        print("\n6. Eliminazione protetta:")
        
        # Prova a eliminare supplier con batches (fallisce)
        success, message = db.suppliers.delete(id1, force=False)
        if not success:
            print(f"   ✓ Protezione funziona: {message.split(':')[0]}")
        
        # Elimina supplier senza batches (successo)
        success, message = db.suppliers.delete(id2, force=False)
        if success:
            print(f"   ✓ {message}")
        
        print("\n7. Statistiche database:")
        stats = db.get_stats()
        for table, count in stats.items():
            if count > 0:
                print(f"   - {table}: {count}")
    
    # Database chiuso automaticamente (context manager)
    
    # Cleanup
    import os
    os.unlink(db_path)
    
    print("\n✅ Nuova interfaccia: più pulita e type-safe!")


def compare_code():
    """Confronta vecchio vs nuovo codice."""
    print("\n\n" + "=" * 60)
    print("CONFRONTO CODICE: Vecchio vs Nuovo")
    print("=" * 60)
    
    print("""
┌─────────────────────────────────────────────────────────┐
│ VECCHIO STILE (models.py - 1904 righe)                │
└─────────────────────────────────────────────────────────┘

class PeptideManager:
    def add_supplier(self, name, country=None, ...):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO suppliers ...
        ''', (name, country, ...))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_suppliers(self, search=None):
        cursor = self.conn.cursor()
        if search:
            cursor.execute('''SELECT * FROM ...''')
        else:
            cursor.execute('''SELECT * FROM ...''')
        return [dict(row) for row in cursor.fetchall()]
    
    # ... altri 50 metodi mescolati ...


┌─────────────────────────────────────────────────────────┐
│ NUOVO STILE (models/supplier.py - 150 righe)          │
└─────────────────────────────────────────────────────────┘

@dataclass
class Supplier(BaseModel):
    name: str = ""
    country: Optional[str] = None
    reliability_rating: Optional[int] = None
    
    def __post_init__(self):
        if self.reliability_rating not in range(1, 6):
            raise ValueError("Rating must be 1-5")

class SupplierRepository(Repository):
    def create(self, supplier: Supplier) -> int:
        self._execute(query, params)
        self._commit()
        return cursor.lastrowid
    
    def get_all(self, search=None) -> List[Supplier]:
        rows = self._fetch_all(query, params)
        return [Supplier.from_row(row) for row in rows]
    
    # Solo 8-10 metodi focalizzati

┌─────────────────────────────────────────────────────────┐
│ VANTAGGI                                                │
└─────────────────────────────────────────────────────────┘

✅ File più piccoli (150 vs 1904 righe)
✅ Type hints (autocomplete IDE)
✅ Validazione automatica
✅ Separazione responsabilità
✅ Testabile (unit tests)
✅ Riusabile (import selettivo)
✅ Manutenibile (chiaro dove modificare)
✅ Scalabile (aggiungi moduli facilmente)
    """)


def main():
    """Run tutte le demo."""
    print("\n🧬 PEPTIDE MANAGEMENT SYSTEM - REFACTORING DEMO")
    print("=" * 60)
    
    # Demo 1: Vecchia interfaccia (ancora funziona)
    demo_old_interface()
    
    # Demo 2: Nuova interfaccia (raccomandata)
    demo_new_interface()
    
    # Confronto codice
    compare_code()
    
    print("\n" + "=" * 60)
    print("🎉 DEMO COMPLETATA!")
    print("=" * 60)
    print("\n📖 Prossimi passi:")
    print("   1. Leggi MIGRATION_GUIDE.md per piano completo")
    print("   2. Run tests: python -m unittest discover tests -v")
    print("   3. Inizia migrazione: git checkout -b refactor/peptides")
    print("\n")


if __name__ == '__main__':
    main()
