"""Ricalcola janoshik_quality_score per fornitori mancanti"""
import sqlite3

def calculate_quality_score(avg_purity, std_purity, total_certificates):
    """
    Score finale 0-100:
    - 60% Purity Score
    - 30% Consistency Score  
    - 10% Volume Score
    """
    # Purity Score (0-100)
    purity_score = avg_purity
    
    # Consistency Score (0-100)
    if std_purity <= 1.0:
        consistency_score = 100
    elif std_purity <= 2.0:
        consistency_score = 90
    elif std_purity <= 3.0:
        consistency_score = 80
    elif std_purity <= 5.0:
        consistency_score = 70
    else:
        consistency_score = max(0, 60 - (std_purity - 5) * 5)
    
    # Volume Score (0-100)
    if total_certificates >= 20:
        volume_score = 100
    elif total_certificates >= 15:
        volume_score = 90
    elif total_certificates >= 10:
        volume_score = 80
    elif total_certificates >= 5:
        volume_score = 70
    else:
        volume_score = 50
    
    # Final Score
    quality_score = (
        purity_score * 0.6 +
        consistency_score * 0.3 +
        volume_score * 0.1
    )
    
    return round(quality_score, 1)

conn = sqlite3.connect('data/production/peptide_management.db')
cur = conn.cursor()

# Trova fornitori con certificati ma senza score
cur.execute('''
    SELECT s.id, s.name
    FROM suppliers s
    INNER JOIN janoshik_certificates j ON s.name = j.supplier_name
    WHERE s.janoshik_quality_score IS NULL
    GROUP BY s.id, s.name
''')

suppliers_to_update = cur.fetchall()

print(f'Fornitori da aggiornare: {len(suppliers_to_update)}')

for supplier_id, supplier_name in suppliers_to_update:
    print(f'\n{supplier_name}:')
    
    # Calcola statistiche
    cur.execute('''
        SELECT 
            purity_percentage
        FROM janoshik_certificates
        WHERE supplier_name = ?
          AND purity_percentage > 0
    ''', (supplier_name,))
    
    purities = [row[0] for row in cur.fetchall()]
    
    if not purities:
        print(f'  Nessun dato di purezza, skip')
        continue
    
    import statistics
    total = len(purities)
    avg_purity = statistics.mean(purities)
    std_purity = statistics.stdev(purities) if len(purities) > 1 else 0
    
    # Calcola score
    score = calculate_quality_score(avg_purity, std_purity or 0, total)
    
    print(f'  Certificati: {total}')
    print(f'  Purezza media: {avg_purity:.2f}%')
    print(f'  Deviazione std: {std_purity:.2f}')
    print(f'  Score calcolato: {score}')
    
    # Aggiorna database
    cur.execute('''
        UPDATE suppliers
        SET janoshik_quality_score = ?,
            janoshik_certificates = ?
        WHERE id = ?
    ''', (score, total, supplier_id))
    
    conn.commit()
    print(f'  ✅ Aggiornato')

print(f'\n✅ Completato! Aggiornati {len(suppliers_to_update)} fornitori')

conn.close()
