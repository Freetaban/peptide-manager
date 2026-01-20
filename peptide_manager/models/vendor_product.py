"""
VendorProduct model - gestisce il catalogo prodotti e prezzi dei fornitori.

Permette di tracciare i prezzi di peptidi e consumabili per ogni fornitore,
abilitando stime di costo accurate nei treatment plans.
"""

from dataclasses import dataclass, field
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal

from .base import BaseModel, Repository


@dataclass
class VendorProduct(BaseModel):
    """Rappresenta un prodotto nel catalogo di un fornitore con prezzo."""
    
    # Campi obbligatori
    supplier_id: int = 0
    product_type: str = ""  # 'peptide', 'syringe', 'needle', 'bac_water', 'alcohol_swab', 'sharps_container'
    product_name: str = ""
    price: Decimal = Decimal('0')
    
    # Campi opzionali
    peptide_id: Optional[int] = None
    mg_per_vial: Optional[Decimal] = None
    units_per_pack: int = 1
    currency: str = 'EUR'
    price_per_mg: Optional[Decimal] = None
    is_available: bool = True
    lead_time_days: Optional[int] = None
    minimum_order_qty: int = 1
    sku: Optional[str] = None
    url: Optional[str] = None
    notes: Optional[str] = None
    last_price_update: Optional[date] = None
    updated_at: Optional[datetime] = None
    
    # Per join con supplier
    supplier_name: Optional[str] = None
    peptide_name: Optional[str] = None
    
    def __post_init__(self):
        """Validazione e conversioni."""
        # Conversione Decimal
        if isinstance(self.price, (int, float, str)):
            self.price = Decimal(str(self.price))
        if self.mg_per_vial and isinstance(self.mg_per_vial, (int, float, str)):
            self.mg_per_vial = Decimal(str(self.mg_per_vial))
        if self.price_per_mg and isinstance(self.price_per_mg, (int, float, str)):
            self.price_per_mg = Decimal(str(self.price_per_mg))
        
        # Conversione date
        if self.last_price_update and isinstance(self.last_price_update, str):
            self.last_price_update = date.fromisoformat(self.last_price_update)
        if self.updated_at and isinstance(self.updated_at, str):
            self.updated_at = datetime.fromisoformat(self.updated_at)
        
        # Conversione bool
        if isinstance(self.is_available, int):
            self.is_available = bool(self.is_available)
        
        # Calcola price_per_mg se peptide
        if self.product_type == 'peptide' and self.mg_per_vial and self.mg_per_vial > 0:
            self.price_per_mg = self.price / self.mg_per_vial
        
        # Validazioni
        if self.supplier_id <= 0:
            raise ValueError("supplier_id deve essere > 0")
        
        valid_types = ['peptide', 'syringe', 'needle', 'bac_water', 'alcohol_swab', 'sharps_container']
        if self.product_type not in valid_types:
            raise ValueError(f"product_type deve essere uno di: {', '.join(valid_types)}")
        
        if not self.product_name or not self.product_name.strip():
            raise ValueError("product_name obbligatorio")
        
        if self.price < 0:
            raise ValueError("price deve essere >= 0")
        
        if self.product_type == 'peptide' and not self.peptide_id:
            raise ValueError("peptide_id obbligatorio per prodotti tipo 'peptide'")
    
    def get_price_display(self) -> str:
        """Formatta prezzo per display."""
        symbol = '€' if self.currency == 'EUR' else self.currency
        return f"{symbol}{self.price:.2f}"
    
    def get_unit_price(self) -> Decimal:
        """Calcola prezzo per unità singola (considerando units_per_pack)."""
        if self.units_per_pack and self.units_per_pack > 0:
            return self.price / Decimal(str(self.units_per_pack))
        return self.price


@dataclass 
class ConsumableDefault(BaseModel):
    """Rappresenta prezzi default per consumabili senza vendor specifico."""
    
    consumable_type: str = ""
    display_name: str = ""
    default_price: Decimal = Decimal('0')
    currency: str = 'EUR'
    units_per_pack: int = 1
    notes: Optional[str] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        if isinstance(self.default_price, (int, float, str)):
            self.default_price = Decimal(str(self.default_price))
        if self.updated_at and isinstance(self.updated_at, str):
            self.updated_at = datetime.fromisoformat(self.updated_at)


