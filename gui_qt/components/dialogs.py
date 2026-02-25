"""Dialog helpers for the PySide6 GUI."""

from PySide6.QtWidgets import QMessageBox, QInputDialog


def confirm_dialog(parent, title, message):
    """Yes/No confirmation. Returns True if user clicked Yes."""
    result = QMessageBox.question(
        parent, title, message,
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.No,
    )
    return result == QMessageBox.Yes


def error_dialog(parent, title, message):
    """Warning / error popup."""
    QMessageBox.warning(parent, title, message)


def input_dialog(parent, title, label, default=""):
    """Single-line text input. Returns the string or None if cancelled."""
    text, ok = QInputDialog.getText(parent, title, label, text=default)
    return text if ok else None
