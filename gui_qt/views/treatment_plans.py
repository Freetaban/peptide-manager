"""Plans tab and dialogs for the Treatment section."""

import json
import math
from datetime import date, timedelta

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QCheckBox,
    QSpinBox,
    QWidget,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QFileDialog,
    QMessageBox,
)
from PySide6.QtCore import Qt, Signal

from .treatment_common import (
    BaseView,
    DataTable,
    confirm_dialog,
    error_dialog,
    FormField,
    FormLayout,
    _DLG_STYLE,
    _STATUS_LABELS,
    _PLAN_STATUS_FILTER,
    _make_buttons,
    _sep,
    _today_str,
)
# Imported here (not at top level) to avoid circular dependency during module loading
def _open_cycle_details(app, cycle_id, parent=None):
    from .treatment_cycles import _CycleDetailsDialog
    _CycleDetailsDialog(app, cycle_id, parent=parent).exec()


# ── Helpers ──────────────────────────────────────────────────────────────

def _parse_calc_params(raw):
    """Parse calculation_params JSON string; return dict or None."""
    if not raw:
        return None
    try:
        return json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        return None


def _build_dose_summary(pep_resources) -> str:
    """Compact static summary: vials needed, injection volume, duration."""
    parts = []
    for res in pep_resources:
        cp = _parse_calc_params(res.get("calculation_params"))
        if res.get("quantity_unit") == "mg":
            mg_needed = float(res.get("quantity_needed") or 0)
        elif cp and cp.get("mg_needed") is not None:
            mg_needed = float(cp["mg_needed"])
        else:
            continue
        if mg_needed <= 0:
            continue
        name = res.get("resource_name", "?")
        mg_vial = float(cp.get("mg_per_vial") or 5.0) if cp else 5.0
        vials = math.ceil(mg_needed / mg_vial)
        dose_mcg = float(cp.get("dose_mcg") or 0) if cp else 0
        daily_freq = int(cp.get("daily_frequency") or 1) if cp else 1
        part = f"{name}: {vials} fiale da {mg_vial:.0f} mg"
        if dose_mcg > 0 and mg_vial > 0:
            ml = float(cp.get("reconstitution_ml") or 2.0) if cp else 2.0
            inj_u = round(dose_mcg / (mg_vial * 1000) * ml * 100, 1)
            dur = math.floor(mg_vial * vials / (dose_mcg / 1000 * daily_freq))
            part += f" · {inj_u} U/dose · {dur} gg"
        parts.append(part)
    return "   |   ".join(parts)


def _build_vial_configurator(pep_resources):
    """Build a widget with per-peptide vial size + reconstitution inputs.

    Shows live: vials needed, injection volume (units), days in fridge.
    Only shown for resources that have dose_mcg in calculation_params.
    """
    frame = QFrame()
    frame.setStyleSheet(
        "QFrame { border: 1px solid #37474f; border-radius: 4px; padding: 6px; }"
    )
    lay = QVBoxLayout(frame)
    lay.setSpacing(6)
    lay.setContentsMargins(8, 8, 8, 8)

    title = QLabel("Configuratore Dosi")
    title.setStyleSheet("font-weight: bold; font-size: 12px; color: #90caf9;")
    lay.addWidget(title)

    grid = QGridLayout()
    grid.setSpacing(6)
    grid.setColumnStretch(0, 2)
    grid.setColumnStretch(3, 3)

    row = 0
    has_any = False
    for res in pep_resources:
        cp = _parse_calc_params(res.get("calculation_params"))

        # mg_needed: preferisci quantity_needed se unit='mg', altrimenti calculation_params
        if res.get("quantity_unit") == "mg":
            mg_needed = float(res.get("quantity_needed") or 0)
        elif cp and cp.get("mg_needed") is not None:
            mg_needed = float(cp["mg_needed"])
        else:
            continue

        dose_mcg = float(cp.get("dose_mcg") or 0) if cp else 0.0
        if mg_needed <= 0 or dose_mcg <= 0:
            continue
        has_any = True

        dose_mcg = float(dose_mcg)
        daily_freq = int(cp.get("daily_frequency") or 1)
        default_mg_vial = float(cp.get("mg_per_vial") or 5.0)

        name_lbl = QLabel(res.get("resource_name", "?"))
        name_lbl.setStyleSheet("color: #e0e0e0;")

        mg_spin = QDoubleSpinBox()
        mg_spin.setRange(1.0, 100.0)
        mg_spin.setSingleStep(1.0)
        mg_spin.setDecimals(0)
        mg_spin.setSuffix(" mg/fiala")
        mg_spin.setValue(default_mg_vial)
        mg_spin.setFixedWidth(110)

        ml_spin = QDoubleSpinBox()
        ml_spin.setRange(0.5, 10.0)
        ml_spin.setSingleStep(0.5)
        ml_spin.setDecimals(1)
        ml_spin.setSuffix(" ml H₂O")
        ml_spin.setValue(2.0)
        ml_spin.setFixedWidth(90)

        result_lbl = QLabel()
        result_lbl.setStyleSheet("color: #a5d6a7; font-size: 11px;")

        def _recalc(
            _=None,
            _mg_needed=mg_needed,
            _dose_mcg=dose_mcg,
            _daily_freq=daily_freq,
            _mg_spin=mg_spin,
            _ml_spin=ml_spin,
            _lbl=result_lbl,
        ):
            mg_vial = _mg_spin.value()
            recon_ml = _ml_spin.value()
            if mg_vial <= 0 or recon_ml <= 0:
                _lbl.setText("—")
                return
            vials = math.ceil(_mg_needed / mg_vial)
            conc_mcg_ml = mg_vial * 1000.0 / recon_ml
            vol_ml = _dose_mcg / conc_mcg_ml
            vol_units = vol_ml * 100.0
            doses_per_vial = mg_vial * 1000.0 / _dose_mcg
            days_per_vial = doses_per_vial / _daily_freq
            _lbl.setText(
                f"{vials} fiale  •  Vol. inj: {vol_units:.1f} U  •  Durata: {days_per_vial:.0f} gg"
            )

        _recalc()
        mg_spin.valueChanged.connect(_recalc)
        ml_spin.valueChanged.connect(_recalc)

        grid.addWidget(name_lbl, row, 0)
        grid.addWidget(mg_spin, row, 1)
        grid.addWidget(ml_spin, row, 2)
        grid.addWidget(result_lbl, row, 3)
        row += 1

    if not has_any:
        hint = QLabel(
            "Clicca «Ricalcola Risorse» per abilitare il configuratore."
        )
        hint.setStyleSheet("color: #757575; font-size: 11px; font-style: italic;")
        lay.addWidget(hint)
    else:
        lay.addLayout(grid)

    return frame


