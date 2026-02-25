"""Form helpers for the PySide6 GUI.

FormField  — descriptor for a single field (creates the widget automatically).
FormLayout — QWidget with QGridLayout, labels on the left, widgets on the right.
"""

from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple

from PySide6.QtWidgets import (
    QWidget,
    QGridLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QDoubleSpinBox,
    QSpinBox,
    QTextEdit,
)
from PySide6.QtCore import Qt


@dataclass
class FormField:
    """Descriptor for a single form field."""

    key: str
    label: str
    field_type: str = "text"  # text | number | decimal | combo | textarea
    value: Any = None
    options: Optional[List[Tuple[Any, str]]] = None  # [(data, display), ...]
    required: bool = False
    min_val: float = 0
    max_val: float = 999999
    decimals: int = 2
    read_only: bool = False


class FormLayout(QWidget):
    """Grid form: labels on the left, input widgets on the right.

    Parameters
    ----------
    fields : list[FormField]
        Field descriptors.
    parent : QWidget | None
        Optional parent widget.
    """

    def __init__(self, fields: List[FormField], parent=None):
        super().__init__(parent)
        self._fields = fields
        self._widgets: dict[str, QWidget] = {}
        grid = QGridLayout(self)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(8)
        grid.setColumnStretch(1, 1)

        for row, f in enumerate(fields):
            lbl = QLabel(f.label + (" *" if f.required else ""))
            lbl.setStyleSheet("color: #aeaeae;")
            lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            grid.addWidget(lbl, row, 0)

            widget = self._make_widget(f)
            self._widgets[f.key] = widget
            grid.addWidget(widget, row, 1)

    # --- public API -------------------------------------------------------

    def get_values(self) -> dict:
        """Return {key: value} for all fields."""
        result = {}
        for f in self._fields:
            w = self._widgets[f.key]
            if isinstance(w, QComboBox):
                result[f.key] = w.currentData()
            elif isinstance(w, QDoubleSpinBox):
                result[f.key] = round(w.value(), f.decimals)
            elif isinstance(w, QSpinBox):
                result[f.key] = w.value()
            elif isinstance(w, QTextEdit):
                result[f.key] = w.toPlainText().strip() or None
            else:
                result[f.key] = w.text().strip()
        return result

    def set_values(self, data: dict):
        """Populate widgets from a dict (missing keys are skipped)."""
        for f in self._fields:
            if f.key not in data:
                continue
            val = data[f.key]
            w = self._widgets[f.key]
            if isinstance(w, QComboBox):
                idx = w.findData(val)
                if idx >= 0:
                    w.setCurrentIndex(idx)
            elif isinstance(w, (QDoubleSpinBox, QSpinBox)):
                if val is not None:
                    w.setValue(float(val) if isinstance(w, QDoubleSpinBox) else int(val))
            elif isinstance(w, QTextEdit):
                w.setPlainText(str(val) if val else "")
            else:
                w.setText(str(val) if val is not None else "")

    def validate(self) -> list:
        """Return a list of error strings (empty == valid)."""
        errors = []
        for f in self._fields:
            if not f.required:
                continue
            w = self._widgets[f.key]
            if isinstance(w, QComboBox):
                if w.currentData() is None:
                    errors.append(f"{f.label} richiesto")
            elif isinstance(w, QTextEdit):
                if not w.toPlainText().strip():
                    errors.append(f"{f.label} richiesto")
            elif isinstance(w, QLineEdit):
                if not w.text().strip():
                    errors.append(f"{f.label} richiesto")
        return errors

    def widget(self, key: str) -> QWidget:
        """Direct access to a field's widget."""
        return self._widgets[key]

    # --- private ----------------------------------------------------------

    def _make_widget(self, f: FormField) -> QWidget:
        if f.field_type == "combo":
            w = QComboBox()
            for data, display in (f.options or []):
                w.addItem(display, data)
            if f.value is not None:
                idx = w.findData(f.value)
                if idx >= 0:
                    w.setCurrentIndex(idx)
            if f.read_only:
                w.setEnabled(False)
            return w

        if f.field_type == "number":
            w = QSpinBox()
            w.setRange(int(f.min_val), int(f.max_val))
            if f.value is not None:
                w.setValue(int(f.value))
            if f.read_only:
                w.setReadOnly(True)
            return w

        if f.field_type == "decimal":
            w = QDoubleSpinBox()
            w.setRange(f.min_val, f.max_val)
            w.setDecimals(f.decimals)
            if f.value is not None:
                w.setValue(float(f.value))
            if f.read_only:
                w.setReadOnly(True)
            return w

        if f.field_type == "textarea":
            w = QTextEdit()
            w.setMaximumHeight(90)
            if f.value:
                w.setPlainText(str(f.value))
            if f.read_only:
                w.setReadOnly(True)
            return w

        # Default: text
        w = QLineEdit()
        if f.value is not None:
            w.setText(str(f.value))
        if f.read_only:
            w.setReadOnly(True)
        return w
