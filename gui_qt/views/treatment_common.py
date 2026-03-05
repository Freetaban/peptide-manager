"""Shared constants, styles, and utility functions for the Treatment section."""

import json
from datetime import date, datetime

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QWidget,
    QComboBox,
    QSpinBox,
    QTextEdit,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QAbstractItemView,
)
from PySide6.QtCore import Qt, Signal

from .base import BaseView
from ..components.data_table import DataTable
from ..components.dialogs import confirm_dialog, error_dialog
from ..components.forms import FormField, FormLayout


# ── Shared constants ─────────────────────────────────────────────────────

_DLG_STYLE = (
    "QDialog { background: #1e1e1e; }"
    "QLineEdit, QComboBox, QTextEdit, QSpinBox, QDoubleSpinBox {"
    " background: #2d2d2d; border: 1px solid #424242;"
    " border-radius: 4px; padding: 6px 10px; color: #e0e0e0; }"
    "QLineEdit:focus, QTextEdit:focus { border-color: #42a5f5; }"
)

_STATUS_LABELS = {
    "planned": "Pianificato",
    "active": "Attivo",
    "paused": "In Pausa",
    "completed": "Completato",
    "cancelled": "Annullato",
    "abandoned": "Abbandonato",
}

_CYCLE_STATUS_FILTER = [
    (None, "Tutti"),
    ("active", "Attivi"),
    ("planned", "Pianificati"),
    ("completed", "Completati"),
]

_PLAN_STATUS_FILTER = [
    (None, "Tutti"),
    ("active", "Attivi"),
    ("planned", "Pianificati"),
    ("completed", "Completati"),
]


def _today_str():
    return date.today().isoformat()


def _make_buttons(dialog, submit_label="Salva"):
    """Standard OK / Cancel button box for dialogs."""
    btns = QDialogButtonBox()
    cancel = btns.addButton("Annulla", QDialogButtonBox.RejectRole)
    cancel.setStyleSheet(
        "background: #424242; color: #e0e0e0; padding: 8px 16px;"
        " border-radius: 4px; font-weight: bold;"
    )
    submit = btns.addButton(submit_label, QDialogButtonBox.AcceptRole)
    submit.setStyleSheet(
        "background: #42a5f5; color: #fff; padding: 8px 16px;"
        " border-radius: 4px; font-weight: bold;"
    )
    btns.rejected.connect(dialog.reject)
    return btns, submit


def _sep(text):
    """Section separator label."""
    lbl = QLabel(text)
    lbl.setStyleSheet(
        "font-weight: bold; color: #aeaeae;"
        " border-bottom: 1px solid #424242; padding: 4px 0;"
    )
    return lbl


def _freq_desc(proto):
    """Build a human-readable frequency description from protocol data."""
    parts = []
    fpd = proto.get("frequency_per_day", 1)
    if fpd:
        parts.append(f"{fpd}x/giorno")
    don = proto.get("days_on")
    doff = proto.get("days_off", 0)
    if don and doff:
        parts.append(f"{don}gg ON {doff}gg OFF")
    elif don:
        parts.append(f"{don}gg ON")
    cdw = proto.get("cycle_duration_weeks")
    if cdw:
        parts.append(f"ciclo {cdw}sett")
    return ", ".join(parts) if parts else "-"
