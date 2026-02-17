"""
Unit tests for VendorProduct model and VendorProductRepository.
"""

import unittest
import sqlite3
import tempfile
import os
from decimal import Decimal

from peptide_manager.models.vendor_product import VendorProduct, VendorProductRepository


class TestVendorProductModel(unittest.TestCase):
    """Tests for VendorProduct dataclass."""

    def _make_product(self, **kwargs):
        defaults = dict(
            supplier_id=1,
            product_type='syringe',
            product_name='Insulin Syringe 1ml',
            price=Decimal('0.15'),
        )
        defaults.update(kwargs)
        return VendorProduct(**defaults)

    def _make_peptide_product(self, **kwargs):
        defaults = dict(
            supplier_id=1,
            product_type='peptide',
            product_name='BPC-157 5mg',
            price=Decimal('25.00'),
            peptide_id=1,
            mg_per_vial=Decimal('5.0'),
        )
        defaults.update(kwargs)
        return VendorProduct(**defaults)

    def test_create_consumable(self):
        p = self._make_product()
        self.assertEqual(p.product_type, 'syringe')
        self.assertEqual(p.price, Decimal('0.15'))
        self.assertTrue(p.is_available)

    def test_create_peptide(self):
        p = self._make_peptide_product()
        self.assertEqual(p.product_type, 'peptide')
        self.assertEqual(p.peptide_id, 1)

    def test_supplier_id_zero_raises(self):
        with self.assertRaises(ValueError):
            self._make_product(supplier_id=0)

    def test_supplier_id_negative_raises(self):
        with self.assertRaises(ValueError):
            self._make_product(supplier_id=-1)

    def test_invalid_product_type_raises(self):
        with self.assertRaises(ValueError):
            self._make_product(product_type='invalid')

    def test_empty_product_name_raises(self):
        with self.assertRaises(ValueError):
            self._make_product(product_name='')

    def test_negative_price_raises(self):
        with self.assertRaises(ValueError):
            self._make_product(price=Decimal('-1'))

    def test_peptide_without_peptide_id_raises(self):
        with self.assertRaises(ValueError):
            VendorProduct(
                supplier_id=1,
                product_type='peptide',
                product_name='BPC',
                price=Decimal('25'),
            )

    def test_decimal_conversions(self):
        p = self._make_peptide_product(price=25.0, mg_per_vial=5.0)
        self.assertIsInstance(p.price, Decimal)
        self.assertIsInstance(p.mg_per_vial, Decimal)

    def test_auto_calculated_price_per_mg(self):
        p = self._make_peptide_product(price=Decimal('25.00'), mg_per_vial=Decimal('5.0'))
        self.assertEqual(p.price_per_mg, Decimal('5'))

    def test_price_per_mg_not_set_for_consumables(self):
        p = self._make_product()
        # price_per_mg should remain None for non-peptide products
        self.assertIsNone(p.price_per_mg)

    def test_date_conversion(self):
        p = self._make_product(last_price_update='2025-06-01')
        from datetime import date
        self.assertEqual(p.last_price_update, date(2025, 6, 1))

    def test_bool_conversion(self):
        p = self._make_product(is_available=0)
        self.assertIs(p.is_available, False)

    def test_get_unit_price(self):
        p = self._make_product(price=Decimal('15.00'), units_per_pack=100)
        self.assertEqual(p.get_unit_price(), Decimal('0.15'))

    def test_get_price_display_eur(self):
        p = self._make_product(price=Decimal('25.50'), currency='EUR')
        self.assertIn('25.50', p.get_price_display())


