"""Templates tab, PhaseWidget, and template dialogs for the Treatment section."""

import json

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
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
)
from PySide6.QtCore import Qt, Signal

from .treatment_common import (
    BaseView,
    DataTable,
    confirm_dialog,
    error_dialog,
    _DLG_STYLE,
    _make_buttons,
    _sep,
)


# ── Template-specific constants ──────────────────────────────────────────

_CATEGORY_OPTIONS = [
    ("body_recomposition", "Body Recomposition"),
    ("weight_loss", "Weight Loss"),
    ("metabolic", "Metabolic Health"),
    ("anti_aging", "Anti-Aging"),
    ("performance", "Performance"),
    ("recovery", "Recovery"),
]

_TIMING_OPTIONS = [
    ("morning", "Mattina"),
    ("evening", "Sera"),
    ("both", "Entrambi"),
]

_EXAMPLE_TEMPLATES = [
    {
        "name": "GH Secretagogue Protocol - Foundation",
        "short_name": "GH-Basic",
        "category": "body_recomposition",
        "total_phases": 3,
        "total_duration_weeks": 16,
        "phases_config": json.dumps([
            {
                "phase_name": "Foundation (Weeks 1-4)",
                "phase_number": 1,
                "duration_weeks": 4,
                "daily_frequency": 1,
                "five_two_protocol": False,
                "administration_times": ["evening"],
                "peptides": [
                    {"peptide_name": "CJC-1295", "dose_mcg": 100, "timing": "evening"},
                    {"peptide_name": "Ipamorelin", "dose_mcg": 100, "timing": "evening"},
                ],
                "description": "Low dose foundation phase",
            },
            {
                "phase_name": "Intensification (Weeks 5-12)",
                "phase_number": 2,
                "duration_weeks": 8,
                "daily_frequency": 2,
                "five_two_protocol": True,
                "administration_times": ["morning", "evening"],
                "peptides": [
                    {"peptide_name": "CJC-1295", "dose_mcg": 200, "timing": "evening"},
                    {"peptide_name": "Ipamorelin", "dose_mcg": 200, "timing": "both"},
                ],
                "description": "Increased dosing with 5-on-2-off pattern",
            },
            {
                "phase_name": "Maintenance (Weeks 13-16)",
                "phase_number": 3,
                "duration_weeks": 4,
                "daily_frequency": 1,
                "five_two_protocol": True,
                "administration_times": ["evening"],
                "peptides": [
                    {"peptide_name": "CJC-1295", "dose_mcg": 150, "timing": "evening"},
                    {"peptide_name": "Ipamorelin", "dose_mcg": 150, "timing": "evening"},
                ],
                "description": "Reduced frequency maintenance",
            },
        ]),
        "expected_outcomes": json.dumps([
            "Improved sleep quality",
            "Increased lean muscle mass",
            "Enhanced recovery",
            "Fat loss support",
        ]),
        "source": "Peptide Protocol Guide",
        "notes": "Standard GH secretagogue protocol for body recomposition",
        "is_active": 1,
    },
    {
        "name": "Metabolic Reset - 12 Week",
        "short_name": "MetRestore",
        "category": "metabolic",
        "total_phases": 2,
        "total_duration_weeks": 12,
        "phases_config": json.dumps([
            {
                "phase_name": "Reset Phase (Weeks 1-8)",
                "phase_number": 1,
                "duration_weeks": 8,
                "daily_frequency": 1,
                "five_two_protocol": False,
                "administration_times": ["morning"],
                "peptides": [
                    {"peptide_name": "Semaglutide", "dose_mcg": 250, "timing": "morning"},
                    {"peptide_name": "BPC-157", "dose_mcg": 250, "timing": "morning"},
                ],
                "description": "Metabolic reset with gut healing",
            },
            {
                "phase_name": "Consolidation (Weeks 9-12)",
                "phase_number": 2,
                "duration_weeks": 4,
                "daily_frequency": 1,
                "five_two_protocol": True,
                "administration_times": ["morning"],
                "peptides": [
                    {"peptide_name": "Semaglutide", "dose_mcg": 500, "timing": "morning"},
                ],
                "description": "Maintenance dosing",
            },
        ]),
        "expected_outcomes": json.dumps([
            "Improved insulin sensitivity",
            "Reduced appetite",
            "Steady weight loss",
            "Better gut health",
        ]),
        "source": "Metabolic Health Protocol",
        "notes": "12-week metabolic reset with gradual dose escalation",
        "is_active": 1,
    },
]


