import types
from types import SimpleNamespace
from decimal import Decimal

import pytest

from peptide_manager import PeptideManager


class FakeCycleRepo:
    def __init__(self, conn):
        pass

    def get_by_id(self, cycle_id):
        # Return a cycle with protocol_snapshot having two peptides (ids 1 and 2)
        return {
            'id': cycle_id,
            'protocol_snapshot': {
                'peptides': [
                    {'peptide_id': 1, 'name': 'BPC', 'target_dose_mcg': 5000},
                    {'peptide_id': 2, 'name': 'TB', 'target_dose_mcg': 5000}
                ]
            }
        }


class FakeComp:
    def __init__(self, peptide_id, mg_amount):
        self.peptide_id = peptide_id
        self.mg_amount = Decimal(str(mg_amount))


class FakeBatch:
    def __init__(self, id, product_name, vials_remaining):
        self.id = id
        self.product_name = product_name
        self.vials_remaining = vials_remaining


class FakeDB:
    def __init__(self):
        self.preparations = SimpleNamespace()
        self.batches = SimpleNamespace()
        self.batch_composition = SimpleNamespace()
        self.peptides = SimpleNamespace()


def test_mix_batch_supports_equal_peptides(monkeypatch):
    pm = PeptideManager(db_path=':memory:')

    # Patch CycleRepository used inside suggest_doses_from_inventory
    import peptide_manager.models.cycle as cycle_mod
    monkeypatch.setattr(cycle_mod, 'CycleRepository', FakeCycleRepo)

    # Prepare fake DB
    fake_db = FakeDB()

    # No active preparations
    fake_db.preparations.get_all = lambda only_active=True: []

    # One mix batch: 5 vials remaining, each vial contains 5 mg of peptide 1 and 5 mg of peptide 2
    mix_batch = FakeBatch(id=10, product_name='Mix BPC+TB', vials_remaining=5)
    fake_db.batches.get_all = lambda only_available=True: [mix_batch]

    # Composition: both peptides 5 mg per vial
    def get_by_batch(batch_id):
        if batch_id == 10:
            return [FakeComp(1, 5.0), FakeComp(2, 5.0)]
        return []

    fake_db.batch_composition.get_by_batch = get_by_batch

    # Attach fake db to manager
    pm.db = fake_db

    # Run suggestion
    result = pm.suggest_doses_from_inventory(1)

    assert 'per_peptide' in result
    per = result['per_peptide']

    # Each peptide should have available_mcg = 5 mg * 5 vials = 25 mg = 25000 mcg
    assert int(per[1]['available_mcg']) == 25000
    assert int(per[2]['available_mcg']) == 25000

    # Mixes should report supported_admins_for_cycle = 5 (each admin needs 5000 mcg)
    mixes = result.get('mixes', [])
    assert len(mixes) == 1
    mix = mixes[0]
    assert mix['supported_admins_for_cycle'] == 5
