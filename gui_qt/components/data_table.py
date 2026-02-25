"""Reusable data-table component for the PySide6 GUI.

Usage
-----
    table = DataTable([
        {"key": "id",   "label": "ID",   "width": 60},
        {"key": "name", "label": "Nome", "stretch": True},
    ])
    table.load_data([{"id": 1, "name": "BPC-157"}])
    table.set_context_menu([
        {"label": "Dettagli", "callback": on_details},
        {"label": "Elimina",  "callback": on_delete, "enabled_when": lambda: app.edit_mode},
    ])
"""

from PySide6.QtWidgets import (
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMenu,
    QAbstractItemView,
)
from PySide6.QtCore import Qt, Signal


class DataTable(QTableWidget):
    """Configurable table with row-dict access and context menu."""

    row_double_clicked = Signal(dict)

    def __init__(self, columns, parent=None):
        """
        Parameters
        ----------
        columns : list[dict]
            Each dict must have ``key`` and ``label``.
            Optional: ``width`` (int, fixed px), ``stretch`` (bool).
        """
        super().__init__(0, len(columns), parent)
        self._columns = columns
        self._rows: list[dict] = []
        self._menu_actions: list[dict] = []

        # Header
        self.setHorizontalHeaderLabels([c["label"] for c in columns])
        header = self.horizontalHeader()
        for i, c in enumerate(columns):
            if c.get("stretch"):
                header.setSectionResizeMode(i, QHeaderView.Stretch)
            elif "width" in c:
                self.setColumnWidth(i, c["width"])
                header.setSectionResizeMode(i, QHeaderView.Fixed)
            else:
                header.setSectionResizeMode(i, QHeaderView.ResizeToContents)

        # Behaviour
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.verticalHeader().setVisible(False)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.cellDoubleClicked.connect(self._on_double_click)

    # --- public API -------------------------------------------------------

    def load_data(self, rows):
        """Clear and repopulate the table from a list of dicts."""
        self._rows = list(rows)
        self.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, col in enumerate(self._columns):
                val = row.get(col["key"], "")
                item = QTableWidgetItem(str(val) if val is not None else "")
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.setItem(r, c, item)

    def selected_row(self):
        """Return the dict for the currently selected row, or None."""
        indexes = self.selectionModel().selectedRows()
        if not indexes:
            return None
        r = indexes[0].row()
        if 0 <= r < len(self._rows):
            return self._rows[r]
        return None

    def set_context_menu(self, actions):
        """Configure right-click menu.

        Parameters
        ----------
        actions : list[dict]
            Each dict: ``label``, ``callback`` (receives row dict),
            optional ``enabled_when`` (callable -> bool),
            optional ``visible_when`` (callable -> bool).
        """
        self._menu_actions = actions

    # --- private ----------------------------------------------------------

    def _on_double_click(self, row, _col):
        if 0 <= row < len(self._rows):
            self.row_double_clicked.emit(self._rows[row])

    def _show_context_menu(self, pos):
        row = self.selected_row()
        if row is None:
            return
        menu = QMenu(self)
        for action_def in self._menu_actions:
            visible = action_def.get("visible_when")
            if visible and not visible():
                continue
            act = menu.addAction(action_def["label"])
            enabled = action_def.get("enabled_when")
            if enabled and not enabled():
                act.setEnabled(False)
            act.triggered.connect(lambda _checked, a=action_def, r=row: a["callback"](r))
        menu.exec(self.viewport().mapToGlobal(pos))
