"""Archive section — Peptidi, Fornitori, Janoshik, Calcolatore tabs."""

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QWidget,
    QSpinBox,
    QDoubleSpinBox,
    QTextEdit,
    QComboBox,
    QTabWidget,
    QGroupBox,
    QSplitter,
    QFrame,
)
from PySide6.QtCore import Qt

from .base import BaseView
from ..components.data_table import DataTable
from ..components.dialogs import confirm_dialog, error_dialog

# ── Shared dialog style ───────────────────────────────────────────────────

_DLG_STYLE = (
    "QDialog { background: #1e1e1e; }"
    "QLineEdit, QComboBox, QTextEdit, QSpinBox, QDoubleSpinBox {"
    " background: #2d2d2d; border: 1px solid #424242;"
    " border-radius: 4px; padding: 6px 10px; color: #e0e0e0; }"
    "QLineEdit:focus, QTextEdit:focus { border-color: #42a5f5; }"
)


def _label(text, bold=False):
    lbl = QLabel(text)
    if bold:
        lbl.setStyleSheet("font-weight: bold;")
    return lbl


def _section_label(text):
    lbl = QLabel(text)
    lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #90caf9;")
    return lbl


# ═════════════════════════════════════════════════════════════════════════
#  PEPTIDI TAB
# ═════════════════════════════════════════════════════════════════════════


