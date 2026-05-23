"""Shipment model — raggruppa uno o più batch in un'unica spedizione."""

from dataclasses import dataclass
from typing import Optional, List
from datetime import date
from decimal import Decimal
from .base import BaseModel, Repository


@dataclass
class Shipment(BaseModel):
    """Una spedizione da un fornitore con il costo di spedizione associato."""
    supplier_id: int = None
    shipping_cost: Optional[Decimal] = None
    currency: str = 'USD'
    shipping_date: Optional[date] = None
    notes: Optional[str] = None

    def __post_init__(self):
        if self.supplier_id is None:
            raise ValueError("Fornitore obbligatorio")
        if isinstance(self.shipping_date, str) and self.shipping_date:
            self.shipping_date = date.fromisoformat(self.shipping_date)
        if isinstance(self.shipping_cost, (int, float, str)) and self.shipping_cost is not None:
            self.shipping_cost = Decimal(str(self.shipping_cost))


class ShipmentRepository(Repository):
    """CRUD per spedizioni."""

    def get_all(self, supplier_id: Optional[int] = None) -> List[dict]:
        query = """
            SELECT s.id, s.supplier_id, s.shipping_cost, s.currency,
                   s.shipping_date, s.notes, s.created_at,
                   sup.name AS supplier_name,
                   COUNT(b.id) AS batch_count
            FROM shipments s
            JOIN suppliers sup ON s.supplier_id = sup.id
            LEFT JOIN batches b ON b.shipment_id = s.id AND b.deleted_at IS NULL
        """
        params = []
        if supplier_id:
            query += " WHERE s.supplier_id = ?"
            params.append(supplier_id)
        query += " GROUP BY s.id ORDER BY s.shipping_date DESC, s.id DESC"
        rows = self._fetch_all(query, tuple(params))
        return [dict(r) for r in rows]

    def get_by_id(self, shipment_id: int) -> Optional[Shipment]:
        row = self._fetch_one("SELECT * FROM shipments WHERE id = ?", (shipment_id,))
        return Shipment.from_row(row) if row else None

    def get_batches(self, shipment_id: int) -> List[dict]:
        rows = self._fetch_all(
            "SELECT b.id, b.product_name, b.batch_number, b.vials_count, b.vials_remaining "
            "FROM batches b WHERE b.shipment_id = ? AND b.deleted_at IS NULL ORDER BY b.id",
            (shipment_id,)
        )
        return [dict(r) for r in rows]

    def create(self, shipment: Shipment) -> int:
        cursor = self._execute(
            "INSERT INTO shipments (supplier_id, shipping_cost, currency, shipping_date, notes) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                shipment.supplier_id,
                float(shipment.shipping_cost) if shipment.shipping_cost is not None else None,
                shipment.currency or 'USD',
                shipment.shipping_date,
                shipment.notes,
            )
        )
        self._commit()
        return cursor.lastrowid

    def update(self, shipment: Shipment) -> bool:
        if shipment.id is None:
            raise ValueError("ID spedizione necessario per update")
        self._execute(
            "UPDATE shipments SET supplier_id=?, shipping_cost=?, currency=?, "
            "shipping_date=?, notes=? WHERE id=?",
            (
                shipment.supplier_id,
                float(shipment.shipping_cost) if shipment.shipping_cost is not None else None,
                shipment.currency or 'USD',
                shipment.shipping_date,
                shipment.notes,
                shipment.id,
            )
        )
        self._commit()
        return True

    def delete(self, shipment_id: int) -> tuple:
        row = self._fetch_one(
            "SELECT COUNT(*) FROM batches WHERE shipment_id = ? AND deleted_at IS NULL",
            (shipment_id,)
        )
        count = row[0] if row else 0
        if count > 0:
            return False, f"La spedizione ha {count} lott(o/i) collegat(o/i). Scollega prima i lotti."
        self._execute("DELETE FROM shipments WHERE id = ?", (shipment_id,))
        self._commit()
        return True, "Spedizione eliminata"
