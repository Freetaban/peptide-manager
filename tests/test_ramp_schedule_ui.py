import pytest

from peptide_manager import PeptideManager


class FakeCycleRepo:
    def __init__(self, conn):
        pass

    def update_ramp_schedule(self, cycle_id, ramp_schedule):
        # simply return True indicating success and record values for test
        self._last = (cycle_id, ramp_schedule)
        return True


def test_update_cycle_ramp_schedule(monkeypatch):
    pm = PeptideManager(db_path=':memory:')

    import peptide_manager.models.cycle as cycle_mod
    monkeypatch.setattr(cycle_mod, 'CycleRepository', FakeCycleRepo)

    # Call through PeptideManager API
    success = pm.update_cycle_ramp_schedule(1, [{'day': 1, 'target_mcg': 2500}])
    assert success is True
