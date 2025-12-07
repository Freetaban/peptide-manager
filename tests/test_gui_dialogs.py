"""
Test per verificare l'integrità dei dialog GUI.
Previene regressioni come quella del 30 Nov 2025 (commit 9817859).

NOTA: Dopo refactoring post-merge Janoshik v2.0.0, le funzioni specifiche
show_add_preparation_dialog e show_administer_dialog non esistono più.
I test ora verificano le 4 funzioni dialog esistenti:
- show_add_protocol_dialog
- show_edit_protocol_dialog
- show_edit_administration_dialog
- show_reconciliation_dialog
"""

import pytest
import re
from pathlib import Path


def test_show_add_protocol_dialog_is_complete():
    """Verifica che show_add_protocol_dialog sia completo."""
    gui_path = Path(__file__).parent.parent / "gui.py"
    content = gui_path.read_text(encoding='utf-8')
    
    pattern = r'def show_add_protocol_dialog\(self.*?\):(.*?)(?=\n    def |\nclass |\Z)'
    match = re.search(pattern, content, re.DOTALL)
    
    assert match, "Funzione show_add_protocol_dialog non trovata!"
    
    function_body = match.group(1)
    
    # Verifica che contenga AlertDialog creation
    assert 'ft.AlertDialog' in function_body, \
        "show_add_protocol_dialog deve creare un ft.AlertDialog!"
    
    # Verifica che contenga overlay.append
    assert 'self.page.overlay.append' in function_body, \
        "Dialog deve essere aggiunto a page.overlay!"
    
    # Verifica che contenga dialog.open = True
    assert '.open = True' in function_body, \
        "Dialog deve essere aperto con .open = True!"
    
    # Verifica che contenga page.update()
    assert 'self.page.update()' in function_body, \
        "Dialog deve chiamare self.page.update()!"


def test_show_edit_administration_dialog_is_complete():
    """Verifica che show_edit_administration_dialog sia completo."""
    gui_path = Path(__file__).parent.parent / "gui.py"
    content = gui_path.read_text(encoding='utf-8')
    
    pattern = r'def show_edit_administration_dialog\(self.*?\):(.*?)(?=\n    def |\nclass |\Z)'
    match = re.search(pattern, content, re.DOTALL)
    
    assert match, "Funzione show_edit_administration_dialog non trovata!"
    
    function_body = match.group(1)
    
    assert 'ft.AlertDialog' in function_body, \
        "show_edit_administration_dialog deve creare un ft.AlertDialog!"
    assert 'self.page.overlay.append' in function_body, \
        "Dialog deve essere aggiunto a page.overlay!"
    assert '.open = True' in function_body, \
        "Dialog deve essere aperto con .open = True!"
    assert 'self.page.update()' in function_body, \
        "Dialog deve chiamare self.page.update()!"


def test_wastage_dialog_has_alertdialog():
    """Verifica che show_wastage_dialog crei un AlertDialog."""
    gui_path = Path(__file__).parent.parent / "gui.py"
    content = gui_path.read_text(encoding='utf-8')
    
    pattern = r'def show_wastage_dialog\(self.*?\):(.*?)(?=\n    def |\nclass |\Z)'
    match = re.search(pattern, content, re.DOTALL)
    
    if not match:
        pytest.skip("Funzione show_wastage_dialog non ancora implementata")
    
    function_body = match.group(1)
    
    assert 'ft.AlertDialog' in function_body, \
        "show_wastage_dialog deve creare un ft.AlertDialog!"


def test_all_dialog_functions_are_complete():
    """Verifica che tutte le funzioni show_*_dialog siano complete."""
    gui_path = Path(__file__).parent.parent / "gui.py"
    content = gui_path.read_text(encoding='utf-8')
    
    # Trova tutte le funzioni show_*_dialog
    dialog_functions = re.findall(r'def (show_\w+_dialog)\(self', content)
    
    assert len(dialog_functions) > 0, "Nessuna funzione dialog trovata!"
    
    incomplete = []
    for func_name in dialog_functions:
        # Estrai il corpo della funzione
        pattern = rf'def {func_name}\(self.*?\):(.*?)(?=\n    def |\nclass |\Z)'
        match = re.search(pattern, content, re.DOTALL)
        
        if match:
            body = match.group(1)
            # Verifica che non finisca prematuramente (senza chiusura dialog)
            has_dialog = 'AlertDialog' in body or 'dialog' in body.lower()
            has_update = 'self.page.update()' in body or 'page.update()' in body
            
            if has_dialog and not has_update:
                incomplete.append(func_name)
    
    assert len(incomplete) == 0, \
        f"Dialog incompleti (manca page.update): {', '.join(incomplete)}"


def test_gui_no_syntax_errors():
    """Verifica che gui.py non abbia errori di sintassi."""
    gui_path = Path(__file__).parent.parent / "gui.py"
    content = gui_path.read_text(encoding='utf-8')
    
    try:
        compile(content, str(gui_path), 'exec')
    except SyntaxError as e:
        pytest.fail(f"gui.py ha errori di sintassi: {e}")


if __name__ == "__main__":
    # Per eseguire direttamente: python tests/test_gui_dialogs.py
    pytest.main([__file__, "-v"])
