"""
Backfill standardized peptide fields

Popola retroattivamente peptide_name_std, quantity_nominal, unit_of_measure
per tutti i 452 certificati esistenti basandosi sul product_name.

Esempi:
- "BPC-157 5mg" → peptide_name_std="BPC157", quantity_nominal=5, unit_of_measure="mg"
- "Tirzepatide 30mg" → peptide_name_std="Tirzepatide", quantity_nominal=30, unit_of_measure="mg"
- "HGH 10 IU" → peptide_name_std="HGH", quantity_nominal=10, unit_of_measure="IU"
"""

import re
import sqlite3
import sys
from pathlib import Path
from typing import Tuple, Optional

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from environment import get_environment


def standardize_peptide_name(product_name: str) -> str:
    """
    Standardizza nome peptide rimuovendo quantità, spazi, trattini extra.
    
    Args:
        product_name: Nome prodotto grezzo (es. "BPC-157 5mg")
        
    Returns:
        Nome standardizzato (es. "BPC157")
    """
    if not product_name:
        return None
    
    # Mappature dirette per peptidi comuni
    name_upper = product_name.upper()
    
    # GLP-1 Agonists
    if 'TIRZEPATIDE' in name_upper or 'TIRZE' in name_upper:
        return 'Tirzepatide'
    if 'SEMAGLUTIDE' in name_upper or 'SEMA' in name_upper:
        return 'Semaglutide'
    if 'RETATRUTIDE' in name_upper or 'RETA' in name_upper:
        return 'Retatrutide'
    if 'LIRAGLUTIDE' in name_upper:
        return 'Liraglutide'
    if 'DULAGLUTIDE' in name_upper:
        return 'Dulaglutide'
    if 'CAGRILINTIDE' in name_upper:
        return 'Cagrilintide'
    if 'MAZDUTIDE' in name_upper:
        return 'Mazdutide'
    
    # Peptidi riparativi
    if 'BPC' in name_upper:
        return 'BPC157'  # Standardizza tutte le varianti (BPC, BPC-157, BPC157)
    if 'TB-500' in name_upper or 'TB500' in name_upper or 'THYMOSIN BETA' in name_upper:
        return 'TB500'
    if 'KPV' in name_upper:
        return 'KPV'
    if 'GHK' in name_upper:
        return 'GHK-Cu'
    
    # Growth Hormone Secretagogues
    if 'IPAMORELIN' in name_upper or 'IPAM' in name_upper:
        return 'Ipamorelin'
    if 'CJC' in name_upper:
        return 'CJC-1295'
    if 'TESAMORELIN' in name_upper or 'TESAM' in name_upper:
        return 'Tesamorelin'
    if 'SERMORELIN' in name_upper:
        return 'Sermorelin'
    if 'HEXARELIN' in name_upper:
        return 'Hexarelin'
    if 'GHRP-2' in name_upper or 'GHRP2' in name_upper:
        return 'GHRP-2'
    if 'GHRP-6' in name_upper or 'GHRP6' in name_upper:
        return 'GHRP-6'
    if 'MK-677' in name_upper or 'MK677' in name_upper or 'IBUTAMOREN' in name_upper:
        return 'MK-677'
    
    # HGH/Somatropin
    if 'SOMATROPIN' in name_upper or 'HGH' in name_upper or 'QITROPE' in name_upper:
        return 'HGH'
    
    # Nootropici/Cognitivi
    if 'SELANK' in name_upper:
        return 'Selank'
    if 'SEMAX' in name_upper:
        return 'Semax'
    if 'CEREBROLYSIN' in name_upper:
        return 'Cerebrolysin'
    if 'NOOPEPT' in name_upper:
        return 'Noopept'
    if 'P21' in name_upper or 'P-21' in name_upper:
        return 'P21'
    
    # Anti-aging/Longevità
    if 'EPITHALON' in name_upper or 'EPITALON' in name_upper:
        return 'Epithalon'
    if 'NAD+' in name_upper or 'NAD ' in name_upper:
        return 'NAD+'
    if 'NMN' in name_upper:
        return 'NMN'
    if 'MOTS-C' in name_upper or 'MOTS' in name_upper:
        return 'MOTS-C'
    if 'HUMANIN' in name_upper:
        return 'Humanin'
    if 'SS-31' in name_upper or 'ELAMIPRETIDE' in name_upper:
        return 'SS-31'
    
    # Metabolici
    if 'AOD' in name_upper:
        return 'AOD-9604'
    if '5-AMINO' in name_upper or '5AMINO' in name_upper:
        return '5-Amino-1MQ'
    if 'TESOFENSINE' in name_upper:
        return 'Tesofensine'
    
    # Immunitari
    if 'THYMOSIN ALPHA' in name_upper or 'TA1' in name_upper or 'TA-1' in name_upper:
        return 'Thymosin-Alpha-1'
    if 'LL-37' in name_upper or 'LL37' in name_upper:
        return 'LL-37'
    if 'THYMULIN' in name_upper:
        return 'Thymulin'
    
    # Sessuali
    if 'PT-141' in name_upper or 'PT141' in name_upper or 'BREMELANOTIDE' in name_upper:
        return 'PT-141'
    if 'MELANOTAN' in name_upper or 'MT-2' in name_upper or 'MT2' in name_upper:
        return 'Melanotan-II'
    if 'KISSPEPTIN' in name_upper:
        return 'Kisspeptin'
    
    # Altri comuni
    if 'DSIP' in name_upper:
        return 'DSIP'
    if 'HCG' in name_upper:
        return 'HCG'
    if 'IGF' in name_upper:
        return 'IGF-1'
    if 'GLOW' in name_upper:
        return 'GLOW'
    if 'SLU' in name_upper:
        return 'SLU-PP-332'
    if 'ENCLOMIPHENE' in name_upper:
        return 'Enclomiphene'
    if 'OXYTOCIN' in name_upper:
        return 'Oxytocin'
    if 'FRAGMENT' in name_upper:
        return 'HGH-Fragment'
    
    # Fallback: prima parola senza numeri e trattini
    # Rimuovi quantità (es. "10mg", "5 mg", "10 IU")
    clean = re.sub(r'\d+\s*(mg|mcg|iu|µg|g)\b', '', product_name, flags=re.IGNORECASE)
    # Rimuovi pipe e tutto dopo
    clean = clean.split('|')[0].strip()
    # Rimuovi descrizioni extra
    clean = re.sub(r'\s+(peptide|lyophilized|vial).*', '', clean, flags=re.IGNORECASE)
    # Prima parola
    first_word = clean.split()[0] if clean.split() else product_name
    # Rimuovi numeri trailing
    first_word = re.sub(r'\d+$', '', first_word)
    # Rimuovi trattini trailing
    first_word = first_word.rstrip('-')
    
    return first_word if first_word else None


