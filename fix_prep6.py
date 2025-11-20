import sqlite3

conn = sqlite3.connect('data/production/peptide_management.db')
cursor = conn.cursor()

cursor.execute("""
    UPDATE preparations 
    SET status = 'depleted', 
        volume_remaining_ml = 0,
        actual_depletion_date = DATE('now')
    WHERE id = 6
""")

conn.commit()
print('✅ Prep #6 marcata come depleted')
conn.close()