def _resolve_peptide_names(phases_config, all_peptides):
    """Resolve peptide_name → peptide_id using name + alias matching (case-insensitive).

    Returns (resolved_phases, unresolved_names).
    Mutates nothing — returns new list.
    """
    # Build lookup: lowercase name/alias → (id, canonical_name)
    lookup = {}
    for p in all_peptides:
        pid = p["id"]
        canonical = p.get("name", "")
        # Register canonical name
        name = canonical.strip().lower()
        if name:
            lookup[name] = (pid, canonical)
        # Register all aliases
        for alias in p.get("aliases", []):
            alias_key = alias.strip().lower()
            if alias_key and alias_key not in lookup:
                lookup[alias_key] = (pid, canonical)

    resolved = []
    unresolved = set()
    for phase in phases_config:
        new_phase = dict(phase)
        new_peptides = []
        for pep in phase.get("peptides", []):
            new_pep = dict(pep)
            # Already has id? Keep it.
            if new_pep.get("peptide_id"):
                new_peptides.append(new_pep)
                continue
            # Resolve by name
            pname = (new_pep.get("peptide_name") or "").strip().lower()
            match = lookup.get(pname)
            if match:
                new_pep["peptide_id"] = match[0]
                new_pep["peptide_name"] = match[1]
                new_peptides.append(new_pep)
            else:
                unresolved.add(pep.get("peptide_name", pname))
        new_phase["peptides"] = new_peptides
        resolved.append(new_phase)
    return resolved, unresolved


def _status_badge(status_key):
    """Return a QLabel styled as a status badge."""
    text = _STATUS_LABELS.get(status_key, status_key or "?")
    colors = {
        "planned": ("#424242", "#e0e0e0"),
        "active": ("#1b5e20", "#a5d6a7"),
        "paused": ("#e65100", "#ffcc80"),
        "completed": ("#1a237e", "#90caf9"),
        "cancelled": ("#b71c1c", "#ef9a9a"),
        "abandoned": ("#b71c1c", "#ef9a9a"),
        "skipped": ("#616161", "#bdbdbd"),
    }
    bg, fg = colors.get(status_key, ("#424242", "#e0e0e0"))
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"background: {bg}; color: {fg}; padding: 2px 8px;"
        " border-radius: 3px; font-weight: bold; font-size: 11px;"
    )
    lbl.setFixedHeight(22)
    return lbl


# ═════════════════════════════════════════════════════════════════════════
#  EXPORT CALENDAR DIALOG
# ═════════════════════════════════════════════════════════════════════════


