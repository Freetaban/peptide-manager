"""Regression tests for PeptideManager.update_administration dose handling.

These exercise the manager-level method (not the repository) because the
volume-reconciliation logic lives there. The key invariant: when a dose is
edited, BOTH the stored administration dose AND the preparation's remaining
volume must move together — otherwise the inventory and the history disagree.

This guards the bug where increasing a dose (with enough volume in the
original preparation) decremented the prep volume but silently kept the OLD
dose on the administration record.
"""

import os
import tempfile

import pytest

from peptide_manager import PeptideManager
from peptide_manager.database import init_database


@pytest.fixture
def manager():
    """A PeptideManager backed by a full-schema temp database."""
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    tmp.close()
    init_database(tmp.name).close()
    mgr = PeptideManager(tmp.name)
    yield mgr
    mgr.close()
    os.unlink(tmp.name)


@pytest.fixture
def prep_id(manager):
    """Supplier → batch → preparation with 10.0 ml available."""
    supplier_id = manager.add_supplier("Reg Supplier", country="IT")
    batch_id = manager.add_batch(
        supplier_id=supplier_id,
        product_name="Reg Peptide",
        vials_count=1,
        mg_per_vial=5.0,
        total_price=100.0,
        purchase_date="2025-01-01",
    )
    return manager.add_preparation(
        batch_id=batch_id,
        vials_used=1,
        volume_ml=10.0,
        preparation_date="2025-01-10",
    )


def _remaining(manager, prep_id):
    return float(manager.db.preparations.get_by_id(prep_id).volume_remaining_ml)


def test_increase_dose_persists_dose_and_decrements_volume(manager, prep_id):
    """Increasing the dose must update the record AND consume the extra volume."""
    admin_id = manager.add_administration(preparation_id=prep_id, dose_ml=0.50)
    assert _remaining(manager, prep_id) == pytest.approx(9.50)

    manager.update_administration(admin_id, dose_ml=0.80)

    # The administration must reflect the new dose (this is the regressed bug).
    admin = manager.db.administrations.get_by_id(admin_id)
    assert float(admin.dose_ml) == pytest.approx(0.80)
    # And the prep must have given up the additional 0.30 ml.
    assert _remaining(manager, prep_id) == pytest.approx(9.20)


def test_decrease_dose_persists_dose_and_restores_volume(manager, prep_id):
    """Decreasing the dose must update the record AND return the freed volume."""
    admin_id = manager.add_administration(preparation_id=prep_id, dose_ml=0.80)
    assert _remaining(manager, prep_id) == pytest.approx(9.20)

    manager.update_administration(admin_id, dose_ml=0.50)

    admin = manager.db.administrations.get_by_id(admin_id)
    assert float(admin.dose_ml) == pytest.approx(0.50)
    assert _remaining(manager, prep_id) == pytest.approx(9.50)


def test_edit_metadata_without_dose_change_leaves_volume(manager, prep_id):
    """Editing only metadata must not touch the preparation volume."""
    admin_id = manager.add_administration(preparation_id=prep_id, dose_ml=0.50)
    before = _remaining(manager, prep_id)

    manager.update_administration(
        admin_id,
        injection_site="Addome",
        notes="corretto",
    )

    admin = manager.db.administrations.get_by_id(admin_id)
    assert admin.injection_site == "Addome"
    assert admin.notes == "corretto"
    assert _remaining(manager, prep_id) == pytest.approx(before)
