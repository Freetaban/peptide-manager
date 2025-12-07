"""
Sync Janoshik data to main suppliers table.

Popola/aggiorna la tabella suppliers con metriche Janoshik:
- Crea suppliers mancanti
- Aggiorna metriche qualità
- Mantiene altri campi intatti (country, email, notes, etc.)
"""

import sqlite3
from datetime import datetime
from typing import Dict, List


def normalize_supplier_name(name: str) -> str:
    """Normalizza nome supplier per matching"""
    if not name:
        return ""
    
    # Lowercase e trim
    name = name.strip().lower()
    
    # Rimuovi protocolli web
    for prefix in ['https://', 'http://', 'www.']:
        if name.startswith(prefix):
            name = name[len(prefix):]
    
    # Rimuovi trailing slash
    if name.endswith('/'):
        name = name[:-1]
    
    return name


def calculate_quality_score(avg_purity: float, min_purity: float, cert_count: int) -> float:
    """
    Calcola quality score 0-100.
    
    Formula:
    - 60% avg purity (95%=0, 100%=100)
    - 30% consistency (min purity penalty)
    - 10% volume (cert count bonus)
    """
    # Purity score
    purity_score = min(100, max(0, (avg_purity - 95) * 20))
    
    # Consistency penalty
    consistency_score = 100 if min_purity >= 99 else min_purity * 1.01
    
    # Volume bonus
    volume_score = min(100, cert_count * 5)
    
    total = (purity_score * 0.6 + consistency_score * 0.3 + volume_score * 0.1)
    return round(total, 2)


def get_janoshik_supplier_metrics(conn: sqlite3.Connection) -> List[Dict]:
    """Estrae metriche aggregate da janoshik_certificates"""
    
    query = """
    SELECT 
        supplier_name,
        COUNT(*) as cert_count,
        AVG(purity_percentage) as avg_purity,
        MIN(purity_percentage) as min_purity,
        MAX(purity_percentage) as max_purity,
        MAX(test_date) as last_test_date
    FROM janoshik_certificates
    WHERE supplier_name IS NOT NULL 
      AND supplier_name != ''
      AND purity_percentage IS NOT NULL
    GROUP BY supplier_name
    """
    
    cursor = conn.execute(query)
    
    metrics = []
    for row in cursor.fetchall():
        supplier_name = row[0]
        cert_count = row[1]
        avg_purity = row[2]
        min_purity = row[3]
        max_purity = row[4]
        last_test_date = row[5]
        
        # Calcola days since last test
        try:
            last_date = datetime.fromisoformat(last_test_date)
            days_since = (datetime.now() - last_date).days
        except:
            days_since = 999
        
        # Quality score
        quality_score = calculate_quality_score(avg_purity, min_purity, cert_count)
        
        # Estrai website se presente nel nome
        website = None
        if any(x in supplier_name.lower() for x in ['.com', '.net', '.org', 'www']):
            website = supplier_name
        
        metrics.append({
            'supplier_name': supplier_name,
            'normalized_name': normalize_supplier_name(supplier_name),
            'website': website,
            'cert_count': cert_count,
            'avg_purity': round(avg_purity, 2),
            'min_purity': round(min_purity, 2),
            'max_purity': round(max_purity, 2),
            'last_test_date': last_test_date,
            'days_since': days_since,
            'quality_score': quality_score
        })
    
    return metrics


def sync_suppliers(db_path: str, dry_run: bool = False):
    """
    Sincronizza suppliers con dati Janoshik.
    
    Args:
        db_path: Path database
        dry_run: Se True, non modifica DB (solo report)
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    print("\n" + "="*80)
    print("🔄 SYNC JANOSHIK → SUPPLIERS TABLE")
    print("="*80)
    
    # Ottieni metriche Janoshik
    print("\n📊 Estrazione metriche Janoshik...")
    janoshik_metrics = get_janoshik_supplier_metrics(conn)
    print(f"   ✓ {len(janoshik_metrics)} suppliers trovati in Janoshik")
    
    # Ottieni suppliers esistenti
    cursor = conn.execute("SELECT id, name, website FROM suppliers WHERE deleted_at IS NULL")
    existing_suppliers = {normalize_supplier_name(row['name']): row for row in cursor.fetchall()}
    print(f"   ✓ {len(existing_suppliers)} suppliers esistenti nella tabella")
    
    # Matching e sync
    matched = 0
    new_suppliers = 0
    updated = 0
    
    print("\n🔄 Sincronizzazione...")
    
    for metric in janoshik_metrics:
        normalized = metric['normalized_name']
        
        # Check se supplier esiste
        if normalized in existing_suppliers:
            # UPDATE esistente
            supplier_id = existing_suppliers[normalized]['id']
            
            update_query = """
            UPDATE suppliers SET
                janoshik_certificates = ?,
                janoshik_avg_purity = ?,
                janoshik_min_purity = ?,
                janoshik_max_purity = ?,
                janoshik_last_test_date = ?,
                janoshik_days_since_last_test = ?,
                janoshik_quality_score = ?,
                janoshik_updated_at = ?
            WHERE id = ?
            """
            
            if not dry_run:
                conn.execute(update_query, (
                    metric['cert_count'],
                    metric['avg_purity'],
                    metric['min_purity'],
                    metric['max_purity'],
                    metric['last_test_date'],
                    metric['days_since'],
                    metric['quality_score'],
                    datetime.now().isoformat(),
                    supplier_id
                ))
            
            matched += 1
            updated += 1
            print(f"   ✓ Updated: {metric['supplier_name'][:50]} (score: {metric['quality_score']:.1f})")
        
        else:
            # INSERT nuovo supplier
            insert_query = """
            INSERT INTO suppliers (
                name, website, 
                janoshik_certificates, janoshik_avg_purity, janoshik_min_purity,
                janoshik_max_purity, janoshik_last_test_date, janoshik_days_since_last_test,
                janoshik_quality_score, janoshik_updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            if not dry_run:
                conn.execute(insert_query, (
                    metric['supplier_name'],
                    metric['website'],
                    metric['cert_count'],
                    metric['avg_purity'],
                    metric['min_purity'],
                    metric['max_purity'],
                    metric['last_test_date'],
                    metric['days_since'],
                    metric['quality_score'],
                    datetime.now().isoformat()
                ))
            
            new_suppliers += 1
            print(f"   + Created: {metric['supplier_name'][:50]} (score: {metric['quality_score']:.1f})")
    
    if not dry_run:
        conn.commit()
    
    conn.close()
    
    # Report finale
    print("\n" + "="*80)
    print("📋 RISULTATI SYNC")
    print("="*80)
    print(f"   Janoshik suppliers: {len(janoshik_metrics)}")
    print(f"   Già esistenti (updated): {updated}")
    print(f"   Nuovi creati: {new_suppliers}")
    print(f"   Totale operazioni: {matched + new_suppliers}")
    
    if dry_run:
        print("\n⚠️  DRY RUN - Nessuna modifica applicata")
    else:
        print("\n✅ Sync completato!")
    
    print("="*80)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Sync Janoshik data to suppliers table")
    parser.add_argument('--db', default='data/development/peptide_management.db', help='Database path')
    parser.add_argument('--dry-run', action='store_true', help='Preview only, no changes')
    args = parser.parse_args()
    
    sync_suppliers(args.db, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
