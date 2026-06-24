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
    QSizePolicy,
    QWidget,
    QComboBox,
    QSpinBox,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QAbstractItemView,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

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
from .treatment_plans import _DaySelector


def _snap_dict(raw) -> dict:
    """Normalizza protocol_snapshot a dict indipendentemente dal formato.
    Formato vecchio: lista di peptidi diretta → {}
    Formato nuovo:   dict con chiavi 'name', 'peptides', ecc. → raw
    """
    return raw if isinstance(raw, dict) else {}


def _snap_peptides(raw) -> list:
    """Estrae la lista peptidi dal protocol_snapshot (qualsiasi formato)."""
    if isinstance(raw, list):
        return raw                          # formato vecchio: la lista È lo snapshot
    if isinstance(raw, dict):
        return raw.get("peptides", [])      # formato nuovo: chiave 'peptides'
    return []


def _snap_weekday_based(pep_list: list) -> bool:
    """True se il ciclo usa il modello weekday (almeno un peptide ha `weekdays`).

    I cicli da protocollo non hanno `weekdays` → usano il modello a blocco
    Giorni ON/OFF. Quelli da planner hanno i giorni per-peptide.
    """
    return any(isinstance(p, dict) and p.get("weekdays") is not None
               for p in (pep_list or []))


def _snap_pep_tuple(pp: dict) -> tuple:
    """Normalizza un peptide dello snapshot a (peptide_id, name, base_dose_mcg).

    Gestisce i due formati di snapshot esistenti:
      - da protocollo: chiavi 'name' / 'target_dose_mcg'
      - da planner:    chiavi 'peptide_name' / 'dose_mcg'
    """
    pid = pp.get("peptide_id") or pp.get("id")
    name = pp.get("name") or pp.get("peptide_name") or "?"
    dose = pp.get("target_dose_mcg")
    if dose is None:
        dose = pp.get("dose_mcg")
    if dose is None:
        dose = 250
    return (pid, name, dose)


def _expand_weekly_schedule(weeks: int, peptides: list, existing: list) -> list:
    """Espande uno schedule completo settimana-per-settimana.

    Usato per la modifica on-the-fly del dosaggio: produce una riga per ogni
    settimana (1..weeks) × peptide, pre-riempita con la dose effettiva.

    Args:
        weeks: numero di settimane del ciclo (cycle_duration_weeks)
        peptides: [(peptide_id, base_dose_mcg), ...] dallo snapshot del protocollo
        existing: ramp_schedule esistente (può essere vuoto)

    Precedenza dose per (settimana, peptide), specchio di Cycle.get_ramp_dose:
        1. dose esplicita in `existing` per quella settimana
        2. se la settimana è oltre l'ultima definita → dose dell'ultima settimana
        3. altrimenti → dose base dal protocollo
    """
    existing = existing or []
    by_week = {}
    max_def_week = 0
    for entry in existing:
        w = entry.get("week", 0)
        max_def_week = max(max_def_week, w)
        for d in entry.get("doses", []):
            by_week[(w, d.get("peptide_id"))] = d.get("dose_mcg")

    schedule = []
    for week in range(1, weeks + 1):
        doses = []
        for pid, base_dose in peptides:
            dose = by_week.get((week, pid))
            if dose is None and max_def_week and week > max_def_week:
                dose = by_week.get((max_def_week, pid))
            if dose is None:
                dose = base_dose
            doses.append({"peptide_id": pid, "dose_mcg": int(round(dose or 0))})
        schedule.append({"week": week, "doses": doses})
    return schedule


# ═════════════════════════════════════════════════════════════════════════
#  RAMP EDITOR WIDGET
# ═════════════════════════════════════════════════════════════════════════


