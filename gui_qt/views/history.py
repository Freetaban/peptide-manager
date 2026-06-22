"""History section — Administrations list and Statistics."""

import io
import base64
from datetime import date, timedelta

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QPushButton,
    QWidget,
    QComboBox,
    QFrame,
    QCheckBox,
    QDateEdit,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QSizePolicy,
    QFileDialog,
    QScrollArea,
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
#  EDIT DIALOG
# ═══════════════════════════════════════════════════════════════════════════════

_SITES = ["Addome", "Coscia DX", "Coscia SX", "Braccio DX", "Braccio SX",
          "Gluteo DX", "Gluteo SX"]
_METHODS = ["Sottocutanea", "Intramuscolare", "Intradermica"]


class _EditDialog(QDialog):
    """Editable form for an existing administration (requires edit mode)."""

    def __init__(self, app, row: dict, parent=None):
        super().__init__(parent)
        self._app = app
        self._row = row
        self._admin_id = row.get("id")
        self.setWindowTitle(f"Modifica somministrazione #{self._admin_id}")
        self.setMinimumWidth(440)
        self.setStyleSheet(_DLG_STYLE)
        self._build_ui()

    def _build_ui(self):
        row = self._row
        lay = QVBoxLayout(self)
        lay.setSpacing(12)

        hdr = QLabel(row.get("peptide_names", "") or "Somministrazione")
        hdr.setStyleSheet("font-size: 15px; font-weight: bold; color: #e0e0e0;")
        lay.addWidget(hdr)

        grid = QGridLayout()
        grid.setColumnStretch(1, 1)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(8)
        self._grid_row = 0

        def add_field(label, widget):
            lbl = QLabel(label)
            lbl.setStyleSheet("color: #9e9e9e;")
            grid.addWidget(lbl, self._grid_row, 0)
            grid.addWidget(widget, self._grid_row, 1)
            self._grid_row += 1

        dt = str(row.get("administration_datetime", "") or "")

        self._date = QDateEdit()
        self._date.setCalendarPopup(True)
        self._date.setDisplayFormat("dd/MM/yyyy")
        qd = QDate.fromString(dt[:10], "yyyy-MM-dd")
        self._date.setDate(qd if qd.isValid() else QDate.currentDate())
        add_field("Data", self._date)

        self._time = QLineEdit(dt[11:16] if len(dt) >= 16 else "")
        add_field("Ora (HH:MM)", self._time)

        dose_ml = float(row.get("dose_ml", 0) or 0)
        self._dose = QLineEdit(f"{dose_ml:.2f}")
        add_field("Dose (ml)", self._dose)

        self._site = QComboBox()
        self._site.setEditable(True)
        self._site.addItems(_SITES)
        self._site.setCurrentText(row.get("injection_site", "") or "")
        add_field("Sito iniezione", self._site)

        self._method = QComboBox()
        self._method.setEditable(True)
        self._method.addItems(_METHODS)
        self._method.setCurrentText(row.get("injection_method", "") or "")
        add_field("Metodo", self._method)

        lay.addLayout(grid)

        lay.addWidget(QLabel("Note"))
        self._notes = QTextEdit()
        self._notes.setMaximumHeight(80)
        self._notes.setPlainText(row.get("notes", "") or "")
        lay.addWidget(self._notes)

        lay.addWidget(QLabel("Effetti collaterali"))
        self._side = QTextEdit()
        self._side.setMaximumHeight(60)
        self._side.setPlainText(row.get("side_effects", "") or "")
        lay.addWidget(self._side)

        lay.addWidget(_sep())

        brow = QHBoxLayout()
        brow.addStretch()
        cancel = QPushButton("Annulla")
        cancel.setStyleSheet(
            "background: #424242; color: #e0e0e0; padding: 8px 16px;"
            " border-radius: 4px; font-weight: bold;"
        )
        cancel.clicked.connect(self.reject)
        brow.addWidget(cancel)
        save = QPushButton("Salva")
        save.setStyleSheet(
            "background: #66bb6a; color: #fff; padding: 8px 16px;"
            " border-radius: 4px; font-weight: bold;"
        )
        save.clicked.connect(self._save)
        brow.addWidget(save)
        lay.addLayout(brow)

    def _save(self):
        from datetime import datetime as _dt

        try:
            dose_ml = round(float(self._dose.text().replace(",", ".")), 2)
        except ValueError:
            error_dialog(self, "Dose non valida", "Inserisci un numero per la dose.")
            return
        if dose_ml <= 0:
            error_dialog(self, "Dose non valida", "La dose deve essere > 0.")
            return

        time_str = self._time.text().strip()
        try:
            _dt.strptime(time_str, "%H:%M")
        except ValueError:
            error_dialog(self, "Ora non valida", "Formato ora non valido (HH:MM).")
            return

        admin_datetime = f"{self._date.date().toString('yyyy-MM-dd')} {time_str}"

        try:
            self._app.manager.update_administration(
                self._admin_id,
                administration_datetime=admin_datetime,
                dose_ml=dose_ml,
                injection_site=self._site.currentText().strip(),
                injection_method=self._method.currentText().strip(),
                notes=self._notes.toPlainText().strip(),
                side_effects=self._side.toPlainText().strip(),
            )
        except Exception as exc:
            error_dialog(self, "Errore aggiornamento", str(exc))
            return

        self._app.show_message(f"Somministrazione #{self._admin_id} aggiornata")
        self.accept()


