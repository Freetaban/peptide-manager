"""
Smoke test GUI - Validazione rapida funzionalità critiche.
Uso: python scripts/smoke_test_gui.py

Esegui prima di ogni commit che modifica gui.py.
"""

import sys
import time
from pathlib import Path

# Aggiungi root al path
sys.path.insert(0, str(Path(__file__).parent.parent))

import flet as ft
from gui import PeptideGUI


class SmokeTestRunner:
    def __init__(self):
        self.tests_passed = []
        self.tests_failed = []
    
    def test_app_initialization(self, page: ft.Page):
        """Test 1: App si inizializza senza crash."""
        try:
            app = PeptideGUI()
            app.page = page
            print("✅ Test 1: App initialization ok")
            self.tests_passed.append("App initialization")
            return app
        except Exception as e:
            print(f"❌ Test 1 FAILED: {e}")
            self.tests_failed.append(("App initialization", str(e)))
            return None
    
    def test_preparations_view(self, app):
        """Test 2: Preparations view si carica."""
        try:
            # Simula navigazione a Preparations
            app.current_view = "preparations"
            content = app.build_preparations_view()
            assert content is not None, "Preparations view è None"
            print("✅ Test 2: Preparations view ok")
            self.tests_passed.append("Preparations view")
        except Exception as e:
            print(f"❌ Test 2 FAILED: {e}")
            self.tests_failed.append(("Preparations view", str(e)))
    
    def test_dialog_methods_exist(self, app):
        """Test 3: Metodi dialog esistono e sono callable."""
        dialog_methods = [
            'show_add_preparation_dialog',
            'show_administer_dialog',
            'show_preparation_details',
        ]
        
        for method_name in dialog_methods:
            try:
                method = getattr(app, method_name, None)
                assert method is not None, f"Metodo {method_name} non esiste"
                assert callable(method), f"Metodo {method_name} non è callable"
                print(f"✅ Test 3.{dialog_methods.index(method_name)+1}: {method_name} exists")
                self.tests_passed.append(f"{method_name} exists")
            except Exception as e:
                print(f"❌ Test 3 FAILED ({method_name}): {e}")
                self.tests_failed.append((f"{method_name} exists", str(e)))
    
    def print_summary(self):
        """Stampa riepilogo test."""
        print("\n" + "="*60)
        print("SMOKE TEST SUMMARY")
        print("="*60)
        print(f"✅ Passed: {len(self.tests_passed)}")
        print(f"❌ Failed: {len(self.tests_failed)}")
        
        if self.tests_failed:
            print("\nFailed tests:")
            for test_name, error in self.tests_failed:
                print(f"  • {test_name}: {error}")
        
        print("="*60)
        
        return len(self.tests_failed) == 0


def main(page: ft.Page):
    """Esegue smoke test suite."""
    page.title = "Smoke Test - Peptide Manager"
    page.window.width = 800
    page.window.height = 600
    
    print("\n" + "="*60)
    print("SMOKE TEST GUI - PEPTIDE MANAGER")
    print("="*60 + "\n")
    
    runner = SmokeTestRunner()
    
    # Test 1: Inizializzazione
    app = runner.test_app_initialization(page)
    
    if app:
        # Test 2: Preparations view
        runner.test_preparations_view(app)
        
        # Test 3: Dialog methods
        runner.test_dialog_methods_exist(app)
    
    # Summary
    success = runner.print_summary()
    
    # Mostra risultato nella GUI
    result_text = "✅ TUTTI I TEST SUPERATI" if success else "❌ ALCUNI TEST FALLITI"
    result_color = ft.Colors.GREEN if success else ft.Colors.RED
    
    page.add(
        ft.Container(
            content=ft.Column([
                ft.Text(
                    result_text,
                    size=24,
                    weight=ft.FontWeight.BOLD,
                    color=result_color,
                ),
                ft.Text(
                    f"Passed: {len(runner.tests_passed)} | Failed: {len(runner.tests_failed)}",
                    size=16,
                ),
                ft.ElevatedButton(
                    "Chiudi",
                    on_click=lambda e: page.window.close()
                ),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=40,
        )
    )
    
    # Auto-close dopo 5 secondi se successo
    if success:
        time.sleep(3)
        page.window.close()
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    try:
        ft.app(target=main)
    except Exception as e:
        print(f"\n❌ SMOKE TEST CRASHED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