class PeptidiTab(BaseView):
    """Peptide catalog: search, add, edit, delete."""

    def __init__(self, app, parent=None):
        super().__init__(app, parent)
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        lay = self.layout()

        toolbar = QHBoxLayout()
        title = QLabel("Peptidi")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        toolbar.addWidget(title)
        toolbar.addStretch()

        self._search = QLineEdit()
        self._search.setPlaceholderText("Cerca peptide...")
        self._search.setFixedWidth(250)
        self._search.textChanged.connect(lambda: self.refresh())
        toolbar.addWidget(self._search)

        add_btn = QPushButton("Aggiungi Peptide")
        add_btn.clicked.connect(self._on_add)
        toolbar.addWidget(add_btn)
        lay.addLayout(toolbar)

        self._table = DataTable([
            {"key": "id",           "label": "ID",          "width": 50},
            {"key": "name",         "label": "Nome",        "stretch": True},
            {"key": "description",  "label": "Descrizione", "stretch": True},
            {"key": "common_uses",  "label": "Usi comuni",  "stretch": True},
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

    def refresh(self):
        search = self._search.text().strip() or None
        try:
            rows = self.manager.get_peptides(search=search)
        except Exception as e:
            error_dialog(self, "Errore", str(e))
            return
        self._table.load_data(sorted(rows, key=lambda r: r.get("id", 0)))

    def _on_add(self):
        dlg = _PeptideDialog(self.app, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh()

    def _on_details(self, row):
        dlg = _PeptideDetailsDialog(self.app, row["id"], parent=self)
        dlg.exec()

    def _on_edit(self, row):
        dlg = _PeptideDialog(self.app, peptide_id=row["id"], parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh()

    def _on_delete(self, row):
        if not confirm_dialog(
            self, "Elimina Peptide",
            f"Eliminare '{row['name']}'? L'operazione è reversibile.",
        ):
            return
        try:
            self.manager.soft_delete_peptide(row["id"])
            self.app.show_message("Peptide eliminato")
            self.refresh()
        except Exception as e:
            error_dialog(self, "Errore", str(e))


class _PeptideDialog(QDialog):
    """Add / Edit peptide."""

    def __init__(self, app, peptide_id=None, parent=None):
        super().__init__(parent)
        self._app = app
        self._id = peptide_id
        self.setWindowTitle("Modifica Peptide" if peptide_id else "Aggiungi Peptide")
        self.setMinimumWidth(420)
        self.setStyleSheet(_DLG_STYLE)

        existing = None
        if peptide_id:
            existing = app.manager.get_peptide_by_id(peptide_id)

        lay = QVBoxLayout(self)
        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.WrapAllRows)

        self._name = QLineEdit(existing.get("name", "") if existing else "")
        self._name.setPlaceholderText("es: BPC-157")
        form.addRow("Nome *", self._name)

        self._desc = QTextEdit(existing.get("description") or "" if existing else "")
        self._desc.setFixedHeight(70)
        form.addRow("Descrizione", self._desc)

        self._uses = QTextEdit(existing.get("common_uses") or "" if existing else "")
        self._uses.setFixedHeight(70)
        form.addRow("Usi comuni", self._uses)

        self._notes = QTextEdit(existing.get("notes") or "" if existing else "")
        self._notes.setFixedHeight(55)
        form.addRow("Note", self._notes)

        lay.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Annulla")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Salva")
        save_btn.setStyleSheet(
            "background: #42a5f5; color: #fff; padding: 8px 16px;"
            " border-radius: 4px; font-weight: bold;"
        )
        save_btn.clicked.connect(self._submit)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        lay.addLayout(btn_row)

    def _submit(self):
        name = self._name.text().strip()
        if not name:
            error_dialog(self, "Validazione", "Il nome è obbligatorio.")
            return
        desc = self._desc.toPlainText().strip() or None
        uses = self._uses.toPlainText().strip() or None
        notes = self._notes.toPlainText().strip() or None
        try:
            if self._id:
                self._app.manager.update_peptide(
                    self._id, name=name, description=desc,
                    common_uses=uses, notes=notes,
                )
            else:
                self._app.manager.add_peptide(
                    name=name, description=desc,
                    common_uses=uses, notes=notes,
                )
        except Exception as e:
            error_dialog(self, "Errore", str(e))
            return
        self.accept()


class _PeptideDetailsDialog(QDialog):
    def __init__(self, app, peptide_id, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Peptide #{peptide_id}")
        self.setMinimumWidth(380)
        self.setStyleSheet(_DLG_STYLE)
        lay = QVBoxLayout(self)

        try:
            p = app.manager.get_peptide_by_id(peptide_id)
        except Exception:
            p = None

        if not p:
            lay.addWidget(QLabel("Peptide non trovato."))
        else:
            lay.addWidget(_label(p.get("name", "?"), bold=True))
            form = QFormLayout()
            form.addRow("Descrizione:", QLabel(p.get("description") or "—"))
            form.addRow("Usi comuni:",  QLabel(p.get("common_uses") or "—"))
            form.addRow("Note:",        QLabel(p.get("notes") or "—"))
            lay.addLayout(form)

        close_btn = QPushButton("Chiudi")
        close_btn.clicked.connect(self.accept)
        lay.addWidget(close_btn, alignment=Qt.AlignRight)


# ═════════════════════════════════════════════════════════════════════════
#  FORNITORI TAB
# ═════════════════════════════════════════════════════════════════════════


class FornitoriTab(BaseView):
    """Supplier catalog: search, add, edit, delete."""

    def __init__(self, app, parent=None):
        super().__init__(app, parent)
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        lay = self.layout()

        toolbar = QHBoxLayout()
        title = QLabel("Fornitori")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        toolbar.addWidget(title)
        toolbar.addStretch()

        self._search = QLineEdit()
        self._search.setPlaceholderText("Cerca fornitore...")
        self._search.setFixedWidth(250)
        self._search.textChanged.connect(lambda: self.refresh())
        toolbar.addWidget(self._search)

        add_btn = QPushButton("Aggiungi Fornitore")
        add_btn.clicked.connect(self._on_add)
        toolbar.addWidget(add_btn)
        lay.addLayout(toolbar)

        self._table = DataTable([
            {"key": "id",                     "label": "ID",      "width": 50},
            {"key": "name",                   "label": "Nome",    "stretch": True},
            {"key": "country",                "label": "Paese",   "width": 100},
            {"key": "website",                "label": "Sito",    "stretch": True},
            {"key": "rating",                 "label": "Rating",  "width": 70},
            {"key": "janoshik_quality_score", "label": "Score",   "width": 70},
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

    def refresh(self):
        search = self._search.text().strip() or None
        try:
            rows = self.manager.get_suppliers(search=search)
        except Exception as e:
            error_dialog(self, "Errore", str(e))
            return
        for r in rows:
            if r.get("rating"):
                r["rating"] = f"{'★' * int(r['rating'])}{'☆' * (5 - int(r['rating']))}"
            score = r.get("janoshik_quality_score")
            r["janoshik_quality_score"] = f"{score:.1f}" if score else "—"
        self._table.load_data(sorted(rows, key=lambda r: r.get("id", 0)))

    def _on_add(self):
        dlg = _SupplierDialog(self.app, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh()

    def _on_details(self, row):
        dlg = _SupplierDetailsDialog(self.app, row["id"], parent=self)
        dlg.exec()

    def _on_edit(self, row):
        dlg = _SupplierDialog(self.app, supplier_id=row["id"], parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh()

    def _on_delete(self, row):
        if not confirm_dialog(
            self, "Elimina Fornitore",
            f"Eliminare '{row['name']}'?",
        ):
            return
        try:
            self.manager.soft_delete_supplier(row["id"])
            self.app.show_message("Fornitore eliminato")
            self.refresh()
        except Exception as e:
            error_dialog(self, "Errore", str(e))


class _SupplierDialog(QDialog):
    """Add / Edit supplier."""

    def __init__(self, app, supplier_id=None, parent=None):
        super().__init__(parent)
        self._app = app
        self._id = supplier_id
        self.setWindowTitle("Modifica Fornitore" if supplier_id else "Aggiungi Fornitore")
        self.setMinimumWidth(420)
        self.setStyleSheet(_DLG_STYLE)

        existing = None
        if supplier_id:
            existing = app.manager.get_supplier_by_id(supplier_id)

        lay = QVBoxLayout(self)
        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.WrapAllRows)

        self._name    = QLineEdit(existing.get("name", "") if existing else "")
        self._country = QLineEdit(existing.get("country") or "" if existing else "")
        self._website = QLineEdit(existing.get("website") or "" if existing else "")
        self._email   = QLineEdit(existing.get("email") or "" if existing else "")

        self._rating = QSpinBox()
        self._rating.setRange(0, 5)
        self._rating.setSpecialValueText("—")
        if existing and existing.get("rating"):
            self._rating.setValue(int(existing["rating"]))

        self._notes = QTextEdit(existing.get("notes") or "" if existing else "")
        self._notes.setFixedHeight(70)

        form.addRow("Nome *",   self._name)
        form.addRow("Paese",    self._country)
        form.addRow("Sito web", self._website)
        form.addRow("Email",    self._email)
        form.addRow("Rating",   self._rating)
        form.addRow("Note",     self._notes)
        lay.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Annulla")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Salva")
        save_btn.setStyleSheet(
            "background: #42a5f5; color: #fff; padding: 8px 16px;"
            " border-radius: 4px; font-weight: bold;"
        )
        save_btn.clicked.connect(self._submit)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        lay.addLayout(btn_row)

    def _submit(self):
        name = self._name.text().strip()
        if not name:
            error_dialog(self, "Validazione", "Il nome è obbligatorio.")
            return
        rating = self._rating.value() or None
        try:
            if self._id:
                self._app.manager.update_supplier(
                    self._id,
                    name=name,
                    country=self._country.text().strip() or None,
                    website=self._website.text().strip() or None,
                    email=self._email.text().strip() or None,
                    rating=rating,
                    notes=self._notes.toPlainText().strip() or None,
                )
            else:
                self._app.manager.add_supplier(
                    name=name,
                    country=self._country.text().strip() or None,
                    website=self._website.text().strip() or None,
                    email=self._email.text().strip() or None,
                    rating=rating,
                    notes=self._notes.toPlainText().strip() or None,
                )
        except Exception as e:
            error_dialog(self, "Errore", str(e))
            return
        self.accept()


class _SupplierDetailsDialog(QDialog):
    def __init__(self, app, supplier_id, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Fornitore #{supplier_id}")
        self.setMinimumWidth(380)
        self.setStyleSheet(_DLG_STYLE)
        lay = QVBoxLayout(self)

        try:
            s = app.manager.get_supplier_by_id(supplier_id)
        except Exception:
            s = None

        if not s:
            lay.addWidget(QLabel("Fornitore non trovato."))
        else:
            lay.addWidget(_label(s.get("name", "?"), bold=True))
            form = QFormLayout()
            form.addRow("Paese:",   QLabel(s.get("country") or "—"))
            form.addRow("Sito:",    QLabel(s.get("website") or "—"))
            form.addRow("Email:",   QLabel(s.get("email") or "—"))
            rating = s.get("rating")
            form.addRow("Rating:",  QLabel(f"{'★' * int(rating)}{'☆' * (5 - int(rating))}" if rating else "—"))
            score = s.get("janoshik_quality_score")
            form.addRow("Score Janoshik:", QLabel(f"{score:.1f}" if score else "—"))
            form.addRow("Note:",    QLabel(s.get("notes") or "—"))
            lay.addLayout(form)

        close_btn = QPushButton("Chiudi")
        close_btn.clicked.connect(self.accept)
        lay.addWidget(close_btn, alignment=Qt.AlignRight)


# ═════════════════════════════════════════════════════════════════════════
#  JANOSHIK TAB
# ═════════════════════════════════════════════════════════════════════════


class JanoshikTab(BaseView):
    """Janoshik analysis: supplier rankings + vendor search."""

    def __init__(self, app, parent=None):
        super().__init__(app, parent)
        self._logic = None
        try:
            from peptide_manager.janoshik.views_logic import JanoshikViewsLogic
            self._logic = JanoshikViewsLogic(app.db_path)
        except Exception:
            pass
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        lay = self.layout()

        # Header
        header = QHBoxLayout()
        title = QLabel("Janoshik")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        header.addWidget(title)
        header.addStretch()
        refresh_btn = QPushButton("Aggiorna Dati")
        refresh_btn.clicked.connect(self.refresh)
        header.addWidget(refresh_btn)
        lay.addLayout(header)

        if not self._logic:
            lay.addWidget(
                QLabel("Modulo Janoshik non disponibile."),
                alignment=Qt.AlignCenter,
            )
            return

        tabs = QTabWidget()

        # ── Tab 1: Classifica Fornitori ───────────────────────────────
        rankings_widget = QWidget()
        rankings_lay = QVBoxLayout(rankings_widget)

        self._rankings_table = DataTable([
            {"key": "rank",             "label": "#",           "width": 40},
            {"key": "supplier_name",    "label": "Fornitore",   "stretch": True},
            {"key": "avg_purity",       "label": "Purezza %",   "width": 90},
            {"key": "std_purity",       "label": "Score",       "width": 80},
            {"key": "total_certs",      "label": "Certificati", "width": 90},
            {"key": "quality_badge",    "label": "Qualità",     "width": 90},
        ])
        rankings_lay.addWidget(self._rankings_table)
        tabs.addTab(rankings_widget, "Classifica Fornitori")

        # ── Tab 2: Ricerca Vendor ─────────────────────────────────────
        search_widget = QWidget()
        search_lay = QVBoxLayout(search_widget)

        search_bar = QHBoxLayout()
        self._peptide_search = QLineEdit()
        self._peptide_search.setPlaceholderText("Nome peptide (es: BPC-157)...")
        self._peptide_search.setFixedWidth(300)
        search_btn = QPushButton("Cerca")
        search_btn.clicked.connect(self._on_vendor_search)
        self._peptide_search.returnPressed.connect(self._on_vendor_search)
        search_bar.addWidget(self._peptide_search)
        search_bar.addWidget(search_btn)
        search_bar.addStretch()
        search_lay.addLayout(search_bar)

        self._vendor_table = DataTable([
            {"key": "supplier_name",       "label": "Vendor",          "stretch": True},
            {"key": "avg_purity",          "label": "Purezza %",       "width": 90},
            {"key": "certificates",        "label": "Certificati",     "width": 90},
            {"key": "last_test",           "label": "Ultimo test",     "width": 110},
            {"key": "recommendation_score","label": "Score",           "width": 70},
        ])
        search_lay.addWidget(self._vendor_table)
        tabs.addTab(search_widget, "Ricerca Vendor")

        lay.addWidget(tabs, 1)

    def refresh(self):
        self._load_rankings()

    def _load_rankings(self):
        if not self._logic:
            return
        try:
            from peptide_manager.janoshik.views_logic import TimeWindow
            results = self._logic.get_supplier_rankings(time_window=TimeWindow.ALL)
            rows = []
            for item in results:
                rows.append({
                    "rank":          item.rank,
                    "supplier_name": item.supplier_name,
                    "avg_purity":    f"{item.avg_purity:.1f}",
                    "std_purity":    f"{item.composite_score:.1f}",
                    "total_certs":   item.total_certificates,
                    "quality_badge": item.quality_badge,
                })
            self._rankings_table.load_data(rows)
        except Exception as e:
            error_dialog(self, "Errore caricamento classifica", str(e))

    def _on_vendor_search(self):
        if not self._logic:
            return
        peptide = self._peptide_search.text().strip()
        if not peptide:
            return
        try:
            result = self._logic.search_vendors_for_peptide(peptide)
            vendors = result.get("all_vendors", [])
            rows = []
            for v in vendors:
                rows.append({
                    "supplier_name":        v.supplier_name,
                    "avg_purity":           f"{v.avg_purity:.1f}" if v.avg_purity else "—",
                    "certificates":         v.certificates,
                    "last_test":            str(v.last_test)[:10] if v.last_test else "—",
                    "recommendation_score": v.recommendation_score,
                })
            self._vendor_table.load_data(rows)
            if not rows:
                self.app.show_message(f"Nessun risultato per '{peptide}'")
        except Exception as e:
            error_dialog(self, "Errore ricerca", str(e))


# ═════════════════════════════════════════════════════════════════════════
#  CALCOLATORE TAB
# ═════════════════════════════════════════════════════════════════════════


class CalcolatoreTab(BaseView):
    """Dose calculator: mcg ↔ ml with active-prep or simulation mode."""

    def __init__(self, app, parent=None):
        super().__init__(app, parent)
        self._concentration_mcg_ml = 0.0
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        lay = self.layout()

        title = QLabel("Calcolatore Dosi")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        lay.addWidget(title)

        # ── Configuration panel ───────────────────────────────────────
        config_group = QGroupBox("Configurazione preparazione")
        config_lay = QVBoxLayout(config_group)

        # Mode selector
        mode_row = QHBoxLayout()
        self._mode_combo = QComboBox()
        self._mode_combo.addItem("Preparazione attiva",  "active")
        self._mode_combo.addItem("Simula preparazione",  "simulate")
        self._mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        mode_row.addWidget(QLabel("Modalità:"))
        mode_row.addWidget(self._mode_combo)
        mode_row.addStretch()
        config_lay.addLayout(mode_row)

        # Active prep selector
        self._prep_combo = QComboBox()
        self._prep_combo.setMinimumWidth(420)
        self._prep_combo.currentIndexChanged.connect(self._on_prep_changed)
        prep_row = QHBoxLayout()
        prep_row.addWidget(QLabel("Preparazione:"))
        prep_row.addWidget(self._prep_combo)
        prep_row.addStretch()
        self._prep_row_widget = QWidget()
        self._prep_row_widget.setLayout(prep_row)
        config_lay.addWidget(self._prep_row_widget)

        # Simulate inputs
        sim_form = QHBoxLayout()
        self._sim_mg = QDoubleSpinBox()
        self._sim_mg.setRange(0.01, 1000)
        self._sim_mg.setDecimals(2)
        self._sim_mg.setSuffix(" mg/fiala")
        self._sim_mg.setValue(5.0)
        self._sim_mg.valueChanged.connect(self._on_sim_changed)

        self._sim_vials = QSpinBox()
        self._sim_vials.setRange(1, 100)
        self._sim_vials.setValue(1)
        self._sim_vials.setSuffix(" fiale")
        self._sim_vials.valueChanged.connect(self._on_sim_changed)

        self._sim_water = QDoubleSpinBox()
        self._sim_water.setRange(0.1, 50)
        self._sim_water.setDecimals(1)
        self._sim_water.setSuffix(" ml H₂O")
        self._sim_water.setValue(2.0)
        self._sim_water.valueChanged.connect(self._on_sim_changed)

        sim_form.addWidget(self._sim_mg)
        sim_form.addWidget(QLabel("×"))
        sim_form.addWidget(self._sim_vials)
        sim_form.addWidget(QLabel("+"))
        sim_form.addWidget(self._sim_water)
        sim_form.addStretch()
        self._sim_widget = QWidget()
        self._sim_widget.setLayout(sim_form)
        config_lay.addWidget(self._sim_widget)

        # Concentration info line
        self._conc_label = QLabel("Concentrazione: —")
        self._conc_label.setStyleSheet("color: #90caf9; font-size: 12px;")
        config_lay.addWidget(self._conc_label)

        lay.addWidget(config_group)

        # ── Calculator panels ─────────────────────────────────────────
        calc_row = QHBoxLayout()

        # mcg → ml
        mcg_group = QGroupBox("Dose → Volume  (mcg → ml)")
        mcg_lay = QFormLayout(mcg_group)
        self._mcg_input = QDoubleSpinBox()
        self._mcg_input.setRange(0, 100000)
        self._mcg_input.setDecimals(1)
        self._mcg_input.setSuffix(" mcg")
        self._mcg_input.valueChanged.connect(self._calc_ml)
        self._ml_result = QLabel("—")
        self._ml_result.setStyleSheet("font-size: 14px; font-weight: bold; color: #a5d6a7;")
        self._units_result = QLabel("—")
        self._units_result.setStyleSheet("color: #90caf9;")
        mcg_lay.addRow("Dose:", self._mcg_input)
        mcg_lay.addRow("Volume:", self._ml_result)
        mcg_lay.addRow("Unità siringha:", self._units_result)
        calc_row.addWidget(mcg_group)

        # ml → mcg
        ml_group = QGroupBox("Volume → Dose  (ml → mcg)")
        ml_lay = QFormLayout(ml_group)
        self._ml_input = QDoubleSpinBox()
        self._ml_input.setRange(0, 100)
        self._ml_input.setDecimals(2)
        self._ml_input.setSuffix(" ml")
        self._ml_input.setSingleStep(0.01)
        self._ml_input.valueChanged.connect(self._calc_mcg)
        self._mcg_result = QLabel("—")
        self._mcg_result.setStyleSheet("font-size: 14px; font-weight: bold; color: #90caf9;")
        ml_lay.addRow("Volume:", self._ml_input)
        ml_lay.addRow("Dose:", self._mcg_result)
        calc_row.addWidget(ml_group)

        lay.addLayout(calc_row)
        lay.addStretch()

        # Initial mode
        self._on_mode_changed()

    def refresh(self):
        """Reload active preparations list."""
        try:
            preps = self.manager.get_preparations(only_active=True)
        except Exception:
            preps = []

        self._prep_combo.blockSignals(True)
        self._prep_combo.clear()
        self._prep_combo.addItem("— seleziona —", None)
        for p in preps:
            label = (
                f"#{p['id']} — {p.get('batch_product', '?')}"
                f" ({p.get('volume_remaining_ml', 0):.1f} ml rimasti)"
            )
            self._prep_combo.addItem(label, p["id"])
        self._prep_combo.blockSignals(False)

        if self._mode_combo.currentData() == "active":
            self._on_prep_changed()

    def _on_mode_changed(self):
        active = self._mode_combo.currentData() == "active"
        self._prep_row_widget.setVisible(active)
        self._sim_widget.setVisible(not active)
        if active:
            self._on_prep_changed()
        else:
            self._on_sim_changed()

    def _on_prep_changed(self):
        prep_id = self._prep_combo.currentData()
        if not prep_id:
            self._set_concentration(0.0, "Nessuna preparazione selezionata")
            return
        try:
            details = self.manager.get_preparation_details(prep_id)
            if details and details.get("concentration_mcg_ml"):
                conc = float(details["concentration_mcg_ml"])
                name = details.get("batch_product", "?")
                self._set_concentration(conc, f"{name} — {conc:.1f} mcg/ml")
            else:
                self._set_concentration(0.0, "Concentrazione non disponibile")
        except Exception as e:
            self._set_concentration(0.0, f"Errore: {e}")

    def _on_sim_changed(self):
        mg = self._sim_mg.value()
        vials = self._sim_vials.value()
        water = self._sim_water.value()
        if water <= 0:
            self._set_concentration(0.0, "Volume acqua non valido")
            return
        total_mg = mg * vials
        conc = total_mg * 1000.0 / water  # mcg/ml
        self._set_concentration(conc, f"Simulazione: {total_mg:.2f} mg / {water:.1f} ml = {conc:.1f} mcg/ml")

    def _set_concentration(self, conc_mcg_ml, info_text):
        self._concentration_mcg_ml = conc_mcg_ml
        self._conc_label.setText(f"Concentrazione: {info_text}")
        self._calc_ml()
        self._calc_mcg()

    def _calc_ml(self):
        dose_mcg = self._mcg_input.value()
        if self._concentration_mcg_ml <= 0 or dose_mcg <= 0:
            self._ml_result.setText("—")
            self._units_result.setText("—")
            return
        ml = dose_mcg / self._concentration_mcg_ml
        units = ml * 100  # U100 syringe: 1 unit = 0.01 ml
        self._ml_result.setText(f"{ml:.3f} ml")
        self._units_result.setText(f"{units:.1f} U")

    def _calc_mcg(self):
        vol_ml = self._ml_input.value()
        if self._concentration_mcg_ml <= 0 or vol_ml <= 0:
            self._mcg_result.setText("—")
            return
        mcg = vol_ml * self._concentration_mcg_ml
        self._mcg_result.setText(f"{mcg:.1f} mcg")
