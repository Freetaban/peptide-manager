"""Treatment section — re-exports from sub-modules.

All classes are split into:
  treatment_common.py     — shared constants, styles, helpers
  treatment_protocols.py  — ProtocolsTab + dialogs
  treatment_cycles.py     — CyclesTab, _RampEditor + dialogs
  treatment_plans.py      — PlansTab + dialogs
  treatment_templates.py  — TemplatesTab, _PhaseWidget + dialogs
"""

from .treatment_protocols import ProtocolsTab  # noqa: F401
from .treatment_cycles import CyclesTab  # noqa: F401
from .treatment_plans import PlansTab  # noqa: F401
from .treatment_templates import TemplatesTab  # noqa: F401
