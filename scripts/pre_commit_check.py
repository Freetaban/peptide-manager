#!/usr/bin/env python3
"""
Pre-commit validation script.
Previene commit con dialog incompleti o errori critici.

Installazione:
    python scripts/install_hooks.py
"""

import sys
import subprocess
from pathlib import Path


def check_gui_dialogs():
    """Verifica integrità dialog in gui.py."""
    print("🔍 Verifico integrità dialog GUI...")
    
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_gui_dialogs.py", "-v"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print("❌ ERRORE: Test dialog GUI falliti!")
        print(result.stdout)
        print(result.stderr)
        return False
    
    print("✅ Dialog GUI ok")
    return True


def check_syntax_errors():
    """Verifica errori di sintassi nei file Python modificati."""
    print("🔍 Verifico sintassi Python...")
    
    # Ottieni file modificati staged per commit
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True,
        text=True
    )
    
    python_files = [
        f for f in result.stdout.strip().split('\n') 
        if f.endswith('.py') and Path(f).exists()
    ]
    
    if not python_files:
        print("✅ Nessun file Python modificato")
        return True
    
    errors = []
    for filepath in python_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                compile(f.read(), filepath, 'exec')
        except SyntaxError as e:
            errors.append(f"{filepath}: {e}")
    
    if errors:
        print("❌ ERRORI DI SINTASSI:")
        for err in errors:
            print(f"  {err}")
        return False
    
    print(f"✅ Sintassi ok ({len(python_files)} file verificati)")
    return True


def check_large_refactoring():
    """Avvisa se il commit modifica troppo codice."""
    print("🔍 Verifico dimensione modifiche...")
    
    result = subprocess.run(
        ["git", "diff", "--cached", "--shortstat"],
        capture_output=True,
        text=True
    )
    
    output = result.stdout.strip()
    if not output:
        return True
    
    # Estrai numero di righe modificate (es: "3 files changed, 176 insertions(+), 89 deletions(-)")
    import re
    match = re.search(r'(\d+) insertion.*?(\d+) deletion', output)
    if match:
        insertions = int(match.group(1))
        deletions = int(match.group(2))
        total_changes = insertions + deletions
        
        if total_changes > 200:
            print(f"⚠️  ATTENZIONE: Commit con {total_changes} righe modificate!")
            print("   Consiglio: spezza in commit più piccoli (1 problema = 1 commit)")
            print("   Per forzare: git commit --no-verify")
            # Non bloccare, solo avvisare
    
    print("✅ Dimensione commit ok")
    return True


def main():
    """Esegue tutti i check pre-commit."""
    print("\n" + "="*60)
    print("PRE-COMMIT VALIDATION")
    print("="*60 + "\n")
    
    checks = [
        ("Sintassi Python", check_syntax_errors),
        ("Dialog GUI", check_gui_dialogs),
        ("Dimensione commit", check_large_refactoring),
    ]
    
    failed = []
    for name, check_func in checks:
        if not check_func():
            failed.append(name)
        print()
    
    if failed:
        print("="*60)
        print(f"❌ COMMIT BLOCCATO - Check falliti: {', '.join(failed)}")
        print("="*60)
        return 1
    
    print("="*60)
    print("✅ TUTTI I CHECK SUPERATI - Commit autorizzato")
    print("="*60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