class TestVendorProductRepository(unittest.TestCase):
    """Tests for VendorProductRepository."""

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.conn = sqlite3.connect(self.temp_db.name)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute('PRAGMA foreign_keys = ON')
        self._create_schema()
        self.repo = VendorProductRepository(self.conn)

    def tearDown(self):
        self.conn.close()
        os.unlink(self.temp_db.name)

    def _create_schema(self):
        self.conn.executescript('''
            CREATE TABLE suppliers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP
            );
            CREATE TABLE peptides (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP
            );
            CREATE TABLE vendor_products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                supplier_id INTEGER NOT NULL,
                product_type TEXT NOT NULL,
                peptide_id INTEGER,
                product_name TEXT NOT NULL,
                mg_per_vial REAL,
                units_per_pack INTEGER DEFAULT 1,
                price REAL NOT NULL,
                currency TEXT DEFAULT 'EUR',
                price_per_mg REAL,
                is_available INTEGER DEFAULT 1,
                lead_time_days INTEGER,
                minimum_order_qty INTEGER DEFAULT 1,
                sku TEXT,
                url TEXT,
                notes TEXT,
                last_price_update DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (supplier_id) REFERENCES suppliers(id),
                FOREIGN KEY (peptide_id) REFERENCES peptides(id)
            );
        ''')

    def _seed(self):
        """Insert suppliers, peptides, and products for query tests."""
        cur = self.conn.cursor()
        cur.execute("INSERT INTO suppliers (name) VALUES ('Supplier A')")
        sup_a = cur.lastrowid
        cur.execute("INSERT INTO suppliers (name) VALUES ('Supplier B')")
        sup_b = cur.lastrowid
        cur.execute("INSERT INTO peptides (name) VALUES ('BPC-157')")
        pep_id = cur.lastrowid

        # Supplier A: peptide product
        cur.execute("""
            INSERT INTO vendor_products
            (supplier_id, product_type, peptide_id, product_name, mg_per_vial, price, price_per_mg, is_available)
            VALUES (?, 'peptide', ?, 'BPC-157 5mg', 5.0, 25.0, 5.0, 1)
        """, (sup_a, pep_id))

        # Supplier B: cheaper peptide product
        cur.execute("""
            INSERT INTO vendor_products
            (supplier_id, product_type, peptide_id, product_name, mg_per_vial, price, price_per_mg, is_available)
            VALUES (?, 'peptide', ?, 'BPC-157 5mg', 5.0, 20.0, 4.0, 1)
        """, (sup_b, pep_id))

        # Supplier A: syringe product
        cur.execute("""
            INSERT INTO vendor_products
            (supplier_id, product_type, product_name, price, is_available)
            VALUES (?, 'syringe', 'Insulin Syringe 1ml', 0.15, 1)
        """, (sup_a,))

        self.conn.commit()
        return sup_a, sup_b, pep_id

    def test_get_by_supplier(self):
        sup_a, sup_b, pep_id = self._seed()
        products = self.repo.get_by_supplier(sup_a)
        # Supplier A has 2 products: peptide + syringe
        self.assertEqual(len(products), 2)

    def test_get_by_peptide(self):
        sup_a, sup_b, pep_id = self._seed()
        products = self.repo.get_by_peptide(pep_id)
        self.assertEqual(len(products), 2)

    def test_get_by_type(self):
        self._seed()
        syringes = self.repo.get_by_type('syringe')
        self.assertEqual(len(syringes), 1)
        self.assertEqual(syringes[0].product_type, 'syringe')

    def test_get_cheapest_peptide_option(self):
        sup_a, sup_b, pep_id = self._seed()
        result = self.repo.get_cheapest_peptide_option(pep_id, Decimal('10'))
        self.assertIsNotNone(result)
        # Supplier B is cheaper at 20.0/vial vs 25.0/vial
        self.assertEqual(result['supplier_id'], sup_b)
        # 10mg needed / 5mg per vial = 2 vials
        self.assertEqual(result['vials_needed'], 2)

    def test_get_cheapest_peptide_option_no_products(self):
        result = self.repo.get_cheapest_peptide_option(999, Decimal('10'))
        self.assertIsNone(result)

    def test_compare_suppliers_for_peptide(self):
        sup_a, sup_b, pep_id = self._seed()
        comparisons = self.repo.compare_suppliers_for_peptide(pep_id)
        self.assertEqual(len(comparisons), 2)
        # Sorted by price_per_mg ascending — Supplier B (4.0) first
        self.assertEqual(comparisons[0]['supplier_id'], sup_b)
        self.assertEqual(comparisons[1]['supplier_id'], sup_a)


if __name__ == '__main__':
    unittest.main()
