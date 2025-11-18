from peptide_manager import PeptideManager
from peptide_manager.models.cycle import CycleRepository
DB='data/staging/peptide_management.db'
pm=PeptideManager(db_path=DB)
repo=CycleRepository(pm.conn)
cur=pm.conn.cursor()
cur.execute("INSERT INTO administrations (preparation_id, protocol_id, administration_datetime, dose_ml, created_at) VALUES (?, ?, datetime('now'), ?, datetime('now'))", (1,1,0.1))
admin_id=cur.lastrowid
pm.conn.commit()
print('inserted', admin_id)
res1=repo.record_administration(1, admin_id)
print('assigned to cycle 1?', res1)
res2=repo.record_administration(2, admin_id)
print('assigned to cycle 2?', res2)
cur.execute('SELECT id, cycle_id FROM administrations WHERE id=?',(admin_id,))
print(cur.fetchone())
