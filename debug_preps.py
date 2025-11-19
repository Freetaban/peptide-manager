from peptide_manager import PeptideManager

mgr = PeptideManager('data/staging/peptide_management.db')
preps = mgr.get_preparations(only_active=True)

print(f'\n=== Preparazioni attive: {len(preps)} ===\n')
for p in preps[:3]:
    print(f"Prep {p['id']}:")
    print(f"  Volume: {p.get('volume_remaining_ml')} ml")
    print(f"  Composition: {p.get('composition')}")
    print()