def extract_quantity_and_unit(product_name: str) -> Tuple[Optional[float], Optional[str]]:
    """
    Estrae quantità nominale e unità di misura dal product_name.
    
    Args:
        product_name: Nome prodotto (es. "Tirzepatide 30mg")
        
    Returns:
        Tupla (quantity, unit) es. (30.0, "mg")
    """
    if not product_name:
        return None, None
    
    # Pattern per quantità + unità
    # Supporta: 10mg, 5 mg, 10IU, 10 IU, 500mcg, 500 mcg
    pattern = r'(\d+(?:\.\d+)?)\s*(mg|mcg|iu|µg|g)\b'
    match = re.search(pattern, product_name, re.IGNORECASE)
    
    if match:
        quantity = float(match.group(1))
        unit = match.group(2).lower()
        
        # Standardizza unità
        if unit in ['iu']:
            unit = 'IU'
        elif unit in ['mcg', 'µg']:
            unit = 'mcg'
        elif unit == 'g':
            unit = 'g'
        else:  # mg
            unit = 'mg'
        
        return quantity, unit
    
    return None, None


def backfill_peptide_fields():
    """Popola peptide_name_std, quantity_nominal, unit_of_measure"""
    env = get_environment()
    conn = sqlite3.connect(env.db_path)
    cursor = conn.cursor()
    
    print("=" * 70)
    print("🔄 BACKFILL: Standardized Peptide Fields")
    print("=" * 70)
    
    # Get all certificates
    cursor.execute("""
        SELECT id, product_name 
        FROM janoshik_certificates
        WHERE product_name IS NOT NULL
        ORDER BY id
    """)
    
    certificates = cursor.fetchall()
    total = len(certificates)
    
    print(f"\n📊 Certificati da processare: {total}")
    print("\n🔧 Processing...")
    
    updated = 0
    skipped = 0
    errors = []
    
    for cert_id, product_name in certificates:
        try:
            # Standardizza nome peptide
            peptide_std = standardize_peptide_name(product_name)
            
            # Estrai quantità e unità
            quantity, unit = extract_quantity_and_unit(product_name)
            
            # Update database
            cursor.execute("""
                UPDATE janoshik_certificates
                SET peptide_name_std = ?,
                    quantity_nominal = ?,
                    unit_of_measure = ?
                WHERE id = ?
            """, (peptide_std, quantity, unit, cert_id))
            
            updated += 1
            
            # Progress every 50
            if updated % 50 == 0:
                print(f"   ⏳ {updated}/{total} ({updated*100/total:.1f}%)")
        
        except Exception as e:
            skipped += 1
            errors.append(f"ID {cert_id} ({product_name}): {e}")
    
    conn.commit()
    
    print(f"\n✅ Backfill completato!")
    print(f"   📊 Total: {total}")
    print(f"   ✅ Updated: {updated}")
    print(f"   ⏭️  Skipped: {skipped}")
    
    if errors:
        print(f"\n⚠️  Errori ({len(errors)}):")
        for err in errors[:10]:  # Show first 10
            print(f"   - {err}")
        if len(errors) > 10:
            print(f"   ... e altri {len(errors)-10}")
    
    # Verify results
    print(f"\n📊 VERIFICA RISULTATI")
    print("=" * 70)
    
    cursor.execute("""
        SELECT 
            peptide_name_std,
            COUNT(*) as count,
            GROUP_CONCAT(DISTINCT unit_of_measure) as units
        FROM janoshik_certificates
        WHERE peptide_name_std IS NOT NULL
        GROUP BY peptide_name_std
        ORDER BY count DESC
        LIMIT 20
    """)
    
    print("\nTop 20 peptidi standardizzati:")
    print(f"{'Peptide':<20} {'Count':>7} {'Units':<15}")
    print("-" * 45)
    for row in cursor:
        print(f"{row[0]:<20} {row[1]:>7} {row[2] or 'N/A':<15}")
    
    # Sample con dettagli
    print(f"\n\n📋 SAMPLE (primi 20 certificati):")
    print("=" * 70)
    
    cursor.execute("""
        SELECT 
            id,
            product_name,
            peptide_name_std,
            quantity_nominal,
            unit_of_measure
        FROM janoshik_certificates
        ORDER BY id
        LIMIT 20
    """)
    
    print(f"{'ID':<5} {'Product Name':<35} {'Std Name':<15} {'Qty':>5} {'Unit':<5}")
    print("-" * 70)
    for row in cursor:
        qty_str = f"{row[3]:.1f}" if row[3] else "N/A"
        print(f"{row[0]:<5} {row[1][:35]:<35} {row[2] or 'N/A':<15} {qty_str:>5} {row[4] or 'N/A':<5}")
    
    conn.close()


if __name__ == "__main__":
    backfill_peptide_fields()
