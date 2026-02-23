"""
Form helpers — Phase 1.

Planned API
-----------
class FormField:
    label: str
    widget: QWidget
    validator: callable | None

class FormLayout(QWidget):
    def __init__(self, fields: list[FormField], parent=None)
    def get_values(self) -> dict
    def set_values(self, data: dict) -> None
    def validate(self) -> list[str]
"""
