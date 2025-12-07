#!/usr/bin/env python3
"""
Export supplier rankings with accuracy metrics to CSV
"""
from peptide_manager.janoshik.manager import JanoshikManager

def main():
    manager = JanoshikManager(db_path="data/development/peptide_management.db")
    
    print("📊 Exporting supplier rankings with accuracy metrics...")
    
    output_file = manager.export_rankings_to_csv(
        "data/exports/janoshik_rankings_with_accuracy.csv"
    )
    
    print(f"✅ Exported: {output_file}")
    print("\nColumns included:")
    print("  • supplier_name")
    print("  • total_score")
    print("  • volume_score, quality_score, accuracy_score")
    print("  • consistency_score, recency_score, endotoxin_score")
    print("  • avg_purity, avg_accuracy (NEW)")
    print("  • certificate_count, certs_with_accuracy (NEW)")

if __name__ == "__main__":
    main()
