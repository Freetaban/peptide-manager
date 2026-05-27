"""
Export utilities: HTML calendar and ICS generation from active cycles.

No external dependencies — stdlib only.
"""

from __future__ import annotations

import json
import uuid
from datetime import date, timedelta
from typing import Dict, List, Optional

_DAYS_IT = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]
_MONTHS_IT = [
    "", "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
    "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre",
]


def build_schedule(manager, start_date: date, end_date: date) -> Dict[date, List[dict]]:
    """
    Compute dose schedule for [start_date, end_date] from active cycles.

    Returns {date: [{'peptide_name', 'dose_mcg', 'cycle_name', 'frequency'}]}.
    Days with no doses are absent.
    """
    from .models.cycle import Cycle

    try:
        active_cycles = [c for c in manager.get_cycles(active_only=False) if c.get("status") == "active"]
    except Exception:
        return {}

    schedule: Dict[date, List[dict]] = {}

    for cycle in active_cycles:
        cycle_id = cycle.get("id")
        cycle_name = cycle.get("name") or f"Ciclo #{cycle_id}"
        proto = cycle.get("protocol_snapshot")

        if not proto:
            continue
        if isinstance(proto, str):
            try:
                proto = json.loads(proto)
                if isinstance(proto, str):
                    proto = json.loads(proto)
            except Exception:
                continue
        if not isinstance(proto, dict):
            continue

        days_on = cycle.get("days_on") if cycle.get("days_on") is not None else proto.get("days_on")
        days_off = (
            cycle.get("days_off") if cycle.get("days_off") is not None else proto.get("days_off", 0)
        )
        frequency_per_day = int(proto.get("frequency_per_day") or 1)

        if days_on is not None and int(days_on) > 0:
            cycle_length = int(days_on) + int(days_off or 0)
            effective_days_on = int(days_on)
        else:
            cycle_length = 1
            effective_days_on = 1

        raw_start = cycle.get("start_date")
        if not raw_start:
            continue
        cycle_start = date.fromisoformat(raw_start) if isinstance(raw_start, str) else raw_start

        raw_resumed = cycle.get("resumed_at")
        if raw_resumed:
            anchor = date.fromisoformat(raw_resumed[:10]) if isinstance(raw_resumed, str) else raw_resumed
        else:
            anchor = cycle_start

        ramp_data = cycle.get("ramp_schedule")  # already parsed list from get_all()
        cycle_obj: Optional[Cycle] = None
        if ramp_data:
            cycle_obj = Cycle(start_date=cycle_start, ramp_schedule=ramp_data)

        custom_doses = proto.get("custom_doses", {})

        for pep in proto.get("peptides", []):
            peptide_id = pep.get("peptide_id")
            peptide_name = pep.get("name") or pep.get("peptide_name") or f"Peptide #{peptide_id}"
            base_dose = float(
                custom_doses.get(str(peptide_id))
                or pep.get("target_dose_mcg")
                or pep.get("dose_mcg")
                or 0
            )

            current = start_date
            while current <= end_date:
                if current < anchor:
                    current += timedelta(days=1)
                    continue

                if (current - anchor).days % cycle_length < effective_days_on:
                    if cycle_obj is not None:
                        exact = cycle_obj.get_ramp_dose(peptide_id, current)
                        dose_mcg = float(exact) if exact is not None else base_dose * cycle_obj.get_ramp_percentage(current)
                    else:
                        dose_mcg = base_dose

                    if dose_mcg > 0:
                        schedule.setdefault(current, []).append({
                            "peptide_name": peptide_name,
                            "dose_mcg": round(dose_mcg),
                            "cycle_name": cycle_name,
                            "frequency": frequency_per_day,
                        })

                current += timedelta(days=1)

    return schedule


