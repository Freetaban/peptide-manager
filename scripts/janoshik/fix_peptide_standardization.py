"""
Fix standardizzazione nomi peptidi duplicati.
Risolve casi come: AOD/AOD-9604, GLP/GLP-2T/GLP-2TZ, etc.
"""

import sqlite3
import re

DB_PATH = "data/development/peptide_management.db"

# Regole di normalizzazione più aggressive
NORMALIZATION_RULES = {
    # AOD variants
    r'AOD[\s-]*9604': 'AOD-9604',
    r'^AOD$': 'AOD-9604',  # AOD da solo → AOD-9604
    
    # GLP variants
    r'GLP[\s-]*1': 'GLP-1',
    r'GLP[\s-]*2T?Z?': 'GLP-2',  # GLP-2T, GLP-2TZ → GLP-2
    
    # BPC variants
    r'BPC[\s-]*157': 'BPC-157',
    
    # TB variants
    r'TB[\s-]*500[\s-]*10\s*mg': 'TB-500',
    r'TB[\s-]*500': 'TB-500',
    
    # CJC variants
    r'CJC[\s-]*1295': 'CJC-1295',
    
    # GHK variants
    r'GHK[\s-]*Cu': 'GHK-Cu',
    
    # Rimuovi spazi extra e normalizza trattini
    r'\s+': ' ',
    r'\s*-\s*': '-',
}

def normalize_peptide_name(name: str) -> str:
    """Normalizza nome peptide con regole aggressive."""
    if not name:
        return name
    
    normalized = name.strip()
    
    # Applica regole in ordine
    for pattern, replacement in NORMALIZATION_RULES.items():
        normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
    
    return normalized.strip()

def fix_standardization():
    """Ri-standardizza tutti i peptide_name_std nel database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Ottieni tutti i certificati con peptide_name_std
    cursor.execute("""
        SELECT id, product_name, peptide_name_std 
        FROM janoshik_certificates 
        WHERE peptide_name_std IS NOT NULL AND peptide_name_std != ''
        ORDER BY peptide_name_std
    """)
    
    rows = cursor.fetchall()
    updates = []
    changes_map = {}
    
    print(f"🔍 Analizzando {len(rows)} certificati...")
    
    for cert_id, product_name, old_std in rows:
        # Ri-normalizza
        new_std = normalize_peptide_name(old_std)
        
        if new_std != old_std:
            updates.append((new_std, cert_id))
            if old_std not in changes_map:
                changes_map[old_std] = set()
            changes_map[old_std].add(new_std)
    
    if not updates:
        print("✅ Nessuna modifica necessaria!")
        conn.close()
        return
    
    print(f"\n📝 Trovate {len(updates)} normalizzazioni da applicare:\n")
    
    # Mostra cambiamenti
    for old_name, new_names in sorted(changes_map.items()):
        print(f"  '{old_name}' → {', '.join(sorted(new_names))}")
    
    # Conferma
    resp = input("\n⚠️  Applicare modifiche? (y/n): ")
    if resp.lower() != 'y':
        print("❌ Annullato")
        conn.close()
        return
    
    # Applica aggiornamenti
    cursor.executemany("""
        UPDATE janoshik_certificates 
        SET peptide_name_std = ?
        WHERE id = ?
    """, updates)
    
    conn.commit()
    
    # Statistiche finali
    cursor.execute("""
        SELECT peptide_name_std, COUNT(*) as cnt
        FROM janoshik_certificates
        WHERE peptide_name_std IS NOT NULL AND peptide_name_std != ''
        GROUP BY peptide_name_std
        ORDER BY cnt DESC, peptide_name_std
    """)
    
    print(f"\n✅ Aggiornati {len(updates)} certificati!")
    print("\n📊 Peptidi unici dopo normalizzazione:\n")
    
    for peptide, count in cursor.fetchall():
        print(f"  {peptide:25s} : {count:3d} certificati")
    
    conn.close()

if __name__ == "__main__":
    fix_standardization()