class _RampEditor(QWidget):
    """Editable ramp schedule: week / peptide / dose.

    get_schedule() returns the list of dicts for the backend.
    set_schedule(schedule, peptides) populates from existing data.
    """

    def __init__(self, parent=None, dose_only=False):
        super().__init__(parent)
        # dose_only: edit-dialog mode — peptide read-only, dose via spinbox,
        # niente preset/aggiungi-riga (si modifica solo il dosaggio per settimana).
        self._dose_only = dose_only
        self._peptides = []  # [(id, name, base_dose_mcg), ...]
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        lay.addWidget(_sep("Ramp Schedule"))

        # Preset buttons (nascosti in dose_only mode)
        self._preset_widget = QWidget()
        preset_row = QHBoxLayout(self._preset_widget)
        preset_row.setContentsMargins(0, 0, 0, 0)
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
        lay.addWidget(self._preset_widget)

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
        self._table.setMinimumHeight(120)
        lay.addWidget(self._table, 1)

        # Add / Remove buttons (nascosti in dose_only mode)
        self._btn_widget = QWidget()
        btn_row = QHBoxLayout(self._btn_widget)
        btn_row.setContentsMargins(0, 0, 0, 0)
        add_btn = QPushButton("+ Aggiungi Riga")
        add_btn.clicked.connect(self._add_row_ui)
        btn_row.addWidget(add_btn)
        rm_btn = QPushButton("- Rimuovi Selezionata")
        rm_btn.clicked.connect(self._remove_selected)
        btn_row.addWidget(rm_btn)
        btn_row.addStretch()
        lay.addWidget(self._btn_widget)

        if self._dose_only:
            self._preset_widget.hide()
            self._btn_widget.hide()

    def set_peptides(self, peptides):
        """Set available peptides: list of (id, name, base_dose_mcg)."""
        self._peptides = list(peptides)

    def set_schedule(self, schedule, current_week: int = 0):
        """Populate table from backend schedule format.

        schedule: [{'week': 1, 'doses': [{'peptide_id': X, 'dose_mcg': Y}, ...]}, ...]
        current_week: 1-indexed current week of the cycle. Weeks before it are
            read-only ("past"), the current week is highlighted, later weeks are
            editable ("future"). 0 disables this (no marking, all editable).
        """
        self._table.setRowCount(0)
        if not schedule:
            return
        current_row = -1
        for entry in schedule:
            week = entry.get("week", 1)
            if current_week <= 0:
                state = "future"
            elif week < current_week:
                state = "past"
            elif week == current_week:
                state = "current"
            else:
                state = "future"
            for dose_item in entry.get("doses", []):
                pid = dose_item.get("peptide_id")
                dose = dose_item.get("dose_mcg", 0)
                pname = self._peptide_name(pid)
                row = self._insert_row(week, pname, pid, dose, state=state)
                if state == "current" and current_row < 0:
                    current_row = row
        # Porta in vista la settimana corrente.
        if current_row >= 0:
            self._table.scrollToItem(self._table.item(current_row, 0))

    def get_schedule(self):
        """Return schedule in backend format.

        Reads dose from a QSpinBox (dose_only mode) or a cell item, and the
        peptide id from a QComboBox or, in dose_only mode, the item's UserRole.
        """
        weeks = {}
        for r in range(self._table.rowCount()):
            week_item = self._table.item(r, 0)
            if not week_item:
                continue
            try:
                week = int(week_item.text())
            except (ValueError, TypeError):
                continue

            spin = self._table.cellWidget(r, 2)
            if spin is not None:
                dose = int(spin.value())
            else:
                dose_item = self._table.item(r, 2)
                try:
                    dose = int(float(dose_item.text()))
                except (ValueError, TypeError, AttributeError):
                    dose = 0

            pep_combo = self._table.cellWidget(r, 1)
            if pep_combo is not None:
                pid = pep_combo.currentData()
            else:
                pep_item = self._table.item(r, 1)
                pid = pep_item.data(Qt.UserRole) if pep_item else None
            if pid is None:
                continue

            weeks.setdefault(week, []).append({"peptide_id": pid, "dose_mcg": dose})

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

    def _insert_row(self, week, pname, pid, dose, state="future"):
        """Insert one row. state: 'past' | 'current' | 'future'. Returns row idx."""
        r = self._table.rowCount()
        self._table.insertRow(r)
        week_item = QTableWidgetItem(str(week))
        self._table.setItem(r, 0, week_item)

        editable_dose = state != "past"

        # --- Colonna Peptide ---
        if self._dose_only:
            # Peptide fisso: etichetta in sola lettura, pid salvato nei dati.
            pep_item = QTableWidgetItem(pname)
            pep_item.setFlags(pep_item.flags() & ~Qt.ItemIsEditable)
            pep_item.setData(Qt.UserRole, pid)
            self._table.setItem(r, 1, pep_item)
            combo = None
        else:
            pep_item = None
            combo = QComboBox()
            for p_id, name, _ in self._peptides:
                combo.addItem(name, p_id)
            idx = combo.findData(pid)
            if idx >= 0:
                combo.setCurrentIndex(idx)
            self._table.setCellWidget(r, 1, combo)

        # --- Colonna Dose ---
        if self._dose_only and editable_dose:
            # Spinbox: dose chiaramente modificabile (no doppio-click).
            spin = QSpinBox()
            spin.setRange(0, 100000)
            spin.setSingleStep(50)
            spin.setValue(int(dose))
            self._table.setCellWidget(r, 2, spin)
            dose_item = None
        else:
            spin = None
            dose_item = QTableWidgetItem(str(int(dose)))
            self._table.setItem(r, 2, dose_item)

        # --- Stile per stato ---
        items = [it for it in (week_item, pep_item, dose_item) if it is not None]
        if state == "past":
            # Settimane già trascorse: sola lettura, grigio attenuato.
            for item in items:
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                item.setForeground(QColor("#777777"))
                item.setBackground(QColor("#262626"))
                item.setToolTip("Settimana già trascorsa (sola lettura)")
            if combo is not None:
                combo.setEnabled(False)
        elif state == "current":
            # Settimana corrente: evidenziata in verde.
            hl = QColor("#2f4a34")
            for item in items:
                item.setBackground(hl)
                item.setToolTip("Settimana corrente")
            if combo is not None:
                combo.setStyleSheet("background: #2f4a34;")
            if spin is not None:
                spin.setStyleSheet("background: #2f4a34;")
        # 'future' → aspetto di default, editabile.
        return r

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
            {"key": "fonte",         "label": "Fonte",      "width": 70},
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

    _IN_CORSO = {"active", "planned", "paused"}

    def refresh(self):
        status_filter = self._status_filter.currentData()
        try:
            all_cycles = self.manager.get_cycles(active_only=False)
            if status_filter == "in_corso":
                cycles = [c for c in all_cycles if c.get("status") in self._IN_CORSO]
            elif status_filter:
                cycles = [c for c in all_cycles if c.get("status") == status_filter]
            else:
                cycles = all_cycles
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
            snapshot = _snap_dict(c.get("protocol_snapshot"))
            proto_name = snapshot.get("name") or c.get("protocol_name", "-")

            rows.append({
                "id": c["id"],
                "name": c.get("name", ""),
                "protocol_name": proto_name,
                "fonte": "Piano" if c.get("plan_phase_id") else "",
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
        self.setMinimumHeight(650)
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

        # Peptidi dallo snapshot + giorni di somministrazione (se weekday-based).
        pep_list = _snap_peptides(c.get("protocol_snapshot"))
        self._weekday_based = _snap_weekday_based(pep_list)

        status_opts = [
            ("planned", "Pianificato"),
            ("active", "Attivo"),
            ("paused", "In Pausa"),
            ("completed", "Completato"),
            ("cancelled", "Annullato"),
        ]

        fields = [
            FormField("name", "Nome", "text",
                      value=c.get("name", ""), required=True),
            FormField("description", "Descrizione", "textarea",
                      value=c.get("description", "")),
            FormField("start_date", "Data Inizio", "text",
                      value=str(c.get("start_date", ""))[:10]),
            FormField("planned_end_date", "Data Fine Prev.", "text",
                      value=str(c.get("planned_end_date", "") or "")[:10]),
        ]
        # I campi Giorni ON/OFF valgono solo per i cicli a blocco continuo: per i
        # cicli weekday-based (Lun/Mer/Ven…) lo schedule è nei `weekdays` dello
        # snapshot, quindi li omettiamo e mostriamo un selettore giorni per peptide.
        if not self._weekday_based:
            fields += [
                FormField("days_on", "Giorni ON", "number",
                          value=c.get("days_on", 5), min_val=1, max_val=365),
                FormField("days_off", "Giorni OFF", "number",
                          value=c.get("days_off", 0), min_val=0, max_val=365),
            ]
        fields += [
            FormField("cycle_duration_weeks", "Durata (sett)", "number",
                      value=c.get("cycle_duration_weeks", 8), min_val=1, max_val=104),
            FormField("status", "Stato", "combo",
                      value=c.get("status", "active"), options=status_opts),
        ]
        self._form = FormLayout(fields)
        self._form.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(self._form)

        # Selettori giorni per-peptide (solo cicli weekday-based).
        # Un selettore per peptide: gestisce anche peptidi con giorni diversi
        # (es. uno tutti i giorni, un altro Lun/Mer/Ven).
        self._day_selectors = []      # [(peptide_id, _DaySelector), ...]
        self._orig_weekdays = {}      # {peptide_id: [giorni ordinati]}
        if self._weekday_based:
            hdr = QLabel("Giorni di somministrazione")
            hdr.setStyleSheet("color: #aeaeae; font-weight: bold;")
            layout.addWidget(hdr)
            grid = QGridLayout()
            grid.setHorizontalSpacing(12)
            grid.setVerticalSpacing(4)
            grid.setColumnStretch(1, 1)
            r = 0
            for pp in pep_list:
                if not isinstance(pp, dict):
                    continue
                pid, name, _dose = _snap_pep_tuple(pp)
                wd = pp.get("weekdays")
                days = list(wd) if wd is not None else list(range(7))
                name_lbl = QLabel(name)
                name_lbl.setStyleSheet("color: #e0e0e0;")
                sel = _DaySelector()
                sel.set_days(days)
                grid.addWidget(name_lbl, r, 0)
                grid.addWidget(sel, r, 1)
                self._day_selectors.append((pid, sel))
                self._orig_weekdays[pid] = sorted(days)
                r += 1
            layout.addLayout(grid)

        # Ramp editor (dose_only: peptide fisso, si modifica solo il dosaggio)
        self._ramp = _RampEditor(dose_only=True)

        # Load peptides from protocol snapshot (gestisce formato protocollo e planner)
        pep_tuples = [_snap_pep_tuple(pp) for pp in pep_list]
        self._ramp.set_peptides(pep_tuples)

        # Espandi una riga per ogni settimana del ciclo, pre-riempita con la dose
        # effettiva: così la dose è modificabile on-the-fly anche su cicli a dose
        # fissa (senza ramp_schedule iniziale). Le settimane già trascorse sono
        # bloccate; la corrente e le future sono editabili.
        weeks = int(c.get("cycle_duration_weeks") or 0)
        if weeks > 0 and pep_tuples:
            base_peps = [(pid, base) for pid, _name, base in pep_tuples]
            full = _expand_weekly_schedule(
                weeks, base_peps, c.get("ramp_schedule") or []
            )
            current_week = self._current_week()
            weeks_total = weeks
            hint = QLabel(
                f"Settimana corrente: {current_week} / {weeks_total}.  "
                "🟩 corrente (evidenziata)  ·  ⬜ futura (modificabile)  ·  "
                "▪️ passata (sola lettura).  Modifica le dosi correnti/future."
            )
            hint.setStyleSheet("color: #9e9e9e; font-size: 11px;")
            hint.setWordWrap(True)
            layout.addWidget(hint)
            self._ramp.set_schedule(full, current_week=current_week)
        else:
            self._ramp.set_schedule(c.get("ramp_schedule") or [])

        layout.addWidget(self._ramp, 1)

        btns, submit = _make_buttons(self)
        submit.clicked.connect(self._submit)
        layout.addWidget(btns)

    def _current_week(self) -> int:
        """Settimana corrente del ciclo (1-indexed) per il lock delle passate.

        Restituisce 1 (= nessuna settimana bloccata) per cicli non ancora avviati
        o senza data d'inizio.
        """
        c = self._cycle
        if c.get("status") in ("planned", "cancelled"):
            return 1
        start = str(c.get("start_date", "") or "")[:10]
        try:
            sd = datetime.strptime(start, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return 1
        return max(1, ((date.today() - sd).days // 7) + 1)

    def _submit(self):
        errors = self._form.validate()
        if errors:
            error_dialog(self, "Validazione", "\n".join(errors))
            return

        vals = self._form.get_values()
        ramp = self._ramp.get_schedule()
        c = self._cycle

        # Giorni: se weekday-based, leggi un set per ogni peptide; altrimenti i
        # campi ON/OFF non sono nel form → mantieni i valori esistenti del ciclo.
        snapshot = None
        if self._weekday_based:
            new_map = {}
            for pid, sel in self._day_selectors:
                days = sorted(sel.get_days())
                if not days:
                    error_dialog(self, "Validazione",
                                 "Seleziona almeno un giorno per ogni peptide.")
                    return
                new_map[pid] = days
            if new_map != self._orig_weekdays:
                snapshot = self._snapshot_with_weekdays(new_map)

        kwargs = dict(
            name=vals["name"],
            description=vals["description"],
            start_date=vals["start_date"] or None,
            planned_end_date=vals["planned_end_date"] or None,
            days_on=vals.get("days_on", c.get("days_on")),
            days_off=vals.get("days_off", c.get("days_off", 0)),
            cycle_duration_weeks=vals["cycle_duration_weeks"],
            status=vals["status"],
            ramp_schedule=ramp if ramp else None,
        )
        if snapshot is not None:
            kwargs["protocol_snapshot"] = snapshot

        try:
            self._app.manager.update_cycle(self._cycle_id, **kwargs)
            self._app.show_message("Ciclo aggiornato")
            self.accept()
        except Exception as e:
            error_dialog(self, "Errore", str(e))

    def _snapshot_with_weekdays(self, new_map):
        """Copia lo snapshot applicando i giorni per-peptide da `new_map`.

        new_map: {peptide_id: [giorni]}.
        """
        import copy

        snap = copy.deepcopy(self._cycle.get("protocol_snapshot"))
        for pp in _snap_peptides(snap):
            if not isinstance(pp, dict):
                continue
            pid = pp.get("peptide_id") or pp.get("id")
            if pid in new_map:
                pp["weekdays"] = new_map[pid]
        return snap


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

        snapshot = _snap_dict(c.get("protocol_snapshot"))
        add_row("Protocollo", snapshot.get("name") or c.get("protocol_name", "-"))
        add_row("Stato", _STATUS_LABELS.get(c.get("status", ""), c.get("status", "")))
        add_row("Inizio", str(c.get("start_date", "-"))[:10])
        add_row("Fine Prev.", str(c.get("planned_end_date") or "-")[:10])
        add_row("Descrizione", c.get("description") or "-")
        if c.get("plan_phase_id"):
            add_row("Fonte", f"Da piano (fase #{c['plan_phase_id']})")

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
            snap_peps = _snap_peptides(c.get("protocol_snapshot"))
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
