"""Inventory section — Batches and Preparations tabs."""

from datetime import date, datetime, timedelta

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QWidget,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QSpinBox,
    QTextEdit,
    QFrame,
)
from PySide6.QtCore import Qt

from .base import BaseView
from ..components.data_table import DataTable
from ..components.dialogs import confirm_dialog, error_dialog
from ..components.forms import FormField, FormLayout


# ── Shared constants ─────────────────────────────────────────────────────

_DILUENTS = [
    ("Bacteriostatic Water", "Bacteriostatic Water"),
    ("Sterile Water", "Sterile Water"),
    ("Sodium Chloride", "Sodium Chloride 0.9%"),
]

_SITES = ["Addome", "Coscia DX", "Coscia SX", "Braccio DX", "Braccio SX",
          "Gluteo DX", "Gluteo SX"]

_METHODS = [("Sottocutanea", "Sottocutanea (SC)"),
            ("Intramuscolare", "Intramuscolare (IM)"),
            ("Intradermica", "Intradermica (ID)")]

_WASTAGE_REASONS = [
    ("spillage", "Fuoriuscita"),
    ("measurement_error", "Errore misurazione"),
    ("contamination", "Contaminazione"),
    ("other", "Altro"),
]

_DLG_STYLE = (
    "QDialog { background: #1e1e1e; }"
    "QLineEdit, QComboBox, QTextEdit, QSpinBox, QDoubleSpinBox {"
    " background: #2d2d2d; border: 1px solid #424242;"
    " border-radius: 4px; padding: 6px 10px; color: #e0e0e0; }"
    "QLineEdit:focus, QTextEdit:focus { border-color: #42a5f5; }"
)


def _today_str():
    return date.today().isoformat()


def _make_buttons(dialog, submit_label="Salva"):
    """Standard OK / Cancel button box for dialogs."""
    btns = QDialogButtonBox()
    cancel = btns.addButton("Annulla", QDialogButtonBox.RejectRole)
    cancel.setStyleSheet(
        "background: #424242; color: #e0e0e0; padding: 8px 16px;"
        " border-radius: 4px; font-weight: bold;"
    )
    submit = btns.addButton(submit_label, QDialogButtonBox.AcceptRole)
    submit.setStyleSheet(
        "background: #42a5f5; color: #fff; padding: 8px 16px;"
        " border-radius: 4px; font-weight: bold;"
    )
    btns.rejected.connect(dialog.reject)
    return btns, submit


# ═════════════════════════════════════════════════════════════════════════
#  BATCHES TAB
# ═════════════════════════════════════════════════════════════════════════


