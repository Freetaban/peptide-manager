"""Today view — week strip + multi-day schedule with configurable range."""

from datetime import date, timedelta, datetime
from functools import partial

from PySide6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QFrame,
    QWidget,
    QComboBox,
    QSizePolicy,
    QDialog,
    QLineEdit,
    QTextEdit,
    QGridLayout,
    QDialogButtonBox,
)
from PySide6.QtCore import Qt, Signal

from .base import BaseView


def _parse_date(val):
    if val is None:
        return None
    if isinstance(val, date) and not isinstance(val, datetime):
        return val
    if isinstance(val, datetime):
        return val.date()
    try:
        return date.fromisoformat(str(val)[:10])
    except (ValueError, TypeError):
        return None


_DAY_SHORT = ["Lu", "Ma", "Me", "Gi", "Ve", "Sa", "Do"]
_DAY_FULL = [
    "Lunedì", "Martedì", "Mercoledì", "Giovedì",
    "Venerdì", "Sabato", "Domenica",
]
_MONTH = [
    "Gen", "Feb", "Mar", "Apr", "Mag", "Giu",
    "Lug", "Ago", "Set", "Ott", "Nov", "Dic",
]

_BLUE = "#42a5f5"
_GREEN = "#66bb6a"
_RED = "#ef5350"
_AMBER = "#ffca28"
_DIM = "#757575"
_SEC = "#aeaeae"

_BTN_REGISTER = (
    "QPushButton { background: %s; color: #fff; border: none;"
    " border-radius: 4px; padding: 4px 14px;"
    " font-size: 12px; font-weight: bold; }"
    "QPushButton:hover { background: #66bb6a; }"
    "QPushButton:pressed { background: #388e3c; }" % _GREEN
)

_BTN_REGISTER_PARTIAL = (
    "QPushButton { background: %s; color: #1a1a1a; border: none;"
    " border-radius: 4px; padding: 4px 14px;"
    " font-size: 12px; font-weight: bold; }"
    "QPushButton:hover { background: #ffd54f; }"
    "QPushButton:pressed { background: #f9a825; }" % _AMBER
)


def _fmt_date(d):
    return f"{_DAY_FULL[d.weekday()]} {d.day} {_MONTH[d.month - 1]}"


# ═══════════════════════════════════════════════════════════════════════
# Day card for the week strip
# ═══════════════════════════════════════════════════════════════════════


class _DayCard(QFrame):
    """Clickable day card with separate labels for name, number, badge."""

    clicked = Signal()

    def __init__(self, day_name, day_num, is_today=False):
        super().__init__()
        self._is_today = is_today
        self._checked = is_today
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(60)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 6, 4, 6)
        lay.setSpacing(0)
        lay.setAlignment(Qt.AlignCenter)

        self._lbl_name = QLabel(day_name)
        self._lbl_name.setAlignment(Qt.AlignCenter)
        self._lbl_num = QLabel(str(day_num))
        self._lbl_num.setAlignment(Qt.AlignCenter)

        for w in (self._lbl_name, self._lbl_num):
            w.setAttribute(Qt.WA_TransparentForMouseEvents)
            lay.addWidget(w)

        self._apply_style()

    def set_checked(self, val):
        self._checked = val
        self._apply_style()

    def mousePressEvent(self, event):
        self.clicked.emit()

    def _apply_style(self):
        if self._is_today and self._checked:
            bg, nc, dc = _BLUE, "rgba(255,255,255,.85)", "#ffffff"
        elif self._is_today:
            bg, nc, dc = "#2a6cb0", "rgba(255,255,255,.7)", "#dddddd"
        elif self._checked:
            bg, nc, dc = "#353535", "#e0e0e0", "#e0e0e0"
        else:
            bg, nc, dc = "#2d2d2d", _SEC, "#e0e0e0"

        border = f"border: 1px solid {_BLUE};" if (self._checked and not self._is_today) else \
                 "" if self._is_today else "border: 1px solid #424242;"
        self.setStyleSheet(f"background: {bg}; border-radius: 8px; {border}")
        t = "background: transparent;"
        self._lbl_name.setStyleSheet(f"font-size: 11px; color: {nc}; {t}")
        self._lbl_num.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {dc}; {t}")


