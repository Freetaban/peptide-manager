"""
Installa Git hooks per prevenire regressioni.
Uso: python scripts/install_hooks.py
"""

import os
import shutil
from pathlib import Path


def install_pre_commit_hook():
    """Installa pre-commit hook nella repository."""
    repo_root = Path(__file__).parent.parent
    hooks_dir = repo_root / ".git" / "hooks"
    
    if not hooks_dir.exists():
        print("❌ Directory .git/hooks non trovata. Sei nella root del repository?")
        return False
    
    # Crea pre-commit hook
    hook_path = hooks_dir / "pre-commit"
    
    # Ottieni path Python corrente
    python_exe = sys.executable
    
    # Script hook (Windows-compatible con path assoluto)
    hook_content = f"""#!{python_exe}
import sys
import subprocess

# Esegui validazione pre-commit
result = subprocess.run(
    [r"{python_exe}", r"{repo_root}\\scripts\\pre_commit_check.py"],
    cwd=r"{repo_root}"
)

sys.exit(result.returncode)
"""
    
    # Windows: crea anche .bat wrapper
    if os.name == 'nt':
        # Usa sys.executable per ottenere il path Python corrente
        python_exe = sys.executable
        bat_path = hooks_dir / "pre-commit.bat"
        bat_content = f"""@echo off
"{python_exe}" "{repo_root}\\scripts\\pre_commit_check.py"
exit /b %errorlevel%
"""
        bat_path.write_text(bat_content, encoding='utf-8')
        print(f"✅ Creato: {bat_path}")
    
    hook_path.write_text(hook_content, encoding='utf-8')
    
    # Rendi eseguibile (Linux/Mac)
    if os.name != 'nt':
        os.chmod(hook_path, 0o755)
    
    print(f"✅ Installato: {hook_path}")
    print("\n📋 Pre-commit hook attivo!")
    print("   Ogni commit verrà validato automaticamente.")
    print("   Per saltare: git commit --no-verify")
    
    return True


def main():
    print("="*60)
    print("INSTALLAZIONE GIT HOOKS")
    print("="*60 + "\n")
    
    if install_pre_commit_hook():
        print("\n✅ Installazione completata!")
        print("\nProssimi commit saranno validati automaticamente.")
    else:
        print("\n❌ Installazione fallita")
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
