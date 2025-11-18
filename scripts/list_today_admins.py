from peptide_manager import PeptideManager
from datetime import date

m = PeptideManager('data/staging/peptide_management.db')
admins = m.get_scheduled_administrations()
print('Scheduled administrations (count):', len(admins))
for a in admins:
    dt = a['administration_datetime']
    try:
        iso = dt.isoformat()
    except Exception:
        iso = str(dt)
    print('id=%s, prep_id=%s, datetime=%s, dose_ml=%s, protocol=%s' % (
        a.get('id'), a.get('preparation_id'), iso, a.get('dose_ml'), a.get('protocol_name')
    ))