# ═══════════════════════════════════════════════════════════════════════════════
#  PEPTIDE REPORT
# ═══════════════════════════════════════════════════════════════════════════════

_CYCLE_COLORS = ['#42a5f5', '#66bb6a', '#ffa726', '#ab47bc', '#26c6da', '#ef9a9a']


def _compute_off_spans(cycle, today):
    """Yield (start_date, end_date) pairs for consecutive OFF days in a cycle."""
    start_str = cycle.get('start_date')
    if not start_str:
        return
    start = date.fromisoformat(start_str)
    end_str = cycle.get('end_date')
    end = date.fromisoformat(end_str) if end_str else today

    weekdays = cycle.get('weekdays')
    days_on = cycle.get('days_on')
    days_off = cycle.get('days_off') or 0

    off_start = None
    d = start
    while d <= end:
        if weekdays is not None:
            is_off = d.weekday() not in weekdays
        elif days_on and days_on > 0:
            elapsed = (d - start).days
            cycle_len = days_on + days_off
            is_off = (elapsed % cycle_len) >= days_on if cycle_len > 0 else False
        else:
            is_off = False  # giornaliero: nessun OFF

        if is_off:
            if off_start is None:
                off_start = d
        else:
            if off_start is not None:
                yield (off_start, d - timedelta(days=1))
                off_start = None
        d += timedelta(days=1)

    if off_start is not None:
        yield (off_start, end)


def _build_report_html(data, b64_img=None):
    """Generate a self-contained HTML report for the peptide."""
    pep = data['peptide']['name']
    stats = data['stats']
    cycles = data['cycles']
    admins = data['administrations']

    # Per-cycle stats
    cycle_stats = {}
    for a in admins:
        cid = a['cycle_id'] or 0
        if cid not in cycle_stats:
            cycle_stats[cid] = {'count': 0, 'ml': 0.0, 'mcg': 0.0,
                                 'name': a['cycle_name']}
        cycle_stats[cid]['count'] += 1
        cycle_stats[cid]['ml'] += a['dose_ml']
        cycle_stats[cid]['mcg'] += a['dose_mcg']

    cycle_rows = ""
    for c in cycles:
        cs = cycle_stats.get(c['id'], {'count': 0, 'ml': 0.0, 'mcg': 0.0})
        avg = cs['ml'] / cs['count'] if cs['count'] else 0
        cycle_rows += (
            f"<tr><td>{c['name']}</td><td>{c['status']}</td>"
            f"<td>{c['start_date'] or '—'}</td><td>{c['end_date'] or '—'}</td>"
            f"<td>{cs['count']}</td><td>{cs['ml']:.2f}</td>"
            f"<td>{cs['mcg']:.0f}</td><td>{avg:.3f}</td></tr>"
        )

    img_tag = (f'<img src="data:image/png;base64,{b64_img}" '
               f'style="max-width:100%;margin-top:16px">'
               if b64_img else '')

    return f"""<!DOCTYPE html>
<html lang="it"><head><meta charset="utf-8">
<title>Report: {pep}</title>
<style>
  body{{font-family:sans-serif;background:#1e1e1e;color:#e0e0e0;padding:24px}}
  h1{{color:#42a5f5}} h2{{color:#aeaeae;border-bottom:1px solid #424242;padding-bottom:4px}}
  table{{border-collapse:collapse;width:100%;margin-top:8px}}
  th{{background:#2d2d2d;color:#aeaeae;padding:8px;text-align:left;font-size:12px}}
  td{{padding:6px 8px;border-bottom:1px solid #333;font-size:12px}}
  .kpi{{display:inline-block;background:#2d2d2d;border-radius:6px;
        padding:12px 20px;margin:4px;text-align:center}}
  .kpi-val{{font-size:22px;font-weight:bold;color:#42a5f5}}
  .kpi-lbl{{font-size:11px;color:#9e9e9e}}
</style></head><body>
<h1>{pep}</h1>
<p style="color:#9e9e9e">Periodo: {stats['first_date'] or '—'} → {stats['last_date'] or '—'}</p>
<h2>Riepilogo</h2>
<div>
  <div class="kpi"><div class="kpi-val">{stats['total_admin']}</div>
    <div class="kpi-lbl">somministrazioni</div></div>
  <div class="kpi"><div class="kpi-val">{stats['total_ml']:.2f}</div>
    <div class="kpi-lbl">ml totali</div></div>
  <div class="kpi"><div class="kpi-val">{stats['total_mcg']:.0f}</div>
    <div class="kpi-lbl">mcg totali</div></div>
  <div class="kpi"><div class="kpi-val">{stats['cycle_count']}</div>
    <div class="kpi-lbl">cicli</div></div>
</div>
<h2>Per Ciclo</h2>
<table><tr><th>Ciclo</th><th>Stato</th><th>Inizio</th><th>Fine</th>
<th>Iniezioni</th><th>ml tot.</th><th>mcg tot.</th><th>ml/inj.</th></tr>
{cycle_rows}</table>
<h2>Grafici</h2>{img_tag}
</body></html>"""


