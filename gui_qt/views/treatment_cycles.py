"""Cycles tab, RampEditor widget, and cycle dialogs for the Treatment section."""

from datetime import date, datetime

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QWidget,
    QComboBox,
    QSpinBox,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QAbstractItemView,
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
    _CYCLE_STATUS_FILTER,
    _make_buttons,
    _sep,
    _freq_desc,
    _today_str,
)


# ═════════════════════════════════════════════════════════════════════════
#  RAMP EDITOR WIDGET
# ═════════════════════════════════════════════════════════════════════════


class _RampEditor(QWidget):
    """Editable ramp schedule: week / peptide / dose.

    get_schedule() returns the list of dicts for the backend.
    set_schedule(schedule, peptides) populates from existing data.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._peptides = []  # [(id, name, base_dose_mcg), ...]
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        lay.addWidget(_sep("Ramp Schedule"))

        # Preset buttons
        preset_row = QHBoxLayout()
        for label, weeks, percents in [
            ("Conservativo", 4, [25, 50, 75, 100]),
            ("Moderato", 2, [50, 100]),
            ("Aggressivo", 1, [50, 100]),
        ]:
            btn = QPushButton(label)
            btn.clicked.connect(
                lambda _c=False, w=weeks, pcts=percents: self._apply_preset(w, pcts)
            )
            preset_row.addWidget(btn)
        preset_row.addStretch()
        lay.addLayout(preset_row)

        # Table
        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["Settimana", "Peptide", "Dose (mcg)"])
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        self._table.setColumnWidth(0, 80)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        self._table.setColumnWidth(2, 120)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.verticalHeader().setVisible(False)
        self._table.setMaximumHeight(200)
        lay.addWidget(self._table)

        # Add / Remove buttons
        btn_row = QHBoxLayout()
        add_btn = QPushButton("+ Aggiungi Riga")
        add_btn.clicked.connect(self._add_row_ui)
        btn_row.addWidget(add_btn)
        rm_btn = QPushButton("- Rimuovi Selezionata")
        rm_btn.clicked.connect(self._remove_selected)
        btn_row.addWidget(rm_btn)
        btn_row.addStretch()
        lay.addLayout(btn_row)

    def set_peptides(self, peptides):
        """Set available peptides: list of (id, name, base_dose_mcg)."""
        self._peptides = list(peptides)

    def set_schedule(self, schedule):
        """Populate table from backend schedule format.

        schedule: [{'week': 1, 'doses': [{'peptide_id': X, 'dose_mcg': Y}, ...]}, ...]
        """
        self._table.setRowCount(0)
        if not schedule:
            return
        for entry in schedule:
            week = entry.get("week", 1)
            for dose_item in entry.get("doses", []):
                pid = dose_item.get("peptide_id")
                dose = dose_item.get("dose_mcg", 0)
                pname = self._peptide_name(pid)
                self._insert_row(week, pname, pid, dose)

    def get_schedule(self):
        """Return schedule in backend format."""
        weeks = {}
        for r in range(self._table.rowCount()):
            week_item = self._table.item(r, 0)
            dose_item = self._table.item(r, 2)
            pep_combo = self._table.cellWidget(r, 1)
            if not week_item or not dose_item:
                continue
            try:
                week = int(week_item.text())
            except (ValueError, TypeError):
                continue
            try:
                dose = int(float(dose_item.text()))
            except (ValueError, TypeError):
                dose = 0

            pid = pep_combo.currentData() if pep_combo else None
            if pid is None:
                continue

            if week not in weeks:
                weeks[week] = []
            weeks[week].append({"peptide_id": pid, "dose_mcg": dose})

        return [
            {"week": w, "doses": doses}
            for w, doses in sorted(weeks.items())
        ]

    # ── Private ──────────────────────────────────────────────────────────

    def _peptide_name(self, pid):
        for p_id, name, _ in self._peptides:
            if p_id == pid:
                return name
        return f"#{pid}"

    def _insert_row(self, week, pname, pid, dose):
        r = self._table.rowCount()
        self._table.insertRow(r)
        self._table.setItem(r, 0, QTableWidgetItem(str(week)))

        combo = QComboBox()
        for p_id, name, _ in self._peptides:
            combo.addItem(name, p_id)
        idx = combo.findData(pid)
        if idx >= 0:
            combo.setCurrentIndex(idx)
        self._table.setCellWidget(r, 1, combo)

        self._table.setItem(r, 2, QTableWidgetItem(str(int(dose))))

    def _add_row_ui(self):
        # Determine next week number
        max_week = 0
        for r in range(self._table.rowCount()):
            item = self._table.item(r, 0)
            if item:
                try:
                    max_week = max(max_week, int(item.text()))
                except (ValueError, TypeError):
                    pass
        first_pid = self._peptides[0][0] if self._peptides else None
        first_name = self._peptides[0][1] if self._peptides else "?"
        base_dose = self._peptides[0][2] if self._peptides else 250
        self._insert_row(max_week + 1, first_name, first_pid, base_dose)

    def _remove_selected(self):
        rows = set(idx.row() for idx in self._table.selectedIndexes())
        for r in sorted(rows, reverse=True):
            self._table.removeRow(r)

    def _apply_preset(self, ramp_weeks, percentages):
        """Fill schedule from a preset: ramp_weeks of gradually increasing dose,
        then full dose for remaining weeks (if protocol has cycle_duration_weeks)."""
        self._table.setRowCount(0)
        if not self._peptides:
            return

        for i, pct in enumerate(percentages, start=1):
            for pid, name, base_dose in self._peptides:
                dose = int(round(base_dose * pct / 100))
                self._insert_row(i, name, pid, dose)


# ═════════════════════════════════════════════════════════════════════════
#  CYCLES TAB
# ═════════════════════════════════════════════════════════════════════════


class CyclesTab(BaseView):
    """Cycles list with status filter and context menu actions."""

    def __init__(self, app, parent=None):
        super().__init__(app, parent)
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        lay = self.layout()

        # Toolbar
        toolbar = QHBoxLayout()
        title = QLabel("Cicli")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        toolbar.addWidget(title)
        toolbar.addStretch()

        self._status_filter = QComboBox()
        for data, label in _CYCLE_STATUS_FILTER:
            self._status_filter.addItem(label, data)
        self._status_filter.currentIndexChanged.connect(lambda: self.refresh())
        toolbar.addWidget(self._status_filter)

        add_btn = QPushButton("Nuovo Ciclo")
        add_btn.clicked.connect(self._on_add)
        toolbar.addWidget(add_btn)
        lay.addLayout(toolbar)

        # Table
        self._table = DataTable([
            {"key": "id",            "label": "ID",         "width": 50},
            {"key": "name",          "label": "Nome",       "stretch": True},
            {"key": "protocol_name", "label": "Protocollo", "width": 160},
            {"key": "status_display", "label": "Stato",     "width": 100},
            {"key": "start_date",    "label": "Inizio",     "width": 100},
            {"key": "progress",      "label": "Progresso",  "width": 80},
        ])
        self._table.set_context_menu([
            {"label": "Dettagli",   "callback": self._on_details},
            {"label": "Modifica",   "callback": self._on_edit,
             "enabled_when": lambda: self.edit_mode},
            {"label": "Elimina",    "callback": self._on_delete,
             "enabled_when": lambda: self.edit_mode},
            # Status actions
            {"label": "Attiva",     "callback": self._on_activate,
             "visible_when": lambda: self._selected_status() == "planned"},
            {"label": "Pausa",      "callback": self._on_pause,
             "visible_when": lambda: self._selected_status() == "active"},
            {"label": "Completa",   "callback": self._on_complete,
             "visible_when": lambda: self._selected_status() == "active"},
            {"label": "Riprendi",   "callback": self._on_resume,
             "visible_when": lambda: self._selected_status() == "paused"},
        ])
        self._table.row_double_clicked.connect(self._on_details)
        lay.addWidget(self._table, 1)

    def _selected_status(self):
        row = self._table.selected_row()
        return row.get("_status") if row else None

    # ── Data ─────────────────────────────────────────────────────────────

    def refresh(self):
        status_filter = self._status_filter.currentData()
        try:
            if status_filter:
                cycles = [
                    c for c in self.manager.get_cycles(active_only=False)
                    if c.get("status") == status_filter
                ]
            else:
                cycles = self.manager.get_cycles(active_only=False)
        except Exception as e:
            error_dialog(self, "Errore", str(e))
            return

        rows = []
        for c in cycles:
            # Compute progress
            cdw = c.get("cycle_duration_weeks")
            start = c.get("start_date")
            progress = "-"
            if cdw and start:
                try:
                    sd = datetime.strptime(str(start)[:10], "%Y-%m-%d").date()
                    elapsed = (date.today() - sd).days
                    current_week = max(1, (elapsed // 7) + 1)
                    progress = f"Sett {min(current_week, cdw)}/{cdw}"
                except (ValueError, TypeError):
                    pass

            # Protocol name from snapshot
            snapshot = c.get("protocol_snapshot") or {}
            proto_name = snapshot.get("name") or c.get("protocol_name", "-")

            rows.append({
                "id": c["id"],
                "name": c.get("name", ""),
                "protocol_name": proto_name,
                "status_display": _STATUS_LABELS.get(c.get("status", ""), c.get("status", "")),
                "start_date": str(c.get("start_date", "-"))[:10],
                "progress": progress,
                "_status": c.get("status"),
            })
        self._table.load_data(rows)

    # ── Actions ──────────────────────────────────────────────────────────

    def _on_add(self):
        dlg = _CycleStartDialog(self.app, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh()

    def _on_details(self, row):
        dlg = _CycleDetailsDialog(self.app, row["id"], parent=self)
        dlg.exec()

    def _on_edit(self, row):
        dlg = _CycleEditDialog(self.app, row["id"], parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh()

    def _on_delete(self, row):
        if not confirm_dialog(
            self, "Elimina Ciclo",
            f"Eliminare il ciclo #{row['id']} ({row['name']})?",
        ):
            return
        try:
            self.manager.delete_cycle(row["id"])
            self.app.show_message("Ciclo eliminato")
            self.refresh()
        except Exception as e:
            error_dialog(self, "Errore", str(e))

    def _on_activate(self, row):
        self._change_status(row, "active", "Ciclo attivato")

    def _on_pause(self, row):
        self._change_status(row, "paused", "Ciclo in pausa")

    def _on_complete(self, row):
        try:
            self.manager.complete_cycle(row["id"])
            self.app.show_message("Ciclo completato")
            self.refresh()
        except Exception as e:
            error_dialog(self, "Errore", str(e))

    def _on_resume(self, row):
        self._change_status(row, "active", "Ciclo ripreso")

    def _change_status(self, row, new_status, msg):
        try:
            self.manager.update_cycle_status(row["id"], new_status)
            self.app.show_message(msg)
            self.refresh()
        except Exception as e:
            error_dialog(self, "Errore", str(e))


# ── Cycle dialogs ───────────────────────────────────────────────────────


class _CycleStartDialog(QDialog):
    """Start a new cycle from a protocol."""

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self._app = app
        self.setWindowTitle("Nuovo Ciclo")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        self.setStyleSheet(_DLG_STYLE)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Protocol combo
        try:
            protocols = self._app.manager.get_protocols(active_only=True)
        except Exception:
            protocols = []

        proto_opts = [(p["id"], p.get("name", f"#{p['id']}")) for p in protocols]
        self._protocols_data = {p["id"]: p for p in protocols}

        self._form = FormLayout([
            FormField("protocol_id", "Protocollo", "combo",
                      options=proto_opts, required=True),
            FormField("name", "Nome Ciclo", "text"),
            FormField("start_date", "Data Inizio", "text", value=_today_str()),
            FormField("planned_end_date", "Data Fine Prev.", "text"),
            FormField("status", "Stato Iniziale", "combo",
                      value="active",
                      options=[("active", "Attivo"), ("planned", "Pianificato")]),
        ])
        layout.addWidget(self._form)

        # Connect protocol change to update ramp editor
        proto_combo = self._form.widget("protocol_id")
        proto_combo.currentIndexChanged.connect(self._on_protocol_changed)

        # Ramp editor
        self._ramp = _RampEditor()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._ramp)
        layout.addWidget(scroll, 1)

        # Load peptides for default protocol
        self._on_protocol_changed()

        # Buttons
        btns, submit = _make_buttons(self, submit_label="Crea Ciclo")
        submit.clicked.connect(self._submit)
        layout.addWidget(btns)

    def _on_protocol_changed(self):
        proto_combo = self._form.widget("protocol_id")
        pid = proto_combo.currentData()
        if pid is None:
            self._ramp.set_peptides([])
            return

        try:
            details = self._app.manager.get_protocol_details(pid)
        except Exception:
            details = self._protocols_data.get(pid, {})

        peptides_list = details.get("peptides", [])
        pep_tuples = [
            (pp.get("peptide_id") or pp.get("id"), pp.get("name", "?"),
             pp.get("target_dose_mcg", 250))
            for pp in peptides_list
        ]
        self._ramp.set_peptides(pep_tuples)
        # Clear existing schedule when protocol changes
        self._ramp.set_schedule([])

    def _submit(self):
        errors = self._form.validate()
        if errors:
            error_dialog(self, "Validazione", "\n".join(errors))
            return

        vals = self._form.get_values()
        ramp = self._ramp.get_schedule()

        try:
            self._app.manager.start_cycle(
                protocol_id=vals["protocol_id"],
                name=vals["name"] or None,
                start_date=vals["start_date"] or None,
                planned_end_date=vals["planned_end_date"] or None,
                ramp_schedule=ramp if ramp else None,
                status=vals["status"],
            )
            self._app.show_message("Ciclo creato")
            self.accept()
        except Exception as e:
            error_dialog(self, "Errore", str(e))


class _CycleEditDialog(QDialog):
    """Edit an existing cycle."""

    def __init__(self, app, cycle_id, parent=None):
        super().__init__(parent)
        self._app = app
        self._cycle_id = cycle_id
        self.setWindowTitle(f"Modifica Ciclo #{cycle_id}")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        self.setStyleSheet(_DLG_STYLE)

        try:
            self._cycle = app.manager.get_cycle_details(cycle_id)
        except Exception as e:
            error_dialog(self, "Errore", str(e))
            self.reject()
            return

        if not self._cycle:
            error_dialog(self, "Errore", "Ciclo non trovato")
            self.reject()
            return

        self._build_ui()

    def _build_ui(self):
        c = self._cycle
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        status_opts = [
            ("planned", "Pianificato"),
            ("active", "Attivo"),
            ("paused", "In Pausa"),
            ("completed", "Completato"),
            ("cancelled", "Annullato"),
        ]

        self._form = FormLayout([
            FormField("name", "Nome", "text",
                      value=c.get("name", ""), required=True),
            FormField("description", "Descrizione", "textarea",
                      value=c.get("description", "")),
            FormField("start_date", "Data Inizio", "text",
                      value=str(c.get("start_date", ""))[:10]),
            FormField("planned_end_date", "Data Fine Prev.", "text",
                      value=str(c.get("planned_end_date", "") or "")[:10]),
            FormField("days_on", "Giorni ON", "number",
                      value=c.get("days_on", 5), min_val=1, max_val=365),
            FormField("days_off", "Giorni OFF", "number",
                      value=c.get("days_off", 0), min_val=0, max_val=365),
            FormField("cycle_duration_weeks", "Durata (sett)", "number",
                      value=c.get("cycle_duration_weeks", 8), min_val=1, max_val=104),
            FormField("status", "Stato", "combo",
                      value=c.get("status", "active"), options=status_opts),
        ])
        layout.addWidget(self._form)

        # Ramp editor
        self._ramp = _RampEditor()

        # Load peptides from protocol snapshot
        snapshot = c.get("protocol_snapshot") or {}
        pep_list = snapshot.get("peptides", [])
        pep_tuples = [
            (pp.get("peptide_id") or pp.get("id"), pp.get("name", "?"),
             pp.get("target_dose_mcg", 250))
            for pp in pep_list
        ]
        self._ramp.set_peptides(pep_tuples)
        self._ramp.set_schedule(c.get("ramp_schedule") or [])

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._ramp)
        layout.addWidget(scroll, 1)

        btns, submit = _make_buttons(self)
        submit.clicked.connect(self._submit)
        layout.addWidget(btns)

    def _submit(self):
        errors = self._form.validate()
        if errors:
            error_dialog(self, "Validazione", "\n".join(errors))
            return

        vals = self._form.get_values()
        ramp = self._ramp.get_schedule()

        try:
            self._app.manager.update_cycle(
                self._cycle_id,
                name=vals["name"],
                description=vals["description"],
                start_date=vals["start_date"] or None,
                planned_end_date=vals["planned_end_date"] or None,
                days_on=vals["days_on"],
                days_off=vals["days_off"],
                cycle_duration_weeks=vals["cycle_duration_weeks"],
                status=vals["status"],
                ramp_schedule=ramp if ramp else None,
            )
            self._app.show_message("Ciclo aggiornato")
            self.accept()
        except Exception as e:
            error_dialog(self, "Errore", str(e))


class _CycleDetailsDialog(QDialog):
    """Read-only cycle details with ramp schedule visualization."""

    def __init__(self, app, cycle_id, parent=None):
        super().__init__(parent)
        self._app = app
        self.setWindowTitle(f"Dettagli Ciclo #{cycle_id}")
        self.setMinimumWidth(560)
        self.setStyleSheet(_DLG_STYLE)

        try:
            self._cycle = app.manager.get_cycle_details(cycle_id)
        except Exception as e:
            error_dialog(self, "Errore", str(e))
            self.reject()
            return

        if not self._cycle:
            error_dialog(self, "Errore", "Ciclo non trovato")
            self.reject()
            return

        self._build_ui()

    def _build_ui(self):
        c = self._cycle
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Title
        title = QLabel(c.get("name", f"Ciclo #{c.get('id', '?')}"))
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

        snapshot = c.get("protocol_snapshot") or {}
        add_row("Protocollo", snapshot.get("name") or c.get("protocol_name", "-"))
        add_row("Stato", _STATUS_LABELS.get(c.get("status", ""), c.get("status", "")))
        add_row("Inizio", str(c.get("start_date", "-"))[:10])
        add_row("Fine Prev.", str(c.get("planned_end_date") or "-")[:10])
        add_row("Descrizione", c.get("description") or "-")

        don = c.get("days_on")
        doff = c.get("days_off", 0)
        if don:
            sched_str = f"{don}gg ON"
            if doff:
                sched_str += f" / {doff}gg OFF"
            add_row("Schedulazione", sched_str)

        cdw = c.get("cycle_duration_weeks")
        if cdw:
            add_row("Durata", f"{cdw} settimane")

        # Current week
        start = c.get("start_date")
        if cdw and start and c.get("status") == "active":
            try:
                sd = datetime.strptime(str(start)[:10], "%Y-%m-%d").date()
                elapsed = (date.today() - sd).days
                current_week = max(1, (elapsed // 7) + 1)
                add_row("Settimana Attuale", f"{min(current_week, cdw)} / {cdw}")
            except (ValueError, TypeError):
                pass

        layout.addLayout(grid)

        # Ramp schedule visualization
        ramp = c.get("ramp_schedule") or []
        if ramp:
            layout.addWidget(_sep("Ramp Schedule"))

            # Build read-only table
            ramp_table = QTableWidget()
            ramp_table.setAlternatingRowColors(True)
            ramp_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            ramp_table.verticalHeader().setVisible(False)
            ramp_table.setMaximumHeight(150)

            # Collect all peptide names
            pep_names = {}
            snap_peps = snapshot.get("peptides", [])
            for pp in snap_peps:
                pid = pp.get("peptide_id") or pp.get("id")
                pep_names[pid] = pp.get("name", f"#{pid}")

            # Count total rows
            total_rows = sum(len(e.get("doses", [])) for e in ramp)
            ramp_table.setColumnCount(3)
            ramp_table.setHorizontalHeaderLabels(["Settimana", "Peptide", "Dose (mcg)"])
            ramp_table.setRowCount(total_rows)
            header = ramp_table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.Fixed)
            ramp_table.setColumnWidth(0, 80)
            header.setSectionResizeMode(1, QHeaderView.Stretch)
            header.setSectionResizeMode(2, QHeaderView.Fixed)
            ramp_table.setColumnWidth(2, 120)

            # Compute current week for highlighting
            current_week = None
            if start and c.get("status") == "active":
                try:
                    sd = datetime.strptime(str(start)[:10], "%Y-%m-%d").date()
                    elapsed = (date.today() - sd).days
                    current_week = max(1, (elapsed // 7) + 1)
                except (ValueError, TypeError):
                    pass

            row_idx = 0
            for entry in ramp:
                week = entry.get("week", "?")
                for dose_item in entry.get("doses", []):
                    pid = dose_item.get("peptide_id")
                    dose = dose_item.get("dose_mcg", 0)
                    pname = pep_names.get(pid, f"#{pid}")

                    items = [
                        QTableWidgetItem(str(week)),
                        QTableWidgetItem(pname),
                        QTableWidgetItem(str(int(dose))),
                    ]
                    # Highlight current week
                    if current_week is not None and week == current_week:
                        for item in items:
                            item.setBackground(Qt.darkGreen)

                    for col, item in enumerate(items):
                        ramp_table.setItem(row_idx, col, item)
                    row_idx += 1

            layout.addWidget(ramp_table)

        # Close
        close_btn = QPushButton("Chiudi")
        close_btn.setFixedWidth(100)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignRight)
