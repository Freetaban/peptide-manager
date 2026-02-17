"""
Path resolution for frozen (PyInstaller) vs source execution.

Frozen exe: data goes in %APPDATA%/PeptideManager/
Source run: data stays in project-relative paths (via Environment).
"""

import os
import sys
from pathlib import Path
from typing import Optional, Union


def is_frozen() -> bool:
    """True when running as a PyInstaller bundle."""
    return getattr(sys, "frozen", False)


def get_bundle_dir() -> Path:
    """Directory containing the app code / bundled resources."""
    if is_frozen():
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def get_data_dir() -> Optional[Path]:
    """
    Return the writable data root for frozen builds.

    Frozen: %APPDATA%/PeptideManager  (created by ensure_data_dirs)
    Source: None  (caller should use Environment instead)
    """
    if not is_frozen():
        return None
    return Path(os.environ["APPDATA"]) / "PeptideManager"


def get_migrations_dir() -> Path:
    """Migrations folder — bundled inside the exe or in project root."""
    return get_bundle_dir() / "migrations"


def ensure_data_dirs(data_dir: Path) -> dict:
    """
    Create the data directory tree under `data_dir`.

    Returns dict of created paths for convenience.
    """
    dirs = {
        "data": data_dir,
        "backups": data_dir / "backups",
        "certificates": data_dir / "certificates",
        "exports": data_dir / "exports",
    }
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)
    return dirs


def ensure_db_parent(db_path: Union[str, Path]) -> None:
    """Create parent directory of the database file if it doesn't exist."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
