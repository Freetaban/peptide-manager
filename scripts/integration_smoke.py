from peptide_manager import PeptideManager

pm = PeptideManager(db_path='data/staging/peptide_management.db')

print('get_batches:', len(pm.get_batches()))
print('get_peptides:', len(pm.get_peptides()))
print('get_cycles:', len(pm.get_cycles(active_only=False)))

# Try suggest_doses_from_inventory safely: only if there's at least one cycle
cycles = pm.get_cycles(active_only=False)
if cycles:
    cid = cycles[0]['id']
    print('suggest for cycle', cid)
    try:
        s = pm.suggest_doses_from_inventory(cid)
        print('suggest keys:', list(s.keys()))
    except Exception as e:
        print('suggest error:', e)
else:
    print('no cycles to run suggest_doses_from_inventory on (this is expected)')