# ═══════════════════════════════════════════════════════════════════════
# Registration dialog
# ═══════════════════════════════════════════════════════════════════════

_SITES = ["Addome", "Coscia DX", "Coscia SX", "Braccio DX", "Braccio SX",
          "Gluteo DX", "Gluteo SX"]
_METHODS = [("Sottocutanea", "Sottocutanea (SC)"),
            ("Intramuscolare", "Intramuscolare (IM)"),
            ("Intradermica", "Intradermica (ID)")]

_DLG_INPUT = (
    "QLineEdit, QComboBox, QTextEdit {"
    " background: #2d2d2d; border: 1px solid #424242;"
    " border-radius: 4px; padding: 6px 10px; color: #e0e0e0; }"
    "QLineEdit:focus, QTextEdit:focus { border-color: #42a5f5; }"
)


class _RegisterDialog(QDialog):
    """Modal form for reviewing / editing before saving an administration."""

    def __init__(self, app, group, parent=None):
        super().__init__(parent)
        self._app = app
        self._group = group
        self.setWindowTitle("Registra somministrazione")
        self.setMinimumWidth(480)
        self.setStyleSheet(
            "QDialog { background: #1e1e1e; }" + _DLG_INPUT
        )
        self._build_ui()

    def _build_ui(self):
        first = self._group[0]
        now = datetime.now()

        # Peptide names header
        names = " + ".join(g.get("peptide_name", "?") for g in self._group)

        is_partial = first.get("status") == "insufficient_volume"
        # For insufficient_volume: suggested_dose_ml is None; use available_ml instead
        target_ml = max((g.get("suggested_dose_ml") or g.get("available_ml") or 0) for g in self._group)
        # Pre-fill with available (partial) dose when volume is insufficient
        ml = target_ml

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        header = QLabel(names)
        header.setStyleSheet("font-size: 15px; font-weight: bold; color: #e0e0e0;")
        layout.addWidget(header)

        # Warning banner for partial dose
        if is_partial:
            missing_ml = max((g.get("missing_ml") or 0) for g in self._group)
            warn_lbl = QLabel(
                f"⚠  Volume insufficiente — disponibile: {ml:.2f} ml"
                f" (mancano ~{missing_ml:.2f} ml).\n"
                "Puoi procedere con la dose disponibile o modificarla."
            )
            warn_lbl.setWordWrap(True)
            warn_lbl.setStyleSheet(
                f"color: {_AMBER}; background: #2a2000; border: 1px solid {_AMBER};"
                " border-radius: 4px; padding: 8px; font-size: 12px;"
            )
            layout.addWidget(warn_lbl)

        # Form grid
        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(8)
        row = 0

        def add_label(text, r):
            lbl = QLabel(text)
            lbl.setStyleSheet("color: #aeaeae;")
            grid.addWidget(lbl, r, 0)

        # Dose ml
        add_label("Dose (ml)", row)
        self._dose = QLineEdit(f"{ml:.2f}")
        self._dose.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #ef5350;"
            " background: #2d2d2d; border: 1px solid #424242;"
            " border-radius: 4px; padding: 6px 10px;"
        )
        grid.addWidget(self._dose, row, 1)
        row += 1

        # Volume available hint
        dist = self._merged_distribution()
        avail = sum(d.get("prep_details", {}).get("volume_remaining_ml", 0) for d in dist)
        if avail > 0:
            hint = QLabel(f"Disponibile: {avail:.2f} ml")
            hint.setStyleSheet("color: #aeaeae; font-size: 11px;")
            grid.addWidget(hint, row, 1)
            row += 1

        # Date
        add_label("Data", row)
        self._date = QLineEdit(now.strftime("%Y-%m-%d"))
        grid.addWidget(self._date, row, 1)
        row += 1

        # Time
        add_label("Ora", row)
        self._time = QLineEdit(now.strftime("%H:%M"))
        grid.addWidget(self._time, row, 1)
        row += 1

        # Injection site
        add_label("Sito iniezione", row)
        self._site = QComboBox()
        for s in _SITES:
            self._site.addItem(s, s)
        grid.addWidget(self._site, row, 1)
        row += 1

        # Injection method
        add_label("Metodo", row)
        self._method = QComboBox()
        for val, label in _METHODS:
            self._method.addItem(label, val)
        grid.addWidget(self._method, row, 1)
        row += 1

        layout.addLayout(grid)

        # Notes
        layout.addWidget(QLabel("Note"))
        self._notes = QTextEdit()
        self._notes.setMaximumHeight(90)

        # Build default notes
        cycle_name = first.get("cycle_name", "N/A")
        target = first.get("target_dose_mcg", 0)
        merged_dist = self._merged_distribution()
        if len(merged_dist) > 1:
            parts = [f"Prep #{d['prep_id']}: {d['ml']:.2f}ml" for d in merged_dist]
            note = "Multi-prep FIFO:\n" + "\n".join(parts)
        elif merged_dist:
            note = f"Preparazione #{merged_dist[0]['prep_id']}"
        else:
            note = ""
        note += f"\nCiclo: {cycle_name}\nDose target: {target:.0f} mcg"
        if is_partial:
            missing_ml = max((g.get("missing_ml") or 0) for g in self._group)
            note += f"\n⚠ Dose ridotta — volume insufficiente (mancano ~{missing_ml:.2f} ml)"
        self._notes.setPlainText(note)
        layout.addWidget(self._notes)

        # Buttons
        btns = QDialogButtonBox()
        cancel = btns.addButton("Annulla", QDialogButtonBox.RejectRole)
        cancel.setStyleSheet(
            "background: #424242; color: #e0e0e0; padding: 8px 16px;"
            " border-radius: 4px; font-weight: bold;"
        )
        submit = btns.addButton("Registra", QDialogButtonBox.AcceptRole)
        submit.setStyleSheet(
            f"background: {_GREEN}; color: #fff; padding: 8px 16px;"
            f" border-radius: 4px; font-weight: bold;"
        )
        btns.rejected.connect(self.reject)
        btns.accepted.connect(self._submit)
        layout.addWidget(btns)

    def _merged_distribution(self):
        """Merge multi_prep_distribution across blend items (max ml per prep)."""
        merged: dict[int, dict] = {}
        for item in self._group:
            for d in (item.get("multi_prep_distribution") or []):
                pid = d["prep_id"]
                if pid not in merged or d["ml"] > merged[pid]["ml"]:
                    merged[pid] = dict(d)
        return list(merged.values())

    def _submit(self):
        # Validate dose
        try:
            user_dose = float(self._dose.text().replace(",", "."))
        except ValueError:
            self._app.show_message("Dose non valida", 4000)
            return
        if user_dose <= 0:
            self._app.show_message("La dose deve essere > 0", 4000)
            return

        # Validate date and time format before proceeding
        try:
            d = datetime.strptime(self._date.text().strip(), "%Y-%m-%d")
        except ValueError:
            self._app.show_message("Formato data non valido (YYYY-MM-DD)", 4000)
            return
        try:
            t = datetime.strptime(self._time.text().strip(), "%H:%M")
        except ValueError:
            self._app.show_message("Formato ora non valido (HH:MM)", 4000)
            return

        first = self._group[0]
        cycle_id = first.get("cycle_id")
        protocol_id = first.get("protocol_id")
        admin_datetime = f"{d.strftime('%Y-%m-%d')} {t.strftime('%H:%M')}"
        site = self._site.currentData()
        method = self._method.currentData()
        notes_text = self._notes.toPlainText().strip() or None

        distribution = self._merged_distribution()
        if not distribution:
            self._app.show_message("Nessuna preparazione disponibile", 4000)
            return

        # Recalculate FIFO if user changed dose significantly
        original_dose = sum(d["ml"] for d in distribution)
        if abs(user_dose - original_dose) > 0.01:
            remaining = user_dose
            recalc = []
            for dist in distribution:
                if remaining <= 0:
                    break
                avail = dist.get("prep_details", {}).get("volume_remaining_ml", 0)
                take = round(min(remaining, avail), 2) if avail else round(remaining, 2)
                if take > 0.01:
                    recalc.append({
                        "prep_id": dist["prep_id"],
                        "ml": take,
                        "concentration_mcg_per_ml": dist.get("concentration_mcg_per_ml", 0),
                    })
                    remaining -= take
            distribution = recalc

        try:
            admin_ids = []
            for i, dist in enumerate(distribution):
                prep_id = dist["prep_id"]
                dose_ml = round(dist["ml"], 2)
                note = notes_text
                if len(distribution) > 1:
                    extra = (f"\n[Multi-prep {i + 1}/{len(distribution)}:"
                             f" {dose_ml}ml da Prep #{prep_id}]")
                    note = (note + extra) if note else extra.strip()

                admin_id = self._app.manager.add_administration(
                    preparation_id=prep_id,
                    dose_ml=dose_ml,
                    administration_datetime=admin_datetime,
                    injection_site=site,
                    injection_method=method,
                    protocol_id=protocol_id,
                    notes=note,
                )
                admin_ids.append(admin_id)

            if cycle_id and admin_ids:
                self._app.manager.assign_administrations_to_cycle(admin_ids, cycle_id)

            names = " + ".join(g.get("peptide_name", "?") for g in self._group)
            total = sum(round(d["ml"], 2) for d in distribution)
            self._app.show_message(f"Registrato: {names} {total:.2f} ml", 3000)
            self.accept()

        except Exception as e:
            self._app.show_message(f"Errore registrazione: {e}", 5000)


