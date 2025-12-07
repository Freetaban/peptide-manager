"""
Re-process certificati Janoshik con parsing migliorato
"""
import sqlite3
import json
from pathlib import Path
from peptide_manager.janoshik.models import JanoshikCertificate
from peptide_manager.janoshik import JanoshikExtractor, LLMProvider

db_path = "data/development/peptide_management.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

print("=" * 80)
print("RE-PROCESSING CERTIFICATI JANOSHIK CON PARSING MIGLIORATO")
print("=" * 80)

# 1. Trova certificati con purity=NULL
query = """
    SELECT task_number, image_file, raw_data 
    FROM janoshik_certificates 
    WHERE purity_percentage IS NULL
"""
cur.execute(query)
certs_to_reprocess = cur.fetchall()

print(f"\n📋 Trovati {len(certs_to_reprocess)} certificati da re-processare")

if len(certs_to_reprocess) == 0:
    print("✓ Nessun certificato da re-processare!")
    conn.close()
    exit(0)

# 2. Re-processa ogni certificato
extractor = JanoshikExtractor(llm_provider=LLMProvider.GPT4O)
updated_count = 0

for task_number, image_file, raw_data_json in certs_to_reprocess:
    print(f"\n🔄 Re-processing #{task_number}...")
    
    try:
        # Parse raw_data
        if raw_data_json:
            raw_data = json.loads(raw_data_json)
        else:
            print(f"   ⚠️ No raw_data, skipping...")
            continue
        
        # Ricrea certificato con parsing migliorato
        # Calcola hash (placeholder)
        image_hash = f"hash_{task_number}"
        
        # Usa from_extracted_data che ha la logica migliorata
        cert = JanoshikCertificate.from_extracted_data(
            extracted=raw_data,
            image_file=image_file or "",
            image_hash=image_hash
        )
        
        # Update database
        update_query = """
            UPDATE janoshik_certificates 
            SET purity_percentage = ?, 
                quantity_tested_mg = ?,
                endotoxin_level = ?
            WHERE task_number = ?
        """
        cur.execute(update_query, (
            cert.purity_percentage,
            cert.quantity_tested_mg,
            cert.endotoxin_level,
            task_number
        ))
        
        print(f"   ✓ Updated: purity={cert.purity_percentage}, qty={cert.quantity_tested_mg}")
        updated_count += 1
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        continue

conn.commit()
conn.close()

print(f"\n{'=' * 80}")
print(f"✓ Re-processing completato!")
print(f"  Certificati aggiornati: {updated_count}/{len(certs_to_reprocess)}")
print(f"{'=' * 80}\n")

# 3. Ri-calcola rankings
print("🔄 Ricalcolo rankings...")
from peptide_manager.janoshik import JanoshikManager

manager = JanoshikManager(db_path=db_path)
scorer = manager.scorer

# Ricarica certificati
conn = sqlite3.connect(db_path)
query = "SELECT * FROM janoshik_certificates"
import pandas as pd
certs_df = pd.read_sql_query(query, conn)
conn.close()

# Calcola rankings
rankings_df = scorer.calculate_rankings(certs_df)

# Converti DataFrame in oggetti SupplierRanking
from peptide_manager.janoshik.models import SupplierRanking
rankings = []
for _, row in rankings_df.iterrows():
    ranking = SupplierRanking(
        supplier_name=row['supplier_name'],
        supplier_website=row.get('supplier_website'),
        total_certificates=int(row.get('total_certificates', 0)),
        recent_certificates=int(row.get('recent_certificates', 0)),
        certs_last_30d=int(row.get('certs_last_30d', 0)),
        avg_purity=float(row['avg_purity']) if pd.notna(row.get('avg_purity')) else None,
        min_purity=float(row['min_purity']) if pd.notna(row.get('min_purity')) else None,
        max_purity=float(row['max_purity']) if pd.notna(row.get('max_purity')) else None,
        std_purity=float(row['std_purity']) if pd.notna(row.get('std_purity')) else None,
        avg_endotoxin_level=float(row['avg_endotoxin_level']) if pd.notna(row.get('avg_endotoxin_level')) else None,
        certs_with_endotoxin=int(row.get('certs_with_endotoxin', 0)),
        volume_score=float(row.get('volume_score', 0)),
        quality_score=float(row.get('quality_score', 0)),
        consistency_score=float(row.get('consistency_score', 0)),
        recency_score=float(row.get('recency_score', 0)),
        endotoxin_score=float(row.get('endotoxin_score', 0)),
        total_score=float(row['total_score']),
        rank_position=int(row.get('rank_position', 0)),
        days_since_last_cert=int(row.get('days_since_last_cert', 0)) if pd.notna(row.get('days_since_last_cert')) else None,
        avg_date_gap=float(row['avg_date_gap']) if pd.notna(row.get('avg_date_gap')) else None,
        peptides_tested=row.get('peptides_tested'),
        data_snapshot=row.get('data_snapshot')
    )
    rankings.append(ranking)

# Salva nel database
from peptide_manager.janoshik.repositories import SupplierRankingRepository
repo = SupplierRankingRepository(db_path)
repo.insert_many(rankings)

print(f"✓ Rankings aggiornati: {len(rankings)} suppliers\n")

# 4. Mostra risultati
print("=" * 80)
print("RISULTATI AGGIORNATI")
print("=" * 80)

conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Certificati ancora con purity=NULL
cur.execute("SELECT COUNT(*) FROM janoshik_certificates WHERE purity_percentage IS NULL")
still_null = cur.fetchone()[0]
print(f"\n⚠️ Certificati ancora con purity=NULL: {still_null}")

if still_null > 0:
    cur.execute("""
        SELECT task_number, supplier_name, peptide_name, quantity_tested_mg
        FROM janoshik_certificates 
        WHERE purity_percentage IS NULL
        LIMIT 5
    """)
    print("\n   Esempi:")
    for row in cur.fetchall():
        print(f"   - #{row[0]}: {row[1]} - {row[2]} (qty={row[3]})")

# Top 5 rankings
print("\n🏆 TOP 5 SUPPLIERS (aggiornato):")
cur.execute("""
    SELECT supplier_name, total_score, total_certificates, avg_purity, days_since_last_cert
    FROM supplier_rankings
    ORDER BY total_score DESC
    LIMIT 5
""")
for i, row in enumerate(cur.fetchall(), 1):
    purity_str = f"{row[3]:.2f}%" if row[3] else "N/A"
    print(f"   {i}. {row[0]}: {row[1]:.2f} pts ({row[2]} certs, {purity_str}, {row[4]} days)")

conn.close()
print("\n" + "=" * 80)
