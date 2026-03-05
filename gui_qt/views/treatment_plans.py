"""Plans tab and dialogs for the Treatment section."""

from datetime import date, timedelta

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QComboBox,
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
            {"label": "Abbandona",  "callback": self._on_abandon,
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
            plans = self.manager.get_treatment_plans(status=status_filter)
        except Exception as e:
            error_dialog(self, "Errore", str(e))
            return

        rows = []
        for p in plans:
            # Phase count — try to get from the plan details
            phases_count = 0
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


# ── Plan dialogs ────────────────────────────────────────────────────────


class _PlanAddDialog(QDialog):
    """Add a new treatment plan, optionally from a template."""

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self._app = app
        self._template_id = None  # currently selected template id
        self.setWindowTitle("Nuovo Piano di Trattamento")
        self.setMinimumWidth(500)
        self.setStyleSheet(_DLG_STYLE)
        self._load_templates()
        self._build_ui()

    def _load_templates(self):
        """Fetch active templates from DB for the selector."""
        self._templates = []  # list of (id, name, total_duration_weeks, notes)
        try:
            cur = self._app.manager.conn.cursor()
            cur.execute("""
                SELECT id, name, total_duration_weeks, notes
                FROM treatment_plan_templates
                WHERE is_active = 1
                ORDER BY category, name
            """)
            self._templates = cur.fetchall()
        except Exception:
            pass  # table may not exist; selector stays empty

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

        btns, submit = _make_buttons(self, submit_label="Crea Piano")
        submit.clicked.connect(self._submit)
        layout.addWidget(btns)

    def _on_template_changed(self, idx):
        data = self._tpl_combo.itemData(idx)
        if data is None:
            self._template_id = None
            return

        tid, tweeks, tnotes = data
        self._template_id = tid

        # Pre-fill fields from template
        start_str = self._form.get_values().get("start_date") or _today_str()
        end_str = ""
        if tweeks:
            try:
                start = date.fromisoformat(start_str)
                end_str = (start + timedelta(weeks=int(tweeks))).isoformat()
            except (ValueError, TypeError):
                pass

        # Fetch template name directly from combo text
        tname = self._tpl_combo.currentText()
        self._form.set_values({
            "name": tname,
            "planned_end_date": end_str,
            "notes": tnotes or "",
        })

    def _submit(self):
        errors = self._form.validate()
        if errors:
            error_dialog(self, "Validazione", "\n".join(errors))
            return

        vals = self._form.get_values()
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


class _PlanDetailsDialog(QDialog):
    """Read-only plan details with phases list."""

    def __init__(self, app, plan_id, parent=None):
        super().__init__(parent)
        self._app = app
        self.setWindowTitle(f"Dettagli Piano #{plan_id}")
        self.setMinimumWidth(520)
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

        # Try to get full details with phases
        self._full = None
        try:
            self._full = app.manager.get_treatment_plan(plan_id)
        except Exception:
            pass

        self._build_ui()

    def _build_ui(self):
        p = self._plan
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Title
        title = QLabel(p.get("name", f"Piano #{p.get('id', '?')}"))
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

        add_row("Stato", _STATUS_LABELS.get(p.get("status", ""), p.get("status", "")))
        add_row("Inizio", str(p.get("start_date", "-"))[:10])
        add_row("Fine Prev.", str(p.get("planned_end_date") or "-")[:10])
        add_row("Descrizione", p.get("description") or "-")
        add_row("Motivazione", p.get("reason") or "-")
        add_row("Note", p.get("notes") or "-")

        # Adherence / days
        adherence = p.get("adherence_percentage")
        if adherence is not None:
            add_row("Aderenza", f"{float(adherence):.0f}%")
        days_completed = p.get("days_completed")
        total_days = p.get("total_planned_days")
        if days_completed is not None:
            days_str = str(days_completed)
            if total_days:
                days_str += f" / {total_days}"
            add_row("Giorni Completati", days_str)

        layout.addLayout(grid)

        # Phases (if multi-phase)
        if self._full and self._full.get("phases"):
            phases = self._full["phases"]
            layout.addWidget(_sep(f"Fasi ({len(phases)})"))

            for ph in phases:
                ph_text = (
                    f"  {ph.get('phase_number', '?')}. {ph.get('phase_name', '?')}"
                    f" — {_STATUS_LABELS.get(ph.get('status', ''), ph.get('status', ''))}"
                )
                dur = ph.get("duration_weeks")
                if dur:
                    ph_text += f" ({dur} sett)"
                ph_lbl = QLabel(ph_text)
                ph_lbl.setStyleSheet("color: #e0e0e0; padding: 2px 0;")
                layout.addWidget(ph_lbl)

        # Close
        close_btn = QPushButton("Chiudi")
        close_btn.setFixedWidth(100)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignRight)
