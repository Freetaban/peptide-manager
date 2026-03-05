"""Protocols tab and dialogs for the Treatment section."""

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QWidget,
    QComboBox,
    QSpinBox,
)
from PySide6.QtCore import Qt

from .treatment_common import (
    BaseView,
    DataTable,
    confirm_dialog,
    error_dialog,
    FormField,
    FormLayout,
    _DLG_STYLE,
    _STATUS_LABELS,
    _make_buttons,
    _sep,
    _freq_desc,
)


# ═════════════════════════════════════════════════════════════════════════
#  PROTOCOLS TAB
# ═════════════════════════════════════════════════════════════════════════


class ProtocolsTab(BaseView):
    """Protocols list with add/edit/delete via context menu."""

    def __init__(self, app, parent=None):
        super().__init__(app, parent)
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        lay = self.layout()

        # Toolbar
        toolbar = QHBoxLayout()
        title = QLabel("Protocolli")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        toolbar.addWidget(title)
        toolbar.addStretch()

        add_btn = QPushButton("Nuovo Protocollo")
        add_btn.clicked.connect(self._on_add)
        toolbar.addWidget(add_btn)
        lay.addLayout(toolbar)

        # Table
        self._table = DataTable([
            {"key": "id",               "label": "ID",        "width": 50},
            {"key": "name",             "label": "Nome",      "stretch": True},
            {"key": "frequency_desc",   "label": "Frequenza", "width": 200},
            {"key": "peptides_display", "label": "Peptidi",   "stretch": True},
            {"key": "admin_count",      "label": "Somm.",     "width": 80},
        ])
        self._table.set_context_menu([
            {"label": "Dettagli",  "callback": self._on_details},
            {"label": "Modifica",  "callback": self._on_edit,
             "enabled_when": lambda: self.edit_mode},
            {"label": "Elimina",   "callback": self._on_delete,
             "enabled_when": lambda: self.edit_mode},
        ])
        self._table.row_double_clicked.connect(self._on_details)
        lay.addWidget(self._table, 1)

    # ── Data ─────────────────────────────────────────────────────────────

    def refresh(self):
        try:
            protocols = self.manager.get_protocols(active_only=True)
        except Exception as e:
            error_dialog(self, "Errore", str(e))
            return

        rows = []
        for p in protocols:
            # Get admin count
            admin_count = 0
            try:
                stats = self.manager.get_protocol_statistics(p["id"])
                admin_count = stats.get("count", 0)
            except Exception:
                pass

            rows.append({
                "id": p["id"],
                "name": p.get("name", ""),
                "frequency_desc": _freq_desc(p),
                "peptides_display": p.get("peptides_display", "-"),
                "admin_count": admin_count,
            })
        self._table.load_data(rows)

    # ── Actions ──────────────────────────────────────────────────────────

    def _on_add(self):
        dlg = _ProtocolAddDialog(self.app, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh()

    def _on_details(self, row):
        dlg = _ProtocolDetailsDialog(self.app, row["id"], parent=self)
        dlg.exec()

    def _on_edit(self, row):
        dlg = _ProtocolEditDialog(self.app, row["id"], parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh()

    def _on_delete(self, row):
        if not confirm_dialog(
            self, "Elimina Protocollo",
            f"Eliminare il protocollo #{row['id']} ({row['name']})?",
        ):
            return
        try:
            self.manager.soft_delete_protocol(row["id"])
            self.app.show_message("Protocollo eliminato")
            self.refresh()
        except Exception as e:
            error_dialog(self, "Errore", str(e))


# ── Protocol dialogs ────────────────────────────────────────────────────


class _ProtocolAddDialog(QDialog):
    """Add a new protocol with peptide assignments."""

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self._app = app
        self.setWindowTitle("Nuovo Protocollo")
        self.setMinimumWidth(550)
        self.setStyleSheet(_DLG_STYLE)
        self._peptide_rows = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        self._form = FormLayout([
            FormField("name", "Nome", "text", required=True),
            FormField("frequency_per_day", "Frequenza/Giorno", "number",
                      value=1, min_val=1, max_val=10),
            FormField("days_on", "Giorni ON", "number",
                      value=5, min_val=1, max_val=365),
            FormField("days_off", "Giorni OFF", "number",
                      value=0, min_val=0, max_val=365),
            FormField("cycle_duration_weeks", "Durata Ciclo (sett)", "number",
                      value=8, min_val=1, max_val=104),
            FormField("description", "Descrizione", "textarea"),
            FormField("notes", "Note", "textarea"),
        ])
        layout.addWidget(self._form)

        # Peptide section
        layout.addWidget(_sep("Peptidi"))

        self._pep_container = QVBoxLayout()
        layout.addLayout(self._pep_container)

        add_pep_btn = QPushButton("+ Aggiungi Peptide")
        add_pep_btn.clicked.connect(self._add_peptide_row)
        layout.addWidget(add_pep_btn)

        # Load peptide list for combos
        try:
            self._all_peptides = self._app.manager.get_peptides()
        except Exception:
            self._all_peptides = []

        # Add one row by default
        self._add_peptide_row()

        # Buttons
        btns, submit = _make_buttons(self)
        submit.clicked.connect(self._submit)
        layout.addWidget(btns)

    def _add_peptide_row(self):
        row_w = QWidget()
        row_l = QHBoxLayout(row_w)
        row_l.setContentsMargins(0, 0, 0, 0)
        row_l.setSpacing(8)

        combo = QComboBox()
        combo.addItem("-- Seleziona --", None)
        for p in self._all_peptides:
            combo.addItem(p.get("name", f"#{p['id']}"), p["id"])
        row_l.addWidget(combo, 2)

        dose = QSpinBox()
        dose.setRange(1, 99999)
        dose.setValue(250)
        dose.setSuffix(" mcg")
        row_l.addWidget(dose, 1)

        rm_btn = QPushButton("X")
        rm_btn.setFixedWidth(30)
        rm_btn.clicked.connect(lambda: self._remove_peptide_row(row_w))
        row_l.addWidget(rm_btn)

        self._pep_container.addWidget(row_w)
        self._peptide_rows.append((row_w, combo, dose))

    def _remove_peptide_row(self, row_w):
        self._peptide_rows = [
            (w, c, d) for w, c, d in self._peptide_rows if w is not row_w
        ]
        row_w.setParent(None)
        row_w.deleteLater()

    def _submit(self):
        errors = self._form.validate()
        if errors:
            error_dialog(self, "Validazione", "\n".join(errors))
            return

        # Collect peptides
        peptides = []
        for _, combo, dose in self._peptide_rows:
            pid = combo.currentData()
            if pid is not None:
                peptides.append((pid, dose.value()))

        if not peptides:
            error_dialog(self, "Validazione", "Aggiungere almeno un peptide")
            return

        vals = self._form.get_values()
        try:
            self._app.manager.add_protocol(
                name=vals["name"],
                frequency_per_day=vals["frequency_per_day"],
                days_on=vals["days_on"],
                days_off=vals["days_off"],
                cycle_duration_weeks=vals["cycle_duration_weeks"],
                peptides=peptides,
                description=vals["description"],
                notes=vals["notes"],
            )
            self._app.show_message("Protocollo creato")
            self.accept()
        except Exception as e:
            error_dialog(self, "Errore", str(e))


class _ProtocolEditDialog(QDialog):
    """Edit protocol base fields (no peptide editing — delete and recreate)."""

    def __init__(self, app, protocol_id, parent=None):
        super().__init__(parent)
        self._app = app
        self._protocol_id = protocol_id
        self.setWindowTitle(f"Modifica Protocollo #{protocol_id}")
        self.setMinimumWidth(500)
        self.setStyleSheet(_DLG_STYLE)

        try:
            self._proto = app.manager.get_protocol_details(protocol_id)
        except Exception as e:
            error_dialog(self, "Errore", str(e))
            self.reject()
            return

        if not self._proto:
            error_dialog(self, "Errore", "Protocollo non trovato")
            self.reject()
            return

        self._build_ui()

    def _build_ui(self):
        p = self._proto
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        self._form = FormLayout([
            FormField("name", "Nome", "text",
                      value=p.get("name", ""), required=True),
            FormField("frequency_per_day", "Frequenza/Giorno", "number",
                      value=p.get("frequency_per_day", 1), min_val=1, max_val=10),
            FormField("days_on", "Giorni ON", "number",
                      value=p.get("days_on", 5), min_val=1, max_val=365),
            FormField("days_off", "Giorni OFF", "number",
                      value=p.get("days_off", 0), min_val=0, max_val=365),
            FormField("cycle_duration_weeks", "Durata Ciclo (sett)", "number",
                      value=p.get("cycle_duration_weeks", 8), min_val=1, max_val=104),
            FormField("description", "Descrizione", "textarea",
                      value=p.get("description", "")),
            FormField("notes", "Note", "textarea",
                      value=p.get("notes", "")),
        ])
        layout.addWidget(self._form)

        # Note about peptides
        hint = QLabel("Per modificare i peptidi, elimina e ricrea il protocollo.")
        hint.setStyleSheet("color: #888; font-style: italic; font-size: 11px;")
        layout.addWidget(hint)

        btns, submit = _make_buttons(self)
        submit.clicked.connect(self._submit)
        layout.addWidget(btns)

    def _submit(self):
        errors = self._form.validate()
        if errors:
            error_dialog(self, "Validazione", "\n".join(errors))
            return

        vals = self._form.get_values()
        try:
            self._app.manager.update_protocol(
                self._protocol_id,
                name=vals["name"],
                frequency_per_day=vals["frequency_per_day"],
                days_on=vals["days_on"],
                days_off=vals["days_off"],
                cycle_duration_weeks=vals["cycle_duration_weeks"],
                description=vals["description"],
                notes=vals["notes"],
            )
            self._app.show_message("Protocollo aggiornato")
            self.accept()
        except Exception as e:
            error_dialog(self, "Errore", str(e))


class _ProtocolDetailsDialog(QDialog):
    """Read-only protocol details with peptide list and stats."""

    def __init__(self, app, protocol_id, parent=None):
        super().__init__(parent)
        self._app = app
        self.setWindowTitle(f"Dettagli Protocollo #{protocol_id}")
        self.setMinimumWidth(520)
        self.setStyleSheet(_DLG_STYLE)

        try:
            self._proto = app.manager.get_protocol_details(protocol_id)
        except Exception as e:
            error_dialog(self, "Errore", str(e))
            self.reject()
            return

        if not self._proto:
            error_dialog(self, "Errore", "Protocollo non trovato")
            self.reject()
            return

        self._build_ui()

    def _build_ui(self):
        p = self._proto
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Title
        title = QLabel(p.get("name", f"Protocollo #{p.get('id', '?')}"))
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # Info grid
        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(6)
        r = 0

        def add_row(label, value):
            nonlocal r
            lbl = QLabel(label)
            lbl.setStyleSheet("color: #aeaeae;")
            lbl.setAlignment(Qt.AlignRight | Qt.AlignTop)
            grid.addWidget(lbl, r, 0)
            val = QLabel(str(value) if value is not None else "-")
            val.setWordWrap(True)
            grid.addWidget(val, r, 1)
            r += 1

        add_row("Frequenza", _freq_desc(p))
        add_row("Descrizione", p.get("description") or "-")
        add_row("Note", p.get("notes") or "-")

        # Peptides
        peptides = p.get("peptides", [])
        if peptides:
            pep_lines = []
            for pp in peptides:
                name = pp.get("name", "?")
                dose = pp.get("target_dose_mcg", "?")
                pep_lines.append(f"  {name}: {dose} mcg")
            add_row("Peptidi", "\n".join(pep_lines))
        else:
            add_row("Peptidi", "-")

        # Stats
        admin_count = p.get("administrations_count", 0)
        add_row("Somministrazioni", str(admin_count))
        first = p.get("first_administration")
        last = p.get("last_administration")
        if first:
            add_row("Prima Somm.", first)
        if last:
            add_row("Ultima Somm.", last)

        layout.addLayout(grid)

        # Close
        close_btn = QPushButton("Chiudi")
        close_btn.setFixedWidth(100)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignRight)
