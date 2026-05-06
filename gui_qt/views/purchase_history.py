"""Purchase history — storico acquisti lotti."""

from datetime import date

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QWidget,
    QComboBox,
    QLineEdit,
    QFrame,
)
from PySide6.QtCore import Qt

from .base import BaseView
from ..components.data_table import DataTable
from ..components.dialogs import error_dialog


# ── Helpers ───────────────────────────────────────────────────────────────────

_DLG_STYLE = (
    "QDialog { background: #1e1e1e; }"
    "QLineEdit, QComboBox { background: #2d2d2d; border: 1px solid #424242;"
    " border-radius: 4px; padding: 6px 10px; color: #e0e0e0; }"
)


def _kpi_frame(label, value, color="#42a5f5"):
    frame = QFrame()
    frame.setFrameShape(QFrame.StyledPanel)
    frame.setStyleSheet(
        "QFrame { background: #2d2d2d; border-radius: 6px; border: 1px solid #424242; }"
    )
    lay = QVBoxLayout(frame)
    lay.setContentsMargins(14, 8, 14, 8)
    lay.setSpacing(2)
    v = QLabel(value)
    v.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {color}; border: none;")
    v.setAlignment(Qt.AlignCenter)
    k = QLabel(label)
    k.setStyleSheet("font-size: 11px; color: #9e9e9e; border: none;")
    k.setAlignment(Qt.AlignCenter)
    lay.addWidget(v)
    lay.addWidget(k)
    return frame, v


def _sep():
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setStyleSheet("color: #424242;")
    return line


def _status_label(batch: dict) -> str:
    remaining = batch.get("vials_remaining", 0) or 0
    exp = batch.get("expiry_date")
    if exp:
        try:
            exp_date = date.fromisoformat(str(exp)[:10])
            if exp_date < date.today():
                return "Scaduto"
        except ValueError:
            pass
    if remaining == 0:
        return "Esaurito"
    return "Disponibile"


def _fmt_price(batch: dict) -> str:
    price = batch.get("total_price")
    if price is None:
        ppv = batch.get("price_per_vial")
        vials = batch.get("vials_count") or 1
        if ppv:
            price = float(ppv) * vials
    if price is None:
        return "—"
    currency = batch.get("currency", "EUR")
    return f"{float(price):.2f} {currency}"


# ═══════════════════════════════════════════════════════════════════════════════
#  DETAIL DIALOG
# ═══════════════════════════════════════════════════════════════════════════════