class _ExportCalendarDialog(QDialog):
    """Date-range picker + export buttons for HTML and ICS calendar."""

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self._app = app
        self.setWindowTitle("Esporta Piano Vacanze")
        self.setMinimumWidth(420)
        self.setStyleSheet(_DLG_STYLE)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        info = QLabel(
            "Genera un calendario con le somministrazioni giornaliere per il periodo scelto.\n"
            "• HTML — apri nel browser e stampa come PDF\n"
            "• ICS — importa in Google Calendar / Outlook / iPhone"
        )
        info.setStyleSheet("color: #aeaeae; font-size: 11px;")
        info.setWordWrap(True)
        layout.addWidget(info)

        layout.addWidget(_sep("Periodo"))

        grid = QGridLayout()
        grid.setSpacing(6)
        grid.setColumnStretch(1, 1)

        today = date.today()
        default_end = today + timedelta(days=60)

        grid.addWidget(QLabel("Dal:"), 0, 0)
        self._start = QLineEdit(today.isoformat())
        self._start.setPlaceholderText("YYYY-MM-DD")
        grid.addWidget(self._start, 0, 1)

        grid.addWidget(QLabel("Al:"), 1, 0)
        self._end = QLineEdit(default_end.isoformat())
        self._end.setPlaceholderText("YYYY-MM-DD")
        grid.addWidget(self._end, 1, 1)

        layout.addLayout(grid)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        html_btn = QPushButton("Salva HTML")
        html_btn.setStyleSheet(
            "background: #1565c0; color: white; padding: 8px 18px;"
            " border-radius: 4px; font-weight: bold;"
        )
        html_btn.clicked.connect(self._save_html)
        btn_row.addWidget(html_btn)

        ics_btn = QPushButton("Salva ICS")
        ics_btn.setStyleSheet(
            "background: #2e7d32; color: white; padding: 8px 18px;"
            " border-radius: 4px; font-weight: bold;"
        )
        ics_btn.clicked.connect(self._save_ics)
        btn_row.addWidget(ics_btn)

        close_btn = QPushButton("Chiudi")
        close_btn.setStyleSheet(
            "background: #424242; color: #e0e0e0; padding: 8px 14px;"
            " border-radius: 4px;"
        )
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)

        layout.addLayout(btn_row)

    def _parse_dates(self):
        """Validate and return (start, end) date objects, or None on error."""
        try:
            start = date.fromisoformat(self._start.text().strip())
            end = date.fromisoformat(self._end.text().strip())
        except ValueError:
            QMessageBox.warning(self, "Errore", "Formato data non valido. Usa YYYY-MM-DD.")
            return None
        if end < start:
            QMessageBox.warning(self, "Errore", "La data di fine deve essere successiva all'inizio.")
            return None
        if (end - start).days > 366:
            QMessageBox.warning(self, "Errore", "Periodo massimo: 366 giorni.")
            return None
        return start, end

    def _build_schedule(self, start, end):
        from peptide_manager.export import build_schedule
        try:
            return build_schedule(self._app.manager, start, end)
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Errore generazione schedule:\n{e}")
            return None

    def _save_html(self):
        dates = self._parse_dates()
        if not dates:
            return
        start, end = dates
        schedule = self._build_schedule(start, end)
        if schedule is None:
            return

        from peptide_manager.export import build_html
        html = build_html(schedule, start, end)

        default_name = f"piano_peptidi_{start}_{end}.html"
        path, _ = QFileDialog.getSaveFileName(
            self, "Salva HTML", default_name, "HTML (*.html)"
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
            self._app.show_message(f"HTML salvato: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Impossibile salvare:\n{e}")

    def _save_ics(self):
        dates = self._parse_dates()
        if not dates:
            return
        start, end = dates
        schedule = self._build_schedule(start, end)
        if schedule is None:
            return

        from peptide_manager.export import build_ics
        ics = build_ics(schedule, start, end)

        default_name = f"piano_peptidi_{start}_{end}.ics"
        path, _ = QFileDialog.getSaveFileName(
            self, "Salva ICS", default_name, "iCalendar (*.ics)"
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(ics)
            self._app.show_message(f"ICS salvato: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Impossibile salvare:\n{e}")


# ═════════════════════════════════════════════════════════════════════════
#  PLANS TAB
# ═════════════════════════════════════════════════════════════════════════


class PlansTab(BaseView):
    """Treatment plans list with status filter and CRUD."""

    def __init__(self, app, parent=None):
        super().__init__(app, parent)
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        lay = self.layout()

        # Toolbar
        toolbar = QHBoxLayout()
        title = QLabel("Piani di Trattamento")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        toolbar.addWidget(title)
        toolbar.addStretch()

        self._status_filter = QComboBox()
        for data, label in _PLAN_STATUS_FILTER:
            self._status_filter.addItem(label, data)
        self._status_filter.currentIndexChanged.connect(lambda: self.refresh())
        toolbar.addWidget(self._status_filter)

        export_btn = QPushButton("Esporta Calendario")
        export_btn.setToolTip("Genera HTML o ICS con il programma giornaliero per le vacanze")
        export_btn.clicked.connect(self._on_export)
        toolbar.addWidget(export_btn)

        add_btn = QPushButton("Nuovo Piano")
        add_btn.clicked.connect(self._on_add)
        toolbar.addWidget(add_btn)
        lay.addLayout(toolbar)

        # Table
        self._table = DataTable([
            {"key": "id",               "label": "ID",         "width": 50},
            {"key": "name",             "label": "Nome",       "stretch": True},
            {"key": "status_display",   "label": "Stato",      "width": 100},
            {"key": "start_date",       "label": "Inizio",     "width": 100},
            {"key": "planned_end_date", "label": "Fine Prev.", "width": 100},
            {"key": "phases_count",     "label": "Fasi",       "width": 60},
        ])
        self._table.set_context_menu([
            {"label": "Dettagli",       "callback": self._on_details},
            {"label": "Modifica",       "callback": self._on_edit,
             "enabled_when": lambda: self.edit_mode},
            {"label": "Elimina",        "callback": self._on_delete,
             "enabled_when": lambda: self.edit_mode},
            # Status actions
            {"label": "Attiva",         "callback": self._on_activate,
             "visible_when": lambda: self._selected_status() == "planned"},
            {"label": "Prossima Fase",  "callback": self._on_next_phase,
             "visible_when": lambda: self._selected_status() == "active"},
            {"label": "Pausa",          "callback": self._on_pause,
             "visible_when": lambda: self._selected_status() == "active"},
            {"label": "Completa",       "callback": self._on_complete,
             "visible_when": lambda: self._selected_status() == "active"},
            {"label": "Abbandona",      "callback": self._on_abandon,
             "visible_when": lambda: self._selected_status() == "active"},
            {"label": "Riprendi",       "callback": self._on_resume,
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
            plans = self.manager.get_treatment_plans(status=status_filter)
        except Exception as e:
            error_dialog(self, "Errore", str(e))
            return

        rows = []
        for p in plans:
            # Use total_phases from plan dict if available (multi-phase plans)
            phases_count = p.get("total_phases") or 0
            if not phases_count:
                # Fallback for legacy plans without total_phases
                try:
                    full = self.manager.get_treatment_plan(p.get("id"))
                    if full and "phases" in full:
                        phases_count = len(full["phases"])
                except Exception:
                    pass

            rows.append({
                "id": p.get("id"),
                "name": p.get("name", ""),
                "status_display": _STATUS_LABELS.get(
                    p.get("status", ""), p.get("status", "")),
                "start_date": str(p.get("start_date", "-"))[:10],
                "planned_end_date": str(p.get("planned_end_date") or "-")[:10],
                "phases_count": phases_count,
                "_status": p.get("status"),
            })
        self._table.load_data(rows)

    # ── Actions ──────────────────────────────────────────────────────────

    def _on_export(self):
        _ExportCalendarDialog(self.app, parent=self).exec()

    def _on_add(self):
        dlg = _PlanAddDialog(self.app, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh()

    def _on_details(self, row):
        dlg = _PlanDetailsDialog(self.app, row["id"], parent=self)
        dlg.exec()
        self.refresh()  # resources or phase state may have changed

    def _on_edit(self, row):
        dlg = _PlanEditDialog(self.app, row["id"], parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh()

    def _on_delete(self, row):
        if not confirm_dialog(
            self, "Elimina Piano",
            f"Eliminare il piano #{row['id']} ({row['name']})?",
        ):
            return
        try:
            self.manager.delete_treatment_plan(row["id"])
            self.app.show_message("Piano eliminato")
            self.refresh()
        except Exception as e:
            error_dialog(self, "Errore", str(e))

    def _on_activate(self, row):
        self._update_plan_status(row["id"], "resume", "Piano attivato")

    def _on_next_phase(self, row):
        try:
            result = self.manager.transition_to_next_phase(row["id"])
            if result.get("plan_continues", True):
                new_ph = result.get("activated_phase") or {}
                msg = f"Fase {new_ph.get('phase_number', '?')} attivata"
            else:
                msg = "Piano completato"
            self.app.show_message(msg)
            self.refresh()
        except Exception as e:
            error_dialog(self, "Errore", str(e))

    def _on_pause(self, row):
        self._update_plan_status(row["id"], "pause", "Piano in pausa")

    def _on_complete(self, row):
        self._update_plan_status(row["id"], "complete", "Piano completato")

    def _on_abandon(self, row):
        if not confirm_dialog(
            self, "Abbandona Piano",
            f"Abbandonare il piano #{row['id']}? Questa azione non e' reversibile.",
        ):
            return
        self._update_plan_status(row["id"], "abandon", "Piano abbandonato")

    def _on_resume(self, row):
        self._update_plan_status(row["id"], "resume", "Piano ripreso")

    def _update_plan_status(self, plan_id, action, msg):
        try:
            if action == "pause":
                self.manager.pause_treatment_plan(plan_id)
            elif action == "resume":
                self.manager.resume_treatment_plan(plan_id)
            elif action == "complete":
                self.manager.complete_treatment_plan(plan_id)
            elif action == "abandon":
                self.manager.abandon_treatment_plan(plan_id)
            self.app.show_message(msg)
            self.refresh()
        except Exception as e:
            error_dialog(self, "Errore", str(e))


# ═════════════════════════════════════════════════════════════════════════
#  PHASE BUILDER — Manual phase definition for plan creation
# ═════════════════════════════════════════════════════════════════════════


class _DaySelector(QWidget):
    """7 toggle buttons for day-of-week selection (0=Mon … 6=Sun). Default: all selected."""

    _LABELS = ["Lu", "Ma", "Me", "Gi", "Ve", "Sa", "Do"]
    _BTN_STYLE = (
        "QPushButton { background: #2d2d2d; color: #757575; border: 1px solid #424242;"
        " border-radius: 3px; font-size: 10px; font-weight: bold; }"
        "QPushButton:checked { background: #1565c0; color: #90caf9; border-color: #1976d2; }"
        "QPushButton:hover:!checked { background: #37474f; color: #aeaeae; }"
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        self._btns = []
        for label in self._LABELS:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setChecked(True)
            btn.setFixedSize(26, 24)
            btn.setStyleSheet(self._BTN_STYLE)
            self._btns.append(btn)
            lay.addWidget(btn)

    def get_days(self):
        return [i for i, btn in enumerate(self._btns) if btn.isChecked()]

    def set_days(self, days):
        day_set = set(days)
        for i, btn in enumerate(self._btns):
            btn.setChecked(i in day_set)


class _PeptideRow(QWidget):
    """One peptide entry in a phase: peptide · dose · freq · day selector · remove."""

    remove_requested = Signal(object)

    def __init__(self, all_peptides, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)

        self._combo = QComboBox()
        for p in all_peptides:
            self._combo.addItem(p.get("name", "?"), p.get("id"))
        lay.addWidget(self._combo, 2)

        def _lbl(text):
            l = QLabel(text)
            l.setStyleSheet("color: #aeaeae;")
            return l

        lay.addWidget(_lbl("Dose:"))
        self._dose = QSpinBox()
        self._dose.setRange(1, 10000)
        self._dose.setValue(250)
        self._dose.setSuffix(" mcg")
        self._dose.setFixedWidth(100)
        lay.addWidget(self._dose)

        lay.addWidget(_lbl("Freq:"))
        self._freq = QSpinBox()
        self._freq.setRange(1, 4)
        self._freq.setValue(1)
        self._freq.setSuffix("×/g")
        self._freq.setFixedWidth(80)
        lay.addWidget(self._freq)

        self._days = _DaySelector(self)
        lay.addWidget(self._days)

        rm = QPushButton("✕")
        rm.setFixedWidth(26)
        rm.setStyleSheet(
            "QPushButton { background: #424242; color: #aeaeae; border: none;"
            " border-radius: 3px; font-weight: bold; }"
            "QPushButton:hover { background: #b71c1c; color: white; }"
        )
        rm.clicked.connect(lambda: self.remove_requested.emit(self))
        lay.addWidget(rm)

    def get_config(self):
        return {
            "peptide_id": self._combo.currentData(),
            "peptide_name": self._combo.currentText(),
            "dose_mcg": self._dose.value(),
            "daily_frequency": self._freq.value(),
            "weekdays": self._days.get_days(),
        }


class _PhaseCard(QFrame):
    """Editable card for a single treatment phase."""

    remove_requested = Signal(object)

    def __init__(self, number, all_peptides, existing=None, parent=None):
        super().__init__(parent)
        self._number = number
        self._all_peptides = all_peptides
        self._pep_rows = []
        self.setStyleSheet(
            "QFrame { border: 1px solid #37474f; border-radius: 4px; }"
            "QLabel { border: none; }"
            "QCheckBox { border: none; color: #aeaeae; }"
        )
        lay = QVBoxLayout(self)
        lay.setSpacing(4)
        lay.setContentsMargins(8, 6, 8, 6)

        # Header row: number · name · duration · frequency · 5/2 · remove
        header = QHBoxLayout()

        self._num_lbl = QLabel(f"Fase {number}")
        self._num_lbl.setStyleSheet("font-weight: bold; color: #90caf9; min-width: 52px;")
        header.addWidget(self._num_lbl)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Nome (es. Ramp up, Mantenimento...)")
        self._name_edit.setStyleSheet(
            "background: #2d2d2d; border: 1px solid #424242;"
            " border-radius: 3px; padding: 4px 8px; color: #e0e0e0;"
        )
        header.addWidget(self._name_edit, 3)

        dur_lbl = QLabel("Durata:")
        dur_lbl.setStyleSheet("color: #aeaeae; padding-left: 6px;")
        header.addWidget(dur_lbl)
        self._dur_spin = QSpinBox()
        self._dur_spin.setRange(1, 52)
        self._dur_spin.setValue(8)
        self._dur_spin.setSuffix(" sett")
        self._dur_spin.setFixedWidth(100)
        header.addWidget(self._dur_spin)

        rm_btn = QPushButton("✕")
        rm_btn.setFixedWidth(26)
        rm_btn.setToolTip("Rimuovi fase")
        rm_btn.setStyleSheet(
            "QPushButton { background: #424242; color: #aeaeae; border: none;"
            " border-radius: 3px; font-weight: bold; }"
            "QPushButton:hover { background: #b71c1c; color: white; }"
        )
        rm_btn.clicked.connect(lambda: self.remove_requested.emit(self))
        header.addWidget(rm_btn)
        lay.addLayout(header)

        # Peptide rows
        self._pep_lay = QVBoxLayout()
        self._pep_lay.setSpacing(3)
        self._pep_lay.setContentsMargins(0, 2, 0, 2)
        lay.addLayout(self._pep_lay)

        add_pep_btn = QPushButton("+ Peptide")
        add_pep_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #90caf9;"
            " border: 1px solid #37474f; border-radius: 3px;"
            " padding: 2px 10px; font-size: 11px; }"
            "QPushButton:hover { background: #1e3a5f; }"
        )
        add_pep_btn.setFixedWidth(110)
        add_pep_btn.clicked.connect(self._add_peptide)
        lay.addWidget(add_pep_btn)

        # Pre-populate from existing phase data
        if existing:
            import json
            self._name_edit.setText(existing.get("phase_name", ""))
            self._dur_spin.setValue(int(existing.get("duration_weeks", 8)))
            peps = existing.get("peptides", [])
            if isinstance(peps, str):
                try:
                    peps = json.loads(peps)
                except Exception:
                    peps = []
            for pep in peps:
                self._add_peptide_with_data(pep)

    def set_number(self, n):
        self._number = n
        self._num_lbl.setText(f"Fase {n}")

    def _add_peptide(self):
        row = _PeptideRow(self._all_peptides, self)
        row.remove_requested.connect(self._remove_peptide)
        self._pep_rows.append(row)
        self._pep_lay.addWidget(row)

    def _add_peptide_with_data(self, pep_data):
        row = _PeptideRow(self._all_peptides, self)
        row.remove_requested.connect(self._remove_peptide)
        pid = pep_data.get("peptide_id")
        if pid is not None:
            idx = row._combo.findData(pid)
            if idx >= 0:
                row._combo.setCurrentIndex(idx)
        row._dose.setValue(int(pep_data.get("dose_mcg", 250)))
        row._freq.setValue(int(pep_data.get("daily_frequency", 1)))
        row._days.set_days(pep_data.get("weekdays", list(range(7))))
        self._pep_rows.append(row)
        self._pep_lay.addWidget(row)

    def _remove_peptide(self, row):
        self._pep_rows.remove(row)
        self._pep_lay.removeWidget(row)
        row.deleteLater()

    def get_config(self):
        name = self._name_edit.text().strip()
        peptides = [r.get_config() for r in self._pep_rows]
        max_freq = max((p.get("daily_frequency", 1) for p in peptides), default=1)
        return {
            "phase_number": self._number,
            "phase_name": name or f"Fase {self._number}",
            "duration_weeks": self._dur_spin.value(),
            "daily_frequency": max_freq,
            "five_two_protocol": False,
            "peptides": peptides,
        }


class _PhaseBuilder(QWidget):
    """Dynamic list of _PhaseCard widgets."""

    def __init__(self, all_peptides, parent=None):
        super().__init__(parent)
        self._all_peptides = all_peptides
        self._cards = []

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        self._cards_lay = QVBoxLayout()
        self._cards_lay.setSpacing(6)
        lay.addLayout(self._cards_lay)

        add_btn = QPushButton("+ Aggiungi Fase")
        add_btn.setStyleSheet(
            "QPushButton { background: #1b5e20; color: #a5d6a7;"
            " border: none; border-radius: 4px; padding: 6px 16px; font-weight: bold; }"
            "QPushButton:hover { background: #2e7d32; }"
        )
        add_btn.setFixedWidth(160)
        add_btn.clicked.connect(self._add_phase)
        lay.addWidget(add_btn)
        lay.addStretch()

    def _add_phase(self):
        card = _PhaseCard(len(self._cards) + 1, self._all_peptides, parent=self)
        card.remove_requested.connect(self._remove_phase)
        self._cards.append(card)
        self._cards_lay.addWidget(card)

    def _remove_phase(self, card):
        self._cards.remove(card)
        self._cards_lay.removeWidget(card)
        card.deleteLater()
        for i, c in enumerate(self._cards):
            c.set_number(i + 1)

    def load_existing(self, phases):
        """Pre-populate builder from existing plan phases (list of dicts from backend)."""
        import json
        for ph in sorted(phases, key=lambda x: x.get("phase_number", 0)):
            peps = ph.get("peptides_config", "[]")
            if isinstance(peps, str):
                try:
                    peps = json.loads(peps)
                except Exception:
                    peps = []
            existing = {
                "phase_name": ph.get("phase_name", ""),
                "duration_weeks": ph.get("duration_weeks", 8),
                "daily_frequency": ph.get("daily_frequency", 1),
                "five_two_protocol": bool(ph.get("five_two_protocol", False)),
                "peptides": peps,
            }
            card = _PhaseCard(len(self._cards) + 1, self._all_peptides, existing=existing, parent=self)
            card.remove_requested.connect(self._remove_phase)
            self._cards.append(card)
            self._cards_lay.addWidget(card)

    def get_phases_config(self):
        return [c.get_config() for c in self._cards]


# ═════════════════════════════════════════════════════════════════════════
#  PLAN ADD DIALOG — Template → Multi-Phase Plan
# ═════════════════════════════════════════════════════════════════════════


class _PlanAddDialog(QDialog):
    """Add a new treatment plan, optionally from a template with phase preview."""

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self._app = app
        self._template_id = None
        self._phases_config = None  # resolved phases from template
        self._unresolved = set()
        self.setWindowTitle("Nuovo Piano di Trattamento")
        self.setMinimumWidth(700)
        self.setMinimumHeight(680)
        self.setStyleSheet(_DLG_STYLE)
        self._load_data()
        self._build_ui()

    def _load_data(self):
        """Fetch templates and peptide list."""
        self._templates = []
        self._templates_phases = {}  # tid → phases_config JSON
        try:
            cur = self._app.manager.conn.cursor()
            cur.execute("""
                SELECT id, name, total_duration_weeks, notes, phases_config
                FROM treatment_plan_templates
                WHERE is_active = 1
                ORDER BY category, name
            """)
            for tid, tname, tweeks, tnotes, tconfig in cur.fetchall():
                self._templates.append((tid, tname, tweeks, tnotes))
                self._templates_phases[tid] = tconfig
        except Exception:
            pass

        try:
            self._all_peptides = self._app.manager.get_peptides() or []
        except Exception:
            self._all_peptides = []

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Template selector (optional)
        if self._templates:
            layout.addWidget(_sep("Da Template (opzionale)"))
            tpl_row = QHBoxLayout()
            self._tpl_combo = QComboBox()
            self._tpl_combo.addItem("— nessun template —", None)
            for tid, tname, tweeks, tnotes in self._templates:
                self._tpl_combo.addItem(tname, (tid, tweeks, tnotes))
            self._tpl_combo.currentIndexChanged.connect(self._on_template_changed)
            tpl_row.addWidget(self._tpl_combo, 1)
            layout.addLayout(tpl_row)
        else:
            self._tpl_combo = None

        # Basic plan info
        self._form = FormLayout([
            FormField("name", "Nome", "text", required=True),
            FormField("start_date", "Data Inizio", "text",
                      value=_today_str(), required=True),
            FormField("planned_end_date", "Data Fine Prev.", "text"),
            FormField("description", "Descrizione", "textarea"),
            FormField("reason", "Motivazione", "textarea"),
            FormField("notes", "Note", "textarea"),
        ])
        layout.addWidget(self._form)

        # ── Manual phase builder (visible by default, hidden when template is chosen)
        self._sep_builder = _sep("Fasi del Piano")
        layout.addWidget(self._sep_builder)

        self._phase_builder = _PhaseBuilder(self._all_peptides, self)
        self._builder_scroll = QScrollArea()
        self._builder_scroll.setWidgetResizable(True)
        self._builder_scroll.setStyleSheet("QScrollArea { border: none; }")
        self._builder_scroll.setWidget(self._phase_builder)
        self._builder_scroll.setMinimumHeight(200)
        layout.addWidget(self._builder_scroll, 1)

        # ── Template preview (hidden by default, shown when template is chosen)
        self._preview_container = QWidget()
        self._preview_layout = QVBoxLayout(self._preview_container)
        self._preview_layout.setContentsMargins(0, 0, 0, 0)
        self._preview_layout.setSpacing(4)
        self._preview_container.setVisible(False)
        layout.addWidget(self._preview_container, 1)

        # Buttons
        btns, submit = _make_buttons(self, submit_label="Crea Piano")
        submit.clicked.connect(self._submit)
        layout.addWidget(btns)

    def _on_template_changed(self, idx):
        data = self._tpl_combo.itemData(idx)
        self._phases_config = None
        self._unresolved = set()

        if data is None:
            self._template_id = None
            self._preview_container.setVisible(False)
            self._sep_builder.setVisible(True)
            self._builder_scroll.setVisible(True)
            return

        # Template selected: hide manual builder, show read-only preview
        self._sep_builder.setVisible(False)
        self._builder_scroll.setVisible(False)

        tid, tweeks, tnotes = data
        self._template_id = tid

        # Pre-fill form fields
        start_str = self._form.get_values().get("start_date") or _today_str()
        end_str = ""
        if tweeks:
            try:
                start = date.fromisoformat(start_str)
                end_str = (start + timedelta(weeks=int(tweeks))).isoformat()
            except (ValueError, TypeError):
                pass

        tname = self._tpl_combo.currentText()
        self._form.set_values({
            "name": tname,
            "planned_end_date": end_str,
            "notes": tnotes or "",
        })

        # Parse phases_config from template and resolve peptide names
        raw_config = self._templates_phases.get(tid, "[]")
        try:
            phases_raw = json.loads(raw_config) or []
        except (json.JSONDecodeError, TypeError):
            phases_raw = []

        if phases_raw:
            self._phases_config, self._unresolved = _resolve_peptide_names(
                phases_raw, self._all_peptides
            )
            self._build_preview()
        else:
            self._preview_container.setVisible(False)

    def _build_preview(self):
        """Build the phase preview widgets."""
        # Clear existing
        while self._preview_layout.count():
            item = self._preview_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        self._preview_layout.addWidget(_sep("Anteprima Fasi"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        container = QWidget()
        c_lay = QVBoxLayout(container)
        c_lay.setSpacing(6)
        c_lay.setContentsMargins(0, 0, 4, 0)

        for ph in (self._phases_config or []):
            ph_num = ph.get("phase_number", "?")
            ph_name = ph.get("phase_name", f"Fase {ph_num}")
            dur = ph.get("duration_weeks", "?")
            freq = ph.get("daily_frequency", 1)
            five_two = " [5/2]" if ph.get("five_two_protocol") else ""

            header = QLabel(f"{ph_num}. {ph_name} ({dur} sett, {freq}×/g{five_two})")
            header.setStyleSheet(
                "color: #e0e0e0; font-weight: bold; padding: 2px 0;"
            )
            c_lay.addWidget(header)

            for pep in ph.get("peptides", []):
                pname = pep.get("peptide_name", "?")
                dose = pep.get("dose_mcg", 0)
                resolved = pep.get("peptide_id") is not None
                icon = "\u2713" if resolved else "\u2717"
                color = "#a5d6a7" if resolved else "#ef9a9a"
                pep_lbl = QLabel(f"    {pname}: {dose} mcg [{icon}]")
                pep_lbl.setStyleSheet(f"color: {color};")
                c_lay.addWidget(pep_lbl)

        c_lay.addStretch()
        scroll.setWidget(container)
        self._preview_layout.addWidget(scroll)

        # Warning for unresolved peptides
        if self._unresolved:
            warn = QLabel(
                f"\u26a0 Peptidi non trovati: {', '.join(sorted(self._unresolved))}"
                " (ignorati nel calcolo risorse)"
            )
            warn.setStyleSheet("color: #ffb74d; font-style: italic; padding: 4px 0;")
            warn.setWordWrap(True)
            self._preview_layout.addWidget(warn)

        self._preview_container.setVisible(True)

    def _submit(self):
        errors = self._form.validate()
        if errors:
            error_dialog(self, "Validazione", "\n".join(errors))
            return

        vals = self._form.get_values()

        # Phases come from template (resolved) or from the manual builder
        phases_config = self._phases_config or self._phase_builder.get_phases_config() or None

        if phases_config:
            try:
                result = self._app.manager.create_treatment_plan(
                    name=vals["name"],
                    start_date=vals["start_date"],
                    phases_config=phases_config,
                    description=vals["description"],
                    calculate_resources=True,
                )
                plan_id = result.get("plan_id")
                reason = vals.get("reason")
                notes = vals.get("notes")
                if (reason or notes) and plan_id:
                    try:
                        self._app.manager.update_treatment_plan(
                            plan_id,
                            reason=reason,
                            notes=notes,
                        )
                    except Exception:
                        pass  # non-critical
                self._app.show_message("Piano creato con risorse calcolate")
                self.accept()
            except Exception as e:
                error_dialog(self, "Errore", str(e))
            return

        # No phases defined → create empty plan (shell for manual cycle linking)
        try:
            self._app.manager.add_treatment_plan(
                name=vals["name"],
                start_date=vals["start_date"],
                planned_end_date=vals["planned_end_date"] or None,
                description=vals["description"],
                reason=vals["reason"],
                notes=vals["notes"],
                protocol_template_id=self._template_id,
            )
            self._app.show_message("Piano creato")
            self.accept()
        except Exception as e:
            error_dialog(self, "Errore", str(e))


# ═════════════════════════════════════════════════════════════════════════
#  PLAN EDIT DIALOG
# ═════════════════════════════════════════════════════════════════════════


class _PlanEditDialog(QDialog):
    """Edit an existing treatment plan."""

    def __init__(self, app, plan_id, parent=None):
        super().__init__(parent)
        self._app = app
        self._plan_id = plan_id
        self.setWindowTitle(f"Modifica Piano #{plan_id}")
        self.setMinimumWidth(700)
        self.setMinimumHeight(700)
        self.setStyleSheet(_DLG_STYLE)

        try:
            self._plan = app.manager.get_treatment_plan_basic(plan_id)
            self._full = app.manager.get_treatment_plan(plan_id) or {}
        except Exception as e:
            error_dialog(self, "Errore", str(e))
            self.reject()
            return

        if not self._plan:
            error_dialog(self, "Errore", "Piano non trovato")
            self.reject()
            return

        try:
            self._all_peptides = app.manager.get_peptides() or []
        except Exception:
            self._all_peptides = []

        self._build_ui()

    def _build_ui(self):
        p = self._plan
        phases = self._full.get("phases", [])
        locked = any(ph.get("status") in ("active", "completed") for ph in phases)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        status_opts = [
            ("planned", "Pianificato"),
            ("active", "Attivo"),
            ("paused", "In Pausa"),
            ("completed", "Completato"),
            ("abandoned", "Abbandonato"),
        ]

        self._form = FormLayout([
            FormField("name", "Nome", "text",
                      value=p.get("name", ""), required=True),
            FormField("start_date", "Data Inizio", "text",
                      value=str(p.get("start_date", ""))[:10], required=True),
            FormField("planned_end_date", "Data Fine Prev.", "text",
                      value=str(p.get("planned_end_date") or "")[:10]),
            FormField("status", "Stato", "combo",
                      value=p.get("status", "active"), options=status_opts),
            FormField("description", "Descrizione", "textarea",
                      value=p.get("description", "")),
            FormField("reason", "Motivazione", "textarea",
                      value=p.get("reason", "")),
            FormField("notes", "Note", "textarea",
                      value=p.get("notes", "")),
        ])
        layout.addWidget(self._form)

        # ── Phase builder ──────────────────────────────────────────────────
        layout.addWidget(_sep("Fasi del Piano"))

        if locked:
            info = QLabel(
                "ℹ  Alcune fasi sono già attive o completate — modifica delle fasi non disponibile."
            )
            info.setStyleSheet("color: #ffb74d; font-style: italic; padding: 4px 0;")
            info.setWordWrap(True)
            layout.addWidget(info)
            self._phase_builder = None
        else:
            self._phase_builder = _PhaseBuilder(self._all_peptides, self)
            if phases:
                self._phase_builder.load_existing(phases)
            builder_scroll = QScrollArea()
            builder_scroll.setWidgetResizable(True)
            builder_scroll.setStyleSheet("QScrollArea { border: none; }")
            builder_scroll.setWidget(self._phase_builder)
            builder_scroll.setMinimumHeight(200)
            layout.addWidget(builder_scroll, 1)

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
            self._app.manager.update_treatment_plan(
                self._plan_id,
                name=vals["name"],
                start_date=vals["start_date"],
                planned_end_date=vals["planned_end_date"] or None,
                status=vals["status"],
                description=vals["description"],
                reason=vals["reason"],
                notes=vals["notes"],
            )
        except Exception as e:
            error_dialog(self, "Errore", str(e))
            return

        if self._phase_builder is not None:
            new_phases = self._phase_builder.get_phases_config()
            if new_phases:
                try:
                    self._app.manager.replace_plan_phases(self._plan_id, new_phases)
                except Exception as e:
                    error_dialog(self, "Errore fasi", str(e))
                    return

        self._app.show_message("Piano aggiornato")
        self.accept()


# ═════════════════════════════════════════════════════════════════════════
#  PLAN DETAILS DIALOG — Dashboard with Phases + Resources
# ═════════════════════════════════════════════════════════════════════════


class _PlanDetailsDialog(QDialog):
    """Operational plan dashboard: info, phases, resources, actions."""

    def __init__(self, app, plan_id, parent=None):
        super().__init__(parent)
        self._app = app
        self._plan_id = plan_id
        self.setWindowTitle(f"Piano #{plan_id}")
        self.setMinimumWidth(760)
        self.setMinimumHeight(500)
        self.setStyleSheet(_DLG_STYLE)

        self._load_data()
        if self._plan is None:
            return
        self._build_ui()

    def _load_data(self):
        """Load plan basic + full (phases + resources)."""
        try:
            self._plan = self._app.manager.get_treatment_plan_basic(self._plan_id)
        except Exception as e:
            error_dialog(self, "Errore", str(e))
            self._plan = None
            self.reject()
            return

        if not self._plan:
            error_dialog(self, "Errore", "Piano non trovato")
            self._plan = None
            self.reject()
            return

        self._full = None
        try:
            self._full = self._app.manager.get_treatment_plan(self._plan_id)
        except Exception:
            pass

    def _build_ui(self):
        p = self._plan
        full = self._full or {}
        layout = self.layout() or QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(12, 12, 12, 12)

        # ── Header: title + status badge (compact) ───────────────────────
        header_row = QHBoxLayout()
        header_row.setSpacing(8)
        title = QLabel(p.get("name", f"Piano #{p.get('id', '?')}"))
        title.setStyleSheet("font-size: 15px; font-weight: bold;")
        header_row.addWidget(title)
        header_row.addStretch()
        header_row.addWidget(_status_badge(p.get("status", "")))
        layout.addLayout(header_row)

        # Compact info line
        current_phase = full.get("current_phase")
        info_parts = [
            str(p.get("start_date", "-"))[:10],
            f"→ {str(p.get('planned_end_date') or '-')[:10]}",
        ]
        if current_phase:
            cp = f"Fase {current_phase.get('phase_number', '?')}: {current_phase.get('phase_name', '?')}"
            info_parts.append(cp)
        info_lbl = QLabel("  |  ".join(info_parts))
        info_lbl.setStyleSheet("color: #aeaeae; font-size: 11px;")
        layout.addWidget(info_lbl)

        # ── Scrollable content area ──────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        content = QWidget()
        c_lay = QVBoxLayout(content)
        c_lay.setSpacing(8)
        c_lay.setContentsMargins(0, 0, 4, 0)

        # ── Phases (compact rows) ─────────────────────────────────────────
        phases = full.get("phases", [])
        if phases:
            c_lay.addWidget(_sep(f"Fasi ({len(phases)})"))
            for ph in phases:
                c_lay.addWidget(self._build_phase_row(ph, current_phase))

        # ── Peptide Resources ────────────────────────────────────────────
        resources = full.get("resources", [])
        pep_resources = [r for r in resources if r.get("resource_type") == "peptide"]
        if pep_resources:
            c_lay.addWidget(_sep("Risorse Peptidi"))
            res_table = QTableWidget(len(pep_resources), 4)
            res_table.setHorizontalHeaderLabels(
                ["Peptide", "Necessari (mg)", "In Stock (mg)", "Da Ordinare"]
            )
            res_table.setAlternatingRowColors(True)
            res_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            res_table.verticalHeader().setVisible(False)
            res_table.setFixedHeight(34 + len(pep_resources) * 32)
            hdr = res_table.horizontalHeader()
            for col in range(4):
                hdr.setSectionResizeMode(col, QHeaderView.Stretch)

            for row_idx, res in enumerate(pep_resources):
                name = res.get("resource_name", "?")
                unit = res.get("quantity_unit", "")

                qty_needed = float(res.get("quantity_needed") or 0)
                qty_avail = float(res.get("quantity_available") or 0)

                if unit == "mg":
                    needed_str = f"{qty_needed:.1f} mg"
                    avail_str = f"{qty_avail:.1f} mg"
                else:
                    cp = _parse_calc_params(res.get("calculation_params"))
                    if cp and cp.get("mg_needed") is not None:
                        mg_per_vial = float(cp.get("mg_per_vial") or 5.0)
                        qty_needed = float(cp['mg_needed'])
                        needed_str = f"{qty_needed:.1f} mg"
                        avail_str = f"{qty_avail * mg_per_vial:.1f} mg*"
                        qty_avail = qty_avail * mg_per_vial
                    else:
                        needed_str = f"{qty_needed:.0f} {unit}"
                        avail_str = f"{qty_avail:.0f} {unit}"

                gap = max(0.0, qty_needed - qty_avail)
                if gap > 0.01:
                    gap_str = f"{gap:.1f} mg"
                    gap_color = Qt.red
                else:
                    gap_str = "—"
                    gap_color = Qt.green

                items = [
                    QTableWidgetItem(name),
                    QTableWidgetItem(needed_str),
                    QTableWidgetItem(avail_str),
                    QTableWidgetItem(gap_str),
                ]
                items[3].setForeground(gap_color)
                items[3].setTextAlignment(Qt.AlignCenter)

                for col, item in enumerate(items):
                    res_table.setItem(row_idx, col, item)
            c_lay.addWidget(res_table)

            # ── Riepilogo fiale (riga compatta, niente spinbox) ───────────
            summary = _build_dose_summary(pep_resources)
            if summary:
                summary_lbl = QLabel(summary)
                summary_lbl.setStyleSheet("color: #90caf9; font-size: 11px; padding: 2px 0;")
                summary_lbl.setWordWrap(True)
                c_lay.addWidget(summary_lbl)

        # ── Consumables (compact horizontal) ─────────────────────────────
        consumables = [r for r in resources if r.get("resource_type") != "peptide"]
        if consumables:
            c_lay.addWidget(_sep("Consumabili"))
            cons_parts = []
            for c in consumables:
                qty = c.get("quantity_needed", 0)
                unit = c.get("quantity_unit", "")
                name = c.get("resource_name", "?")
                cons_parts.append(f"{name}: {qty} {unit}")
            cons_lbl = QLabel("  •  ".join(cons_parts))
            cons_lbl.setStyleSheet("color: #e0e0e0; font-size: 11px;")
            cons_lbl.setWordWrap(True)
            c_lay.addWidget(cons_lbl)

        c_lay.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

        # ── Action buttons (fixed at bottom) ─────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        plan_status = p.get("status", "")
        phases_list = full.get("phases", []) if full else []
        any_phase_active = any(ph.get("status") == "active" for ph in phases_list)

        export_cal_btn = QPushButton("Esporta Calendario")
        export_cal_btn.clicked.connect(lambda: _ExportCalendarDialog(self._app, parent=self).exec())
        btn_row.addWidget(export_cal_btn)

        if resources:
            recalc_btn = QPushButton("Ricalcola Risorse")
            recalc_btn.clicked.connect(self._on_recalculate)
            btn_row.addWidget(recalc_btn)

        # Mostra "Attiva Prima Fase" se il piano è pianificato O se è attivo
        # ma nessuna fase è ancora stata avviata concretamente
        if plan_status in ("planned", "active") and phases and not any_phase_active:
            activate_btn = QPushButton("Attiva Prima Fase")
            activate_btn.setStyleSheet(
                "background: #2e7d32; color: white; padding: 8px 16px;"
                " border-radius: 4px; font-weight: bold;"
            )
            activate_btn.clicked.connect(self._on_activate_first)
            btn_row.addWidget(activate_btn)

        if plan_status == "active" and current_phase and any_phase_active:
            next_btn = QPushButton("Prossima Fase")
            next_btn.setStyleSheet(
                "background: #1565c0; color: white; padding: 8px 16px;"
                " border-radius: 4px; font-weight: bold;"
            )
            next_btn.clicked.connect(self._on_next_phase)
            btn_row.addWidget(next_btn)

        close_btn = QPushButton("Chiudi")
        close_btn.setStyleSheet(
            "background: #424242; color: #e0e0e0; padding: 8px 16px;"
            " border-radius: 4px; font-weight: bold;"
        )
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def _build_phase_widget(self, ph, current_phase):
        """Build a read-only widget for a single phase."""
        w = QFrame()
        is_current = (
            current_phase
            and ph.get("id") == current_phase.get("id")
        )
        border_color = "#4caf50" if is_current else "#424242"
        w.setStyleSheet(
            f"QFrame {{ border: 1px solid {border_color};"
            " border-radius: 4px; padding: 6px; }}"
        )
        lay = QVBoxLayout(w)
        lay.setSpacing(3)
        lay.setContentsMargins(8, 6, 8, 6)

        # Header: number, name, status badge, duration
        header_row = QHBoxLayout()
        ph_num = ph.get("phase_number", "?")
        ph_name = ph.get("phase_name", f"Fase {ph_num}")
        dur = ph.get("duration_weeks", "?")
        header_lbl = QLabel(f"{ph_num}. {ph_name} ({dur} sett)")
        header_lbl.setStyleSheet("font-weight: bold; color: #e0e0e0; border: none;")
        header_row.addWidget(header_lbl)
        header_row.addStretch()
        badge = _status_badge(ph.get("status", "planned"))
        badge.setStyleSheet(badge.styleSheet() + " border: none;")
        header_row.addWidget(badge)
        lay.addLayout(header_row)

        # Peptides
        peptides_config = ph.get("peptides_config", "[]")
        try:
            peptides = json.loads(peptides_config) if isinstance(peptides_config, str) else peptides_config
        except (json.JSONDecodeError, TypeError):
            peptides = []

        if peptides:
            pep_parts = []
            for pep in peptides:
                pname = pep.get("peptide_name", "?")
                dose = pep.get("dose_mcg", 0)
                pep_parts.append(f"{pname}: {dose} mcg")
            pep_lbl = QLabel("  " + "  |  ".join(pep_parts))
            pep_lbl.setStyleSheet("color: #aeaeae; font-size: 11px; border: none;")
            lay.addWidget(pep_lbl)

        # Link to cycle — clickable button
        cycle_id = ph.get("cycle_id")
        if cycle_id:
            cycle_btn = QPushButton(f"  Ciclo #{cycle_id} →")
            cycle_btn.setStyleSheet(
                "QPushButton { color: #42a5f5; font-size: 11px; border: none;"
                " background: transparent; padding: 0 0 0 2px; text-align: left; }"
                "QPushButton:hover { color: #90caf9; }"
            )
            cycle_btn.setCursor(Qt.PointingHandCursor)
            cycle_btn.clicked.connect(
                lambda _=False, cid=cycle_id: _open_cycle_details(self._app, cid, self)
            )
            lay.addWidget(cycle_btn)

        return w

    def _build_phase_row(self, ph, current_phase):
        """Compact single-row representation of a phase (no heavy card border)."""
        is_current = current_phase and ph.get("id") == current_phase.get("id")

        ph_num = ph.get("phase_number", "?")
        ph_name = ph.get("phase_name", f"Fase {ph_num}")
        dur = ph.get("duration_weeks", "?")
        status = ph.get("status", "planned")
        status_label = _STATUS_LABELS.get(status, status)

        # Peptide summary
        try:
            raw = ph.get("peptides_config", "[]")
            peptides = json.loads(raw) if isinstance(raw, str) else (raw or [])
        except Exception:
            peptides = []
        pep_text = "  |  ".join(
            f"{p.get('peptide_name', '?')}: {p.get('dose_mcg', 0)} mcg"
            for p in peptides
        )

        dot_color = "#4caf50" if is_current else "#616161"
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(4, 2, 4, 2)
        lay.setSpacing(1)

        header_row = QHBoxLayout()
        header_row.setSpacing(6)
        dot = QLabel("●")
        dot.setStyleSheet(f"color: {dot_color}; font-size: 10px;")
        dot.setFixedWidth(14)
        header_row.addWidget(dot)
        title_lbl = QLabel(f"{ph_num}. {ph_name}  ({dur} sett)")
        weight = "bold" if is_current else "normal"
        title_lbl.setStyleSheet(f"font-weight: {weight}; color: #e0e0e0;")
        header_row.addWidget(title_lbl, 1)
        badge = _status_badge(status)
        header_row.addWidget(badge)
        lay.addLayout(header_row)

        detail_row = QHBoxLayout()
        detail_row.setSpacing(6)
        detail_row.addSpacing(20)  # indent under dot
        if pep_text:
            pep_lbl = QLabel(pep_text)
            pep_lbl.setStyleSheet("color: #888; font-size: 11px;")
            detail_row.addWidget(pep_lbl, 1)
        cycle_id = ph.get("cycle_id")
        if cycle_id:
            cycle_btn = QPushButton(f"Ciclo #{cycle_id} →")
            cycle_btn.setStyleSheet(
                "QPushButton { color: #42a5f5; font-size: 11px; border: none;"
                " background: transparent; padding: 0; }"
                "QPushButton:hover { color: #90caf9; }"
            )
            cycle_btn.setCursor(Qt.PointingHandCursor)
            cycle_btn.clicked.connect(
                lambda _=False, cid=cycle_id: _open_cycle_details(self._app, cid, self)
            )
            detail_row.addWidget(cycle_btn)
        lay.addLayout(detail_row)

        return w

    # ── Actions ──────────────────────────────────────────────────────────

    def _on_recalculate(self):
        try:
            self._app.manager.update_plan_resources(self._plan_id)
            self._app.show_message("Risorse ricalcolate")
            self._rebuild()
        except Exception as e:
            error_dialog(self, "Errore", str(e))

    def _on_activate_first(self):
        try:
            result = self._app.manager.activate_plan_phase(self._plan_id, 1)
            cycle_id = result.get("cycle_id")
            msg = "Prima fase attivata"
            if cycle_id:
                msg += f" — Ciclo #{cycle_id} creato"
            self._app.show_message(msg)
            self._rebuild()
        except Exception as e:
            error_dialog(self, "Errore", str(e))

    def _on_next_phase(self):
        try:
            result = self._app.manager.transition_to_next_phase(self._plan_id)
            if result.get("plan_continues", True):
                new_ph = result.get("activated_phase") or {}
                msg = f"Fase {new_ph.get('phase_number', '?')} attivata"
                cycle_id = result.get("new_cycle_id")
                if cycle_id:
                    msg += f" — Ciclo #{cycle_id} creato"
            else:
                msg = "Piano completato"
            self._app.show_message(msg)
            self._rebuild()
        except Exception as e:
            error_dialog(self, "Errore", str(e))

    def _rebuild(self):
        """Reload data and rebuild UI in place."""
        # Remove all widgets from layout
        layout = self.layout()
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
            sub = item.layout()
            if sub:
                while sub.count():
                    child = sub.takeAt(0)
                    cw = child.widget()
                    if cw:
                        cw.deleteLater()

        self._load_data()
        if self._plan is not None:
            self._build_ui()
