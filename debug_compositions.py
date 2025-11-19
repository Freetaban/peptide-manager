from peptide_manager import PeptideManager

mgr = PeptideManager('data/staging/peptide_management.db')

# Test get_peptides_in_batch
compositions = mgr.db.batch_composition.get_peptides_in_batch(1)
print(f'\n=== Batch 1 compositions: {len(compositions)} ===\n')
for comp in compositions:
    print(f"Peptide {comp.get('peptide_id')}: {comp.get('peptide_name')}")
    print(f"  mg_per_vial: {comp.get('mg_per_vial')}")
    print(f"  mg_amount: {comp.get('mg_amount')}")
    print(f"  Full dict: {comp}")
    print()
