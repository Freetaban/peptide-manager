"""Tests for _expand_weekly_schedule — the on-the-fly cycle dose editor logic.

WHY this matters: a cycle started at a flat dose has NO ramp_schedule, so the
edit dialog had no rows to show. This helper expands a full week-by-week grid
pre-filled with the effective dose so the user can raise the dose going forward.
The dose precedence here must mirror Cycle.get_ramp_dose, otherwise the editor
would display doses that disagree with what the cycle actually administers.
"""

from gui_qt.views.treatment_cycles import (
    _expand_weekly_schedule, _snap_pep_tuple, _snap_weekday_based)


def _dose(schedule, week, pid):
    """Pull the dose for (week, peptide) out of an expanded schedule."""
    entry = next(e for e in schedule if e["week"] == week)
    return next(d["dose_mcg"] for d in entry["doses"] if d["peptide_id"] == pid)


def test_flat_dose_cycle_fills_every_week_with_base_dose():
    """No ramp_schedule → every week gets the protocol base dose (the bug case)."""
    schedule = _expand_weekly_schedule(weeks=4, peptides=[(1, 500)], existing=[])

    assert len(schedule) == 4
    assert [e["week"] for e in schedule] == [1, 2, 3, 4]
    assert all(_dose(schedule, w, 1) == 500 for w in range(1, 5))


def test_existing_ramp_weeks_are_preserved():
    """Explicit doses in the existing ramp win over the base dose."""
    existing = [
        {"week": 1, "doses": [{"peptide_id": 1, "dose_mcg": 250}]},
        {"week": 2, "doses": [{"peptide_id": 1, "dose_mcg": 375}]},
    ]
    schedule = _expand_weekly_schedule(weeks=4, peptides=[(1, 500)], existing=existing)

    assert _dose(schedule, 1, 1) == 250
    assert _dose(schedule, 2, 1) == 375
    # Weeks beyond the last defined ramp week carry the last week's dose forward,
    # mirroring Cycle.get_ramp_dose (NOT the base dose).
    assert _dose(schedule, 3, 1) == 375
    assert _dose(schedule, 4, 1) == 375


def test_multi_peptide_produces_one_row_per_peptide_per_week():
    schedule = _expand_weekly_schedule(
        weeks=2, peptides=[(1, 500), (2, 1000)], existing=[]
    )
    assert len(schedule) == 2
    assert all(len(e["doses"]) == 2 for e in schedule)
    assert _dose(schedule, 1, 2) == 1000


def test_zero_weeks_yields_empty_schedule():
    assert _expand_weekly_schedule(weeks=0, peptides=[(1, 500)], existing=[]) == []


# --- _snap_pep_tuple: snapshot format normalization -------------------------
# WHY: planner-generated cycles store peptide name/dose under DIFFERENT keys
# than protocol-generated ones. Reading only the protocol keys showed "?" as
# the peptide name and silently defaulted the dose, even though the cycle
# administers a real, named peptide.


def test_snap_pep_tuple_protocol_format():
    pp = {"peptide_id": 6, "name": "Retatrutide", "target_dose_mcg": 500}
    assert _snap_pep_tuple(pp) == (6, "Retatrutide", 500)


def test_snap_pep_tuple_planner_format():
    pp = {"peptide_id": 6, "peptide_name": "Retatrutide", "dose_mcg": 500,
          "daily_frequency": 1, "weekdays": [0, 2, 4]}
    assert _snap_pep_tuple(pp) == (6, "Retatrutide", 500)


def test_snap_pep_tuple_missing_fields_fall_back():
    pid, name, dose = _snap_pep_tuple({"peptide_id": 6})
    assert (pid, name, dose) == (6, "?", 250)


# --- _snap_weekday_based: choose day-selector vs ON/OFF model ----------------
# WHY: the edit dialog shows per-peptide day selectors (Mon/Wed/Fri…) only for
# weekday-based (planner) cycles. Protocol-based cycles have no weekdays and must
# keep the days_on/days_off block fields instead. Per-peptide selectors also
# handle the case where peptides administer on DIFFERENT days.


def test_weekday_based_true_when_any_peptide_has_weekdays():
    assert _snap_weekday_based([{"peptide_id": 6, "weekdays": [0, 2, 4]}]) is True


def test_weekday_based_false_for_protocol_cycle():
    # No weekdays key → block ON/OFF model, not weekday-based.
    assert _snap_weekday_based([{"peptide_id": 6, "target_dose_mcg": 500}]) is False


def test_weekday_based_true_when_peptides_differ():
    # Mixed days across peptides is still weekday-based (per-peptide selectors).
    peps = [{"peptide_id": 1, "weekdays": [0, 1, 2, 3, 4, 5, 6]},
            {"peptide_id": 2, "weekdays": [0, 2, 4]}]
    assert _snap_weekday_based(peps) is True


def test_weekday_based_false_for_empty():
    assert _snap_weekday_based([]) is False
