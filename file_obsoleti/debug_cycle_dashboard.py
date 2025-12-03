from peptide_manager import PeptideManager
from datetime import date

mgr = PeptideManager('data/staging/peptide_management.db')
result = mgr.get_scheduled_administrations(date.today())

print(f'\n=== TO-DO LIST OGGI: {len(result)} tasks ===\n')
for r in result:
    print(f"✓ Peptide: {r.get('peptide_name')}")
    print(f"  Dose target: {r.get('target_dose_mcg')} mcg")
    print(f"  Preleva: {r.get('suggested_dose_ml')} ml")
    print(f"  Prep: #{r.get('preparation_id')}")
    print(f"  Ciclo: {r.get('cycle_name')}")
    print(f"  Status: {r.get('status')}")
    print()
