from types import SimpleNamespace
from decimal import Decimal

from peptide_manager import PeptideManager


class FakeCycleRepo:
    def __init__(self, conn):
        pass

    def get_by_id(self, cycle_id):
        return {
            'id': cycle_id,
            'protocol_snapshot': {
                'peptides': [
                    {'peptide_id': 1, 'name': 'A', 'target_dose_mcg': 2000},
                    {'peptide_id': 2, 'name': 'B', 'target_dose_mcg': 1000},
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


class FakePrep:
    def __init__(self, batch_id, vials_used, volume_ml, volume_remaining_ml):
        self.batch_id = batch_id
        self.vials_used = vials_used
        self.volume_ml = volume_ml
        self.volume_remaining_ml = volume_remaining_ml


def test_mix_unequal_and_prep_plus_batch(monkeypatch):
    pm = PeptideManager(db_path=':memory:')

    import peptide_manager.models.cycle as cycle_mod
    monkeypatch.setattr(cycle_mod, 'CycleRepository', FakeCycleRepo)

    fake_db = SimpleNamespace()

    # One mix batch: peptide 1 = 10 mg/vial, peptide2 = 2 mg/vial, 3 vials
    mix_batch = FakeBatch(id=20, product_name='Mix A+B', vials_remaining=3)
    fake_db.batches = SimpleNamespace(get_all=lambda only_available=True: [mix_batch])

    def get_by_batch(batch_id):
        if batch_id == 20:
            return [FakeComp(1, 10.0), FakeComp(2, 2.0)]
        return []

    fake_db.batch_composition = SimpleNamespace(get_by_batch=get_by_batch)

    # One preparation from another batch (batch 30) that gives peptide 1 via prep
    prep = FakePrep(batch_id=30, vials_used=1, volume_ml=10, volume_remaining_ml=2)
    fake_db.preparations = SimpleNamespace(get_all=lambda only_active=True: [prep])

    def get_by_batch2(batch_id):
        if batch_id == 30:
            return [FakeComp(1, 5.0)]
        return []

    # batch_composition should handle both
    def batch_comp_get(batch_id):
        return get_by_batch(batch_id) or get_by_batch2(batch_id)

    fake_db.batch_composition.get_by_batch = batch_comp_get

    pm.db = fake_db

    result = pm.suggest_doses_from_inventory(1)
    per = result['per_peptide']

    # Compute expected: mix batch -> peptide1: 10mg *3 =30mg, peptide2:2mg*3=6mg
    # prep -> peptide1: 5mg in 10ml, remaining 2ml => 5mg * (2/10) =1mg => 1000mcg
    assert int(per[1]['available_mcg']) == 30000 + 1000
    assert int(per[2]['available_mcg']) == 6000
