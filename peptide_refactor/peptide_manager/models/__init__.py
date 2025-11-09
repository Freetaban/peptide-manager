"""
Models package - espone tutte le classi modello e repository.
"""

from .base import BaseModel, Repository
from .supplier import Supplier, SupplierRepository

__all__ = [
    'BaseModel',
    'Repository',
    'Supplier',
    'SupplierRepository',
]
