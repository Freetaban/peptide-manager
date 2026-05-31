"""Archive section — Peptidi, Fornitori, Calcolatore tabs."""

import re
from pathlib import Path

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
    QTextBrowser,
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

# ── Compendium parser ─────────────────────────────────────────────────────

_DOCS_DIR = Path(__file__).parent.parent.parent / "docs"
_COMPENDIUM_FILES = [
    _DOCS_DIR / "COMPENDIO_PEPTIDI.md",
    _DOCS_DIR / "COMPENDIO_AAS_FARMACI.md",
]


def _norm(name: str) -> str:
    """Normalise a name for matching: lowercase, strip non-alphanumeric."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


class _CompendiumParser:
    """Lazy singleton: parses both compendium docs and exposes lookup()."""

    _instance = None

    @classmethod
    def get(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._sections: dict[str, str] = {}  # norm_key → raw markdown text
        for path in _COMPENDIUM_FILES:
            if path.exists():
                self._parse(path.read_text(encoding="utf-8"))

    def _parse(self, text: str):
        """Split on ### headers; register each section under all name variants."""
        lines = text.splitlines()
        current_header = None
        current_lines: list[str] = []

        def _flush():
            if current_header:
                self._register(current_header, "\n".join(current_lines))

        for line in lines:
            if line.startswith("### "):
                _flush()
                current_header = line[4:].strip()
                current_lines = []
            elif line.startswith("## ") or line.strip() == "---":
                # Don't flush on ## or --- — keep accumulating inside section
                # (--- separators between sections in the same ## group are ok)
                current_lines.append(line)
            else:
                current_lines.append(line)

        _flush()

    def _register(self, header: str, content: str):
        """Register a section under the main name and any parenthetical aliases."""
        # header examples: "BPC-157", "TB-500 (Thymosin Beta-4)", "PT-141 (Bremelanotide)"
        parts = re.split(r"[(/]", header)
        names = [p.strip().rstrip(")") for p in parts if p.strip()]
        for name in names:
            key = _norm(name)
            if key and key not in self._sections:
                self._sections[key] = f"### {header}\n{content}"

    def lookup(self, peptide_name: str) -> str | None:
        """Return raw markdown for peptide_name, or None if not found."""
        key = _norm(peptide_name)
        if key in self._sections:
            return self._sections[key]
        # partial match fallback: check if key is a substring of any registered key
        for k, v in self._sections.items():
            if key in k or k in key:
                return v
        return None


def _md_to_html(md: str) -> str:
    """Convert structured markdown to HTML for QTextBrowser."""
    lines = md.splitlines()
    html_parts = ["<style>"
                  "body{font-family:sans-serif;font-size:13px;color:#e0e0e0;"
                  "background:#1e1e1e;padding:8px}"
                  "h2{color:#90caf9;margin:12px 0 4px}"
                  "h3{color:#80cbc4;margin:10px 0 4px}"
                  "h4{color:#ce93d8;margin:8px 0 2px}"
                  "table{border-collapse:collapse;width:100%;margin:6px 0}"
                  "td,th{border:1px solid #424242;padding:4px 8px;text-align:left}"
                  "th{background:#2d2d2d;color:#90caf9}"
                  "tr:nth-child(even){background:#252525}"
                  "ul{margin:4px 0;padding-left:20px}"
                  "li{margin:2px 0}"
                  "b{color:#ffcc02}"
                  "hr{border:none;border-top:1px solid #424242;margin:10px 0}"
                  "</style><body>"]

    in_table = False
    in_list = False
    i = 0
    while i < len(lines):
        line = lines[i]

        # Close open lists before non-list content
        if in_list and not line.strip().startswith("- "):
            html_parts.append("</ul>")
            in_list = False

        if line.startswith("### "):
            if in_table:
                html_parts.append("</table>"); in_table = False
            html_parts.append(f"<h3>{line[4:].strip()}</h3>")
        elif line.startswith("## "):
            if in_table:
                html_parts.append("</table>"); in_table = False
            html_parts.append(f"<h2>{line[3:].strip()}</h2>")
        elif line.startswith("#### "):
            html_parts.append(f"<h4>{line[5:].strip()}</h4>")
        elif line.strip() == "---":
            if in_table:
                html_parts.append("</table>"); in_table = False
            html_parts.append("<hr>")
        elif line.startswith("|"):
            # Markdown table row
            cells = [c.strip() for c in line.strip("|").split("|")]
            # Skip separator rows like |---|---|
            if all(re.match(r"^[-: ]+$", c) for c in cells):
                i += 1
                continue
            if not in_table:
                html_parts.append("<table>")
                in_table = True
                # First row → header
                row = "".join(f"<th>{_inline(c)}</th>" for c in cells)
                html_parts.append(f"<tr>{row}</tr>")
            else:
                row = "".join(f"<td>{_inline(c)}</td>" for c in cells)
                html_parts.append(f"<tr>{row}</tr>")
        else:
            if in_table:
                html_parts.append("</table>"); in_table = False
            stripped = line.strip()
            if stripped.startswith("- ") or stripped.startswith("* "):
                if not in_list:
                    html_parts.append("<ul>"); in_list = True
                html_parts.append(f"<li>{_inline(stripped[2:])}</li>")
            elif stripped:
                html_parts.append(f"<p>{_inline(stripped)}</p>")

        i += 1

    if in_table:
        html_parts.append("</table>")
    if in_list:
        html_parts.append("</ul>")
    html_parts.append("</body>")
    return "\n".join(html_parts)


