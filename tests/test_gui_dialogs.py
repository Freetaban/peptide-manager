"""
Test per verificare l'integrità della GUI modulare.

L'architettura è ora completamente modulare:
- gui.py: thin wrapper (entry point)
- gui_modular/app.py: shell applicazione (PeptideApp)
- gui_modular/views/*.py: viste individuali
"""

import pytest
from pathlib import Path


def test_gui_no_syntax_errors():
    """Verifica che gui.py non abbia errori di sintassi."""
    gui_path = Path(__file__).parent.parent / "gui.py"
    content = gui_path.read_text(encoding='utf-8')

    try:
        compile(content, str(gui_path), 'exec')
    except SyntaxError as e:
        pytest.fail(f"gui.py ha errori di sintassi: {e}")


def test_app_no_syntax_errors():
    """Verifica che gui_modular/app.py non abbia errori di sintassi."""
    app_path = Path(__file__).parent.parent / "gui_modular" / "app.py"
    content = app_path.read_text(encoding='utf-8')

    try:
        compile(content, str(app_path), 'exec')
    except SyntaxError as e:
        pytest.fail(f"app.py ha errori di sintassi: {e}")


def test_all_views_no_syntax_errors():
    """Verifica che tutte le viste modulari non abbiano errori di sintassi."""
    views_dir = Path(__file__).parent.parent / "gui_modular" / "views"

    view_files = list(views_dir.glob("*.py"))
    assert len(view_files) > 0, "Nessun file vista trovato!"

    errors = []
    for view_file in view_files:
        content = view_file.read_text(encoding='utf-8')
        try:
            compile(content, str(view_file), 'exec')
        except SyntaxError as e:
            errors.append(f"{view_file.name}: {e}")

    assert len(errors) == 0, f"Errori di sintassi nelle viste: {'; '.join(errors)}"


def test_all_views_registered():
    """Verifica che app.py registri tutte le viste disponibili."""
    app_path = Path(__file__).parent.parent / "gui_modular" / "app.py"
    content = app_path.read_text(encoding='utf-8')

    expected_views = [
        'dashboard', 'batches', 'peptides', 'suppliers',
        'preparations', 'protocols', 'cycles', 'administrations',
        'calculator', 'treatment_planner', 'janoshik'
    ]

    for view_name in expected_views:
        assert f"'{view_name}'" in content, \
            f"Vista '{view_name}' non registrata in app.py!"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
