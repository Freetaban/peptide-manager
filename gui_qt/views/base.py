"""Base view widget for all PySide6 views."""

from PySide6.QtWidgets import QWidget, QVBoxLayout


class BaseView(QWidget):
    """Base class for all section views.

    Provides:
    - Reference to the main application window (``self.app``)
    - Shortcut to ``self.manager`` (PeptideManager)
    - ``self.edit_mode`` property
    - ``refresh()`` hook for subclass data reload
    - Pre-configured QVBoxLayout with 20 px margins
    """

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

    @property
    def manager(self):
        """Shortcut to PeptideManager instance."""
        return self.app.manager

    @property
    def edit_mode(self):
        """Current edit-mode state from the main window."""
        return self.app.edit_mode

    def refresh(self):
        """Reload data from the database. Override in subclasses."""