# ═════════════════════════════════════════════════════════════════════════
#  TEMPLATES TAB
# ═════════════════════════════════════════════════════════════════════════


class TemplatesTab(BaseView):
    """Treatment plan templates — CRUD + phase editor."""

    def __init__(self, app, parent=None):
        super().__init__(app, parent)
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        lay = self.layout()

        # Toolbar
        toolbar = QHBoxLayout()
        title = QLabel("Template di Trattamento")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        toolbar.addWidget(title)
        toolbar.addStretch()

        examples_btn = QPushButton("Aggiungi Esempi")
        examples_btn.clicked.connect(self._on_add_examples)
        toolbar.addWidget(examples_btn)

        add_btn = QPushButton("Nuovo Template")
        add_btn.clicked.connect(self._on_add)
        toolbar.addWidget(add_btn)
        lay.addLayout(toolbar)

        # Table
        self._table = DataTable([
            {"key": "id",           "label": "ID",        "width": 50},
            {"key": "name",         "label": "Nome",      "stretch": True},
            {"key": "short_name",   "label": "Short",     "width": 90},
            {"key": "category",     "label": "Categoria", "width": 160},
            {"key": "total_phases", "label": "Fasi",      "width": 55},
            {"key": "total_weeks",  "label": "Sett.",     "width": 55},
            {"key": "active",       "label": "Attivo",    "width": 65},
        ])
        self._table.set_context_menu([
            {"label": "Dettagli",         "callback": self._on_details},
            {"label": "Modifica",         "callback": self._on_edit,
             "enabled_when": lambda: self.edit_mode},
            {"label": "Duplica",          "callback": self._on_duplicate},
            {"label": "Attiva/Disattiva", "callback": self._on_toggle},
            {"label": "Elimina",          "callback": self._on_delete,
             "enabled_when": lambda: self.edit_mode},
        ])
        self._table.row_double_clicked.connect(self._on_details)
        lay.addWidget(self._table, 1)

    def _conn(self):
        return self.manager.conn

    # ── Data ─────────────────────────────────────────────────────────────

    def refresh(self):
        try:
            cur = self._conn().cursor()
            cur.execute("""
                SELECT id, name, short_name, category,
                       total_phases, total_duration_weeks, is_active
                FROM treatment_plan_templates
                ORDER BY category, name
            """)
            rows = []
            cat_labels = dict(_CATEGORY_OPTIONS)
            for tid, name, short_name, cat, phases, weeks, active in cur.fetchall():
                rows.append({
                    "id": tid,
                    "name": name,
                    "short_name": short_name or "—",
                    "category": cat_labels.get(cat, cat or "—"),
                    "total_phases": phases,
                    "total_weeks": weeks,
                    "active": "Sì" if active else "No",
                    "_is_active": bool(active),
                })
            self._table.load_data(rows)
        except Exception as e:
            error_dialog(self, "Errore", str(e))

    # ── Actions ──────────────────────────────────────────────────────────

    def _on_add(self):
        dlg = _TemplateDialog(self.app, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh()

    def _on_details(self, row):
        dlg = _TemplateDetailsDialog(self.app, row["id"], parent=self)
        dlg.exec()

    def _on_edit(self, row):
        dlg = _TemplateDialog(self.app, template_id=row["id"], parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh()

    def _on_duplicate(self, row):
        try:
            cur = self._conn().cursor()
            cur.execute("""
                SELECT name, short_name, category, total_phases,
                       total_duration_weeks, phases_config,
                       expected_outcomes, source, notes
                FROM treatment_plan_templates WHERE id = ?
            """, (row["id"],))
            r = cur.fetchone()
            if not r:
                return
            (name, short_name, cat, phases, weeks,
             phases_config, outcomes, source, notes) = r
            cur.execute("""
                INSERT INTO treatment_plan_templates
                (name, short_name, category, total_phases, total_duration_weeks,
                 is_active, phases_config, expected_outcomes, source, notes)
                VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
            """, (
                f"{name} (Copia)", short_name, cat, phases, weeks,
                phases_config, outcomes,
                f"Duplicato da: {source or name}", notes,
            ))
            self._conn().commit()
            self.app.show_message("Template duplicato")
            self.refresh()
        except Exception as e:
            error_dialog(self, "Errore", str(e))

    def _on_toggle(self, row):
        try:
            new_state = 0 if row["_is_active"] else 1
            cur = self._conn().cursor()
            cur.execute(
                "UPDATE treatment_plan_templates SET is_active = ? WHERE id = ?",
                (new_state, row["id"]),
            )
            self._conn().commit()
            status = "disattivato" if row["_is_active"] else "attivato"
            self.app.show_message(f"Template {status}")
            self.refresh()
        except Exception as e:
            error_dialog(self, "Errore", str(e))

    def _on_delete(self, row):
        if not confirm_dialog(
            self, "Elimina Template",
            f"Eliminare il template '{row['name']}'? L'azione è irreversibile.",
        ):
            return
        try:
            cur = self._conn().cursor()
            cur.execute(
                "DELETE FROM treatment_plan_templates WHERE id = ?",
                (row["id"],),
            )
            self._conn().commit()
            self.app.show_message("Template eliminato")
            self.refresh()
        except Exception as e:
            error_dialog(self, "Errore", str(e))

    def _on_add_examples(self):
        try:
            added = 0
            cur = self._conn().cursor()
            for t in _EXAMPLE_TEMPLATES:
                cur.execute(
                    "SELECT id FROM treatment_plan_templates WHERE name = ?",
                    (t["name"],),
                )
                if cur.fetchone():
                    continue  # già presente
                cur.execute("""
                    INSERT INTO treatment_plan_templates
                    (name, short_name, category, total_phases, total_duration_weeks,
                     is_active, phases_config, expected_outcomes, source, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    t["name"], t.get("short_name"), t.get("category"),
                    t["total_phases"], t["total_duration_weeks"],
                    t.get("is_active", 1),
                    t["phases_config"], t.get("expected_outcomes"),
                    t.get("source"), t.get("notes"),
                ))
                added += 1
            self._conn().commit()
            msg = f"{added} template/i aggiunti" if added else "Template già presenti"
            self.app.show_message(msg)
            self.refresh()
        except Exception as e:
            error_dialog(self, "Errore", str(e))


# ── Template dialogs ─────────────────────────────────────────────────────


class _TemplateDialog(QDialog):
    """Add / edit a treatment plan template with per-phase editor."""

    def __init__(self, app, template_id=None, parent=None):
        super().__init__(parent)
        self._app = app
        self._template_id = template_id
        self.setWindowTitle(
            f"Modifica Template #{template_id}" if template_id else "Nuovo Template"
        )
        self.setMinimumWidth(720)
        self.setMinimumHeight(620)
        self.setStyleSheet(_DLG_STYLE)

        self._data = {}
        self._phases_raw = []

        if template_id:
            try:
                cur = app.manager.conn.cursor()
                cur.execute("""
                    SELECT name, short_name, category, is_active,
                           phases_config, expected_outcomes, source, notes
                    FROM treatment_plan_templates WHERE id = ?
                """, (template_id,))
                r = cur.fetchone()
                if r:
                    (name, short_name, cat, active,
                     phases_config, outcomes, source, notes) = r
                    self._data = {
                        "name": name,
                        "short_name": short_name or "",
                        "category": cat or "body_recomposition",
                        "is_active": active,
                        "phases_config": phases_config or "[]",
                        "expected_outcomes": outcomes or "[]",
                        "source": source or "",
                        "notes": notes or "",
                    }
            except Exception as e:
                error_dialog(self, "Errore", str(e))
                self.reject()
                return

        try:
            self._phases_raw = json.loads(
                self._data.get("phases_config", "[]")
            ) or []
        except (json.JSONDecodeError, KeyError):
            self._phases_raw = []

        if not self._phases_raw:
            self._phases_raw = [{
                "phase_name": "Fase 1", "phase_number": 1,
                "duration_weeks": 4, "daily_frequency": 1,
                "five_two_protocol": False,
                "administration_times": ["morning"],
                "peptides": [], "description": "",
            }]

        try:
            self._peptides = app.manager.get_peptides() or []
        except Exception:
            self._peptides = []

        self._phase_widgets = []
        self._build_ui()

    def _build_ui(self):
        d = self._data
        outer = QVBoxLayout(self)
        outer.setSpacing(10)

        # ── Basic info ──────────────────────────────────────────────────
        outer.addWidget(_sep("Informazioni Template"))
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)

        grid.addWidget(QLabel("Nome *"), 0, 0)
        self._name = QLineEdit(d.get("name", ""))
        self._name.setPlaceholderText("es. GH Protocol - Advanced")
        grid.addWidget(self._name, 0, 1)

        grid.addWidget(QLabel("Nome Breve"), 0, 2)
        self._short_name = QLineEdit(d.get("short_name", ""))
        self._short_name.setPlaceholderText("es. GH-Adv")
        grid.addWidget(self._short_name, 0, 3)

        grid.addWidget(QLabel("Categoria"), 1, 0)
        self._category = QComboBox()
        for val, lbl in _CATEGORY_OPTIONS:
            self._category.addItem(lbl, val)
        idx = self._category.findData(d.get("category", "body_recomposition"))
        if idx >= 0:
            self._category.setCurrentIndex(idx)
        grid.addWidget(self._category, 1, 1)

        grid.addWidget(QLabel("Fonte"), 1, 2)
        self._source = QLineEdit(d.get("source", "Custom"))
        grid.addWidget(self._source, 1, 3)

        grid.addWidget(QLabel("Note"), 2, 0)
        self._notes = QTextEdit(d.get("notes", ""))
        self._notes.setMaximumHeight(55)
        grid.addWidget(self._notes, 2, 1, 1, 3)

        outer.addLayout(grid)

        # ── Phases ──────────────────────────────────────────────────────
        ph_header = QHBoxLayout()
        ph_header.addWidget(_sep("Fasi"))
        ph_header.addStretch()
        add_ph_btn = QPushButton("+ Aggiungi Fase")
        add_ph_btn.clicked.connect(self._add_phase)
        ph_header.addWidget(add_ph_btn)
        outer.addLayout(ph_header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        self._phases_container = QWidget()
        self._phases_layout = QVBoxLayout(self._phases_container)
        self._phases_layout.setSpacing(8)
        self._phases_layout.setContentsMargins(0, 0, 4, 0)
        self._phases_layout.addStretch()
        scroll.setWidget(self._phases_container)
        outer.addWidget(scroll, 1)

        for phase in self._phases_raw:
            self._append_phase_widget(phase)

        # ── Buttons ─────────────────────────────────────────────────────
        btns, submit = _make_buttons(self, submit_label="Salva Template")
        submit.clicked.connect(self._submit)
        outer.addWidget(btns)

    def _append_phase_widget(self, phase_data):
        pw = _PhaseWidget(len(self._phase_widgets), phase_data, self._peptides, self)
        pw.remove_requested.connect(self._remove_phase)
        # Insert before the trailing stretch
        self._phases_layout.insertWidget(
            self._phases_layout.count() - 1, pw
        )
        self._phase_widgets.append(pw)

    def _add_phase(self):
        n = len(self._phase_widgets) + 1
        self._append_phase_widget({
            "phase_name": f"Fase {n}",
            "phase_number": n,
            "duration_weeks": 4,
            "daily_frequency": 1,
            "five_two_protocol": False,
            "administration_times": ["morning"],
            "peptides": [],
            "description": "",
        })

    def _remove_phase(self, widget):
        if len(self._phase_widgets) <= 1:
            error_dialog(self, "Attenzione", "Deve esserci almeno una fase.")
            return
        self._phases_layout.removeWidget(widget)
        widget.deleteLater()
        self._phase_widgets.remove(widget)
        for i, pw in enumerate(self._phase_widgets):
            pw.set_index(i)

    def _submit(self):
        name = self._name.text().strip()
        if not name:
            error_dialog(self, "Validazione", "Il nome è obbligatorio.")
            return

        phases = [pw.get_data() for pw in self._phase_widgets]
        for i, p in enumerate(phases):
            p["phase_number"] = i + 1
        total_weeks = sum(p.get("duration_weeks", 0) for p in phases)

        # Preserve expected_outcomes from original data (not edited here)
        outcomes = self._data.get("expected_outcomes")

        conn = self._app.manager.conn
        try:
            cur = conn.cursor()
            vals = (
                name,
                self._short_name.text().strip() or None,
                self._category.currentData(),
                len(phases),
                total_weeks,
                1,
                json.dumps(phases),
                outcomes,
                self._source.text().strip() or None,
                self._notes.toPlainText().strip() or None,
            )
            if self._template_id:
                cur.execute("""
                    UPDATE treatment_plan_templates
                    SET name=?, short_name=?, category=?, total_phases=?,
                        total_duration_weeks=?, is_active=?, phases_config=?,
                        expected_outcomes=?, source=?, notes=?,
                        updated_at=CURRENT_TIMESTAMP
                    WHERE id=?
                """, (*vals, self._template_id))
            else:
                cur.execute("""
                    INSERT INTO treatment_plan_templates
                    (name, short_name, category, total_phases, total_duration_weeks,
                     is_active, phases_config, expected_outcomes, source, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, vals)
            conn.commit()
            self._app.show_message(
                "Template aggiornato" if self._template_id else "Template creato"
            )
            self.accept()
        except Exception as e:
            error_dialog(self, "Errore", str(e))


class _PhaseWidget(QWidget):
    """Inline editor for a single template phase."""

    remove_requested = Signal(object)

    def __init__(self, index, phase_data, peptides, parent=None):
        super().__init__(parent)
        self._peptides = peptides
        self._phase_data = dict(phase_data)
        self._build_ui()
        self.set_index(index)

    def set_index(self, index):
        self._index = index
        self._header_label.setText(f"Fase {index + 1}")

    def get_data(self):
        peptides = []
        for r in range(self._pep_table.rowCount()):
            name_item = self._pep_table.item(r, 0)
            dose_item = self._pep_table.item(r, 1)
            timing_combo = self._pep_table.cellWidget(r, 2)
            if not name_item or not dose_item:
                continue
            try:
                dose = float(dose_item.text())
            except (ValueError, TypeError):
                dose = 0.0
            peptides.append({
                "peptide_name": name_item.text(),
                "peptide_id": name_item.data(Qt.UserRole),
                "dose_mcg": dose,
                "timing": timing_combo.currentData() if timing_combo else "morning",
            })
        return {
            "phase_name": self._phase_name.text().strip()
                          or f"Fase {self._index + 1}",
            "phase_number": self._index + 1,
            "duration_weeks": self._weeks.value(),
            "daily_frequency": self._freq.value(),
            "five_two_protocol": self._five_two.isChecked(),
            "administration_times": [self._timing_default.currentData()],
            "peptides": peptides,
            "description": self._description.toPlainText().strip(),
        }

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 8, 10, 8)
        outer.setSpacing(6)
        self.setStyleSheet(
            "QWidget { border: 1px solid #424242; border-radius: 6px; }"
            "QLabel, QCheckBox { border: none; }"
        )

        # Header
        header_row = QHBoxLayout()
        self._header_label = QLabel("")
        self._header_label.setStyleSheet(
            "font-weight: bold; color: #42a5f5; border: none;"
        )
        header_row.addWidget(self._header_label)
        header_row.addStretch()
        rm_btn = QPushButton("× Rimuovi")
        rm_btn.setStyleSheet(
            "color: #ef9a9a; background: transparent; border: none;"
        )
        rm_btn.clicked.connect(lambda: self.remove_requested.emit(self))
        header_row.addWidget(rm_btn)
        outer.addLayout(header_row)

        # Fields row
        fields = QHBoxLayout()
        fields.setSpacing(8)
        fields.addWidget(QLabel("Nome:"))
        self._phase_name = QLineEdit(self._phase_data.get("phase_name", ""))
        self._phase_name.setMinimumWidth(160)
        fields.addWidget(self._phase_name)

        fields.addWidget(QLabel("Sett.:"))
        self._weeks = QSpinBox()
        self._weeks.setRange(1, 104)
        self._weeks.setValue(int(self._phase_data.get("duration_weeks", 4)))
        self._weeks.setFixedWidth(58)
        fields.addWidget(self._weeks)

        fields.addWidget(QLabel("Freq/g:"))
        self._freq = QSpinBox()
        self._freq.setRange(1, 10)
        self._freq.setValue(int(self._phase_data.get("daily_frequency", 1)))
        self._freq.setFixedWidth(52)
        fields.addWidget(self._freq)

        self._five_two = QCheckBox("5/2")
        self._five_two.setChecked(
            bool(self._phase_data.get("five_two_protocol", False))
        )
        fields.addWidget(self._five_two)

        fields.addWidget(QLabel("Timing:"))
        self._timing_default = QComboBox()
        for val, lbl in _TIMING_OPTIONS:
            self._timing_default.addItem(lbl, val)
        admin_times = self._phase_data.get("administration_times", ["morning"])
        default_t = admin_times[0] if admin_times else "morning"
        idx = self._timing_default.findData(default_t)
        if idx >= 0:
            self._timing_default.setCurrentIndex(idx)
        fields.addWidget(self._timing_default)

        fields.addStretch()
        outer.addLayout(fields)

        # Description
        desc_row = QHBoxLayout()
        desc_row.addWidget(QLabel("Descr.:"))
        self._description = QTextEdit(self._phase_data.get("description", ""))
        self._description.setMaximumHeight(48)
        desc_row.addWidget(self._description)
        outer.addLayout(desc_row)

        # Peptide table
        outer.addWidget(QLabel("Peptidi:"))
        self._pep_table = QTableWidget(0, 4)
        self._pep_table.setHorizontalHeaderLabels(
            ["Peptide", "Dose (mcg)", "Timing", ""]
        )
        hdr = self._pep_table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.Fixed)
        self._pep_table.setColumnWidth(1, 90)
        hdr.setSectionResizeMode(2, QHeaderView.Fixed)
        self._pep_table.setColumnWidth(2, 90)
        hdr.setSectionResizeMode(3, QHeaderView.Fixed)
        self._pep_table.setColumnWidth(3, 28)
        self._pep_table.setMaximumHeight(130)
        self._pep_table.verticalHeader().setVisible(False)
        self._pep_table.setAlternatingRowColors(True)
        self._pep_table.setStyleSheet("border: 1px solid #424242;")
        outer.addWidget(self._pep_table)

        # Populate existing peptides
        for pep in self._phase_data.get("peptides", []):
            self._insert_pep_row(
                pep.get("peptide_name", "?"),
                pep.get("peptide_id"),
                pep.get("dose_mcg", 0),
                pep.get("timing", "morning"),
            )

        # Add-peptide row
        add_row = QHBoxLayout()
        self._pep_combo = QComboBox()
        for p in self._peptides:
            self._pep_combo.addItem(
                p.get("name", f"#{p.get('id')}"), p.get("id")
            )
        self._pep_combo.setMinimumWidth(160)
        add_row.addWidget(self._pep_combo)

        self._dose_field = QLineEdit()
        self._dose_field.setPlaceholderText("dose mcg")
        self._dose_field.setFixedWidth(80)
        add_row.addWidget(self._dose_field)

        self._add_timing = QComboBox()
        for val, lbl in _TIMING_OPTIONS:
            self._add_timing.addItem(lbl, val)
        self._add_timing.setFixedWidth(90)
        add_row.addWidget(self._add_timing)

        add_pep_btn = QPushButton("+ Peptide")
        add_pep_btn.clicked.connect(self._add_peptide)
        add_row.addWidget(add_pep_btn)
        add_row.addStretch()
        outer.addLayout(add_row)

    def _insert_pep_row(self, name, pep_id, dose, timing):
        r = self._pep_table.rowCount()
        self._pep_table.insertRow(r)

        name_item = QTableWidgetItem(name)
        name_item.setData(Qt.UserRole, pep_id)
        name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
        self._pep_table.setItem(r, 0, name_item)

        self._pep_table.setItem(r, 1, QTableWidgetItem(str(dose)))

        t_combo = QComboBox()
        for val, lbl in _TIMING_OPTIONS:
            t_combo.addItem(lbl, val)
        idx = t_combo.findData(timing)
        if idx >= 0:
            t_combo.setCurrentIndex(idx)
        self._pep_table.setCellWidget(r, 2, t_combo)

        rm = QPushButton("×")
        rm.setStyleSheet(
            "color: #ef9a9a; background: transparent; border: none; padding: 0;"
        )
        rm.clicked.connect(self._remove_pep_row)
        self._pep_table.setCellWidget(r, 3, rm)

    def _add_peptide(self):
        if self._pep_combo.count() == 0:
            return
        dose_text = self._dose_field.text().strip()
        try:
            dose = float(dose_text) if dose_text else 0.0
        except ValueError:
            dose = 0.0
        self._insert_pep_row(
            self._pep_combo.currentText(),
            self._pep_combo.currentData(),
            dose,
            self._add_timing.currentData(),
        )
        self._dose_field.clear()

    def _remove_pep_row(self):
        btn = self.sender()
        for r in range(self._pep_table.rowCount()):
            if self._pep_table.cellWidget(r, 3) is btn:
                self._pep_table.removeRow(r)
                return


class _TemplateDetailsDialog(QDialog):
    """Read-only details view for a template, showing all phases."""

    def __init__(self, app, template_id, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Template #{template_id}")
        self.setMinimumWidth(540)
        self.setStyleSheet(_DLG_STYLE)

        try:
            cur = app.manager.conn.cursor()
            cur.execute("""
                SELECT name, short_name, category, total_phases,
                       total_duration_weeks, is_active,
                       phases_config, source, notes
                FROM treatment_plan_templates WHERE id = ?
            """, (template_id,))
            row = cur.fetchone()
        except Exception as e:
            error_dialog(self, "Errore", str(e))
            self.reject()
            return

        if not row:
            error_dialog(self, "Errore", "Template non trovato")
            self.reject()
            return

        (name, short_name, cat, total_phases, total_weeks,
         active, phases_config, source, notes) = row

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Title
        title_lbl = QLabel(name)
        title_lbl.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title_lbl)

        # Info grid
        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(5)
        cat_labels = dict(_CATEGORY_OPTIONS)
        rows_info = [
            ("Categoria", cat_labels.get(cat, cat or "—")),
            ("Nome Breve", short_name or "—"),
            ("Durata Totale", f"{total_phases} fasi, {total_weeks} sett."),
            ("Attivo", "Sì" if active else "No"),
            ("Fonte", source or "—"),
        ]
        for r_idx, (lbl, val) in enumerate(rows_info):
            l = QLabel(lbl)
            l.setStyleSheet("color: #aeaeae;")
            l.setAlignment(Qt.AlignRight | Qt.AlignTop)
            grid.addWidget(l, r_idx, 0)
            v = QLabel(str(val))
            v.setWordWrap(True)
            grid.addWidget(v, r_idx, 1)
        if notes:
            n_lbl = QLabel("Note")
            n_lbl.setStyleSheet("color: #aeaeae;")
            n_lbl.setAlignment(Qt.AlignRight | Qt.AlignTop)
            grid.addWidget(n_lbl, len(rows_info), 0)
            n_val = QLabel(notes)
            n_val.setWordWrap(True)
            grid.addWidget(n_val, len(rows_info), 1)
        layout.addLayout(grid)

        # Phases
        try:
            phases = json.loads(phases_config or "[]") or []
        except json.JSONDecodeError:
            phases = []

        if phases:
            layout.addWidget(_sep(f"Fasi ({len(phases)})"))
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setStyleSheet("QScrollArea { border: none; }")
            container = QWidget()
            c_lay = QVBoxLayout(container)
            c_lay.setSpacing(6)
            for ph in phases:
                ph_name = ph.get("phase_name", f"Fase {ph.get('phase_number', '?')}")
                ph_weeks = ph.get("duration_weeks", "?")
                ph_freq = ph.get("daily_frequency", 1)
                ph_52 = " [5/2]" if ph.get("five_two_protocol") else ""
                ph_lbl = QLabel(
                    f"  {ph.get('phase_number', '?')}. {ph_name}"
                    f" — {ph_weeks} sett., {ph_freq}×/g{ph_52}"
                )
                ph_lbl.setStyleSheet("color: #e0e0e0; font-weight: bold;")
                c_lay.addWidget(ph_lbl)
                for pep in ph.get("peptides", []):
                    pep_lbl = QLabel(
                        f"     • {pep.get('peptide_name', '?')}"
                        f" {pep.get('dose_mcg', 0)} mcg"
                        f" [{pep.get('timing', '')}]"
                    )
                    pep_lbl.setStyleSheet("color: #aeaeae;")
                    c_lay.addWidget(pep_lbl)
                if ph.get("description"):
                    d_lbl = QLabel(f"     {ph['description']}")
                    d_lbl.setStyleSheet("color: #757575; font-style: italic;")
                    d_lbl.setWordWrap(True)
                    c_lay.addWidget(d_lbl)
            c_lay.addStretch()
            scroll.setWidget(container)
            layout.addWidget(scroll, 1)

        close_btn = QPushButton("Chiudi")
        close_btn.setFixedWidth(100)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignRight)