class BatchesTab(BaseView):
    """Batches list with search, add/edit/delete via context menu."""

    def __init__(self, app, parent=None):
        super().__init__(app, parent)
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        lay = self.layout()

        # Toolbar
        toolbar = QHBoxLayout()
        title = QLabel("Lotti")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        toolbar.addWidget(title)
        toolbar.addStretch()

        self._search = QLineEdit()
        self._search.setPlaceholderText("Cerca lotto...")
        self._search.setFixedWidth(250)
        self._search.textChanged.connect(lambda: self.refresh())
        toolbar.addWidget(self._search)

        add_btn = QPushButton("Aggiungi Lotto")
        add_btn.clicked.connect(self._on_add)
        toolbar.addWidget(add_btn)
        lay.addLayout(toolbar)

        # Table
        self._table = DataTable([
            {"key": "id",                   "label": "ID",           "width": 50},
            {"key": "product_name",         "label": "Prodotto",     "stretch": True},
            {"key": "composition_summary",  "label": "Composizione", "stretch": True},
            {"key": "supplier_name",        "label": "Fornitore",    "width": 140},
            {"key": "vials_status",         "label": "Fiale",        "width": 80},
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
        search = self._search.text().strip() or None
        try:
            batches = self.manager.get_batches(search=search, only_available=True)
        except Exception as e:
            error_dialog(self, "Errore", str(e))
            return

        rows = []
        for b in batches:
            # Build composition summary
            try:
                details = self.manager.get_batch_details(b["id"])
                comp = details.get("composition", [])
                names = [c.get("name", "?") for c in comp]
                if len(names) > 2:
                    summary = ", ".join(names[:2]) + f" +{len(names) - 2}"
                else:
                    summary = ", ".join(names) if names else "-"
            except Exception:
                summary = "-"

            rows.append({
                "id": b["id"],
                "product_name": b.get("product_name", ""),
                "composition_summary": summary,
                "supplier_name": b.get("supplier_name", ""),
                "vials_status": f"{b.get('vials_remaining', 0)}/{b.get('vials_count', 0)}",
            })
        self._table.load_data(rows)

    # ── Actions ──────────────────────────────────────────────────────────

    def _on_add(self):
        dlg = _BatchAddDialog(self.app, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh()

    def _on_details(self, row):
        dlg = _BatchDetailsDialog(self.app, row["id"], parent=self)
        dlg.exec()

    def _on_edit(self, row):
        dlg = _BatchEditDialog(self.app, row["id"], parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh()

    def _on_delete(self, row):
        if not confirm_dialog(
            self, "Elimina Lotto",
            f"Eliminare il lotto #{row['id']} ({row['product_name']})?",
        ):
            return
        try:
            self.manager.soft_delete_batch(row["id"])
            self.app.show_message("Lotto eliminato")
            self.refresh()
        except Exception as e:
            error_dialog(self, "Errore", str(e))


# ── Batch dialogs ────────────────────────────────────────────────────────


class _BatchDetailsDialog(QDialog):
    """Read-only batch detail view."""

    def __init__(self, app, batch_id, parent=None):
        super().__init__(parent)
        self._app = app
        self.setWindowTitle(f"Dettagli Lotto #{batch_id}")
        self.setMinimumWidth(500)
        self.setStyleSheet(_DLG_STYLE)

        try:
            details = app.manager.get_batch_details(batch_id)
        except Exception as e:
            error_dialog(self, "Errore", str(e))
            self.reject()
            return

        if not details:
            error_dialog(self, "Errore", "Lotto non trovato")
            self.reject()
            return

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Title
        title = QLabel(details.get("product_name", f"Lotto #{batch_id}"))
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

        add_row("Fornitore", details.get("supplier_name", "-"))
        add_row("N. Batch", details.get("batch_number") or "-")
        mfg = details.get("manufacturing_date")
        add_row("Data Produzione", mfg.isoformat() if hasattr(mfg, "isoformat") else (mfg or "-"))
        add_row("Acquisto", details.get("purchase_date", "-"))
        add_row("Scadenza", details.get("expiry_date", "-"))
        vr = details.get("vials_remaining", 0)
        vc = details.get("vials_count", 0)
        add_row("Fiale", f"{vr} / {vc}")
        currency = details.get("currency") or "USD"
        add_row("Prezzo", f"{details.get('total_price', 0):.2f} {currency}"
                if details.get("total_price") else "-")
        shipment_id = details.get("shipment_id")
        if shipment_id:
            try:
                s = self._app.manager.get_shipment_details(shipment_id)
                cost = s.get("shipping_cost")
                s_date = s.get("shipping_date", "")
                label = f"#{shipment_id}"
                if s_date:
                    label += f" — {s_date}"
                if cost:
                    label += f" — {float(cost):.2f} {s.get('currency', '')}"
                add_row("Spedizione", label)
            except Exception:
                add_row("Spedizione", f"#{shipment_id}")
        else:
            add_row("Spedizione", "-")
        add_row("Conservazione", details.get("storage_location", "-"))

        # Composition
        comp = details.get("composition", [])
        if comp:
            lines = []
            for c in comp:
                mg = c.get("mg_per_vial") or c.get("mg_amount", 0)
                lines.append(f"  {c.get('name', '?')}: {mg} mg/fiala")
            add_row("Composizione", "\n".join(lines))

        # Preparations
        preps = details.get("preparations", [])
        add_row("Preparazioni", str(len(preps)))

        layout.addLayout(grid)

        # Close button
        close_btn = QPushButton("Chiudi")
        close_btn.setFixedWidth(100)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignRight)


class _BatchAddDialog(QDialog):
    """Add a new batch."""

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self._app = app
        self.setWindowTitle("Aggiungi Lotto")
        self.setMinimumWidth(550)
        self.setStyleSheet(_DLG_STYLE)
        self._peptide_checks: list[tuple[int, QCheckBox, QDoubleSpinBox]] = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Base fields
        suppliers = self._app.manager.get_suppliers()
        supplier_opts = [(s["id"], s.get("name", f"#{s['id']}")) for s in suppliers]

        shipments = self._app.manager.get_shipments()
        shipment_opts = [(None, "(nessuna spedizione)")] + [
            (s["id"], f"#{s['id']} — {s.get('supplier_name', '')} — {s.get('shipping_date', '')}")
            for s in shipments
        ]
        self._form = FormLayout([
            FormField("supplier_id", "Fornitore", "combo",
                      options=supplier_opts, required=True),
            FormField("product_name", "Prodotto", "text", required=True),
            FormField("batch_number", "Numero Batch", "text", required=True),
            FormField("shipment_id", "Spedizione", "combo", options=shipment_opts),
            FormField("vials_count", "N. Fiale", "number", value=1, min_val=1),
            FormField("total_price", "Prezzo", "decimal", value=0),
            FormField("currency", "Valuta", "combo",
                      options=[("USD", "USD ($)"), ("EUR", "EUR (€)")], value="USD"),
            FormField("manufacturing_date", "Data Produzione", "text", value=""),
            FormField("purchase_date", "Data Acquisto", "text", value=_today_str()),
            FormField("expiry_date", "Scadenza", "text",
                      value=(date.today() + timedelta(days=365)).isoformat()),
            FormField("storage_location", "Conservazione", "text", value="Frigo"),
        ])
        layout.addWidget(self._form)

        # Peptide composition
        layout.addWidget(self._sep("Composizione Peptidi"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(200)
        pep_container = QWidget()
        pep_layout = QVBoxLayout(pep_container)
        pep_layout.setContentsMargins(4, 4, 4, 4)
        pep_layout.setSpacing(4)

        peptides = self._app.manager.get_peptides()
        for p in peptides:
            row_w = QWidget()
            row_l = QHBoxLayout(row_w)
            row_l.setContentsMargins(0, 0, 0, 0)
            row_l.setSpacing(8)

            cb = QCheckBox(p.get("name", f"#{p['id']}"))
            row_l.addWidget(cb, 1)

            mg = QDoubleSpinBox()
            mg.setRange(0.01, 9999)
            mg.setDecimals(2)
            mg.setValue(5.0)
            mg.setSuffix(" mg/fiala")
            mg.setEnabled(False)
            cb.toggled.connect(mg.setEnabled)
            row_l.addWidget(mg)

            pep_layout.addWidget(row_w)
            self._peptide_checks.append((p["id"], cb, mg))

        pep_layout.addStretch()
        scroll.setWidget(pep_container)
        layout.addWidget(scroll)

        # Buttons
        btns, submit = _make_buttons(self)
        submit.clicked.connect(self._submit)
        layout.addWidget(btns)

    def _submit(self):
        errors = self._form.validate()
        if errors:
            error_dialog(self, "Validazione", "\n".join(errors))
            return

        vals = self._form.get_values()
        peptide_ids = []
        peptide_amounts = {}
        total_mg = 0

        for pid, cb, mg in self._peptide_checks:
            if cb.isChecked():
                peptide_ids.append(pid)
                peptide_amounts[pid] = mg.value()
                total_mg += mg.value()

        if not peptide_ids:
            error_dialog(self, "Validazione", "Selezionare almeno un peptide")
            return

        try:
            self._app.manager.add_batch(
                supplier_id=vals["supplier_id"],
                product_name=vals["product_name"],
                batch_number=vals["batch_number"],
                shipment_id=vals["shipment_id"] or None,
                peptide_ids=peptide_ids,
                peptide_amounts=peptide_amounts,
                vials_count=vals["vials_count"],
                mg_per_vial=round(total_mg, 2),
                total_price=vals["total_price"],
                currency=vals["currency"],
                manufacturing_date=vals["manufacturing_date"] or None,
                purchase_date=vals["purchase_date"],
                expiry_date=vals["expiry_date"] or None,
                storage_location=vals["storage_location"] or None,
            )
            self._app.show_message("Lotto aggiunto")
            self.accept()
        except Exception as e:
            error_dialog(self, "Errore", str(e))

    @staticmethod
    def _sep(text):
        lbl = QLabel(text)
        lbl.setStyleSheet(
            "font-weight: bold; color: #aeaeae;"
            " border-bottom: 1px solid #424242; padding: 4px 0;"
        )
        return lbl


class _BatchEditDialog(QDialog):
    """Edit an existing batch."""

    def __init__(self, app, batch_id, parent=None):
        super().__init__(parent)
        self._app = app
        self._batch_id = batch_id
        self.setWindowTitle(f"Modifica Lotto #{batch_id}")
        self.setMinimumWidth(550)
        self.setStyleSheet(_DLG_STYLE)
        self._peptide_checks: list[tuple[int, QCheckBox, QDoubleSpinBox]] = []

        try:
            self._details = app.manager.get_batch_details(batch_id)
        except Exception as e:
            error_dialog(self, "Errore", str(e))
            self.reject()
            return

        if not self._details:
            error_dialog(self, "Errore", "Lotto non trovato")
            self.reject()
            return

        self._build_ui()

    def _build_ui(self):
        d = self._details
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        suppliers = self._app.manager.get_suppliers()
        supplier_opts = [(s["id"], s.get("name", f"#{s['id']}")) for s in suppliers]

        mfg = d.get("manufacturing_date")
        mfg_str = mfg.isoformat() if hasattr(mfg, "isoformat") else (mfg or "")
        shipments = self._app.manager.get_shipments()
        shipment_opts = [(None, "(nessuna spedizione)")] + [
            (s["id"], f"#{s['id']} — {s.get('supplier_name', '')} — {s.get('shipping_date', '')}")
            for s in shipments
        ]
        self._form = FormLayout([
            FormField("supplier_id", "Fornitore", "combo",
                      value=d.get("supplier_id"), options=supplier_opts, required=True),
            FormField("product_name", "Prodotto", "text",
                      value=d.get("product_name"), required=True),
            FormField("batch_number", "Numero Batch", "text",
                      value=d.get("batch_number", ""), required=True),
            FormField("shipment_id", "Spedizione", "combo",
                      value=d.get("shipment_id"), options=shipment_opts),
            FormField("vials_count", "N. Fiale (totali)", "number",
                      value=d.get("vials_count", 1), min_val=1),
            FormField("vials_remaining", "Fiale Rimanenti", "number",
                      value=d.get("vials_remaining", 0), min_val=0),
            FormField("total_price", "Prezzo", "decimal",
                      value=d.get("total_price", 0)),
            FormField("currency", "Valuta", "combo",
                      options=[("USD", "USD ($)"), ("EUR", "EUR (€)")],
                      value=d.get("currency", "USD")),
            FormField("manufacturing_date", "Data Produzione", "text",
                      value=mfg_str),
            FormField("purchase_date", "Data Acquisto", "text",
                      value=d.get("purchase_date", "")),
            FormField("expiry_date", "Scadenza", "text",
                      value=d.get("expiry_date", "")),
            FormField("storage_location", "Conservazione", "text",
                      value=d.get("storage_location", "")),
        ])
        layout.addWidget(self._form)

        # Peptide composition
        sep = QLabel("Composizione Peptidi")
        sep.setStyleSheet(
            "font-weight: bold; color: #aeaeae;"
            " border-bottom: 1px solid #424242; padding: 4px 0;"
        )
        layout.addWidget(sep)

        existing_comp = {c["peptide_id"]: c for c in d.get("composition", [])}

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(200)
        pep_container = QWidget()
        pep_layout = QVBoxLayout(pep_container)
        pep_layout.setContentsMargins(4, 4, 4, 4)
        pep_layout.setSpacing(4)

        peptides = self._app.manager.get_peptides()
        for p in peptides:
            row_w = QWidget()
            row_l = QHBoxLayout(row_w)
            row_l.setContentsMargins(0, 0, 0, 0)
            row_l.setSpacing(8)

            cb = QCheckBox(p.get("name", f"#{p['id']}"))
            row_l.addWidget(cb, 1)

            mg = QDoubleSpinBox()
            mg.setRange(0.01, 9999)
            mg.setDecimals(2)
            mg.setValue(5.0)
            mg.setSuffix(" mg/fiala")
            mg.setEnabled(False)
            cb.toggled.connect(mg.setEnabled)
            row_l.addWidget(mg)

            # Pre-fill if existing
            if p["id"] in existing_comp:
                cb.setChecked(True)
                mg.setEnabled(True)
                mg_val = existing_comp[p["id"]].get("mg_per_vial") or \
                         existing_comp[p["id"]].get("mg_amount", 5)
                mg.setValue(float(mg_val))

            pep_layout.addWidget(row_w)
            self._peptide_checks.append((p["id"], cb, mg))

        pep_layout.addStretch()
        scroll.setWidget(pep_container)
        layout.addWidget(scroll)

        # Buttons
        btns, submit = _make_buttons(self)
        submit.clicked.connect(self._submit)
        layout.addWidget(btns)

    def _submit(self):
        errors = self._form.validate()
        if errors:
            error_dialog(self, "Validazione", "\n".join(errors))
            return

        vals = self._form.get_values()
        peptide_ids = []
        peptide_amounts = {}
        total_mg = 0

        for pid, cb, mg in self._peptide_checks:
            if cb.isChecked():
                peptide_ids.append(pid)
                peptide_amounts[pid] = mg.value()
                total_mg += mg.value()

        if not peptide_ids:
            error_dialog(self, "Validazione", "Selezionare almeno un peptide")
            return

        try:
            self._app.manager.update_batch(
                self._batch_id,
                supplier_id=vals["supplier_id"],
                product_name=vals["product_name"],
                batch_number=vals["batch_number"],
                shipment_id=vals["shipment_id"] or None,
                peptide_ids=peptide_ids,
                peptide_amounts=peptide_amounts,
                vials_count=vals["vials_count"],
                vials_remaining=vals["vials_remaining"],
                mg_per_vial=round(total_mg, 2),
                total_price=vals["total_price"],
                currency=vals["currency"],
                manufacturing_date=vals["manufacturing_date"] or None,
                purchase_date=vals["purchase_date"],
                expiry_date=vals["expiry_date"] or None,
                storage_location=vals["storage_location"] or None,
            )
            self._app.show_message("Lotto aggiornato")
            self.accept()
        except Exception as e:
            error_dialog(self, "Errore", str(e))


# ═════════════════════════════════════════════════════════════════════════
#  PREPARATIONS TAB
# ═════════════════════════════════════════════════════════════════════════


class PreparationsTab(BaseView):
    """Preparations list with search, add/edit/delete and administer."""

    def __init__(self, app, parent=None):
        super().__init__(app, parent)
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        lay = self.layout()

        # Toolbar
        toolbar = QHBoxLayout()
        title = QLabel("Preparazioni")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        toolbar.addWidget(title)
        toolbar.addStretch()

        self._search = QLineEdit()
        self._search.setPlaceholderText("Cerca preparazione...")
        self._search.setFixedWidth(250)
        self._search.textChanged.connect(lambda: self.refresh())
        toolbar.addWidget(self._search)

        add_btn = QPushButton("Aggiungi Preparazione")
        add_btn.clicked.connect(self._on_add)
        toolbar.addWidget(add_btn)
        lay.addLayout(toolbar)

        # Table
        self._table = DataTable([
            {"key": "id",            "label": "ID",       "width": 50},
            {"key": "batch_product", "label": "Batch",    "stretch": True},
            {"key": "volume_status", "label": "Volume",   "width": 120},
            {"key": "percentage",    "label": "%",        "width": 60},
            {"key": "expiry_date",   "label": "Scadenza", "width": 110},
        ])
        self._table.set_context_menu([
            {"label": "Dettagli",                "callback": self._on_details},
            {"label": "Registra Somministrazione", "callback": self._on_administer,
             "visible_when": self._has_volume},
            {"label": "Modifica",                "callback": self._on_edit,
             "enabled_when": lambda: self.edit_mode},
            {"label": "Elimina",                 "callback": self._on_delete,
             "enabled_when": lambda: self.edit_mode},
        ])
        self._table.row_double_clicked.connect(self._on_details)
        lay.addWidget(self._table, 1)

    def _has_volume(self):
        """Context-menu visibility: selected row has remaining volume."""
        row = self._table.selected_row()
        if not row:
            return False
        return row.get("_volume_remaining", 0) > 0.01

    # ── Data ─────────────────────────────────────────────────────────────

    def refresh(self):
        search = self._search.text().strip().lower() if hasattr(self, "_search") else ""
        try:
            preps = self.manager.get_preparations(only_active=True)
        except Exception as e:
            error_dialog(self, "Errore", str(e))
            return

        rows = []
        for p in preps:
            product = p.get("batch_product", "")
            # Client-side search filter
            if search and search not in str(product).lower() \
                    and search not in str(p.get("id", "")):
                continue

            vol_rem = float(p.get("volume_remaining_ml", 0))
            vol_tot = float(p.get("volume_ml", 0))
            pct = round(vol_rem / vol_tot * 100) if vol_tot > 0 else 0

            # Truncate product name
            display_product = product[:30] + "..." if len(str(product)) > 30 else product

            rows.append({
                "id": p["id"],
                "batch_product": f"#{p.get('batch_id', '?')} {display_product}",
                "volume_status": f"{vol_rem:.2f} / {vol_tot:.2f} ml",
                "percentage": f"{pct}%",
                "expiry_date": p.get("expiry_date", "-"),
                # Hidden data for logic
                "_volume_remaining": vol_rem,
                "_prep_id": p["id"],
            })
        self._table.load_data(rows)

    # ── Actions ──────────────────────────────────────────────────────────

    def _on_add(self):
        dlg = _PrepAddDialog(self._app_ref(), parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh()

    def _on_details(self, row):
        dlg = _PrepDetailsDialog(self._app_ref(), row["id"], parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh()  # wastage may have been recorded

    def _on_edit(self, row):
        dlg = _PrepEditDialog(self._app_ref(), row["id"], parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh()

    def _on_delete(self, row):
        if not confirm_dialog(
            self, "Elimina Preparazione",
            f"Eliminare la preparazione #{row['id']}?",
        ):
            return
        try:
            self.manager.soft_delete_preparation(row["id"], restore_vials=True)
            self.app.show_message("Preparazione eliminata")
            self.refresh()
        except Exception as e:
            error_dialog(self, "Errore", str(e))

    def _on_administer(self, row):
        dlg = _AdministerDialog(self._app_ref(), row["id"], parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh()

    def _app_ref(self):
        """Return the main app reference."""
        return self.app


# ── Preparation dialogs ──────────────────────────────────────────────────


class _PrepDetailsDialog(QDialog):
    """Read-only preparation detail view with wastage recording."""

    def __init__(self, app, prep_id, parent=None):
        super().__init__(parent)
        self._app = app
        self._prep_id = prep_id
        self.setWindowTitle(f"Dettagli Preparazione #{prep_id}")
        self.setMinimumWidth(520)
        self.setStyleSheet(_DLG_STYLE)

        try:
            self._prep = app.manager.get_preparation_details(prep_id)
        except Exception as e:
            error_dialog(self, "Errore", str(e))
            self.reject()
            return

        if not self._prep:
            error_dialog(self, "Errore", "Preparazione non trovata")
            self.reject()
            return

        self._build_ui()

    def _build_ui(self):
        p = self._prep
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Title
        title = QLabel(f"Preparazione #{p['id']} — {p.get('batch_product', '')}")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        title.setWordWrap(True)
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

        add_row("Data Preparazione", p.get("preparation_date", "-"))
        add_row("Scadenza", p.get("expiry_date", "-"))

        vol_rem = float(p.get("volume_remaining_ml", 0))
        vol_tot = float(p.get("volume_ml", 0))
        add_row("Volume", f"{vol_rem:.2f} / {vol_tot:.2f} ml")

        conc = p.get("concentration_mg_ml")
        if conc:
            add_row("Concentrazione", f"{float(conc):.2f} mg/ml ({float(conc) * 1000:.0f} mcg/ml)")

        add_row("Fiale Usate", p.get("vials_used", "-"))
        add_row("Diluente", p.get("diluent", "-"))

        # Peptides in this preparation
        peptides = p.get("peptides", [])
        if peptides:
            pep_text = "\n".join(
                f"  {pp.get('name', '?')}: {pp.get('mg_per_vial', '?')} mg/fiala"
                for pp in peptides
            )
            add_row("Peptidi", pep_text)

        admin_count = p.get("administrations_count", 0)
        add_row("Somministrazioni", str(admin_count))

        # Wastage
        wastage = float(p.get("wastage_ml") or 0)
        if wastage > 0:
            add_row("Spreco Totale", f"{wastage:.2f} ml")
            # Wastage history
            try:
                history = self._app.manager.get_wastage_history(self._prep_id)
                if history:
                    lines = []
                    for h in history:
                        lines.append(
                            f"  {h.get('date', '?')}: {h.get('volume', 0):.2f} ml"
                            f" — {h.get('reason', '')}"
                        )
                    add_row("Storico Spreco", "\n".join(lines))
            except Exception:
                pass

        add_row("Note", p.get("notes", "-"))

        layout.addLayout(grid)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        if vol_rem > 0.01:
            wastage_btn = QPushButton("Registra Spreco")
            wastage_btn.setStyleSheet(
                "background: #ef5350; color: #fff; padding: 8px 16px;"
                " border-radius: 4px; font-weight: bold;"
            )
            wastage_btn.clicked.connect(self._on_wastage)
            btn_row.addWidget(wastage_btn)

        close_btn = QPushButton("Chiudi")
        close_btn.setFixedWidth(100)
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def _on_wastage(self):
        dlg = _WastageDialog(self._app, self._prep_id, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.accept()  # close details too, triggering parent refresh


class _PrepAddDialog(QDialog):
    """Add a new preparation."""

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self._app = app
        self.setWindowTitle("Aggiungi Preparazione")
        self.setMinimumWidth(480)
        self.setStyleSheet(_DLG_STYLE)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        batches = self._app.manager.get_batches(only_available=True)
        batch_opts = [
            (b["id"], f"#{b['id']} {b.get('product_name', '')[:30]}")
            for b in batches
        ]

        today = _today_str()
        exp = (date.today() + timedelta(days=30)).isoformat()

        self._form = FormLayout([
            FormField("batch_id", "Lotto", "combo",
                      options=batch_opts, required=True),
            FormField("vials_used", "Fiale Utilizzate", "number", value=1, min_val=1),
            FormField("volume_ml", "Volume (ml)", "decimal", value=5.0, min_val=0.1),
            FormField("diluent", "Diluente", "combo",
                      value="Bacteriostatic Water", options=_DILUENTS),
            FormField("preparation_date", "Data Preparazione", "text", value=today),
            FormField("expiry_date", "Scadenza", "text", value=exp),
            FormField("notes", "Note", "textarea"),
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
            self._app.manager.add_preparation(
                batch_id=vals["batch_id"],
                vials_used=vals["vials_used"],
                volume_ml=vals["volume_ml"],
                diluent=vals["diluent"],
                preparation_date=vals["preparation_date"] or None,
                expiry_date=vals["expiry_date"] or None,
                notes=vals["notes"],
            )
            self._app.show_message("Preparazione aggiunta")
            self.accept()
        except Exception as e:
            error_dialog(self, "Errore", str(e))


class _PrepEditDialog(QDialog):
    """Edit an existing preparation (limited fields)."""

    def __init__(self, app, prep_id, parent=None):
        super().__init__(parent)
        self._app = app
        self._prep_id = prep_id
        self.setWindowTitle(f"Modifica Preparazione #{prep_id}")
        self.setMinimumWidth(480)
        self.setStyleSheet(_DLG_STYLE)

        try:
            self._prep = app.manager.get_preparation_details(prep_id)
        except Exception as e:
            error_dialog(self, "Errore", str(e))
            self.reject()
            return

        if not self._prep:
            error_dialog(self, "Errore", "Preparazione non trovata")
            self.reject()
            return

        self._build_ui()

    def _build_ui(self):
        p = self._prep
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Header — read-only info
        header = QLabel(f"Prep #{p['id']} — Batch #{p.get('batch_id', '?')}"
                        f" {p.get('batch_product', '')}")
        header.setStyleSheet("font-weight: bold; color: #aeaeae;")
        header.setWordWrap(True)
        layout.addWidget(header)

        self._form = FormLayout([
            FormField("volume_remaining_ml", "Volume Rimanente (ml)", "decimal",
                      value=float(p.get("volume_remaining_ml", 0)),
                      min_val=0, max_val=float(p.get("volume_ml", 100))),
            FormField("diluent", "Diluente", "combo",
                      value=p.get("diluent", "Bacteriostatic Water"),
                      options=_DILUENTS),
            FormField("expiry_date", "Scadenza", "text",
                      value=p.get("expiry_date", "")),
            FormField("notes", "Note", "textarea",
                      value=p.get("notes", "")),
        ])
        layout.addWidget(self._form)

        btns, submit = _make_buttons(self)
        submit.clicked.connect(self._submit)
        layout.addWidget(btns)

    def _submit(self):
        vals = self._form.get_values()
        try:
            self._app.manager.update_preparation(
                self._prep_id,
                volume_remaining_ml=vals["volume_remaining_ml"],
                diluent=vals["diluent"],
                expiry_date=vals["expiry_date"] or None,
                notes=vals["notes"],
            )
            self._app.show_message("Preparazione aggiornata")
            self.accept()
        except Exception as e:
            error_dialog(self, "Errore", str(e))


class _AdministerDialog(QDialog):
    """Register an administration from a specific preparation."""

    def __init__(self, app, prep_id, parent=None):
        super().__init__(parent)
        self._app = app
        self._prep_id = prep_id
        self.setWindowTitle("Registra Somministrazione")
        self.setMinimumWidth(480)
        self.setStyleSheet(_DLG_STYLE)

        try:
            self._prep = app.manager.get_preparation_details(prep_id)
        except Exception as e:
            error_dialog(self, "Errore", str(e))
            self.reject()
            return

        self._build_ui()

    def _build_ui(self):
        p = self._prep
        now = datetime.now()
        vol_rem = float(p.get("volume_remaining_ml", 0))

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Header
        header = QLabel(f"Preparazione #{p['id']} — {p.get('batch_product', '')}")
        header.setStyleSheet("font-size: 15px; font-weight: bold;")
        header.setWordWrap(True)
        layout.addWidget(header)

        avail = QLabel(f"Volume disponibile: {vol_rem:.2f} ml")
        avail.setStyleSheet("color: #aeaeae; font-size: 12px;")
        layout.addWidget(avail)

        # Protocols for dropdown
        try:
            protocols = self._app.manager.get_protocols(active_only=True)
        except Exception:
            protocols = []
        proto_opts = [(None, "(nessuno)")] + [
            (pr["id"], pr.get("name", f"#{pr['id']}")) for pr in protocols
        ]

        self._form = FormLayout([
            FormField("dose_ml", "Dose (ml)", "decimal", value=0.25,
                      min_val=0.01, max_val=vol_rem),
            FormField("admin_date", "Data", "text", value=now.strftime("%Y-%m-%d")),
            FormField("admin_time", "Ora", "text", value=now.strftime("%H:%M")),
            FormField("injection_site", "Sito Iniezione", "combo",
                      value="Addome",
                      options=[(s, s) for s in _SITES]),
            FormField("injection_method", "Metodo", "combo",
                      value="Sottocutanea",
                      options=_METHODS),
            FormField("protocol_id", "Protocollo", "combo",
                      options=proto_opts),
            FormField("notes", "Note", "textarea"),
        ])
        layout.addWidget(self._form)

        btns, submit = _make_buttons(self, submit_label="Registra")
        submit.setStyleSheet(
            "background: #66bb6a; color: #fff; padding: 8px 16px;"
            " border-radius: 4px; font-weight: bold;"
        )
        submit.clicked.connect(self._submit)
        layout.addWidget(btns)

    def _submit(self):
        vals = self._form.get_values()

        # Validate date/time
        try:
            d = datetime.strptime(vals["admin_date"], "%Y-%m-%d")
        except ValueError:
            error_dialog(self, "Errore", "Formato data non valido (YYYY-MM-DD)")
            return
        try:
            t = datetime.strptime(vals["admin_time"], "%H:%M")
        except ValueError:
            error_dialog(self, "Errore", "Formato ora non valido (HH:MM)")
            return

        admin_dt = f"{d.strftime('%Y-%m-%d')} {t.strftime('%H:%M')}"
        dose = vals["dose_ml"]
        if dose <= 0:
            error_dialog(self, "Errore", "La dose deve essere > 0")
            return

        try:
            self._app.manager.add_administration(
                preparation_id=self._prep_id,
                dose_ml=round(dose, 2),
                administration_datetime=admin_dt,
                injection_site=vals["injection_site"],
                injection_method=vals["injection_method"],
                protocol_id=vals["protocol_id"],
                notes=vals["notes"],
            )
            self._app.show_message(f"Somministrazione registrata: {dose:.2f} ml")
            self.accept()
        except Exception as e:
            error_dialog(self, "Errore", str(e))


class _WastageDialog(QDialog):
    """Record wastage on a preparation."""

    def __init__(self, app, prep_id, parent=None):
        super().__init__(parent)
        self._app = app
        self._prep_id = prep_id
        self.setWindowTitle("Registra Spreco")
        self.setMinimumWidth(400)
        self.setStyleSheet(_DLG_STYLE)

        try:
            prep = app.manager.get_preparation_details(prep_id)
            self._max_vol = float(prep.get("volume_remaining_ml", 0))
        except Exception:
            self._max_vol = 100

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        hint = QLabel(f"Volume massimo: {self._max_vol:.2f} ml")
        hint.setStyleSheet("color: #aeaeae;")
        layout.addWidget(hint)

        self._form = FormLayout([
            FormField("volume_ml", "Volume Sprecato (ml)", "decimal",
                      value=0.0, min_val=0.01, max_val=self._max_vol, required=True),
            FormField("reason", "Motivo", "combo",
                      value="spillage", options=_WASTAGE_REASONS),
            FormField("notes", "Note", "textarea"),
        ])
        layout.addWidget(self._form)

        btns, submit = _make_buttons(self, submit_label="Registra Spreco")
        submit.setStyleSheet(
            "background: #ef5350; color: #fff; padding: 8px 16px;"
            " border-radius: 4px; font-weight: bold;"
        )
        submit.clicked.connect(self._submit)
        layout.addWidget(btns)

    def _submit(self):
        errors = self._form.validate()
        if errors:
            error_dialog(self, "Validazione", "\n".join(errors))
            return

        vals = self._form.get_values()
        vol = vals["volume_ml"]
        if vol <= 0:
            error_dialog(self, "Errore", "Il volume deve essere > 0")
            return

        try:
            success, msg = self._app.manager.record_wastage(
                self._prep_id,
                volume_ml=round(vol, 2),
                reason=vals["reason"],
                notes=vals["notes"],
            )
            if success:
                self._app.show_message(f"Spreco registrato: {vol:.2f} ml")
                self.accept()
            else:
                error_dialog(self, "Errore", msg)
        except Exception as e:
            error_dialog(self, "Errore", str(e))


# ═════════════════════════════════════════════════════════════════════════
#  SHIPMENTS TAB
# ═════════════════════════════════════════════════════════════════════════


class ShipmentsTab(BaseView):
    """Tab per la gestione delle spedizioni."""

    def __init__(self, app, parent=None):
        super().__init__(app, parent)
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        lay = self.layout()

        toolbar = QHBoxLayout()
        title = QLabel("Spedizioni")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        toolbar.addWidget(title)
        toolbar.addStretch()

        add_btn = QPushButton("Nuova Spedizione")
        add_btn.clicked.connect(self._on_add)
        toolbar.addWidget(add_btn)
        lay.addLayout(toolbar)

        self._table = DataTable([
            {"key": "id",            "label": "ID",         "width": 50},
            {"key": "supplier_name", "label": "Fornitore",  "stretch": True},
            {"key": "shipping_date", "label": "Data",       "width": 110},
            {"key": "cost_display",  "label": "Spedizione", "width": 120},
            {"key": "batch_count",   "label": "Lotti",      "width": 60},
        ])
        self._table.set_context_menu([
            {"label": "Dettagli", "callback": self._on_details},
            {"label": "Modifica", "callback": self._on_edit,
             "enabled_when": lambda: self.edit_mode},
            {"label": "Elimina",  "callback": self._on_delete,
             "enabled_when": lambda: self.edit_mode},
        ])
        self._table.row_double_clicked.connect(self._on_details)
        lay.addWidget(self._table, 1)

    def refresh(self):
        try:
            shipments = self.manager.get_shipments()
        except Exception as e:
            error_dialog(self, "Errore", str(e))
            return

        rows = []
        for s in shipments:
            cost = s.get("shipping_cost")
            currency = s.get("currency", "")
            cost_display = f"{float(cost):.2f} {currency}" if cost is not None else "-"
            rows.append({
                "id": s["id"],
                "supplier_name": s.get("supplier_name", ""),
                "shipping_date": s.get("shipping_date") or "-",
                "cost_display": cost_display,
                "batch_count": s.get("batch_count", 0),
            })
        self._table.load_data(rows)

    def _on_add(self):
        dlg = _ShipmentAddDialog(self.app, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh()

    def _on_details(self, row):
        dlg = _ShipmentDetailsDialog(self.app, row["id"], parent=self)
        dlg.exec()

    def _on_edit(self, row):
        dlg = _ShipmentEditDialog(self.app, row["id"], parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh()

    def _on_delete(self, row):
        if not confirm_dialog(
            self, "Elimina Spedizione",
            f"Eliminare la spedizione #{row['id']}?",
        ):
            return
        try:
            success, msg = self.manager.delete_shipment(row["id"])
            if success:
                self.app.show_message("Spedizione eliminata")
                self.refresh()
            else:
                error_dialog(self, "Impossibile eliminare", msg)
        except Exception as e:
            error_dialog(self, "Errore", str(e))


# ── Shipment dialogs ─────────────────────────────────────────────────────


class _ShipmentAddDialog(QDialog):

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self._app = app
        self.setWindowTitle("Nuova Spedizione")
        self.setMinimumWidth(480)
        self.setStyleSheet(_DLG_STYLE)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        suppliers = self._app.manager.get_suppliers()
        supplier_opts = [(s["id"], s.get("name", f"#{s['id']}")) for s in suppliers]

        self._form = FormLayout([
            FormField("supplier_id", "Fornitore", "combo",
                      options=supplier_opts, required=True),
            FormField("shipping_date", "Data Spedizione", "text", value=_today_str()),
            FormField("shipping_cost", "Costo Spedizione", "decimal", value=0),
            FormField("currency", "Valuta", "combo",
                      options=[("USD", "USD ($)"), ("EUR", "EUR (€)")], value="USD"),
            FormField("notes", "Note", "textarea"),
        ])
        layout.addWidget(self._form)

        btns, submit = _make_buttons(self, submit_label="Crea Spedizione")
        submit.clicked.connect(self._submit)
        layout.addWidget(btns)

    def _submit(self):
        errors = self._form.validate()
        if errors:
            error_dialog(self, "Validazione", "\n".join(errors))
            return
        vals = self._form.get_values()
        try:
            self._app.manager.add_shipment(
                supplier_id=vals["supplier_id"],
                shipping_cost=vals["shipping_cost"] or None,
                currency=vals["currency"],
                shipping_date=vals["shipping_date"] or None,
                notes=vals["notes"],
            )
            self._app.show_message("Spedizione creata")
            self.accept()
        except Exception as e:
            error_dialog(self, "Errore", str(e))


class _ShipmentDetailsDialog(QDialog):

    def __init__(self, app, shipment_id, parent=None):
        super().__init__(parent)
        self._app = app
        self.setWindowTitle(f"Spedizione #{shipment_id}")
        self.setMinimumWidth(520)
        self.setStyleSheet(_DLG_STYLE)

        try:
            self._data = app.manager.get_shipment_details(shipment_id)
        except Exception as e:
            error_dialog(self, "Errore", str(e))
            self.reject()
            return

        if not self._data:
            error_dialog(self, "Errore", "Spedizione non trovata")
            self.reject()
            return

        self._build_ui()

    def _build_ui(self):
        d = self._data
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        title = QLabel(f"Spedizione #{d['id']} — {d.get('supplier_name', '')}")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

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

        add_row("Fornitore", d.get("supplier_name", "-"))
        add_row("Data Spedizione", d.get("shipping_date") or "-")
        cost = d.get("shipping_cost")
        currency = d.get("currency", "")
        add_row("Costo Spedizione", f"{float(cost):.2f} {currency}" if cost is not None else "-")
        add_row("Note", d.get("notes") or "-")
        layout.addLayout(grid)

        # Batch collegati
        batches = d.get("batches", [])
        if batches:
            sep = QLabel(f"Lotti collegati ({len(batches)})")
            sep.setStyleSheet(
                "font-weight: bold; color: #aeaeae;"
                " border-bottom: 1px solid #424242; padding: 4px 0; margin-top: 6px;"
            )
            layout.addWidget(sep)

            batch_table = DataTable([
                {"key": "id",               "label": "ID",      "width": 50},
                {"key": "product_name",     "label": "Prodotto","stretch": True},
                {"key": "batch_number",     "label": "Batch #", "width": 120},
                {"key": "vials_remaining",  "label": "Fiale",   "width": 60},
            ])
            batch_table.load_data([dict(b) for b in batches])
            batch_table.setFixedHeight(32 + len(batches) * 28)
            layout.addWidget(batch_table)
        else:
            layout.addWidget(QLabel("Nessun lotto collegato."))

        close_btn = QPushButton("Chiudi")
        close_btn.setFixedWidth(100)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignRight)


class _ShipmentEditDialog(QDialog):

    def __init__(self, app, shipment_id, parent=None):
        super().__init__(parent)
        self._app = app
        self._shipment_id = shipment_id
        self.setWindowTitle(f"Modifica Spedizione #{shipment_id}")
        self.setMinimumWidth(480)
        self.setStyleSheet(_DLG_STYLE)

        try:
            self._data = app.manager.get_shipment_details(shipment_id)
        except Exception as e:
            error_dialog(self, "Errore", str(e))
            self.reject()
            return

        if not self._data:
            error_dialog(self, "Errore", "Spedizione non trovata")
            self.reject()
            return

        self._build_ui()

    def _build_ui(self):
        d = self._data
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        suppliers = self._app.manager.get_suppliers()
        supplier_opts = [(s["id"], s.get("name", f"#{s['id']}")) for s in suppliers]

        self._form = FormLayout([
            FormField("supplier_id", "Fornitore", "combo",
                      value=d.get("supplier_id"), options=supplier_opts, required=True),
            FormField("shipping_date", "Data Spedizione", "text",
                      value=d.get("shipping_date") or ""),
            FormField("shipping_cost", "Costo Spedizione", "decimal",
                      value=d.get("shipping_cost") or 0),
            FormField("currency", "Valuta", "combo",
                      options=[("USD", "USD ($)"), ("EUR", "EUR (€)")],
                      value=d.get("currency", "USD")),
            FormField("notes", "Note", "textarea", value=d.get("notes") or ""),
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
            self._app.manager.update_shipment(
                self._shipment_id,
                supplier_id=vals["supplier_id"],
                shipping_cost=vals["shipping_cost"] or None,
                currency=vals["currency"],
                shipping_date=vals["shipping_date"] or None,
                notes=vals["notes"],
            )
            self._app.show_message("Spedizione aggiornata")
            self.accept()
        except Exception as e:
            error_dialog(self, "Errore", str(e))