class VendorProductRepository(Repository):
    """Repository per operazioni CRUD sui prodotti vendor."""
    
    def __init__(self, db):
        super().__init__(db, 'vendor_products', VendorProduct)
    
    def get_by_supplier(self, supplier_id: int) -> List[VendorProduct]:
        """
        Recupera tutti i prodotti di un fornitore.
        
        Args:
            supplier_id: ID del fornitore
            
        Returns:
            Lista di prodotti
        """
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT vp.*, s.name as supplier_name, p.name as peptide_name
            FROM vendor_products vp
            LEFT JOIN suppliers s ON vp.supplier_id = s.id
            LEFT JOIN peptides p ON vp.peptide_id = p.id
            WHERE vp.supplier_id = ?
            ORDER BY vp.product_type, vp.product_name
        """, (supplier_id,))
        
        return [self._row_to_entity(dict(row)) for row in cursor.fetchall()]
    
    def get_by_peptide(self, peptide_id: int, available_only: bool = True) -> List[VendorProduct]:
        """
        Recupera tutti i prodotti per un peptide specifico.
        
        Args:
            peptide_id: ID del peptide
            available_only: Se True, solo prodotti disponibili
            
        Returns:
            Lista di prodotti ordinati per prezzo per mg
        """
        cursor = self.db.conn.cursor()
        
        query = """
            SELECT vp.*, s.name as supplier_name, p.name as peptide_name
            FROM vendor_products vp
            LEFT JOIN suppliers s ON vp.supplier_id = s.id
            LEFT JOIN peptides p ON vp.peptide_id = p.id
            WHERE vp.peptide_id = ?
        """
        params = [peptide_id]
        
        if available_only:
            query += " AND vp.is_available = 1"
        
        query += " ORDER BY vp.price_per_mg ASC NULLS LAST"
        
        cursor.execute(query, params)
        return [self._row_to_entity(dict(row)) for row in cursor.fetchall()]
    
    def get_by_type(self, product_type: str, available_only: bool = True) -> List[VendorProduct]:
        """
        Recupera prodotti per tipo (consumabili).
        
        Args:
            product_type: Tipo prodotto ('syringe', 'needle', etc.)
            available_only: Se True, solo disponibili
            
        Returns:
            Lista prodotti
        """
        cursor = self.db.conn.cursor()
        
        query = """
            SELECT vp.*, s.name as supplier_name
            FROM vendor_products vp
            LEFT JOIN suppliers s ON vp.supplier_id = s.id
            WHERE vp.product_type = ?
        """
        params = [product_type]
        
        if available_only:
            query += " AND vp.is_available = 1"
        
        query += " ORDER BY vp.price ASC"
        
        cursor.execute(query, params)
        return [self._row_to_entity(dict(row)) for row in cursor.fetchall()]
    
    def get_cheapest_peptide_option(self, peptide_id: int, mg_needed: Decimal) -> Optional[dict]:
        """
        Trova l'opzione più economica per acquisire una quantità di peptide.
        
        Args:
            peptide_id: ID peptide
            mg_needed: Quantità necessaria in mg
            
        Returns:
            Dict con supplier, product, vials_needed, total_cost o None
        """
        products = self.get_by_peptide(peptide_id, available_only=True)
        
        if not products:
            return None
        
        best_option = None
        best_cost = None
        
        for product in products:
            if not product.mg_per_vial or product.mg_per_vial <= 0:
                continue
            
            # Calcola vials necessari (arrotonda per eccesso)
            vials_needed = int((mg_needed / product.mg_per_vial) + Decimal('0.999999'))
            vials_needed = max(vials_needed, product.minimum_order_qty)
            
            total_cost = product.price * vials_needed
            
            if best_cost is None or total_cost < best_cost:
                best_cost = total_cost
                best_option = {
                    'supplier_id': product.supplier_id,
                    'supplier_name': product.supplier_name,
                    'product': product,
                    'vials_needed': vials_needed,
                    'total_cost': total_cost,
                    'mg_acquired': product.mg_per_vial * vials_needed
                }
        
        return best_option
    
    def compare_suppliers_for_peptide(self, peptide_id: int) -> List[dict]:
        """
        Confronta prezzi di tutti i fornitori per un peptide.
        
        Args:
            peptide_id: ID peptide
            
        Returns:
            Lista di confronti ordinata per prezzo/mg
        """
        products = self.get_by_peptide(peptide_id, available_only=True)
        
        comparisons = []
        for product in products:
            comparisons.append({
                'supplier_id': product.supplier_id,
                'supplier_name': product.supplier_name,
                'product_name': product.product_name,
                'mg_per_vial': product.mg_per_vial,
                'price': product.price,
                'price_per_mg': product.price_per_mg,
                'currency': product.currency,
                'lead_time_days': product.lead_time_days,
                'url': product.url
            })
        
        return sorted(comparisons, key=lambda x: x['price_per_mg'] or Decimal('999999'))


class ConsumableDefaultRepository(Repository):
    """Repository per prezzi default consumabili."""
    
    def __init__(self, db):
        super().__init__(db, 'consumable_defaults', ConsumableDefault)
    
    def get_by_type(self, consumable_type: str) -> Optional[ConsumableDefault]:
        """Recupera default per tipo."""
        cursor = self.db.conn.cursor()
        cursor.execute(
            "SELECT * FROM consumable_defaults WHERE consumable_type = ?",
            (consumable_type,)
        )
        row = cursor.fetchone()
        return self._row_to_entity(dict(row)) if row else None
    
    def get_all_defaults(self) -> List[ConsumableDefault]:
        """Recupera tutti i defaults."""
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT * FROM consumable_defaults ORDER BY consumable_type")
        return [self._row_to_entity(dict(row)) for row in cursor.fetchall()]
