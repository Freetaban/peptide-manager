"""Plans tab and dialogs for the Treatment section."""

import json
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


# ── Helpers ──────────────────────────────────────────────────────────────

def _resolve_peptide_names(phases_config, all_peptides):
    """Resolve peptide_name → peptide_id using case-insensitive matching.

    Returns (resolved_phases, unresolved_names).
    Mutates nothing — returns new list.
    """
    # Build lookup: lowercase name → (id, canonical_name)
    lookup = {}
    for p in all_peptides:
        name = (p.get("name") or "").strip().lower()
        if name:
            lookup[name] = (p["id"], p.get("name", ""))

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
            new_ph = result.get("new_phase", {})
            msg = f"Fase {new_ph.get('phase_number', '?')} attivata"
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
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # ── Section 1: Plan Info ─────────────────────────────────────────
        header_row = QHBoxLayout()
        title = QLabel(p.get("name", f"Piano #{p.get('id', '?')}"))
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        header_row.addWidget(title)
        header_row.addStretch()
        header_row.addWidget(_status_badge(p.get("status", "")))
        layout.addLayout(header_row)

        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(5)
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

        add_row("Inizio", str(p.get("start_date", "-"))[:10])
        add_row("Fine Prev.", str(p.get("planned_end_date") or "-")[:10])
        if p.get("description"):
            add_row("Descrizione", p["description"])
        if p.get("reason"):
            add_row("Motivazione", p["reason"])

        # Current phase
        current_phase = full.get("current_phase")
        if current_phase:
            cp_name = current_phase.get("phase_name", "?")
            cp_num = current_phase.get("phase_number", "?")
            add_row("Fase Attuale", f"{cp_num}. {cp_name}")

        layout.addLayout(grid)

        # ── Section 2: Phases ────────────────────────────────────────────
        phases = full.get("phases", [])
        if phases:
            layout.addWidget(_sep(f"Fasi ({len(phases)})"))

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setStyleSheet("QScrollArea { border: none; }")
            scroll.setMaximumHeight(200)
            phases_w = QWidget()
            phases_lay = QVBoxLayout(phases_w)
            phases_lay.setSpacing(4)
            phases_lay.setContentsMargins(0, 0, 4, 0)

            for ph in phases:
                pw = self._build_phase_widget(ph, current_phase)
                phases_lay.addWidget(pw)
            phases_lay.addStretch()
            scroll.setWidget(phases_w)
            layout.addWidget(scroll)

        # ── Section 3: Peptide Resources ─────────────────────────────────
        resources = full.get("resources", [])
        pep_resources = [r for r in resources if r.get("resource_type") == "peptide"]
        if pep_resources:
            layout.addWidget(_sep("Risorse Peptidi"))
            res_table = QTableWidget(len(pep_resources), 5)
            res_table.setHorizontalHeaderLabels(
                ["Peptide", "Necessari", "Disponibili", "Gap", "Stato"]
            )
            res_table.setAlternatingRowColors(True)
            res_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            res_table.verticalHeader().setVisible(False)
            res_table.setMaximumHeight(min(35 + len(pep_resources) * 28, 180))
            hdr = res_table.horizontalHeader()
            hdr.setSectionResizeMode(0, QHeaderView.Stretch)
            for col in range(1, 5):
                hdr.setSectionResizeMode(col, QHeaderView.Fixed)
                res_table.setColumnWidth(col, 90)

            for row_idx, res in enumerate(pep_resources):
                name = res.get("resource_name", "?")
                needed = res.get("quantity_needed", 0)
                avail = res.get("quantity_available", 0)
                gap = res.get("quantity_gap", 0)
                unit = res.get("quantity_unit", "")
                needs_order = res.get("needs_ordering", False)

                items = [
                    QTableWidgetItem(name),
                    QTableWidgetItem(f"{needed} {unit}"),
                    QTableWidgetItem(f"{avail} {unit}"),
                    QTableWidgetItem(f"{gap}" if gap and float(gap) > 0 else "0"),
                    QTableWidgetItem("Da Ordinare" if needs_order else "OK"),
                ]
                # Color the status column
                if needs_order:
                    items[4].setForeground(Qt.red)
                else:
                    items[4].setForeground(Qt.green)

                for col, item in enumerate(items):
                    res_table.setItem(row_idx, col, item)
            layout.addWidget(res_table)

        # ── Section 4: Consumables ───────────────────────────────────────
        consumables = [r for r in resources if r.get("resource_type") != "peptide"]
        if consumables:
            layout.addWidget(_sep("Consumabili"))
            for c in consumables:
                qty = c.get("quantity_needed", 0)
                unit = c.get("quantity_unit", "")
                name = c.get("resource_name", "?")
                c_lbl = QLabel(f"  {name}: {qty} {unit}")
                c_lbl.setStyleSheet("color: #e0e0e0;")
                layout.addWidget(c_lbl)

        # ── Action buttons ───────────────────────────────────────────────
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

        # Link to cycle
        cycle_id = ph.get("cycle_id")
        if cycle_id:
            cycle_lbl = QLabel(f"  Ciclo #{cycle_id}")
            cycle_lbl.setStyleSheet(
                "color: #42a5f5; font-size: 11px; border: none;"
            )
            lay.addWidget(cycle_lbl)

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
            new_ph = result.get("new_phase", {})
            msg = f"Fase {new_ph.get('phase_number', '?')} attivata"
            cycle_id = result.get("cycle_id")
            if cycle_id:
                msg += f" — Ciclo #{cycle_id} creato"
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
