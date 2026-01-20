"""Verifica che le ottimizzazioni della tabella storico siano state applicate correttamente."""
import re

def check_file_optimizations(filepath):
    """Verifica le ottimizzazioni in un file."""
    print(f"\n🔍 Controllo file: {filepath}")
    print("="*60)
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = {
        "✅ Rimossi limiti caratteri peptide_names": r"peptide_names'\]\)(?!\[:)",
        "✅ Rimossi limiti caratteri batch_product": r"batch_product'\]\)(?!\[:)",
        "✅ Rimossi limiti caratteri preparation_display": r"preparation_display'\]\)(?!\[:)",
        "✅ Rimossi limiti caratteri injection_site": r"injection_site'\]\)(?!\[:)",
        "✅ Rimossi limiti caratteri injection_method": r"injection_method'\]\)(?!\[:)",
        "✅ Rimossi limiti caratteri protocol_name": r"protocol_name'\]\)(?!\[:)",
        "✅ Column spacing aumentato (10)": r"column_spacing=10",
        "✅ Horizontal margin aumentato (10)": r"horizontal_margin=10",
        "✅ results_container expand": r"results_container = ft\.Container\(expand=True\)",
        "✅ Column finale expand": r"scroll=ft\.ScrollMode\.AUTO, expand=True\)",
        "✅ Tabella in Row con scroll": r"ft\.Row\(\[\s*table_content",
    }
    
    results = []
    for check_name, pattern in checks.items():
        if re.search(pattern, content):
            print(f"  {check_name}")
            results.append(True)
        else:
            print(f"  ❌ {check_name.replace('✅ ', '')}")
            results.append(False)
    
    passed = sum(results)
    total = len(results)
    print(f"\n📊 Risultato: {passed}/{total} verifiche passate")
    
    return passed == total

# Verifica entrambi i file
files_to_check = [
    r"c:\Users\ftaba\source\peptide-management-system\gui_modular\views\administrations.py",
    r"c:\Users\ftaba\source\peptide-management-system\gui.py"
]

all_passed = True
for filepath in files_to_check:
    try:
        passed = check_file_optimizations(filepath)
        all_passed = all_passed and passed
    except FileNotFoundError:
        print(f"⚠️  File non trovato: {filepath}")
        all_passed = False
    except Exception as e:
        print(f"❌ Errore durante verifica: {e}")
        all_passed = False

print("\n" + "="*60)
if all_passed:
    print("✅ TUTTE LE OTTIMIZZAZIONI SONO STATE APPLICATE CORRETTAMENTE!")
else:
    print("⚠️  Alcune verifiche non sono passate. Rivedi le modifiche.")
print("="*60)
