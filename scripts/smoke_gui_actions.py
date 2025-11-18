from peptide_manager import PeptideManager
import sqlite3
from pathlib import Path

DB='data/staging/peptide_management.db'
pm = PeptideManager(db_path=DB)

print('Connected to staging DB:', DB)
# List protocols
try:
    protocols = pm.get_protocols() if hasattr(pm, 'get_protocols') else []
except Exception:
    protocols = []

print('Protocols found:', len(protocols))
if protocols:
    for p in protocols[:5]:
        print(' -', p.get('id'), p.get('name'))

# If no protocols via API, query DB directly
if not protocols:
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    try:
        cur.execute('SELECT id, name FROM protocols LIMIT 5')
        rows = cur.fetchall()
        print('Protocols (raw):', rows)
        proto_id = rows[0][0] if rows else None
    except Exception as e:
        print('Error reading protocols:', e)
        proto_id = None
    finally:
        conn.close()
else:
    proto_id = protocols[0].get('id')

if not proto_id:
    print('No protocol found; cannot start cycle automatically. Manual check required.')
    raise SystemExit(1)

print('Using protocol_id =', proto_id)

# Start cycle
try:
    cid = pm.start_cycle(protocol_id=proto_id, name='SMOKE_TEST_CYCLE')
    print('Created cycle id', cid)
except Exception as e:
    print('Error creating cycle:', e)
    raise

# Run stock suggestion
try:
    report = pm.suggest_doses_from_inventory(cid)
    print('Suggest report keys:', list(report.keys()))
    # Print per_peptide summary
    per = report.get('per_peptide', {})
    for pid, info in per.items():
        print('PEP', pid, info.get('name'), 'planned', info.get('planned_mcg'), 'avail', info.get('available_mcg'))
except Exception as e:
    print('Error suggest:', e)

# Create a fake administration to test assign_administrations_to_cycle
# We'll insert into administrations table a test row (minimal) and then assign it
conn = sqlite3.connect(DB)
cur = conn.cursor()
cur.execute("INSERT INTO administrations (preparation_id, protocol_id, administration_datetime, dose_ml, created_at) VALUES (?, ?, datetime('now'), ?, datetime('now'))", (1, proto_id, 0.1))
admin_id = cur.lastrowid
conn.commit()
conn.close()
print('Inserted fake administration id', admin_id)

# Assign retroactively
try:
    n = pm.assign_administrations_to_cycle([admin_id], cid)
    print('Assigned administrations count:', n)
except Exception as e:
    print('Error assign administrations:', e)

# Verify administration now has cycle_id
conn = sqlite3.connect(DB)
cur = conn.cursor()
cur.execute('SELECT id, cycle_id, protocol_id FROM administrations WHERE id = ?', (admin_id,))
print('Administration row after assign:', cur.fetchone())
conn.close()

print('SMOKE GUI ACTIONS COMPLETE')