def _inline(text: str) -> str:
    """Convert inline markdown (bold, italic, code) to HTML."""
    # **bold**
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    # *italic*
    text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
    # `code`
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
    return text


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
        self.setMinimumSize(760, 680)
        self.setStyleSheet(_DLG_STYLE)
        lay = QVBoxLayout(self)
        lay.setSpacing(8)

        try:
            p = app.manager.get_peptide_by_id(peptide_id)
        except Exception:
            p = None

        if not p:
            lay.addWidget(QLabel("Peptide non trovato."))
            close_btn = QPushButton("Chiudi")
            close_btn.clicked.connect(self.accept)
            lay.addWidget(close_btn, alignment=Qt.AlignRight)
            return

        name = p.get("name", "?")
        self.setWindowTitle(name)

        # ── DB info (compatta, in cima) ───────────────────────────────────
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet("font-size: 20px; font-weight: bold; color: #90caf9;")
        lay.addWidget(name_lbl)

        db_frame = QFrame()
        db_frame.setStyleSheet("QFrame { background: #252525; border-radius: 6px; }")
        db_lay = QFormLayout(db_frame)
        db_lay.setContentsMargins(12, 8, 12, 8)
        db_lay.setSpacing(4)
        db_lay.setHorizontalSpacing(16)

        def _db_row(label, value):
            if value:
                lbl = QLabel(value)
                lbl.setWordWrap(True)
                db_lay.addRow(f"<b>{label}</b>", lbl)

        _db_row("Descrizione", p.get("description"))
        _db_row("Usi comuni",  p.get("common_uses"))
        aliases = p.get("aliases", [])
        _db_row("Sinonimi",    ", ".join(aliases) if aliases else None)
        _db_row("Note",        p.get("notes"))

        if db_lay.rowCount() > 0:
            lay.addWidget(db_frame)

        # ── Compendium section ────────────────────────────────────────────
        compendium_md = _CompendiumParser.get().lookup(name)

        sep = QLabel("Scheda di riferimento scientifica")
        sep.setStyleSheet(
            "font-size: 12px; font-weight: bold; color: #757575;"
            " border-top: 1px solid #424242; padding-top: 8px;"
        )
        lay.addWidget(sep)

        browser = QTextBrowser()
        browser.setOpenExternalLinks(False)
        browser.setStyleSheet(
            "QTextBrowser { background: #1a1a1a; border: 1px solid #333;"
            " border-radius: 4px; padding: 4px; }"
        )

        if compendium_md:
            browser.setHtml(_md_to_html(compendium_md))
        else:
            browser.setHtml(
                "<body style='color:#757575;font-family:sans-serif;padding:16px'>"
                f"<p>Nessuna scheda di riferimento trovata per <b>{name}</b>.</p>"
                "<p style='font-size:11px'>Aggiungi i dati nei file "
                "<code>docs/COMPENDIO_PEPTIDI.md</code> o "
                "<code>docs/COMPENDIO_AAS_FARMACI.md</code>.</p>"
                "</body>"
            )
        lay.addWidget(browser, 1)

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
            form.addRow("Note:",    QLabel(s.get("notes") or "—"))
            lay.addLayout(form)

        close_btn = QPushButton("Chiudi")
        close_btn.clicked.connect(self.accept)
        lay.addWidget(close_btn, alignment=Qt.AlignRight)


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
            if details and details.get("concentration_mg_ml"):
                conc = float(details["concentration_mg_ml"]) * 1000.0  # mg/ml → mcg/ml
                name = details.get("batch_product", "?")
                peps = details.get("peptides") or []
                pep_names = " + ".join(p.get("name", "?") for p in peps) if peps else name
                self._set_concentration(conc, f"{pep_names} — {conc:.1f} mcg/ml")
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
