"""
View Modules
"""
import sys
from pathlib import Path

# Ensure gui_modular is in path
_views_dir = Path(__file__).parent
_gui_modular_dir = _views_dir.parent
if str(_gui_modular_dir) not in sys.path:
    sys.path.insert(0, str(_gui_modular_dir))

__all__ = [
    'DashboardView',
    'BatchesView',
    'PeptidesView',
    'SuppliersView',
    'PreparationsView',
    'ProtocolsView',
    'CyclesView',
    'AdministrationsView',
    'CalculatorView',
    'TreatmentPlannerView',
    'JanoshikView'
]

try:
    from .dashboard import DashboardView
    from .batches import BatchesView
    from .peptides import PeptidesView
    from .suppliers import SuppliersView
    from .preparations import PreparationsView
    from .protocols import ProtocolsView
    from .cycles import CyclesView
    from .administrations import AdministrationsView
    from .calculator import CalculatorView
    from .treatment_planner import TreatmentPlannerView
    from .janoshik import JanoshikView
except ImportError:
    # Fallback for direct execution
    from views.dashboard import DashboardView
    from views.batches import BatchesView
    from views.peptides import PeptidesView
    from views.suppliers import SuppliersView
    from views.preparations import PreparationsView
    from views.protocols import ProtocolsView
    from views.cycles import CyclesView
    from views.administrations import AdministrationsView
    from views.calculator import CalculatorView
    from views.treatment_planner import TreatmentPlannerView
    from views.janoshik import JanoshikView
