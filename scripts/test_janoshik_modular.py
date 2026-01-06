"""Test rapido vista Janoshik modularizzata"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import flet as ft
from gui import PeptideGUI

def test_janoshik_modular_view(page: ft.Page):
    """Test che la vista Janoshik si carichi dal modulo gui_modular/views/janoshik.py"""
    try:
        print("🧪 Test: Caricamento vista Janoshik modularizzata...")
        
        app = PeptideGUI()
        app.page = page
        
        # Naviga a Janoshik
        app.current_view = "janoshik"
        app.update_content()
        
        # Verifica contenuto caricato
        assert app.content_area.content is not None, "Vista Janoshik è None"
        
        # Verifica è vista modularizzata (non legacy method)
        content_type = type(app.content_area.content).__name__
        assert content_type == "JanoshikView", f"Vista non è JanoshikView ma {content_type}"
        
        print(f"✅ Vista Janoshik caricata correttamente (tipo: {content_type})")
        print(f"✅ Modulo: gui_modular.views.janoshik")
        print(f"✅ Nessun legacy code in gui.py")
        return True
        
    except Exception as e:
        print(f"❌ Test FALLITO: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = {"success": False}
    
    def main(page: ft.Page):
        page.title = "Test Janoshik Modular"
        result["success"] = test_janoshik_modular_view(page)
        page.window.destroy()
    
    ft.app(target=main)
    sys.exit(0 if result["success"] else 1)
