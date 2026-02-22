"""Build standalone Windows exe via flet pack (PyInstaller wrapper)."""

import shutil
import subprocess
import sys
from pathlib import Path


def main():
    project_root = Path(__file__).resolve().parent.parent
    entry_point = project_root / "gui_modular" / "app.py"

    if not entry_point.exists():
        print(f"ERROR: {entry_point} not found. Run from the project root.")
        sys.exit(1)

    flet_exe = shutil.which("flet")
    if flet_exe is None:
        print("ERROR: 'flet' CLI not found on PATH. Is the venv activated?")
        sys.exit(1)

    cmd = [
        flet_exe, "pack",
        str(entry_point),
        "--name", "PeptideManager",
        "-D",
        "-y",
        # Data files
        "--add-data", f"migrations{';'}migrations",
        # Hidden imports — lazy / dynamic imports PyInstaller can't detect
        "--hidden-import", "peptide_manager.backup",
        "--hidden-import", "peptide_manager.calculator",
        "--hidden-import", "peptide_manager.paths",
        "--hidden-import", "gui_modular.views.template_manager",
        "--hidden-import", "gui_modular.components.forms",
        "--hidden-import", "gui_modular.components.dialogs",
        "--hidden-import", "openai",
        "--hidden-import", "anthropic",
        "--hidden-import", "google.generativeai",
        "--hidden-import", "PIL",
        "--hidden-import", "PIL.Image",
        "--hidden-import", "bs4.builder._htmlparser",
        "--hidden-import", "dateutil.tz",
        "--hidden-import", "rich.markup",
        # Windows metadata
        "--product-name", "Peptide Manager",
        "--product-version", "1.0.0",
        "--file-description", "Peptide Management System",
    ]

    print(f"Running: flet pack ...")
    print(f"  Entry point: {entry_point}")
    print(f"  Output:      dist/PeptideManager/PeptideManager.exe")
    print()

    result = subprocess.run(cmd, cwd=str(project_root))

    if result.returncode != 0:
        print(f"\nBuild failed (exit code {result.returncode}).")
        sys.exit(result.returncode)

    exe = project_root / "dist" / "PeptideManager" / "PeptideManager.exe"
    if exe.exists():
        print(f"\nBuild succeeded: {exe}")
    else:
        print(f"\nBuild completed but exe not found at expected path: {exe}")


if __name__ == "__main__":
    main()
