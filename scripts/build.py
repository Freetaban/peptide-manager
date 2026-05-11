"""Build standalone Windows exe via PyInstaller (PySide6 Qt app)."""

import shutil
import subprocess
import sys
from pathlib import Path


def main():
    project_root = Path(__file__).resolve().parent.parent
    entry_point = project_root / "gui_qt" / "app.py"

    if not entry_point.exists():
        print(f"ERROR: {entry_point} not found. Run from the project root.")
        sys.exit(1)

    pyinstaller_exe = shutil.which("pyinstaller")
    if pyinstaller_exe is None:
        print("ERROR: 'pyinstaller' not found on PATH. Is the venv activated?")
        sys.exit(1)

    sep = ";"  # Windows path separator for --add-data

    cmd = [
        pyinstaller_exe,
        str(entry_point),
        "--name", "PeptideManager",
        "--onedir",
        "--noconfirm",
        "--windowed",
        # Data files
        "--add-data", f"migrations{sep}migrations",
        "--add-data", f"gui_qt/style.qss{sep}gui_qt",
        "--add-data", f"docs/COMPENDIO_PEPTIDI.md{sep}docs",
        "--add-data", f"docs/COMPENDIO_AAS_FARMACI.md{sep}docs",
        # Hidden imports — lazy / dynamic imports PyInstaller can't detect
        "--hidden-import", "peptide_manager.backup",
        "--hidden-import", "peptide_manager.calculator",
        "--hidden-import", "peptide_manager.paths",
        "--hidden-import", "peptide_manager.janoshik",
        "--hidden-import", "qtawesome",
        "--hidden-import", "openai",
        "--hidden-import", "anthropic",
        "--hidden-import", "google.generativeai",
        "--hidden-import", "PIL",
        "--hidden-import", "PIL.Image",
        "--hidden-import", "bs4.builder._htmlparser",
        "--hidden-import", "dateutil.tz",
        "--hidden-import", "rich.markup",
        "--hidden-import", "pandas",
        # Windows metadata
        "--product-name", "Peptide Manager",
        "--product-version", "1.0.0",
        "--file-description", "Peptide Management System",
    ]

    print("Running: pyinstaller ...")
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