# ═══════════════════════════════════════════════════════════════════════
# Main view
# ═══════════════════════════════════════════════════════════════════════


class TodayView(BaseView):
    """Combined week-strip + multi-day schedule list."""

    _DAYS_OPTIONS = [3, 7, 14]

    def __init__(self, app, parent=None):
        super().__init__(app, parent)
        self._selected_date = date.today()
        self._days_ahead = 7
        self._day_cards: list[tuple[date, _DayCard]] = []
        self._conc_map: dict[int, float] = {}
        self._build_ui()
        self.refresh()

    # ── UI construction ──────────────────────────────────────────────

    def _build_ui(self):
        lay = self.layout()

        # Top bar
        top = QHBoxLayout()
        title = QLabel("Programma")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        top.addWidget(title)
        top.addStretch()
        top.addWidget(QLabel("Giorni:"))
        self._days_combo = QComboBox()
        for n in self._DAYS_OPTIONS:
            self._days_combo.addItem(str(n), n)
        self._days_combo.setCurrentIndex(1)
        self._days_combo.currentIndexChanged.connect(self._on_days_changed)
        top.addWidget(self._days_combo)
        lay.addLayout(top)

        # Week strip
        strip = QFrame()
        strip_lay = QHBoxLayout(strip)
        strip_lay.setContentsMargins(0, 6, 0, 6)
        strip_lay.setSpacing(6)
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        for i in range(7):
            d = monday + timedelta(days=i)
            card = _DayCard(_DAY_SHORT[d.weekday()], d.day, is_today=(d == today))
            card.clicked.connect(partial(self._on_day_clicked, d))
            self._day_cards.append((d, card))
            strip_lay.addWidget(card, 1)
        lay.addWidget(strip)

        # Scrollable day sections
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._container = QWidget()
        self._clayout = QVBoxLayout(self._container)
        self._clayout.setAlignment(Qt.AlignTop)
        self._scroll.setWidget(self._container)
        lay.addWidget(self._scroll, 1)

    # ── Slots ────────────────────────────────────────────────────────

    def _on_day_clicked(self, d):
        self._selected_date = d
        for cd, card in self._day_cards:
            card.set_checked(cd == d)
        self.refresh()

    def _on_days_changed(self, _index):
        self._days_ahead = self._days_combo.currentData()
        self.refresh()

    # ── Data & refresh ───────────────────────────────────────────────

    def refresh(self):
        while self._clayout.count():
            w = self._clayout.takeAt(0).widget()
            if w:
                w.deleteLater()

        today = date.today()

        # Today's pending / overdue items
        try:
            today_pending = self.manager.get_scheduled_administrations()
        except Exception:
            today_pending = []

        # Build concentration map from ALL active preparations so the
        # forecast shows ml estimates even for peptides not scheduled today.
        self._conc_map = {}   # peptide_id → concentration mcg/ml
        try:
            active_preps = self.manager.get_preparations(only_active=True)
            for prep in active_preps:
                for pc in (prep.get("peptides") or prep.get("composition") or []):
                    pid = pc.get("peptide_id")
                    if pid and pid not in self._conc_map:
                        mg = pc.get("mg_amount") or pc.get("mg_per_vial") or 0
                        vials = prep.get("vials_used", 1)
                        vol = prep.get("volume_ml", 1)
                        if mg > 0 and vol > 0:
                            self._conc_map[pid] = (mg * vials / vol) * 1000
        except Exception:
            pass

        # Build prep map from today's schedule (blend grouping in forecast)
        self._prep_map = {}   # (peptide_id, cycle_id) → preparation_id
        for it in today_pending:
            pid = it.get("peptide_id")
            prep_id = it.get("preparation_id")
            cid = it.get("cycle_id")
            if prep_id is not None and pid is not None and cid is not None:
                self._prep_map[(pid, cid)] = prep_id

        # Completed administrations
        lookback = max(self._days_ahead, 7) + 1
        try:
            recent = self.manager.get_administrations(days_back=lookback)
        except Exception:
            recent = []

        done_by_date: dict[date, list] = {}
        for a in recent:
            ad = _parse_date(a.get("administration_datetime"))
            if ad:
                done_by_date.setdefault(ad, []).append(a)

        # Active cycles for forecast
        try:
            cycles = self.manager.get_cycles(active_only=True)
        except Exception:
            cycles = []

        # Day sections
        for offset in range(self._days_ahead):
            d = self._selected_date + timedelta(days=offset)
            self._clayout.addWidget(
                self._day_section(d, today, today_pending, done_by_date.get(d, []), cycles)
            )
        self._clayout.addStretch()

    # ── Grouping ─────────────────────────────────────────────────────

    @staticmethod
    def _group_by_prep(items):
        """Group items by (preparation_id, cycle_id) → merge blend peptides.

        The backend returns one item per peptide in a blend, each with its own
        ``suggested_dose_ml`` calculated from that peptide's concentration.
        Grouping lets the UI treat the blend as a single injection and use
        ``max(ml)`` across the group — correct because one syringe delivers
        all peptides simultaneously.
        """
        groups: dict[tuple, list] = {}
        for item in items:
            key = (item.get("preparation_id"), item.get("cycle_id"))
            groups.setdefault(key, []).append(item)
        return list(groups.values())

    # ── Day section ──────────────────────────────────────────────────

    def _day_section(self, d, today, today_pending, completed, cycles):
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        border = _BLUE if d == today else "#424242"
        frame.setStyleSheet(
            "QFrame { background: #252525; border-radius: 6px;"
            " border-left: 3px solid %s; margin: 2px 0; padding: 8px; }" % border
        )
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(12, 8, 12, 8)

        if d == today:
            txt = f"OGGI \u2014 {_fmt_date(d)}"
        elif d == today + timedelta(days=1):
            txt = f"DOMANI \u2014 {_fmt_date(d)}"
        else:
            txt = _fmt_date(d)
        hdr = QLabel(txt)
        hdr.setStyleSheet(
            "font-weight: bold; font-size: 14px; color: %s; padding-bottom: 4px;"
            % (_BLUE if d == today else "#e0e0e0")
        )
        lay.addWidget(hdr)

        if d == today:
            self._items_today(lay, today_pending, completed)
        elif d < today:
            self._items_past(lay, completed)
        else:
            self._items_future(lay, d, cycles)

        return frame

    # ── Today items ──────────────────────────────────────────────────

    def _items_today(self, lay, pending, completed):
        has = False
        for a in completed:
            has = True
            lay.addWidget(self._completed_label(a))
        for group in self._group_by_prep(pending):
            has = True
            lay.addWidget(self._pending_row(group))
        if not has:
            lay.addWidget(self._empty("Nessuna somministrazione programmata"))

    def _items_past(self, lay, completed):
        if not completed:
            lay.addWidget(self._empty("\u2014"))
            return
        for a in completed:
            lay.addWidget(self._completed_label(a))

    def _items_future(self, lay, d, cycles):
        items = self._forecast(d, cycles)
        if not items:
            lay.addWidget(self._empty("Nessuna somministrazione prevista"))
            return
        # Group by preparation (blend awareness) using today's prep map
        for group in self._group_forecast(items):
            lay.addWidget(self._forecast_label(group))

    def _group_forecast(self, items):
        """Group forecast items by known preparation_id (from today's schedule)."""
        groups: dict[tuple, list] = {}
        for name, dose, cname, pid, cid in items:
            prep_id = self._prep_map.get((pid, cid))
            # Known prep → group by (prep_id, cycle_id); unknown → unique key
            key = (prep_id, cid) if prep_id is not None else (f"_u{pid}", cid)
            groups.setdefault(key, []).append((name, dose, cname, pid))
        return list(groups.values())

    def _forecast_label(self, group):
        """Render a (possibly merged) forecast row."""
        if len(group) == 1:
            name, dose, cname, pid = group[0]
            dose_str = f"{dose:.0f} mcg"
        else:
            name = " + ".join(g[0] for g in group)
            dose_str = "+".join(f"{g[1]:.0f}" for g in group) + " mcg"
            pid = group[0][3]  # use first peptide for concentration lookup
            cname = group[0][2]
            dose = max(g[1] for g in group)  # for ml calc, use max dose

        conc = self._conc_map.get(pid, 0)
        if conc > 0:
            # For blends, ml is the same injection — use max single-peptide ml
            ml = max(g[1] / conc for g in group) if len(group) > 1 else dose / conc
            ml_html = (
                f'  <span style="color: {_RED}; font-weight: bold;">'
                f'~{ml:.2f} ml</span>'
            )
        else:
            ml_html = ""

        html = (
            f'<span style="color: {_SEC};">\u00b7  {name}  {dose_str}</span>'
            f'{ml_html}'
            f'  <span style="color: {_DIM};">[{cname}]</span>'
        )
        lbl = QLabel(html)
        lbl.setTextFormat(Qt.RichText)
        lbl.setStyleSheet("padding: 2px 0 2px 16px;")
        return lbl

    # ── Row widgets ──────────────────────────────────────────────────

    def _completed_label(self, admin):
        peptide = admin.get("peptide_name") or admin.get("peptide_names", "?")
        ml = float(admin.get("dose_ml", 0))
        proto = admin.get("protocol_name", "")
        text = f"\u2713  {peptide}  {ml:.2f} ml"
        if proto:
            text += f"  [{proto}]"
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {_GREEN}; padding: 2px 0 2px 16px;")
        return lbl

    def _pending_row(self, group):
        """Row for one injection — single peptide or blend group."""
        row = QWidget()
        rlay = QHBoxLayout(row)
        rlay.setContentsMargins(16, 4, 8, 4)
        rlay.setSpacing(8)

        first = group[0]
        sched = first.get("schedule_status", "")
        prep_st = first.get("status", "")
        cycle = first.get("cycle_name", "")

        # Icon & colour
        if sched == "overdue":
            days_over = first.get("days_overdue", 0)
            icon, color = "\u26a0", _RED
            suffix = f"  (in ritardo {days_over}gg)"
        else:
            icon, color = "\u25cb", _AMBER
            suffix = ""

        # Peptide names & doses
        if len(group) == 1:
            pname = first.get("peptide_name", "?")
            dose_mcg = first.get("ramped_dose_mcg") or first.get("target_dose_mcg", 0)
            dose_str = f"{dose_mcg:.0f} mcg"
        else:
            pname = " + ".join(g.get("peptide_name", "?") for g in group)
            doses = "+".join(
                f'{(g.get("ramped_dose_mcg") or g.get("target_dose_mcg", 0)):.0f}'
                for g in group
            )
            dose_str = f"{doses} mcg"

        # Volume: max ml across group (blend = same injection)
        ml = max((g.get("suggested_dose_ml") or 0) for g in group)
        ml_html = (
            f'  <span style="color: {_RED}; font-weight: bold; font-size: 14px;">'
            f'{ml:.2f} ml</span>'
        ) if ml > 0 else ""

        warn = ""
        if prep_st == "no_prep":
            warn = f'  <span style="color: {_RED};">\u2014 nessuna preparazione</span>'
        elif prep_st == "insufficient_volume":
            warn = f'  <span style="color: {_RED};">\u2014 volume insufficiente</span>'

        html = (
            f'<span style="color: {color};">{icon}  {pname}  {dose_str}</span>'
            f'{ml_html}'
            f'  <span style="color: {_SEC};">[{cycle}]</span>'
            f'<span style="color: {color};">{suffix}</span>'
            f'{warn}'
        )
        info = QLabel(html)
        info.setTextFormat(Qt.RichText)
        rlay.addWidget(info, 1)

        if prep_st == "ready":
            btn = QPushButton("Registra")
            btn.setFixedWidth(90)
            btn.setStyleSheet(_BTN_REGISTER)
            btn.clicked.connect(partial(self._register, group))
            rlay.addWidget(btn)
        elif prep_st == "insufficient_volume":
            btn = QPushButton("Registra ⚠")
            btn.setFixedWidth(100)
            btn.setStyleSheet(_BTN_REGISTER_PARTIAL)
            btn.setToolTip("Volume insufficiente — verrà registrata la dose disponibile")
            btn.clicked.connect(partial(self._register, group))
            rlay.addWidget(btn)

        return row

    # ── Quick register ───────────────────────────────────────────────

    def _register(self, group):
        """Open registration dialog for review/edit before saving."""
        dlg = _RegisterDialog(self.app, group, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh()

    # ── Forecast ─────────────────────────────────────────────────────

    def _forecast(self, target, cycles):
        """Expected items for *target* date → list of (name, mcg, cycle_name, pid, cycle_id)."""
        items = []
        for c in cycles:
            snap = c.get("protocol_snapshot")
            if not isinstance(snap, dict):
                continue
            peptides = snap.get("peptides", [])
            if not peptides:
                continue

            start = _parse_date(c.get("start_date"))
            end = _parse_date(c.get("planned_end_date"))
            if start and target < start:
                continue
            if end and target > end:
                continue

            days_on = snap.get("days_on") or c.get("days_on")
            days_off = snap.get("days_off", 0) or c.get("days_off", 0)
            if days_on and days_on > 0 and start:
                elapsed = (target - start).days
                period = days_on + days_off
                if period > 0 and (elapsed % period) >= days_on:
                    continue

            week = max(1, ((target - start).days // 7 + 1)) if start else 1
            ramp = c.get("ramp_schedule") or []
            cname = c.get("name", "")

            for p in peptides:
                base = p.get("target_dose_mcg") or p.get("dose_mcg", 0)
                dose = base
                for entry in ramp:
                    if entry.get("week") == week:
                        for rd in entry.get("doses", []):
                            if rd.get("peptide_id") == p.get("peptide_id"):
                                dose = rd.get("dose_mcg", base)
                                break
                        else:
                            pct = entry.get("percentage")
                            if pct is not None:
                                dose = base * pct / 100
                        break
                pname = p.get("name") or p.get("peptide_name", "?")
                items.append((pname, dose, cname, p.get("peptide_id"), c.get("id")))

        return sorted(items, key=lambda x: x[0])

    # ── Helpers ──────────────────────────────────────────────────────

    def _empty(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {_DIM}; padding: 4px 0 4px 16px; font-style: italic;")
        return lbl