class _PeptideReportDialog(QDialog):
    """Storico completo per un singolo peptide: riepilogo + grafici + export HTML."""

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self._app = app
        self._data = None
        self._fig = None
        self.setWindowTitle("Report Peptide")
        self.setMinimumWidth(900)
        self.setMinimumHeight(700)
        self.setStyleSheet(
            "QDialog{background:#1e1e1e}"
            "QLineEdit,QComboBox,QDateEdit,QTextEdit{"
            "background:#2d2d2d;border:1px solid #424242;"
            "border-radius:4px;padding:5px 8px;color:#e0e0e0}"
            "QDateEdit::drop-down{border:none;background:#424242;border-radius:2px}"
            "QTabWidget::pane{border:1px solid #424242}"
            "QTabBar::tab{background:#2d2d2d;color:#aeaeae;padding:6px 14px;"
            "border:1px solid #424242;border-bottom:none;border-radius:3px 3px 0 0}"
            "QTabBar::tab:selected{background:#353535;color:#e0e0e0}"
            "QTableWidget{background:#2d2d2d;color:#e0e0e0;gridline-color:#333}"
            "QHeaderView::section{background:#353535;color:#aeaeae;padding:4px;"
            "border:1px solid #424242}"
            "QCheckBox{color:#aeaeae}"
        )
        self._load_peptides()
        self._build_ui()

    def _load_peptides(self):
        try:
            self._peptides = self._app.manager.get_peptides() or []
        except Exception:
            self._peptides = []

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(8)

        # ── Selectors ───────────────────────────────────────────────────
        sel = QHBoxLayout()
        sel.setSpacing(8)
        sel.addWidget(QLabel("Peptide:"))
        self._pep_combo = QComboBox()
        self._pep_combo.setMinimumWidth(200)
        for p in self._peptides:
            self._pep_combo.addItem(p.get('name', '?'), p.get('id'))
        sel.addWidget(self._pep_combo)

        sel.addSpacing(12)
        self._from_cb = QCheckBox("Dal:")
        self._from_date = QDateEdit()
        self._from_date.setCalendarPopup(True)
        self._from_date.setDisplayFormat("dd/MM/yyyy")
        self._from_date.setDate(QDate.currentDate().addMonths(-6))
        self._from_date.setEnabled(False)
        self._from_cb.toggled.connect(self._from_date.setEnabled)
        sel.addWidget(self._from_cb)
        sel.addWidget(self._from_date)

        self._to_cb = QCheckBox("Al:")
        self._to_date = QDateEdit()
        self._to_date.setCalendarPopup(True)
        self._to_date.setDisplayFormat("dd/MM/yyyy")
        self._to_date.setDate(QDate.currentDate())
        self._to_date.setEnabled(False)
        self._to_cb.toggled.connect(self._to_date.setEnabled)
        sel.addWidget(self._to_cb)
        sel.addWidget(self._to_date)

        load_btn = QPushButton("Carica")
        load_btn.setStyleSheet(
            "background:#1565c0;color:#fff;padding:6px 16px;"
            "border-radius:4px;font-weight:bold"
        )
        load_btn.clicked.connect(self._load)
        sel.addWidget(load_btn)
        sel.addStretch()
        lay.addLayout(sel)

        # ── Tabs ────────────────────────────────────────────────────────
        self._tabs = QTabWidget()

        self._summary_scroll = QScrollArea()
        self._summary_scroll.setWidgetResizable(True)
        self._summary_scroll.setStyleSheet("QScrollArea{border:none}")
        self._summary_content = QWidget()
        self._summary_lay = QVBoxLayout(self._summary_content)
        self._summary_lay.setAlignment(Qt.AlignTop)
        self._summary_scroll.setWidget(self._summary_content)
        self._tabs.addTab(self._summary_scroll, "Riepilogo")

        self._chart_widget = QWidget()
        self._chart_lay = QVBoxLayout(self._chart_widget)
        self._tabs.addTab(self._chart_widget, "Grafici")

        lay.addWidget(self._tabs, 1)

        # ── Buttons ─────────────────────────────────────────────────────
        brow = QHBoxLayout()
        brow.addStretch()
        self._html_btn = QPushButton("Salva HTML")
        self._html_btn.setEnabled(False)
        self._html_btn.clicked.connect(self._save_html)
        brow.addWidget(self._html_btn)
        close_btn = QPushButton("Chiudi")
        close_btn.setStyleSheet(
            "background:#424242;color:#e0e0e0;padding:6px 14px;border-radius:4px"
        )
        close_btn.clicked.connect(self.accept)
        brow.addWidget(close_btn)
        lay.addLayout(brow)

    # ── Load ────────────────────────────────────────────────────────────

    def _load(self):
        pid = self._pep_combo.currentData()
        if not pid:
            return
        df = self._from_date.date().toString("yyyy-MM-dd") if self._from_cb.isChecked() else None
        dt = self._to_date.date().toString("yyyy-MM-dd") if self._to_cb.isChecked() else None
        try:
            self._data = self._app.manager.get_peptide_history_report(pid, df, dt)
        except Exception as e:
            from ..components.dialogs import error_dialog
            error_dialog(self, "Errore", str(e))
            return
        self._refresh_summary()
        self._refresh_charts()
        self._html_btn.setEnabled(True)

    # ── Summary tab ─────────────────────────────────────────────────────

    def _refresh_summary(self):
        while self._summary_lay.count():
            item = self._summary_lay.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        d = self._data
        s = d['stats']

        title = QLabel(d['peptide']['name'])
        title.setStyleSheet("font-size:16px;font-weight:bold;color:#42a5f5")
        self._summary_lay.addWidget(title)

        # KPI row
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(8)
        for val, lbl, color in [
            (str(s['total_admin']),       "somministrazioni",  "#42a5f5"),
            (f"{s['total_ml']:.2f} ml",   "ml totali",         "#26c6da"),
            (f"{s['total_mcg']:.0f} mcg", "mcg totali",        "#66bb6a"),
            (str(s['cycle_count']),        "cicli",             "#ab47bc"),
        ]:
            f, _ = _kpi_frame(lbl, val, color)
            kpi_row.addWidget(f)
        if s['first_date']:
            period = f"{s['first_date']} → {s['last_date']}"
            f, _ = _kpi_frame("periodo", period, "#ffa726")
            kpi_row.addWidget(f)
        kpi_row.addStretch()
        kpi_w = QWidget()
        kpi_w.setLayout(kpi_row)
        self._summary_lay.addWidget(kpi_w)

        # Per-cycle stats
        admins = d['administrations']
        cycles = d['cycles']
        if not cycles:
            self._summary_lay.addWidget(QLabel("Nessun ciclo trovato."))
            return

        cycle_stats = {}
        for a in admins:
            cid = a['cycle_id'] or 0
            if cid not in cycle_stats:
                cycle_stats[cid] = {'count': 0, 'ml': 0.0, 'mcg': 0.0}
            cycle_stats[cid]['count'] += 1
            cycle_stats[cid]['ml'] += a['dose_ml']
            cycle_stats[cid]['mcg'] += a['dose_mcg']

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color:#424242")
        self._summary_lay.addWidget(sep)

        lbl = QLabel("Per Ciclo")
        lbl.setStyleSheet("font-weight:bold;color:#aeaeae;padding:4px 0")
        self._summary_lay.addWidget(lbl)

        cols = ["Ciclo", "Stato", "Inizio", "Fine",
                "Iniezioni", "ml tot.", "mcg tot.", "ml/inj."]
        tbl = QTableWidget(len(cycles), len(cols))
        tbl.setHorizontalHeaderLabels(cols)
        tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tbl.verticalHeader().setVisible(False)
        tbl.setAlternatingRowColors(True)
        tbl.setStyleSheet(
            "QTableWidget{background:#2d2d2d;color:#e0e0e0;gridline-color:#333}"
            "QHeaderView::section{background:#353535;color:#aeaeae;padding:4px;"
            "border:1px solid #333}"
        )
        hdr = tbl.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.Stretch)
        for col in range(1, len(cols)):
            hdr.setSectionResizeMode(col, QHeaderView.ResizeToContents)
        tbl.setFixedHeight(34 + len(cycles) * 28)

        for row, c in enumerate(cycles):
            cs = cycle_stats.get(c['id'], {'count': 0, 'ml': 0.0, 'mcg': 0.0})
            avg = cs['ml'] / cs['count'] if cs['count'] else 0.0
            for col, val in enumerate([
                c['name'], c['status'],
                c['start_date'] or '—', c['end_date'] or '—',
                str(cs['count']), f"{cs['ml']:.2f}",
                f"{cs['mcg']:.0f}", f"{avg:.3f}",
            ]):
                tbl.setItem(row, col, QTableWidgetItem(val))

        self._summary_lay.addWidget(tbl)
        self._summary_lay.addStretch()

    # ── Charts tab ──────────────────────────────────────────────────────

    def _refresh_charts(self):
        while self._chart_lay.count():
            item = self._chart_lay.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._fig = None

        if not _HAS_PANDAS:
            self._chart_lay.addWidget(QLabel("Pandas non disponibile."))
            return

        try:
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
            from matplotlib.figure import Figure
            import matplotlib.dates as mdates
            import pandas as pd
        except ImportError:
            self._chart_lay.addWidget(QLabel("Matplotlib non disponibile."))
            return

        admins = self._data['administrations']
        cycles = self._data['cycles']
        if not admins:
            self._chart_lay.addWidget(
                QLabel("Nessuna somministrazione nel periodo selezionato."))
            return

        df = pd.DataFrame(admins)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')

        today = date.today()

        fig = Figure(figsize=(11, 7), facecolor='#1e1e1e')
        fig.subplots_adjust(hspace=0.42, left=0.08, right=0.97, top=0.94, bottom=0.10)
        ax1 = fig.add_subplot(2, 1, 1)
        ax2 = fig.add_subplot(2, 1, 2)

        for ax in (ax1, ax2):
            ax.set_facecolor('#252525')
            for sp in ax.spines.values():
                sp.set_color('#424242')
            ax.tick_params(colors='#aeaeae', labelsize=8)
            ax.yaxis.label.set_color('#aeaeae')
            ax.title.set_color('#e0e0e0')
            ax.grid(True, color='#333', linewidth=0.5, alpha=0.6)

        import matplotlib.patches as mpatches
        legend_handles = []

        # ── Background: cycle spans + OFF spans ──────────────────────
        off_patch_added = False
        for i, cycle in enumerate(cycles):
            if not cycle.get('start_date'):
                continue
            ts = pd.Timestamp(cycle['start_date'])
            end_raw = cycle.get('end_date')
            te = pd.Timestamp(end_raw) if end_raw else pd.Timestamp(today)
            color = _CYCLE_COLORS[i % len(_CYCLE_COLORS)]

            for ax in (ax1, ax2):
                ax.axvspan(ts, te, alpha=0.06, color=color, zorder=0)

            for off_s, off_e in _compute_off_spans(cycle, today):
                ts_off = pd.Timestamp(off_s)
                te_off = pd.Timestamp(off_e) + pd.Timedelta(days=1)
                for ax in (ax1, ax2):
                    ax.axvspan(ts_off, te_off, alpha=0.18,
                               color='#ef5350', zorder=1)
            if not off_patch_added and list(_compute_off_spans(cycle, today)):
                legend_handles.append(
                    mpatches.Patch(color='#ef5350', alpha=0.4, label='Giorni OFF'))
                off_patch_added = True

        # ── Administrations per cycle ─────────────────────────────────
        for i, cycle in enumerate(cycles):
            color = _CYCLE_COLORS[i % len(_CYCLE_COLORS)]
            cdf = df[df['cycle_id'] == cycle['id']]
            if cdf.empty:
                continue
            ax1.vlines(cdf['date'], 0, cdf['dose_ml'],
                       color=color, linewidth=1.5, alpha=0.85, zorder=3)
            sc = ax1.scatter(cdf['date'], cdf['dose_ml'],
                             color=color, s=28, zorder=4,
                             label=cycle['name'])
            legend_handles.append(sc)

        # Admins without cycle
        no_cyc = df[df['cycle_id'].isna()]
        if not no_cyc.empty:
            ax1.vlines(no_cyc['date'], 0, no_cyc['dose_ml'],
                       color='#9e9e9e', linewidth=1.5, alpha=0.8, zorder=3)
            sc = ax1.scatter(no_cyc['date'], no_cyc['dose_ml'],
                             color='#9e9e9e', s=28, zorder=4, label='Senza ciclo')
            legend_handles.append(sc)

        ax1.set_title("Somministrazioni nel tempo  "
                      "(sfondo rosso = giorni OFF)", fontsize=10)
        ax1.set_ylabel("Dose (ml)", fontsize=9)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
        ax1.xaxis.set_major_locator(mdates.AutoDateLocator())
        if legend_handles:
            ax1.legend(handles=legend_handles, fontsize=8,
                       facecolor='#2d2d2d', edgecolor='#424242',
                       labelcolor='#e0e0e0', loc='upper left')

        # ── Cumulative ───────────────────────────────────────────────
        df['cum_ml'] = df['dose_ml'].cumsum()
        ax2.step(df['date'], df['cum_ml'], color='#42a5f5',
                 linewidth=1.8, where='post', zorder=3)
        ax2.fill_between(df['date'], df['cum_ml'], alpha=0.15,
                         color='#42a5f5', step='post', zorder=2)
        ax2.set_title("Dose cumulativa (ml)", fontsize=10)
        ax2.set_ylabel("ml cumulativi", fontsize=9)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
        ax2.xaxis.set_major_locator(mdates.AutoDateLocator())

        fig.autofmt_xdate(rotation=30)

        canvas = FigureCanvasQTAgg(fig)
        canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._chart_lay.addWidget(canvas)
        self._fig = fig

    # ── Export ──────────────────────────────────────────────────────────

    def _figure_to_b64(self):
        if self._fig is None:
            return None
        buf = io.BytesIO()
        self._fig.savefig(buf, format='png', dpi=150,
                          facecolor='#1e1e1e', bbox_inches='tight')
        buf.seek(0)
        return base64.b64encode(buf.read()).decode()

    def _save_html(self):
        if not self._data:
            return
        pep_name = self._data['peptide']['name'].replace(' ', '_')
        path, _ = QFileDialog.getSaveFileName(
            self, "Salva Report HTML",
            f"report_{pep_name}.html", "HTML (*.html)"
        )
        if not path:
            return
        html = _build_report_html(self._data, self._figure_to_b64())
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(html)
            self._app.show_message(f"Report salvato: {path}")
        except Exception as e:
            from ..components.dialogs import error_dialog
            error_dialog(self, "Errore", str(e))


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

        report_btn = QPushButton("Report Peptide")
        report_btn.setStyleSheet(
            "QPushButton{background:#1565c0;color:#fff;padding:5px 12px;"
            "border-radius:4px;font-weight:bold}"
            "QPushButton:hover{background:#1976d2}"
        )
        report_btn.clicked.connect(self._on_report)
        fbar.addWidget(report_btn)
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
            {"label": "Modifica", "callback": self._on_edit,
             "enabled_when": lambda: self.edit_mode},
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

    def _on_report(self):
        dlg = _PeptideReportDialog(self.app, parent=self)
        dlg.exec()

    def _on_details(self, row: dict):
        dlg = _DetailsDialog(row, self)
        dlg.exec()

    def _on_edit(self, row: dict):
        dlg = _EditDialog(self.app, row, self)
        if dlg.exec() == QDialog.Accepted:
            # Editing a dose adjusts a preparation volume too → refresh all.
            self.app.refresh_all_views()

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
