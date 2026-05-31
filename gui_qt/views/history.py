"""History section — Administrations list and Statistics."""

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
    QComboBox,
    QFrame,
    QCheckBox,
    QDateEdit,
)
from PySide6.QtCore import Qt, QDate

from .base import BaseView
from ..components.data_table import DataTable
from ..components.dialogs import confirm_dialog, error_dialog

try:
    import pandas as pd

    _HAS_PANDAS = True
except ImportError:
    _HAS_PANDAS = False


# ── Helpers ───────────────────────────────────────────────────────────────────

_DLG_STYLE = (
    "QDialog { background: #1e1e1e; }"
    "QLineEdit, QComboBox, QTextEdit {"
    " background: #2d2d2d; border: 1px solid #424242;"
    " border-radius: 4px; padding: 6px 10px; color: #e0e0e0; }"
)


def _kpi_frame(label, value, color="#42a5f5"):
    """Mini KPI card; returns (frame, value_label)."""
    frame = QFrame()
    frame.setFrameShape(QFrame.StyledPanel)
    frame.setStyleSheet(
        "QFrame { background: #2d2d2d; border-radius: 6px; border: 1px solid #424242; }"
    )
    lay = QVBoxLayout(frame)
    lay.setContentsMargins(12, 8, 12, 8)
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
    """Thin horizontal separator."""
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setStyleSheet("color: #424242;")
    return line


# ═══════════════════════════════════════════════════════════════════════════════
#  DETAIL DIALOG
# ═══════════════════════════════════════════════════════════════════════════════


