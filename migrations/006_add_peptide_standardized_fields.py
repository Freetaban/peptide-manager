"""
Migration: Add standardized peptide fields

Aggiunge campi per nome peptide standardizzato e quantità nominale:
- peptide_name: Nome peptide standardizzato (es. BPC157, Tirzepatide)
- quantity_nominal: Quantità dichiarata in unità nominale (es. 5, 10, 30)
- unit_of_measure: Unità di misura (mg, IU, mcg)
"""

import sqlite3
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'scripts'))

from environment import get_environment

def migrate():
    """Applica migrazione"""
    env = get_environment()
    conn = sqlite3.connect(env.db_path)
    cursor = conn.cursor()
    
    print("🔧 Migration: Add peptide_name, quantity_nominal, unit_of_measure")
    print("=" * 70)
    
    # Check if columns already exist
    cursor.execute("PRAGMA table_info(janoshik_certificates)")
    columns = {row[1] for row in cursor.fetchall()}
    
    migrations_needed = []
    
    if 'peptide_name_std' not in columns:
        migrations_needed.append(
            "ALTER TABLE janoshik_certificates ADD COLUMN peptide_name_std TEXT"
        )
        print("✅ Will add: peptide_name_std")
    else:
        print("⏭️  Skip: peptide_name_std (already exists)")
    
    if 'quantity_nominal' not in columns:
        migrations_needed.append(
            "ALTER TABLE janoshik_certificates ADD COLUMN quantity_nominal REAL"
        )
        print("✅ Will add: quantity_nominal")
    else:
        print("⏭️  Skip: quantity_nominal (already exists)")
    
    if 'unit_of_measure' not in columns:
        migrations_needed.append(
            "ALTER TABLE janoshik_certificates ADD COLUMN unit_of_measure TEXT"
        )
        print("✅ Will add: unit_of_measure")
    else:
        print("⏭️  Skip: unit_of_measure (already exists)")
    
    if not migrations_needed:
        print("\n✅ All columns already exist! No migration needed.")
        conn.close()
        return
    
    # Apply migrations
    print(f"\n🔨 Applying {len(migrations_needed)} migrations...")
    
    for sql in migrations_needed:
        try:
            cursor.execute(sql)
            print(f"   ✓ {sql}")
        except sqlite3.OperationalError as e:
            print(f"   ⚠️  {sql} - {e}")
    
    conn.commit()
    
    print("\n✅ Migration completed!")
    print(f"📊 Database: {env.db_path}")
    
    # Verify
    cursor.execute("PRAGMA table_info(janoshik_certificates)")
    new_columns = [row[1] for row in cursor.fetchall()]
    
    print(f"\n📋 Total columns: {len(new_columns)}")
    print("New peptide fields:")
    for col in ['peptide_name_std', 'quantity_nominal', 'unit_of_measure']:
        status = "✅" if col in new_columns else "❌"
        print(f"  {status} {col}")
    
    conn.close()

if __name__ == "__main__":
    migrate()