class _DetailDialog(QDialog):
    def __init__(self, row: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Lotto #{row.get('id', '?')} — {row.get('product_name', '')}")
        self.setMinimumWidth(460)
        self.setStyleSheet(_DLG_STYLE)

        lay = QVBoxLayout(self)
        lay.setSpacing(12)

        grid = QGridLayout()
        grid.setColumnStretch(1, 1)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(6)

        def add_row(r, label, value):
            lbl = QLabel(label + ":")
            lbl.setStyleSheet("color: #9e9e9e;")
            val = QLabel(str(value) if value else "—")
            val.setWordWrap(True)
            val.setStyleSheet("color: #e0e0e0;")
            grid.addWidget(lbl, r, 0, Qt.AlignTop | Qt.AlignRight)
            grid.addWidget(val, r, 1)

        vials_c = row.get("vials_count", "?")
        vials_r = row.get("vials_received", "")
        vials_str = str(vials_c)
        if vials_r and str(vials_r) != str(vials_c):
            vials_str += f"  (ricevuti: {vials_r})"

        add_row(0,  "Prodotto",       row.get("product_name", ""))
        add_row(1,  "N° Lotto",       row.get("batch_number", ""))
        add_row(2,  "Fornitore",      row.get("supplier_name", ""))
        add_row(3,  "Data Acquisto",  row.get("purchase_date", ""))
        add_row(4,  "Scadenza",       row.get("expiry_date", ""))
        add_row(5,  "Produzione",     row.get("manufacturing_date", ""))
        add_row(6,  "Vials",          vials_str)
        add_row(7,  "Rimanenti",      row.get("vials_remaining", ""))
        add_row(8,  "mg/Vial",        row.get("mg_per_vial", ""))
        add_row(9,  "Prezzo Totale",  _fmt_price(row))
        add_row(10, "Prezzo/Vial",    (
            f"{float(row['price_per_vial']):.2f} {row.get('currency','EUR')}"
            if row.get("price_per_vial") else "—"
        ))
        add_row(11, "Ubicazione",     row.get("storage_location", ""))
        add_row(12, "Stato",          _status_label(row))
        add_row(13, "Note",           row.get("notes", ""))

        lay.addLayout(grid)
        lay.addWidget(_sep())

        close_btn = QPushButton("Chiudi")
        close_btn.setStyleSheet(
            "background: #424242; color: #e0e0e0; padding: 8px 16px;"
            " border-radius: 4px; font-weight: bold;"
        )
        close_btn.clicked.connect(self.accept)
        lay.addWidget(close_btn, alignment=Qt.AlignRight)


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN TAB
# ═══════════════════════════════════════════════════════════════════════════════


_COLUMNS = [
    {"key": "_purchase_date", "label": "Data Acquisto", "width": 110},
    {"key": "product_name",   "label": "Prodotto",       "stretch": True},
    {"key": "batch_number",   "label": "N° Lotto",       "width": 120},
    {"key": "supplier_name",  "label": "Fornitore",      "width": 160},
    {"key": "_vials",         "label": "Vials",          "width": 80},
    {"key": "_remaining",     "label": "Rimanenti",      "width": 80},
    {"key": "_price",         "label": "Prezzo",         "width": 110},
    {"key": "_status",        "label": "Stato",          "width": 90},
]


class PurchaseHistoryTab(BaseView):
    """Storico di tutti i lotti acquistati."""

    def __init__(self, app, parent=None):
        super().__init__(app, parent)
        self._all_batches: list[dict] = []
        self._build_ui()

    # ── Build UI ─────────────────────────────────────────────────────────────

    def _build_ui(self):
        lay = self.layout()
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)

        # KPI bar
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(8)
        f1, self._kpi_count  = _kpi_frame("Acquisti totali",   "—", "#42a5f5")
        f2, self._kpi_total  = _kpi_frame("Spesa totale",      "—", "#66bb6a")
        f3, self._kpi_vials  = _kpi_frame("Vials acquistati",  "—", "#ffa726")
        f4, self._kpi_active = _kpi_frame("Lotti disponibili", "—", "#ab47bc")
        for f in (f1, f2, f3, f4):
            kpi_row.addWidget(f)
        lay.addLayout(kpi_row)

        # Filters bar
        bar = QHBoxLayout()
        bar.setSpacing(6)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Cerca prodotto o n° lotto…")
        self._search.setFixedWidth(220)
        self._search.textChanged.connect(self._apply_filters)
        bar.addWidget(self._search)

        self._supplier_combo = QComboBox()
        self._supplier_combo.setFixedWidth(170)
        self._supplier_combo.currentIndexChanged.connect(self._apply_filters)
        bar.addWidget(self._supplier_combo)

        self._year_combo = QComboBox()
        self._year_combo.setFixedWidth(100)
        self._year_combo.currentIndexChanged.connect(self._apply_filters)
        bar.addWidget(self._year_combo)

        self._status_combo = QComboBox()
        self._status_combo.setFixedWidth(130)
        for label, value in [
            ("Tutti gli stati", None),
            ("Disponibile",     "Disponibile"),
            ("Esaurito",        "Esaurito"),
            ("Scaduto",         "Scaduto"),
        ]:
            self._status_combo.addItem(label, value)
        self._status_combo.currentIndexChanged.connect(self._apply_filters)
        bar.addWidget(self._status_combo)

        bar.addStretch()
        lay.addLayout(bar)

        # Table
        self._table = DataTable(_COLUMNS, self)
        self._table.row_double_clicked.connect(self._show_detail)
        self._table.set_context_menu([
            {"label": "Dettagli", "callback": self._show_detail},
        ])
        lay.addWidget(self._table)

    # ── Data ─────────────────────────────────────────────────────────────────

    def refresh(self):
        try:
            # All non-deleted batches (available + depleted + expired)
            raw = self.manager.get_batches()
        except Exception as e:
            error_dialog(self, "Errore", str(e))
            return

        # Enrich with display fields
        for b in raw:
            b["_purchase_date"] = str(b.get("purchase_date") or "")[:10] or "—"
            b["_vials"]         = str(b.get("vials_count") or "—")
            b["_remaining"]     = str(b.get("vials_remaining") or "0")
            b["_price"]         = _fmt_price(b)
            b["_status"]        = _status_label(b)

        self._all_batches = sorted(
            raw,
            key=lambda b: str(b.get("purchase_date") or ""),
            reverse=True,
        )

        self._rebuild_filters()
        self._apply_filters()
        self._update_kpis(raw)

    def _rebuild_filters(self):
        # Fornitore
        self._supplier_combo.blockSignals(True)
        prev_supplier = self._supplier_combo.currentData()
        self._supplier_combo.clear()
        self._supplier_combo.addItem("Tutti i fornitori", None)
        seen = {}
        for b in self._all_batches:
            sid = b.get("supplier_id")
            if sid and sid not in seen:
                seen[sid] = b.get("supplier_name", f"#{sid}")
        for sid, name in sorted(seen.items(), key=lambda x: x[1]):
            self._supplier_combo.addItem(name, sid)
        idx = self._supplier_combo.findData(prev_supplier)
        self._supplier_combo.setCurrentIndex(max(0, idx))
        self._supplier_combo.blockSignals(False)

        # Anno
        self._year_combo.blockSignals(True)
        prev_year = self._year_combo.currentData()
        self._year_combo.clear()
        self._year_combo.addItem("Tutti gli anni", None)
        years = sorted(
            {str(b.get("purchase_date") or "")[:4] for b in self._all_batches
             if b.get("purchase_date")},
            reverse=True,
        )
        for y in years:
            self._year_combo.addItem(y, y)
        idx = self._year_combo.findData(prev_year)
        self._year_combo.setCurrentIndex(max(0, idx))
        self._year_combo.blockSignals(False)

    def _apply_filters(self):
        text    = self._search.text().strip().lower()
        sup_id  = self._supplier_combo.currentData()
        year    = self._year_combo.currentData()
        status  = self._status_combo.currentData()

        rows = []
        for b in self._all_batches:
            if text and text not in (b.get("product_name") or "").lower() \
                    and text not in (b.get("batch_number") or "").lower():
                continue
            if sup_id and b.get("supplier_id") != sup_id:
                continue
            if year and not str(b.get("purchase_date") or "").startswith(year):
                continue
            if status and b["_status"] != status:
                continue
            rows.append(b)

        self._table.load_data(rows)

    def _update_kpis(self, batches):
        total_price = 0.0
        has_price   = False
        total_vials = 0
        active      = 0

        for b in batches:
            vc = b.get("vials_count") or 0
            total_vials += vc

            if b["_status"] == "Disponibile":
                active += 1

            price = b.get("total_price")
            if price is None:
                ppv = b.get("price_per_vial")
                if ppv:
                    price = float(ppv) * (vc or 1)
            if price is not None:
                total_price += float(price)
                has_price = True

        self._kpi_count.setText(str(len(batches)))
        self._kpi_total.setText(f"{total_price:.0f} €" if has_price else "—")
        self._kpi_vials.setText(str(total_vials))
        self._kpi_active.setText(str(active))

    # ── Detail ────────────────────────────────────────────────────────────────

    def _show_detail(self, row: dict):
        dlg = _DetailDialog(row, self)
        dlg.exec()
