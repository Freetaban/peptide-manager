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
    QPushButton,
    QScrollArea,
    QWidget,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
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
        self.setMinimumWidth(620)
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

        # Template selector
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

        # Form fields
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

        # Phase preview area (hidden until template selected)
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
            return

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

        # Template with phases → use create_treatment_plan()
        if self._phases_config:
            try:
                result = self._app.manager.create_treatment_plan(
                    name=vals["name"],
                    start_date=vals["start_date"],
                    phases_config=self._phases_config,
                    description=vals["description"],
                    calculate_resources=True,
                )
                plan_id = result.get("plan_id")
                # Store reason/notes on the plan if provided
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
                self._app.show_message("Piano multi-fase creato con risorse calcolate")
                self.accept()
            except Exception as e:
                error_dialog(self, "Errore", str(e))
            return

        # No template → simple plan (legacy path)
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
        self.setMinimumWidth(500)
        self.setStyleSheet(_DLG_STYLE)

        try:
            self._plan = app.manager.get_treatment_plan_basic(plan_id)
        except Exception as e:
            error_dialog(self, "Errore", str(e))
            self.reject()
            return

        if not self._plan:
            error_dialog(self, "Errore", "Piano non trovato")
            self.reject()
            return

        self._build_ui()

    def _build_ui(self):
        p = self._plan
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
            self._app.show_message("Piano aggiornato")
            self.accept()
        except Exception as e:
            error_dialog(self, "Errore", str(e))


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
        self.setMinimumWidth(650)
        self.setMinimumHeight(550)
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

        # ── Phases ───────────────────────────────────────────────────────
        phases = full.get("phases", [])
        if phases:
            c_lay.addWidget(_sep(f"Fasi ({len(phases)})"))
            for ph in phases:
                pw = self._build_phase_widget(ph, current_phase)
                c_lay.addWidget(pw)

        # ── Peptide Resources ────────────────────────────────────────────
        resources = full.get("resources", [])
        pep_resources = [r for r in resources if r.get("resource_type") == "peptide"]
        if pep_resources:
            c_lay.addWidget(_sep("Risorse Peptidi"))
            res_table = QTableWidget(len(pep_resources), 4)
            res_table.setHorizontalHeaderLabels(
                ["Peptide", "Necessari (mg)", "Disponibili (mg)", "Stato"]
            )
            res_table.setAlternatingRowColors(True)
            res_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            res_table.verticalHeader().setVisible(False)
            res_table.setFixedHeight(28 + len(pep_resources) * 26)
            hdr = res_table.horizontalHeader()
            hdr.setSectionResizeMode(0, QHeaderView.Stretch)
            for col in range(1, 4):
                hdr.setSectionResizeMode(col, QHeaderView.Fixed)
                res_table.setColumnWidth(col, 100)

            for row_idx, res in enumerate(pep_resources):
                name = res.get("resource_name", "?")
                needs_order = res.get("needs_ordering", False)
                unit = res.get("quantity_unit", "")

                qty_needed = float(res.get("quantity_needed") or 0)
                qty_avail = float(res.get("quantity_available") or 0)

                if unit == "mg":
                    needed_str = f"{qty_needed:.1f} mg"
                    avail_str = f"{qty_avail:.1f} mg"
                else:
                    # Piani vecchi (unit='vials'): mostra mg se disponibile in calculation_params
                    cp = _parse_calc_params(res.get("calculation_params"))
                    if cp and cp.get("mg_needed") is not None:
                        mg_per_vial = float(cp.get("mg_per_vial") or 5.0)
                        needed_str = f"{float(cp['mg_needed']):.1f} mg"
                        avail_str = f"{qty_avail * mg_per_vial:.1f} mg*"
                    else:
                        needed_str = f"{qty_needed:.0f} {unit}"
                        avail_str = f"{qty_avail:.0f} {unit}"

                items = [
                    QTableWidgetItem(name),
                    QTableWidgetItem(needed_str),
                    QTableWidgetItem(avail_str),
                    QTableWidgetItem("Da Ordinare" if needs_order else "OK"),
                ]
                if needs_order:
                    items[3].setForeground(Qt.red)
                else:
                    items[3].setForeground(Qt.green)

                for col, item in enumerate(items):
                    res_table.setItem(row_idx, col, item)
            c_lay.addWidget(res_table)

            # ── Configuratore Fiale ───────────────────────────────────────
            c_lay.addWidget(_build_vial_configurator(pep_resources))

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

        if resources:
            recalc_btn = QPushButton("Ricalcola Risorse")
            recalc_btn.clicked.connect(self._on_recalculate)
            btn_row.addWidget(recalc_btn)

        if plan_status == "planned" and phases:
            activate_btn = QPushButton("Attiva Prima Fase")
            activate_btn.setStyleSheet(
                "background: #2e7d32; color: white; padding: 8px 16px;"
                " border-radius: 4px; font-weight: bold;"
            )
            activate_btn.clicked.connect(self._on_activate_first)
            btn_row.addWidget(activate_btn)

        if plan_status == "active" and current_phase:
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
