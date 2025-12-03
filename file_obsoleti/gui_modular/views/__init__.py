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
    'CyclesView',
    'AdministrationsView',
    'CalculatorView'
]

from .dashboard import DashboardView
from .batches import BatchesView
from .peptides import PeptidesView
from .suppliers import SuppliersView
from .preparations import PreparationsView
from .protocols import ProtocolsView
from .cycles import CyclesView
from .administrations import AdministrationsView
from .calculator import CalculatorView