def build_html(schedule: Dict[date, List[dict]], start_date: date, end_date: date) -> str:
    """Render schedule as a self-contained styled HTML document."""
    rows = []
    current = start_date
    while current <= end_date:
        doses = schedule.get(current, [])
        day_name = _DAYS_IT[current.weekday()]
        date_str = f"{current.day} {_MONTHS_IT[current.month]} {current.year}"
        is_weekend = current.weekday() >= 5

        if doses:
            parts = []
            for d in doses:
                freq = f" × {d['frequency']}" if d["frequency"] > 1 else ""
                parts.append(f'{d["peptide_name"]}: <strong>{d["dose_mcg"]} mcg</strong>{freq}')
            content = " &nbsp;&bull;&nbsp; ".join(parts)
            row_class = "wk dose-row" if is_weekend else "dose-row"
        else:
            content = '<span class="rest">riposo</span>'
            row_class = "wk rest-row" if is_weekend else "rest-row"

        rows.append(
            f'<tr class="{row_class}">'
            f'<td class="dn">{day_name}</td>'
            f'<td class="dc">{date_str}</td>'
            f'<td class="sc">{content}</td>'
            f"</tr>"
        )
        current += timedelta(days=1)

    today = date.today()
    return f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<title>Piano Peptidi {start_date} – {end_date}</title>
<style>
body{{font-family:Arial,sans-serif;font-size:13px;background:#f5f5f5;margin:0;padding:20px}}
h1{{font-size:17px;color:#1a237e;margin:0 0 3px}}
.meta{{color:#888;font-size:11px;margin-bottom:16px}}
.hint{{font-size:11px;color:#aaa;margin-bottom:12px}}
table{{border-collapse:collapse;width:100%;background:#fff;border-radius:6px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.15)}}
th{{background:#1a237e;color:#fff;padding:7px 12px;text-align:left;font-size:11px;font-weight:600}}
td{{padding:5px 12px;border-bottom:1px solid #eee;vertical-align:middle}}
.dn{{width:36px;font-weight:bold;color:#666;font-size:11px}}
.dc{{width:160px;color:#444}}
.sc{{color:#222}}
.dose-row{{background:#fff}}
.rest-row{{background:#fafafa}}
.rest-row .sc{{color:#bbb}}
.wk{{background:#f3f3ff}}
.wk .dn{{color:#7986cb}}
.rest{{color:#ccc}}
@media print{{body{{padding:0;background:#fff}}.hint{{display:none}}table{{box-shadow:none}}}}
</style>
</head>
<body>
<h1>Piano Peptidi</h1>
<p class="meta">Dal {start_date} al {end_date} &nbsp;·&nbsp; Generato il {today}</p>
<p class="hint">Per salvare come PDF: <em>File &rarr; Stampa &rarr; Salva come PDF</em></p>
<table>
<thead><tr><th>Gg</th><th>Data</th><th>Somministrazione</th></tr></thead>
<tbody>{"".join(rows)}</tbody>
</table>
</body>
</html>"""


def build_ics(schedule: Dict[date, List[dict]], start_date: date, end_date: date) -> str:
    """Render schedule as an iCalendar (.ics) string (RFC 5545)."""
    events = []
    current = start_date
    while current <= end_date:
        doses = schedule.get(current)
        if not doses:
            current += timedelta(days=1)
            continue

        summary_parts = [f"{d['peptide_name']} {d['dose_mcg']}mcg" for d in doses]
        desc_parts = []
        for d in doses:
            freq = f" × {d['frequency']}/g" if d["frequency"] > 1 else ""
            desc_parts.append(f"{d['peptide_name']}: {d['dose_mcg']} mcg{freq} ({d['cycle_name']})")

        summary = "Peptidi: " + ", ".join(summary_parts)
        description = "\\n".join(desc_parts)
        dtstart = current.strftime("%Y%m%d")
        dtend = (current + timedelta(days=1)).strftime("%Y%m%d")
        uid = f"peptide-{current.isoformat()}-{uuid.uuid4().hex[:8]}@peptidemanager"

        events.append(
            f"BEGIN:VEVENT\r\n"
            f"DTSTART;VALUE=DATE:{dtstart}\r\n"
            f"DTEND;VALUE=DATE:{dtend}\r\n"
            f"SUMMARY:{summary}\r\n"
            f"DESCRIPTION:{description}\r\n"
            f"UID:{uid}\r\n"
            f"END:VEVENT"
        )
        current += timedelta(days=1)

    body = "\r\n".join(events)
    return (
        "BEGIN:VCALENDAR\r\n"
        "VERSION:2.0\r\n"
        "PRODID:-//PeptideManager//IT\r\n"
        "CALSCALE:GREGORIAN\r\n"
        "METHOD:PUBLISH\r\n"
        + (body + "\r\n" if body else "")
        + "END:VCALENDAR"
    )
