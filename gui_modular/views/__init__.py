"""
View Modules
"""

__all__ = [
    'DashboardView',
    'BatchesView',
    'PeptidesView',
    'SuppliersView',
    'PreparationsView',
    'ProtocolsView',
    'AdministrationsView',
    'CalculatorView'
]

from .dashboard import DashboardView
from .batches import BatchesView
from .peptides import PeptidesView
from .suppliers import SuppliersView
from .preparations import PreparationsView
from .protocols import ProtocolsView
from .administrations import AdministrationsView
from .calculator import CalculatorView