class _DetailsDialog(QDialog):
    def __init__(self, row: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Somministrazione #{row.get('id', '?')}")
        self.setMinimumWidth(440)
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

        dt = str(row.get("administration_datetime", "") or "")
        data_str = dt[:10] if len(dt) >= 10 else dt
        ora_str = dt[11:16] if len(dt) >= 16 else ""

        dose_ml = row.get("dose_ml", 0) or 0
        dose_mcg = row.get("dose_mcg")

        add_row(0,  "Data",         data_str)
        add_row(1,  "Ora",          ora_str)
        add_row(2,  "Peptide",      row.get("peptide_names", ""))
        add_row(3,  "Prodotto",     row.get("batch_product", ""))
        add_row(4,  "Preparazione", row.get("preparation_display", ""))
        add_row(5,  "Dose (ml)",    f"{float(dose_ml):.3f}")
        add_row(6,  "Dose (mcg)",   f"{float(dose_mcg):.1f}" if dose_mcg else "—")
        add_row(7,  "Sito",         row.get("injection_site", ""))
        add_row(8,  "Metodo",       row.get("injection_method", ""))
        add_row(9,  "Protocollo",   row.get("protocol_name", ""))
        add_row(10, "Note",         row.get("notes", ""))
        add_row(11, "Effetti",      row.get("side_effects", ""))

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
#  ADMINISTRATIONS TAB
# ═══════════════════════════════════════════════════════════════════════════════


class AdministrationsTab(BaseView):
    """Storico somministrazioni con filtri lato client (pandas)."""

    _COLS = [
        {"key": "id",                  "label": "ID",         "width": 50},
        {"key": "_date",               "label": "Data",       "width": 100},
        {"key": "_time",               "label": "Ora",        "width": 58},
        {"key": "peptide_names",       "label": "Peptide",    "stretch": True},
        {"key": "batch_product",       "label": "Prodotto",   "width": 130},
        {"key": "preparation_display", "label": "Prep",       "width": 80},
        {"key": "_dose_ml",            "label": "ml",         "width": 60},
        {"key": "_dose_mcg",           "label": "mcg",        "width": 70},
        {"key": "injection_site",      "label": "Sito",       "width": 100},
        {"key": "injection_method",    "label": "Metodo",     "width": 120},
        {"key": "protocol_name",       "label": "Protocollo", "width": 110},
    ]

    def __init__(self, app, parent=None):
        super().__init__(app, parent)
        self._df_all = None
        self._build_ui()
        self.refresh()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        lay = self.layout()

        title = QLabel("Storico Somministrazioni")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        lay.addWidget(title)

        # Filter bar
        fbar = QHBoxLayout()
        fbar.setSpacing(8)

        self._f_notes = QLineEdit()
        self._f_notes.setPlaceholderText("Cerca note...")
        self._f_notes.setFixedWidth(170)
        self._f_notes.textChanged.connect(self._apply_filters)
        fbar.addWidget(self._f_notes)

        self._f_from_cb = QCheckBox("Da:")
        self._f_from_cb.setStyleSheet("color: #aeaeae;")
        self._f_from = QDateEdit()
        self._f_from.setCalendarPopup(True)
        self._f_from.setDisplayFormat("dd/MM/yyyy")
        self._f_from.setDate(QDate.currentDate().addDays(-30))
        self._f_from.setEnabled(False)
        self._f_from_cb.toggled.connect(self._f_from.setEnabled)
        self._f_from_cb.toggled.connect(self._apply_filters)
        self._f_from.dateChanged.connect(self._apply_filters)
        fbar.addWidget(self._f_from_cb)
        fbar.addWidget(self._f_from)

        self._f_to_cb = QCheckBox("A:")
        self._f_to_cb.setStyleSheet("color: #aeaeae;")
        self._f_to = QDateEdit()
        self._f_to.setCalendarPopup(True)
        self._f_to.setDisplayFormat("dd/MM/yyyy")
        self._f_to.setDate(QDate.currentDate())
        self._f_to.setEnabled(False)
        self._f_to_cb.toggled.connect(self._f_to.setEnabled)
        self._f_to_cb.toggled.connect(self._apply_filters)
        self._f_to.dateChanged.connect(self._apply_filters)
        fbar.addWidget(self._f_to_cb)
        fbar.addWidget(self._f_to)

        self._f_peptide = QComboBox()
        self._f_peptide.setFixedWidth(140)
        self._f_peptide.currentIndexChanged.connect(self._apply_filters)
        fbar.addWidget(self._f_peptide)

        self._f_site = QComboBox()
        self._f_site.setFixedWidth(120)
        self._f_site.currentIndexChanged.connect(self._apply_filters)
        fbar.addWidget(self._f_site)

        self._f_method = QComboBox()
        self._f_method.setFixedWidth(140)
        self._f_method.currentIndexChanged.connect(self._apply_filters)
        fbar.addWidget(self._f_method)

        self._f_protocol = QComboBox()
        self._f_protocol.setFixedWidth(140)
        self._f_protocol.currentIndexChanged.connect(self._apply_filters)
        fbar.addWidget(self._f_protocol)

        reset_btn = QPushButton("Reset")
        reset_btn.setFixedWidth(58)
        reset_btn.clicked.connect(self._reset_filters)
        fbar.addWidget(reset_btn)

        fbar.addStretch()
        lay.addLayout(fbar)

        # KPI strip
        kbar = QHBoxLayout()
        kbar.setSpacing(8)
        f1, self._kpi_count = _kpi_frame("somministrazioni", "—", "#42a5f5")
        f2, self._kpi_ml    = _kpi_frame("ml totali",        "—", "#26c6da")
        f3, self._kpi_mcg   = _kpi_frame("mcg totali",       "—", "#66bb6a")
        f4, self._kpi_days  = _kpi_frame("giorni distinti",  "—", "#ab47bc")
        for f in (f1, f2, f3, f4):
            kbar.addWidget(f)
        kbar.addStretch()
        self._lbl_range = QLabel("")
        self._lbl_range.setStyleSheet("color: #9e9e9e; font-size: 11px;")
        kbar.addWidget(self._lbl_range, alignment=Qt.AlignVCenter)
        lay.addLayout(kbar)

        # Table
        self._table = DataTable(self._COLS)
        self._table.set_context_menu([
            {"label": "Dettagli", "callback": self._on_details},
            {"label": "Elimina",  "callback": self._on_delete,
             "enabled_when": lambda: self.edit_mode},
        ])
        self._table.row_double_clicked.connect(self._on_details)
        lay.addWidget(self._table, 1)

    # ── Data ─────────────────────────────────────────────────────────────────

    def refresh(self):
        """Reload from DB, then apply current filters."""
        if not _HAS_PANDAS:
            self._table.load_data([])
            self._kpi_count.setText("N/A")
            return
        try:
            self._df_all = self.manager.get_all_administrations_df()
        except Exception as exc:
            error_dialog(self, "Errore caricamento", str(exc))
            self._df_all = None
            return
        self._populate_combos()
        self._apply_filters()

    def _populate_combos(self):
        """Fill filter combos from the full dataset (block signals while doing so)."""
        if self._df_all is None:
            return
        df = self._df_all

        def _fill(combo, values, placeholder):
            combo.blockSignals(True)
            current = combo.currentData()
            combo.clear()
            combo.addItem(placeholder, "")
            for v in values:
                combo.addItem(v, v)
            # restore selection if still present
            idx = combo.findData(current)
            combo.setCurrentIndex(idx if idx >= 0 else 0)
            combo.blockSignals(False)

        peptides = sorted({
            p for cell in df["peptide_names"].dropna() for p in [cell] if cell and cell != "N/A"
        })
        sites = sorted(df["injection_site"].dropna().unique())
        methods = sorted(df["injection_method"].dropna().unique())
        protocols = sorted({
            p for p in df["protocol_name"].dropna().unique() if p and p != "Nessuno"
        })

        _fill(self._f_peptide, peptides, "Peptide (tutti)")
        _fill(self._f_site,    sites,    "Sito (tutti)")
        _fill(self._f_method,  methods,  "Metodo (tutti)")
        _fill(self._f_protocol,protocols,"Protocollo (tutti)")

    def _apply_filters(self):
        if self._df_all is None:
            return
        df = self._df_all.copy()

        # Notes search
        q = self._f_notes.text().strip()
        if q:
            df = df[df["notes"].str.contains(q, case=False, na=False)]

        # Date range
        if self._f_from_cb.isChecked():
            date_from = pd.to_datetime(self._f_from.date().toString("yyyy-MM-dd")).date()
            df = df[df["date"] >= date_from]
        if self._f_to_cb.isChecked():
            date_to = pd.to_datetime(self._f_to.date().toString("yyyy-MM-dd")).date()
            df = df[df["date"] <= date_to]

        # Combo filters
        if self._f_peptide.currentData():
            val = self._f_peptide.currentData()
            df = df[df["peptide_names"].str.contains(val, case=False, na=False)]
        if self._f_site.currentData():
            df = df[df["injection_site"] == self._f_site.currentData()]
        if self._f_method.currentData():
            df = df[df["injection_method"] == self._f_method.currentData()]
        if self._f_protocol.currentData():
            df = df[df["protocol_name"] == self._f_protocol.currentData()]

        self._update_kpis(df)
        self._load_table(df)

    def _update_kpis(self, df):
        count = len(df)
        total_ml = df["dose_ml"].sum() if count else 0.0
        total_mcg = df["dose_mcg"].sum() if (count and "dose_mcg" in df.columns) else 0.0
        days = df["date"].nunique() if count else 0

        self._kpi_count.setText(str(count))
        self._kpi_ml.setText(f"{float(total_ml):.1f}")
        self._kpi_mcg.setText(f"{float(total_mcg):.0f}" if total_mcg else "—")
        self._kpi_days.setText(str(days))

        if count:
            first = str(df["date"].min())
            last = str(df["date"].max())
            self._lbl_range.setText(f"Prima: {first}  •  Ultima: {last}")
        else:
            self._lbl_range.setText("")

    def _load_table(self, df):
        rows = []
        for _, r in df.iterrows():
            dt = str(r.get("administration_datetime", "") or "")
            dose_ml = r.get("dose_ml", 0) or 0
            dose_mcg = r.get("dose_mcg")
            rows.append({
                **r.to_dict(),
                "_date":     dt[:10] if len(dt) >= 10 else dt,
                "_time":     dt[11:16] if len(dt) >= 16 else "",
                "_dose_ml":  f"{float(dose_ml):.2f}",
                "_dose_mcg": f"{float(dose_mcg):.0f}" if dose_mcg else "—",
            })
        self._table.load_data(rows)

    # ── Actions ──────────────────────────────────────────────────────────────

    def _reset_filters(self):
        self._f_notes.blockSignals(True)
        self._f_from_cb.blockSignals(True)
        self._f_to_cb.blockSignals(True)
        self._f_notes.clear()
        self._f_from_cb.setChecked(False)
        self._f_to_cb.setChecked(False)
        self._f_notes.blockSignals(False)
        self._f_from_cb.blockSignals(False)
        self._f_to_cb.blockSignals(False)
        self._f_peptide.setCurrentIndex(0)   # triggers _apply_filters via signal
        self._f_site.setCurrentIndex(0)
        self._f_method.setCurrentIndex(0)
        self._f_protocol.setCurrentIndex(0)

    def _on_details(self, row: dict):
        dlg = _DetailsDialog(row, self)
        dlg.exec()

    def _on_delete(self, row: dict):
        admin_id = row.get("id")
        if not confirm_dialog(
            self,
            "Elimina Somministrazione",
            f"Eliminare la somministrazione #{admin_id}?\n"
            "Il volume NON verrà ripristinato alla preparazione.",
        ):
            return
        try:
            ok, msg = self.manager.soft_delete_administration(admin_id, restore_volume=False)
            if ok:
                self.app.show_message(f"Somministrazione #{admin_id} eliminata")
                self.refresh()
            else:
                error_dialog(self, "Errore eliminazione", msg)
        except Exception as exc:
            error_dialog(self, "Errore", str(exc))


# ═══════════════════════════════════════════════════════════════════════════════
#  STATISTICS TAB
# ═══════════════════════════════════════════════════════════════════════════════


class StatisticsTab(BaseView):
    """Statistiche aggregate: globali, per peptide, per mese."""

    _PEPTIDE_COLS = [
        {"key": "peptide",    "label": "Peptide",   "stretch": True},
        {"key": "count",      "label": "N",          "width": 60},
        {"key": "total_ml",   "label": "ml tot.",    "width": 80},
        {"key": "total_mcg",  "label": "mcg tot.",   "width": 90},
        {"key": "avg_ml",     "label": "ml medi",    "width": 80},
    ]

    _MONTH_COLS = [
        {"key": "month",      "label": "Mese",       "width": 100},
        {"key": "count",      "label": "N",           "width": 60},
        {"key": "total_ml",   "label": "ml tot.",     "width": 80},
        {"key": "total_mcg",  "label": "mcg tot.",    "width": 90},
    ]

    def __init__(self, app, parent=None):
        super().__init__(app, parent)
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        lay = self.layout()

        title = QLabel("Statistiche")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        lay.addWidget(title)

        refresh_btn = QPushButton("Aggiorna")
        refresh_btn.setFixedWidth(90)
        refresh_btn.clicked.connect(self.refresh)
        hdr = QHBoxLayout()
        hdr.addWidget(title)
        hdr.addStretch()
        hdr.addWidget(refresh_btn)
        lay.addLayout(hdr)

        # Global KPIs
        kbar = QHBoxLayout()
        kbar.setSpacing(8)
        f1, self._k_total  = _kpi_frame("totale sommin.",   "—", "#42a5f5")
        f2, self._k_ml     = _kpi_frame("ml totali",        "—", "#26c6da")
        f3, self._k_avg    = _kpi_frame("ml medi/dose",     "—", "#ffa726")
        f4, self._k_days   = _kpi_frame("giorni distinti",  "—", "#ab47bc")
        f5, self._k_peptid = _kpi_frame("peptidi distinti", "—", "#66bb6a")
        for f in (f1, f2, f3, f4, f5):
            kbar.addWidget(f)
        kbar.addStretch()
        lay.addLayout(kbar)

        self._lbl_range = QLabel("")
        self._lbl_range.setStyleSheet("color: #9e9e9e; font-size: 11px;")
        lay.addWidget(self._lbl_range)

        lay.addWidget(_sep())

        # Per-peptide + per-month side by side
        tables_row = QHBoxLayout()
        tables_row.setSpacing(16)

        left = QVBoxLayout()
        left.addWidget(QLabel("Per Peptide"))
        self._tbl_peptide = DataTable(self._PEPTIDE_COLS)
        left.addWidget(self._tbl_peptide, 1)
        tables_row.addLayout(left, 6)

        right = QVBoxLayout()
        right.addWidget(QLabel("Per Mese"))
        self._tbl_month = DataTable(self._MONTH_COLS)
        right.addWidget(self._tbl_month, 1)
        tables_row.addLayout(right, 4)

        lay.addLayout(tables_row, 1)

    def refresh(self):
        if not _HAS_PANDAS:
            self._k_total.setText("N/A")
            return
        try:
            df = self.manager.get_all_administrations_df()
        except Exception as exc:
            error_dialog(self, "Errore caricamento", str(exc))
            return

        self._update_kpis(df)
        self._update_by_peptide(df)
        self._update_by_month(df)

    def _update_kpis(self, df):
        if df.empty:
            for lbl in (self._k_total, self._k_ml, self._k_avg, self._k_days, self._k_peptid):
                lbl.setText("0")
            self._lbl_range.setText("")
            return

        total = len(df)
        total_ml = float(df["dose_ml"].sum())
        avg_ml = total_ml / total if total else 0.0
        days = df["date"].nunique()
        # count distinct peptides: split multi-peptide entries by ","
        all_peps = set()
        for cell in df["peptide_names"].dropna():
            for p in str(cell).split(","):
                p = p.strip()
                if p and p != "N/A":
                    all_peps.add(p)

        self._k_total.setText(str(total))
        self._k_ml.setText(f"{total_ml:.1f}")
        self._k_avg.setText(f"{avg_ml:.2f}")
        self._k_days.setText(str(days))
        self._k_peptid.setText(str(len(all_peps)))
        self._lbl_range.setText(
            f"Prima: {df['date'].min()}  •  Ultima: {df['date'].max()}"
        )

    def _update_by_peptide(self, df):
        if df.empty:
            self._tbl_peptide.load_data([])
            return

        # Explode multi-peptide rows
        expanded = []
        for _, r in df.iterrows():
            names = str(r.get("peptide_names", "") or "")
            for pep in names.split(","):
                pep = pep.strip()
                if pep and pep != "N/A":
                    expanded.append({
                        "peptide": pep,
                        "dose_ml": float(r["dose_ml"] or 0),
                        "dose_mcg": float(r["dose_mcg"] or 0) if r.get("dose_mcg") else 0.0,
                    })

        if not expanded:
            self._tbl_peptide.load_data([])
            return

        exp_df = pd.DataFrame(expanded)
        grp = exp_df.groupby("peptide").agg(
            count=("dose_ml", "count"),
            total_ml=("dose_ml", "sum"),
            total_mcg=("dose_mcg", "sum"),
            avg_ml=("dose_ml", "mean"),
        ).reset_index().sort_values("count", ascending=False)

        rows = []
        for _, r in grp.iterrows():
            rows.append({
                "peptide":   r["peptide"],
                "count":     int(r["count"]),
                "total_ml":  f"{r['total_ml']:.1f}",
                "total_mcg": f"{r['total_mcg']:.0f}" if r["total_mcg"] else "—",
                "avg_ml":    f"{r['avg_ml']:.2f}",
            })
        self._tbl_peptide.load_data(rows)

    def _update_by_month(self, df):
        if df.empty:
            self._tbl_month.load_data([])
            return

        df2 = df.copy()
        df2["month"] = df2["date"].apply(lambda d: str(d)[:7])  # YYYY-MM

        has_mcg = "dose_mcg" in df2.columns

        if has_mcg:
            grp = df2.groupby("month").agg(
                count=("dose_ml", "count"),
                total_ml=("dose_ml", "sum"),
                total_mcg=("dose_mcg", "sum"),
            ).reset_index().sort_values("month", ascending=False)
        else:
            grp = df2.groupby("month").agg(
                count=("dose_ml", "count"),
                total_ml=("dose_ml", "sum"),
            ).reset_index().sort_values("month", ascending=False)

        rows = []
        for _, r in grp.iterrows():
            rows.append({
                "month":     r["month"],
                "count":     int(r["count"]),
                "total_ml":  f"{r['total_ml']:.1f}",
                "total_mcg": f"{r.get('total_mcg', 0):.0f}" if has_mcg else "—",
            })
        self._tbl_month.load_data(rows)
