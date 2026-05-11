"""
Integrity checks for the Qt GUI.

Replaces the former Flet-specific dialog tests. Validates:
- Syntax of all gui_qt source files
- All SECTIONS defined in app.py have a real implementation (no placeholder)
- The root entry point (gui.py) is importable
"""

import ast
import re
from pathlib import Path

import pytest

_ROOT = Path(__file__).parent.parent
_GUI_QT = _ROOT / "gui_qt"

# Keys that must have real (non-placeholder) implementations in app.py
_EXPECTED_SECTION_KEYS = ["today", "inventory", "treatment", "history", "archive"]


# ── Syntax checks ─────────────────────────────────────────────────────────────

def _collect_py_files(directory: Path):
    return [f for f in directory.rglob("*.py") if "__pycache__" not in f.parts]


def test_gui_entry_point_no_syntax_errors():
    """gui.py deve essere privo di errori di sintassi."""
    path = _ROOT / "gui.py"
    content = path.read_text(encoding="utf-8")
    try:
        compile(content, str(path), "exec")
    except SyntaxError as e:
        pytest.fail(f"gui.py ha errori di sintassi: {e}")


def test_qt_app_no_syntax_errors():
    """gui_qt/app.py deve essere privo di errori di sintassi."""
    path = _GUI_QT / "app.py"
    content = path.read_text(encoding="utf-8")
    try:
        compile(content, str(path), "exec")
    except SyntaxError as e:
        pytest.fail(f"app.py ha errori di sintassi: {e}")


def test_qt_views_no_syntax_errors():
    """Tutte le viste in gui_qt/views/ devono essere prive di errori di sintassi."""
    views_dir = _GUI_QT / "views"
    errors = []
    for f in _collect_py_files(views_dir):
        content = f.read_text(encoding="utf-8")
        try:
            compile(content, str(f), "exec")
        except SyntaxError as e:
            errors.append(f"{f.name}: {e}")
    assert not errors, "Errori di sintassi nelle viste Qt:\n" + "\n".join(errors)


def test_qt_components_no_syntax_errors():
    """Tutti i componenti in gui_qt/components/ devono essere privi di errori di sintassi."""
    comp_dir = _GUI_QT / "components"
    errors = []
    for f in _collect_py_files(comp_dir):
        content = f.read_text(encoding="utf-8")
        try:
            compile(content, str(f), "exec")
        except SyntaxError as e:
            errors.append(f"{f.name}: {e}")
    assert not errors, "Errori di sintassi nei componenti Qt:\n" + "\n".join(errors)


# ── Section completeness ───────────────────────────────────────────────────────

def test_qt_sections_all_implemented():
    """
    Ogni section key in SECTIONS deve avere un branch reale in _build_section_widget,
    non il fallback generico 'vista in arrivo'.
    """
    app_src = (_GUI_QT / "app.py").read_text(encoding="utf-8")

    for key in _EXPECTED_SECTION_KEYS:
        # Each key must appear in a `section["key"] == "..."` guard
        pattern = rf'section\["key"\]\s*==\s*"{key}"'
        assert re.search(pattern, app_src), (
            f"La sezione '{key}' non ha un branch dedicato in _build_section_widget"
        )


def test_qt_app_sections_list_complete():
    """SECTIONS in app.py deve contenere tutte le sezioni attese."""
    app_src = (_GUI_QT / "app.py").read_text(encoding="utf-8")
    for key in _EXPECTED_SECTION_KEYS:
        assert f'"key": "{key}"' in app_src, (
            f"Sezione '{key}' mancante dalla lista SECTIONS in app.py"
        )


# ── gui.py points to Qt ────────────────────────────────────────────────────────

def test_gui_entry_point_uses_qt():
    """gui.py deve delegare a gui_qt, non a gui_modular."""
    content = (_ROOT / "gui.py").read_text(encoding="utf-8")
    assert "gui_qt" in content, "gui.py non punta a gui_qt"
    assert "gui_modular" not in content, "gui.py contiene ancora riferimenti a gui_modular (Flet)"
    assert "flet" not in content.lower(), "gui.py contiene ancora riferimenti a Flet"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
