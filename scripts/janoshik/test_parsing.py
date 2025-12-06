"""Test parsing logic with real data"""
import json

# Simula i 3 casi reali
test_cases = [
    {
        'name': 'Multi-vial (stesso peptide)',
        'task': '79432',
        'results': {
            "Retatrutide": "25.41 mg; 24.98 mg",
            "Purity": "99.798%; 99.782%"
        }
    },
    {
        'name': 'Single peptide',
        'task': '82282',
        'results': {
            "Retatrutide": "44.33 mg",
            "Purity": "99.720%"
        }
    },
    {
        'name': 'Multi-peptide mix',
        'task': '87708',
        'results': {
            "GHK-Cu": "71.36 mg",
            "BPC-157": "12.41 mg",
            "TB-500 (TB4)": "11.12 mg",
            "KPV": "11.75 mg"
        }
    }
]

def parse_certificate(results):
    """Replica la logica di from_extracted_data"""
    quantities = []
    purities = []
    
    for key, value in results.items():
        key_lower = key.lower()
        value_str = str(value)
        
        try:
            if 'purity' in key_lower:
                if ';' in value_str:
                    for part in value_str.split(';'):
                        clean = part.replace('%', '').strip()
                        purities.append(float(clean))
                else:
                    clean = value_str.replace('%', '').strip()
                    purities.append(float(clean))
            
            elif 'mg' in value_str.lower() and 'eu/mg' not in value_str.lower():
                if ';' in value_str:
                    for part in value_str.split(';'):
                        clean = part.replace('mg', '').strip()
                        quantities.append(float(clean))
                else:
                    clean = value_str.replace('mg', '').strip()
                    quantities.append(float(clean))
        
        except (ValueError, AttributeError) as e:
            print(f"  ERROR parsing '{key}': {value} -> {e}")
    
    # Conta peptidi distinti (escludi 'Purity' e 'Endotoxin')
    peptide_keys = [k for k in results.keys() 
                   if k.lower() not in ['purity', 'endotoxin'] 
                   and 'mg' in str(results[k]).lower()]
    num_distinct_peptides = len(peptide_keys)
    
    # Calcola purity con logica aggiornata
    if num_distinct_peptides > 1:
        # Multi-peptide mix: purity = None
        purity = None
    elif purities:
        # Single o multi-vial: calcola media
        purity = sum(purities) / len(purities)
    else:
        purity = None
    
    quantity = sum(quantities) if quantities else None
    
    return purity, quantity, num_distinct_peptides

print("="*80)
for case in test_cases:
    print(f"\n{case['name']} (Task #{case['task']})")
    print(f"  Raw results: {case['results']}")
    
    purity, quantity, num_peptides = parse_certificate(case['results'])
    
    print(f"  Parsed purity: {purity:.2f}%" if purity else "  Parsed purity: None")
    print(f"  Parsed quantity: {quantity:.2f} mg" if quantity else "  Parsed quantity: None")
    print(f"  Number of peptides: {num_peptides}")
    
    if num_peptides > 1:
        print(f"  ⚠️  MULTI-PEPTIDE MIX -> purity should be None")
    elif purity is None:
        print(f"  ❌ BUG: Single peptide but purity is None!")
    else:
        print(f"  ✅ OK")
