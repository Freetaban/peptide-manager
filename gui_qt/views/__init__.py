"""View modules for the PySide6 GUI."""

from .base import BaseView
from .today import TodayView
from .inventory import BatchesTab, PreparationsTab, ShipmentsTab
from .treatment import ProtocolsTab, CyclesTab, PlansTab, TemplatesTab

__all__ = [
    "BaseView",
    "TodayView",
    "BatchesTab",
    "PreparationsTab",
    "ShipmentsTab",
    "ProtocolsTab",
    "CyclesTab",
    "PlansTab",
    "TemplatesTab",
]
