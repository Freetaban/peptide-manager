"""
Peptide Management System
Sistema completo per la gestione di peptidi: acquisto, inventario, 
preparazioni, protocolli e somministrazioni.
"""

__version__ = '0.1.0'
__author__ = 'Your Name'

from .database import init_database
from .models import PeptideManager
from .calculator import DilutionCalculator
from .reports import ReportGenerator

__all__ = [
    'init_database',
    'PeptideManager',
    'DilutionCalculator',
    'ReportGenerator'
]
