"""Recalculate rankings with corrected accuracy algorithm"""
from peptide_manager.janoshik import JanoshikManager
from peptide_manager.janoshik.models import SupplierRanking
from peptide_manager.janoshik.repositories import SupplierRankingRepository
import sqlite3
import pandas as pd

db = 'data/development/peptide_management.db'

print("🔄 Recalculating rankings with improved accuracy algorithm...")
print("   • Outliers (±50%) excluded")
print("   • Positive deviations (more quantity) = 100 score")
print("   • Negative deviations (less quantity) = double penalty\n")

# Load certificates
conn = sqlite3.connect(db)
certs = pd.read_sql_query('SELECT * FROM janoshik_certificates', conn)
conn.close()

# Calculate rankings
mgr = JanoshikManager(db_path=db)
rankings = mgr.scorer.calculate_rankings(certs)

# Convert to SupplierRanking objects
objs = [
    SupplierRanking(**{k: v for k, v in row.items() if k in SupplierRanking.__dataclass_fields__})
    for _, row in rankings.iterrows()
]

# Save to database
repo = SupplierRankingRepository(db)
repo.insert_many(objs)

print(f"✅ Updated {len(objs)} suppliers\n")

# Show top 10
print("🏆 TOP 10 SUPPLIERS (new algorithm):")
conn = sqlite3.connect(db)
top10 = pd.read_sql_query("""
    SELECT 
        rank_position,
        supplier_name,
        total_score,
        avg_purity,
        avg_accuracy,
        certs_with_accuracy,
        accuracy_score
    FROM supplier_rankings
    ORDER BY rank_position
    LIMIT 10
""", conn)
conn.close()

for _, row in top10.iterrows():
    acc_str = f"{row['avg_accuracy']:.1f}%" if pd.notna(row['avg_accuracy']) else "N/A"
    print(f"  {int(row['rank_position']):2d}. {row['supplier_name']}")
    print(f"      Total: {row['total_score']:.2f} | Purity: {row['avg_purity']:.2f}% | Accuracy: {acc_str} ({int(row['certs_with_accuracy'])} certs, score: {row['accuracy_score']:.1f})")
