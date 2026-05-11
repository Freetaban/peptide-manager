"""
Smoke test Qt GUI — validazione non-interattiva.
Uso: python scripts/smoke_test_gui.py

Verifica che tutti i moduli Qt importino senza errori e che il backend
si inizializzi correttamente. Non richiede display o interazione grafica.
"""

import sys
import importlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

_passed = []
_failed = []


def check(name, fn):
    try:
        fn()
        _passed.append(name)
        print(f"  OK  {name}")
    except Exception as e:
        _failed.append((name, str(e)))
        print(f"  FAIL  {name}: {e}")


# ── Import checks ─────────────────────────────────────────────────────────────

def _import(module):
    importlib.import_module(module)


check("import gui_qt.app",                  lambda: _import("gui_qt.app"))
check("import gui_qt.views.today",          lambda: _import("gui_qt.views.today"))
check("import gui_qt.views.inventory",      lambda: _import("gui_qt.views.inventory"))
check("import gui_qt.views.treatment",      lambda: _import("gui_qt.views.treatment"))
check("import gui_qt.views.history",        lambda: _import("gui_qt.views.history"))
check("import gui_qt.views.archive",        lambda: _import("gui_qt.views.archive"))
check("import gui_qt.views.purchase_history", lambda: _import("gui_qt.views.purchase_history"))
check("import gui_qt.components.data_table", lambda: _import("gui_qt.components.data_table"))
check("import gui_qt.components.dialogs",   lambda: _import("gui_qt.components.dialogs"))
check("import gui_qt.components.forms",     lambda: _import("gui_qt.components.forms"))

# ── Backend init ──────────────────────────────────────────────────────────────

def _backend_init():
    import tempfile, os
    from peptide_manager import PeptideManager
    from peptide_manager.database import init_database

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        conn = init_database(db_path)
        conn.close()
        mgr = PeptideManager(db_path)
        mgr.get_peptides()
        mgr.get_suppliers()
        mgr.get_batches()
        mgr.get_preparations()
        mgr.get_protocols()
        mgr.get_cycles()
        mgr.close()
    finally:
        try:
            os.unlink(db_path)
        except OSError:
            pass


check("backend init + basic reads", _backend_init)

# ── Summary ───────────────────────────────────────────────────────────────────

print()
print("=" * 50)
print(f"Passed: {len(_passed)}  Failed: {len(_failed)}")
if _failed:
    print("\nFailed:")
    for name, err in _failed:
        print(f"  • {name}: {err}")
print("=" * 50)

sys.exit(0 if not _failed else 1)
