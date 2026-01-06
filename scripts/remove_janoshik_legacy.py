"""Script per rimuovere blocco legacy Janoshik da gui.py"""

def remove_janoshik_block():
    """Rimuove righe 1975-3345 (blocco Janoshik) da gui.py"""
    gui_path = "gui.py"
    
    # Leggi tutto
    with open(gui_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    total_lines = len(lines)
    print(f"📄 gui.py: {total_lines} righe")
    
    # Verifica markers
    start_marker_found = False
    end_marker_found = False
    
    # Cerca "# JANOSHIK MARKET" circa riga 1975
    for i in range(1970, 1980):
        if "# JANOSHIK MARKET" in lines[i]:
            start_idx = i - 2  # Include anche linea vuota e separatore prima
            start_marker_found = True
            print(f"✅ Trovato inizio blocco Janoshik a riga {i+1}")
            break
    
    # Cerca "def start_gui" circa riga 3346
    for i in range(3340, 3350):
        if i < len(lines) and lines[i].strip().startswith("def start_gui"):
            end_idx = i  # Non includere start_gui
            end_marker_found = True
            print(f"✅ Trovato start_gui a riga {i+1}")
            break
    
    if not (start_marker_found and end_marker_found):
        print("❌ Marker non trovati!")
        return False
    
    # Calcola righe da rimuovere
    lines_to_remove = end_idx - start_idx
    print(f"🗑️  Rimuovo righe {start_idx+1} - {end_idx} ({lines_to_remove} righe)")
    
    # Crea nuovo contenuto
    new_lines = lines[:start_idx] + lines[end_idx:]
    new_total = len(new_lines)
    
    print(f"📝 Nuovo file: {new_total} righe (rimosso {total_lines - new_total} righe)")
    
    # Scrivi
    with open(gui_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    print(f"✅ File aggiornato!")
    return True

if __name__ == "__main__":
    import sys
    if remove_janoshik_block():
        sys.exit(0)
    else:
        sys.exit(1)
