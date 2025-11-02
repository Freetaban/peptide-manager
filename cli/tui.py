"""
DOS-style TUI (Text User Interface) per Peptide Management System.
Interfaccia immersiva con menu numerati in stile MS-DOS.
"""

import os
import sys
from peptide_manager import PeptideManager
from datetime import datetime


def clear_screen():
    """Pulisce lo schermo."""
    os.system('cls' if os.name == 'nt' else 'clear')


def draw_box(title, width=78):
    """Disegna un box ASCII attorno al titolo."""
    print("╔" + "═" * (width - 2) + "╗")
    padding = (width - 2 - len(title)) // 2
    print("║" + " " * padding + title + " " * (width - 2 - padding - len(title)) + "║")
    print("╚" + "═" * (width - 2) + "╝")


def draw_header(title):
    """Header stile DOS."""
    clear_screen()
    print("═" * 80)
    print(f"  PEPTIDE MANAGEMENT SYSTEM v0.1.0 - {title}")
    print("═" * 80)
    print()


def pause(msg="Premi INVIO per continuare..."):
    """Pausa stile DOS."""
    input(f"\n{msg}")


def menu_choice(options, title="MENU"):
    """
    Mostra menu numerato e ritorna scelta.
    
    Args:
        options: Lista di tuple (label, callback_or_value)
        title: Titolo del menu
    """
    while True:
        draw_header(title)
        
        for i, (label, _) in enumerate(options, 1):
            print(f"  [{i}] {label}")
        
        print(f"\n  [0] Indietro / Esci")
        print("\n" + "─" * 80)
        
        try:
            choice = input("\n  Scelta: ").strip()
            
            if choice == '0':
                return 0
            
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                return idx + 1
            
            print("\n❌ Scelta non valida")
            pause()
        
        except (ValueError, KeyboardInterrupt):
            print("\n❌ Input non valido")
            pause()


# ============================================================
# MENU PEPTIDES
# ============================================================

def menu_peptides(manager):
    """Menu gestione peptidi."""
    while True:
        choice = menu_choice([
            ("Lista peptidi", None),
            ("Cerca peptide", None),
            ("Aggiungi peptide", None),
            ("Modifica peptide", None),
            ("Dettagli peptide", None),
            ("Trova duplicati", None),
            ("Elimina peptide", None),
        ], "GESTIONE PEPTIDI")
        
        if choice == 0:
            return
        elif choice == 1:
            list_peptides(manager)
        elif choice == 2:
            search_peptides(manager)
        elif choice == 3:
            add_peptide(manager)
        elif choice == 4:
            edit_peptide(manager)
        elif choice == 5:
            show_peptide(manager)
        elif choice == 6:
            find_duplicate_peptides(manager)
        elif choice == 7:
            delete_peptide(manager)


def list_peptides(manager):
    """Lista tutti i peptidi."""
    draw_header("CATALOGO PEPTIDI")
    
    peptides = manager.get_peptides()
    
    if not peptides:
        print("  Catalogo vuoto.\n")
        pause()
        return
    
    print(f"  Totale peptidi: {len(peptides)}\n")
    print("  " + "─" * 76)
    
    for p in peptides:
        print(f"  [#{p['id']:3}] {p['name']}")
        if p['description']:
            print(f"        {p['description'][:70]}")
    
    print("  " + "─" * 76)
    pause()


def show_peptide(manager):
    """Mostra dettagli peptide."""
    draw_header("DETTAGLI PEPTIDE")
    
    peptide_id = input("\n  ID Peptide: ").strip()
    
    try:
        peptide_id = int(peptide_id)
        peptide = manager.get_peptide_by_id(peptide_id)
        
        if not peptide:
            print("\n  ❌ Peptide non trovato")
            pause()
            return
        
        cursor = manager.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM batch_composition WHERE peptide_id = ?', (peptide_id,))
        batches = cursor.fetchone()[0]
        
        print("\n  " + "═" * 76)
        print(f"  ID: #{peptide['id']}")
        print(f"  Nome: {peptide['name']}")
        if peptide['description']:
            print(f"  Descrizione: {peptide['description']}")
        if peptide['common_uses']:
            print(f"  Usi: {peptide['common_uses']}")
        if peptide['notes']:
            print(f"  Note: {peptide['notes']}")
        print(f"\n  Presente in {batches} batches")
        print("  " + "═" * 76)
        
        pause()
    
    except ValueError:
        print("\n  ❌ ID non valido")
        pause()


def search_peptides(manager):
    """Cerca peptidi."""
    draw_header("CERCA PEPTIDI")
    
    query = input("\n  Termine di ricerca: ").strip()
    
    if not query:
        return
    
    results = manager.get_peptides(search=query)
    
    print(f"\n  Risultati per '{query}': {len(results)}\n")
    print("  " + "─" * 76)
    
    for p in results:
        print(f"  [#{p['id']:3}] {p['name']}")
        if p['description']:
            print(f"        {p['description'][:70]}")
    
    print("  " + "─" * 76)
    pause()


def add_peptide(manager):
    """Aggiungi peptide."""
    draw_header("NUOVO PEPTIDE")
    
    print("\n  Inserisci dati (INVIO per saltare campi opzionali):\n")
    
    name = input("  Nome: ").strip()
    if not name:
        print("\n  ❌ Nome obbligatorio")
        pause()
        return
    
    description = input("  Descrizione: ").strip()
    uses = input("  Usi comuni: ").strip()
    notes = input("  Note: ").strip()
    
    try:
        peptide_id = manager.add_peptide(
            name=name,
            description=description if description else None,
            common_uses=uses if uses else None,
            notes=notes if notes else None
        )
        
        print(f"\n  ✓ Peptide '{name}' aggiunto (ID: {peptide_id})")
        pause()
    
    except Exception as e:
        print(f"\n  ❌ Errore: {e}")
        pause()


def edit_peptide(manager):
    """Modifica peptide."""
    draw_header("MODIFICA PEPTIDE")
    
    peptide_id = input("\n  ID Peptide: ").strip()
    
    try:
        peptide_id = int(peptide_id)
        peptide = manager.get_peptide_by_id(peptide_id)
        
        if not peptide:
            print("\n  ❌ Peptide non trovato")
            pause()
            return
        
        print(f"\n  Peptide attuale: {peptide['name']}")
        print("\n  Nuovi valori (INVIO per mantenere):\n")
        
        new_name = input(f"  Nome [{peptide['name']}]: ").strip()
        new_desc = input(f"  Descrizione [{peptide['description'] or ''}]: ").strip()
        new_uses = input(f"  Usi [{peptide['common_uses'] or ''}]: ").strip()
        new_notes = input(f"  Note [{peptide['notes'] or ''}]: ").strip()
        
        changes = {}
        if new_name and new_name != peptide['name']:
            changes['name'] = new_name
        if new_desc != (peptide['description'] or ''):
            changes['description'] = new_desc if new_desc else None
        if new_uses != (peptide['common_uses'] or ''):
            changes['common_uses'] = new_uses if new_uses else None
        if new_notes != (peptide['notes'] or ''):
            changes['notes'] = new_notes if new_notes else None
        
        if not changes:
            print("\n  ⚠️  Nessuna modifica")
            pause()
            return
        
        confirm = input("\n  Confermare? (s/n): ").strip().lower()
        if confirm != 's':
            print("\n  Annullato")
            pause()
            return
        
        manager.update_peptide(peptide_id, **changes)
        print(f"\n  ✓ Peptide #{peptide_id} aggiornato")
        pause()
    
    except ValueError:
        print("\n  ❌ ID non valido")
        pause()
    except Exception as e:
        print(f"\n  ❌ Errore: {e}")
        pause()


def delete_peptide(manager):
    """Elimina peptide."""
    draw_header("ELIMINA PEPTIDE")
    
    peptide_id = input("\n  ID Peptide: ").strip()
    
    try:
        peptide_id = int(peptide_id)
        peptide = manager.get_peptide_by_id(peptide_id)
        
        if not peptide:
            print("\n  ❌ Peptide non trovato")
            pause()
            return
        
        print(f"\n  ⚠️  ELIMINA: #{peptide_id} - {peptide['name']}")
        confirm = input("\n  CONFERMARE ELIMINAZIONE? (s/n): ").strip().lower()
        
        if confirm != 's':
            print("\n  Annullato")
            pause()
            return
        
        success = manager.delete_peptide(peptide_id)
        if success:
            print(f"\n  ✓ Peptide #{peptide_id} eliminato")
        pause()
    
    except ValueError:
        print("\n  ❌ ID non valido")
        pause()
    except Exception as e:
        print(f"\n  ❌ Errore: {e}")
        pause()


def find_duplicate_peptides(manager):
    """Trova duplicati."""
    draw_header("TROVA DUPLICATI")
    
    from collections import defaultdict
    import re
    
    def normalize(name):
        name = name.strip().upper()
        name = re.sub(r'([A-Z]+)(\d+)', r'\1-\2', name)
        name = re.sub(r'\s+', '-', name)
        return re.sub(r'-+', '-', name)
    
    peptides = manager.get_peptides()
    groups = defaultdict(list)
    
    for p in peptides:
        normalized = normalize(p['name'])
        groups[normalized].append(p)
    
    duplicates = {k: v for k, v in groups.items() if len(v) > 1}
    
    if not duplicates:
        print("\n  ✓ Nessun duplicato trovato\n")
        pause()
        return
    
    print(f"\n  Gruppi duplicati: {len(duplicates)}\n")
    print("  " + "─" * 76)
    
    for norm, group in duplicates.items():
        print(f"\n  {norm}:")
        for p in group:
            print(f"    [#{p['id']:3}] {p['name']}")
    
    print("\n  " + "─" * 76)
    pause()


# ============================================================
# MENU BATCHES
# ============================================================

def menu_batches(manager):
    """Menu gestione batches."""
    while True:
        choice = menu_choice([
            ("Lista batches", None),
            ("Dettagli batch", None),
            ("Aggiungi batch", None),
            ("Usa fiale", None),
            ("Correggi fiale", None),
            ("Batches in scadenza", None),
            ("Elimina batch", None),
        ], "GESTIONE BATCHES")
        
        if choice == 0:
            return
        elif choice == 1:
            list_batches(manager)
        elif choice == 2:
            show_batch(manager)
        elif choice == 3:
            print("\n  Usa: peptide-manager batches add")
            pause()
        elif choice == 4:
            use_vials(manager)
        elif choice == 5:
            adjust_vials_tui(manager)
        elif choice == 6:
            expiring_batches(manager)
        elif choice == 7:
            delete_batch(manager)


def list_batches(manager):
    """Lista batches."""
    draw_header("INVENTARIO BATCHES")
    
    batches = manager.get_batches(only_available=True)
    
    if not batches:
        print("  Nessun batch disponibile.\n")
        pause()
        return
    
    print(f"  Batches disponibili: {len(batches)}\n")
    print("  " + "─" * 76)
    
    for b in batches:
        print(f"  [#{b['id']:3}] {b['product_name']}")
        print(f"        Fornitore: {b['supplier_name']}")
        print(f"        Fiale: {b['vials_remaining']}/{b['vials_count']} | Prezzo: {b['total_price']:.2f} {b['currency']}")
    
    print("  " + "─" * 76)
    pause()


def show_batch(manager):
    """Mostra dettagli batch."""
    draw_header("DETTAGLI BATCH")
    
    batch_id = input("\n  ID Batch: ").strip()
    
    try:
        batch_id = int(batch_id)
        batch = manager.get_batch_details(batch_id)
        
        if not batch:
            print("\n  ❌ Batch non trovato")
            pause()
            return
        
        print("\n  " + "═" * 76)
        print(f"  ID: #{batch['id']}")
        print(f"  Prodotto: {batch['product_name']}")
        print(f"  Fornitore: {batch['supplier_name']} ({batch['supplier_country']})")
        print(f"  Acquisto: {batch['purchase_date']} | Scadenza: {batch.get('expiry_date', 'N/A')}")
        print(f"  Fiale: {batch['vials_remaining']}/{batch['vials_count']}")
        print(f"  Prezzo: {batch['total_price']:.2f} {batch['currency']}")
        
        if batch.get('batch_number'):
            print(f"  Batch #: {batch['batch_number']}")
        if batch.get('storage_location'):
            print(f"  Storage: {batch['storage_location']}")
        
        print(f"\n  Composizione:")
        for comp in batch['composition']:
            print(f"    • {comp['name']}: {comp['mg_per_vial']}mg/fiala")
        
        if batch['certificates']:
            print(f"\n  Certificati: {len(batch['certificates'])}")
        
        if batch['preparations']:
            print(f"\n  Preparazioni: {len(batch['preparations'])}")
        
        print("  " + "═" * 76)
        pause()
    
    except ValueError:
        print("\n  ❌ ID non valido")
        pause()


def use_vials(manager):
    """Usa fiale."""
    draw_header("USA FIALE")
    
    batch_id = input("\n  ID Batch: ").strip()
    
    try:
        batch_id = int(batch_id)
        batch = manager.get_batch_details(batch_id)
        
        if not batch:
            print("\n  ❌ Batch non trovato")
            pause()
            return
        
        print(f"\n  Batch: {batch['product_name']}")
        print(f"  Fiale disponibili: {batch['vials_remaining']}")
        
        count = input("\n  Fiale da usare: ").strip()
        count = int(count)
        
        confirm = input(f"\n  Usare {count} fiala/e? (s/n): ").strip().lower()
        if confirm != 's':
            print("\n  Annullato")
            pause()
            return
        
        success = manager.use_vials(batch_id, count)
        if success:
            print(f"\n  ✓ {count} fiala/e utilizzate")
        pause()
    
    except ValueError:
        print("\n  ❌ Input non valido")
        pause()


def adjust_vials_tui(manager):
    """Correggi fiale."""
    draw_header("CORREZIONE FIALE")
    
    batch_id = input("\n  ID Batch: ").strip()
    
    try:
        batch_id = int(batch_id)
        batch = manager.get_batch_details(batch_id)
        
        if not batch:
            print("\n  ❌ Batch non trovato")
            pause()
            return
        
        print(f"\n  Batch: {batch['product_name']}")
        print(f"  Fiale attuali: {batch['vials_remaining']}/{batch['vials_count']}")
        
        adjustment = input("\n  Aggiustamento (+/-): ").strip()
        adjustment = int(adjustment)
        
        reason = input("  Motivo: ").strip()
        
        new_total = batch['vials_remaining'] + adjustment
        print(f"\n  Nuovo totale: {new_total} fiale")
        
        confirm = input("\n  Confermare? (s/n): ").strip().lower()
        if confirm != 's':
            print("\n  Annullato")
            pause()
            return
        
        success = manager.adjust_vials(batch_id, adjustment, reason if reason else None)
        if success:
            print(f"\n  ✓ Correzione applicata")
        pause()
    
    except ValueError:
        print("\n  ❌ Input non valido")
        pause()


def expiring_batches(manager):
    """Batches in scadenza."""
    draw_header("BATCHES IN SCADENZA")
    
    cursor = manager.conn.cursor()
    cursor.execute('''
        SELECT b.id, b.product_name, b.expiry_date, b.vials_remaining
        FROM batches b
        WHERE b.expiry_date IS NOT NULL
        AND b.expiry_date <= date('now', '+60 days')
        AND b.vials_remaining > 0
        ORDER BY b.expiry_date
    ''')
    
    expiring = cursor.fetchall()
    
    if not expiring:
        print("\n  ✓ Nessun batch in scadenza (60 giorni)\n")
        pause()
        return
    
    print(f"\n  Batches in scadenza: {len(expiring)}\n")
    print("  " + "─" * 76)
    
    for batch_id, product, expiry, vials in expiring:
        exp_date = datetime.strptime(expiry, '%Y-%m-%d')
        days_left = (exp_date - datetime.now()).days
        
        urgency = '🔴' if days_left < 30 else '🟡'
        print(f"  {urgency} [#{batch_id:3}] {product}")
        print(f"       Scadenza: {expiry} (tra {days_left} giorni)")
        print(f"       Fiale: {vials}")
    
    print("  " + "─" * 76)
    pause()


def delete_batch(manager):
    """Elimina batch."""
    draw_header("ELIMINA BATCH")
    
    batch_id = input("\n  ID Batch: ").strip()
    
    try:
        batch_id = int(batch_id)
        batch = manager.get_batch_details(batch_id)
        
        if not batch:
            print("\n  ❌ Batch non trovato")
            pause()
            return
        
        print(f"\n  ⚠️  ELIMINA: #{batch_id} - {batch['product_name']}")
        if batch['preparations']:
            print(f"\n  ATTENZIONE: {len(batch['preparations'])} preparazioni saranno eliminate!")
        
        confirm = input("\n  CONFERMARE ELIMINAZIONE? (s/n): ").strip().lower()
        
        if confirm != 's':
            print("\n  Annullato")
            pause()
            return
        
        success = manager.delete_batch(batch_id, force=True)
        if success:
            print(f"\n  ✓ Batch #{batch_id} eliminato")
        pause()
    
    except ValueError:
        print("\n  ❌ ID non valido")
        pause()


# ============================================================
# MENU PREPARATIONS
# ============================================================

def menu_preparations(manager):
    """Menu preparazioni."""
    while True:
        choice = menu_choice([
            ("Lista preparazioni", None),
            ("Dettagli preparazione", None),
            ("Nuova preparazione", None),
            ("Registra somministrazione", None),
            ("Preparazioni scadute", None),
            ("Elimina preparazione", None),
        ], "GESTIONE PREPARAZIONI")
        
        if choice == 0:
            return
        elif choice == 1:
            list_preparations(manager)
        elif choice == 2:
            show_preparation(manager)
        elif choice == 3:
            print("\n  Usa: peptide-manager preparations add")
            pause()
        elif choice == 4:
            print("\n  Usa: peptide-manager preparations use <id>")
            pause()
        elif choice == 5:
            expired_preparations(manager)
        elif choice == 6:
            delete_preparation(manager)


def list_preparations(manager):
    """Lista preparazioni."""
    draw_header("PREPARAZIONI ATTIVE")
    
    preps = manager.get_preparations(only_active=True)
    
    if not preps:
        print("  Nessuna preparazione attiva.\n")
        pause()
        return
    
    print(f"  Preparazioni: {len(preps)}\n")
    print("  " + "─" * 76)
    
    for p in preps:
        percentage = (p['volume_remaining_ml'] / p['volume_ml'] * 100) if p['volume_ml'] > 0 else 0
        print(f"  [#{p['id']:3}] {p['batch_product']}")
        print(f"        Volume: {p['volume_remaining_ml']:.1f}ml/{p['volume_ml']}ml ({percentage:.0f}%)")
        print(f"        Scadenza: {p['expiry_date'] or 'N/A'}")
    
    print("  " + "─" * 76)
    pause()


def show_preparation(manager):
    """Mostra preparazione."""
    draw_header("DETTAGLI PREPARAZIONE")
    
    prep_id = input("\n  ID Preparazione: ").strip()
    
    try:
        prep_id = int(prep_id)
        prep = manager.get_preparation_details(prep_id)
        
        if not prep:
            print("\n  ❌ Preparazione non trovata")
            pause()
            return
        
        print("\n  " + "═" * 76)
        print(f"  ID: #{prep['id']}")
        print(f"  Batch: {prep['product_name']}")
        print(f"  Data: {prep['preparation_date']} | Scadenza: {prep['expiry_date']}")
        print(f"  Volume: {prep['volume_remaining_ml']:.1f}ml / {prep['volume_ml']}ml")
        print(f"  Concentrazione: {prep['concentration_mg_ml']:.3f}mg/ml ({prep['concentration_mg_ml']*1000:.1f}mcg/ml)")
        print(f"  Fiale usate: {prep['vials_used']}")
        print(f"  Diluente: {prep['diluent']}")
        if prep['storage_location']:
            print(f"  Storage: {prep['storage_location']}")
        print(f"\n  Somministrazioni: {prep['administrations_count']}")
        print("  " + "═" * 76)
        pause()
    
    except ValueError:
        print("\n  ❌ ID non valido")
        pause()


def expired_preparations(manager):
    """Preparazioni scadute."""
    draw_header("PREPARAZIONI SCADUTE")
    
    expired = manager.get_expired_preparations()
    
    if not expired:
        print("\n  ✓ Nessuna preparazione scaduta\n")
        pause()
        return
    
    print(f"\n  Preparazioni scadute: {len(expired)}\n")
    print("  " + "─" * 76)
    
    for p in expired:
        days_expired = (datetime.now() - datetime.strptime(p['expiry_date'], '%Y-%m-%d')).days
        print(f"  [#{p['id']:3}] {p['product_name']}")
        print(f"        Scaduta: {p['expiry_date']} ({days_expired} giorni fa)")
        print(f"        Volume: {p['volume_remaining_ml']:.1f}ml")
    
    print("  " + "─" * 76)
    pause()


def delete_preparation(manager):
    """Elimina preparazione."""
    draw_header("ELIMINA PREPARAZIONE")
    
    prep_id = input("\n  ID Preparazione: ").strip()
    
    try:
        prep_id = int(prep_id)
        prep = manager.get_preparation_details(prep_id)
        
        if not prep:
            print("\n  ❌ Preparazione non trovata")
            pause()
            return
        
        print(f"\n  ⚠️  ELIMINA: #{prep_id} - {prep['product_name']}")
        print(f"  Somministrazioni: {prep['administrations_count']}")
        
        restore = input("\n  Ripristinare fiale al batch? (s/n): ").strip().lower()
        
        confirm = input("\n  CONFERMARE ELIMINAZIONE? (s/n): ").strip().lower()
        
        if confirm != 's':
            print("\n  Annullato")
            pause()
            return
        
        success = manager.delete_preparation(prep_id, restore_vials=(restore == 's'))
        if success:
            print(f"\n  ✓ Preparazione #{prep_id} eliminata")
        pause()
    
    except ValueError:
        print("\n  ❌ ID non valido")
        pause()


# ============================================================
# MENU PROTOCOLS
# ============================================================

def menu_protocols(manager):
    """Menu protocolli."""
    while True:
        choice = menu_choice([
            ("Lista protocolli", None),
            ("Dettagli protocollo", None),
            ("Nuovo protocollo", None),
            ("Attiva/Disattiva", None),
            ("Statistiche", None),
            ("Elimina protocollo", None),
        ], "GESTIONE PROTOCOLLI")
        
        if choice == 0:
            return
        elif choice == 1:
            list_protocols(manager)
        elif choice == 2:
            show_protocol(manager)
        elif choice == 3:
            print("\n  Usa: peptide-manager protocols add")
            pause()
        elif choice == 4:
            toggle_protocol(manager)
        elif choice == 5:
            protocol_stats(manager)
        elif choice == 6:
            delete_protocol(manager)


def list_protocols(manager):
    """Lista protocolli."""
    draw_header("PROTOCOLLI")
    
    protos = manager.get_protocols(active_only=False)
    
    if not protos:
        print("  Nessun protocollo.\n")
        pause()
        return
    
    print(f"  Protocolli: {len(protos)}\n")
    print("  " + "─" * 76)
    
    for p in protos:
        status = '✓' if p['active'] else '✗'
        print(f"  [{status}] [#{p['id']:3}] {p['name']}")
        print(f"        Dose: {p['dose_ml']}ml x {p['frequency_per_day']}/giorno")
        if p['days_on']:
            print(f"        Schema: {p['days_on']} ON, {p['days_off']} OFF")
    
    print("  " + "─" * 76)
    pause()


def show_protocol(manager):
    """Mostra protocollo."""
    draw_header("DETTAGLI PROTOCOLLO")
    
    protocol_id = input("\n  ID Protocollo: ").strip()
    
    try:
        protocol_id = int(protocol_id)
        protocol = manager.get_protocol_details(protocol_id)
        
        if not protocol:
            print("\n  ❌ Protocollo non trovato")
            pause()
            return
        
        status = '✓ ATTIVO' if protocol['active'] else '✗ DISATTIVATO'
        
        print("\n  " + "═" * 76)
        print(f"  ID: #{protocol['id']}")
        print(f"  Nome: {protocol['name']} [{status}]")
        if protocol['description']:
            print(f"  Descrizione: {protocol['description']}")
        print(f"\n  Dosaggio: {protocol['dose_ml']}ml x {protocol['frequency_per_day']}/giorno")
        if protocol['days_on']:
            print(f"  Schema: {protocol['days_on']} ON, {protocol['days_off']} OFF")
        if protocol['cycle_duration_weeks']:
            print(f"  Durata: {protocol['cycle_duration_weeks']} settimane")
        
        if protocol['peptides']:
            print(f"\n  Peptidi:")
            for pep in protocol['peptides']:
                print(f"    • {pep['name']}: {pep['target_dose_mcg']}mcg")
        
        if protocol['administrations_count'] > 0:
            print(f"\n  Somministrazioni: {protocol['administrations_count']}")
        
        print("  " + "═" * 76)
        pause()
    
    except ValueError:
        print("\n  ❌ ID non valido")
        pause()


def toggle_protocol(manager):
    """Attiva/disattiva protocollo."""
    draw_header("ATTIVA/DISATTIVA PROTOCOLLO")
    
    protocol_id = input("\n  ID Protocollo: ").strip()
    
    try:
        protocol_id = int(protocol_id)
        protocol = manager.get_protocol_details(protocol_id)
        
        if not protocol:
            print("\n  ❌ Protocollo non trovato")
            pause()
            return
        
        current_status = "ATTIVO" if protocol['active'] else "DISATTIVATO"
        new_status = not protocol['active']
        new_status_text = "ATTIVO" if new_status else "DISATTIVATO"
        
        print(f"\n  Protocollo: {protocol['name']}")
        print(f"  Stato attuale: {current_status}")
        print(f"  Nuovo stato: {new_status_text}")
        
        confirm = input("\n  Confermare? (s/n): ").strip().lower()
        if confirm != 's':
            print("\n  Annullato")
            pause()
            return
        
        if new_status:
            manager.activate_protocol(protocol_id)
        else:
            manager.deactivate_protocol(protocol_id)
        
        print(f"\n  ✓ Protocollo {new_status_text.lower()}")
        pause()
    
    except ValueError:
        print("\n  ❌ ID non valido")
        pause()


def protocol_stats(manager):
    """Statistiche protocollo."""
    draw_header("STATISTICHE PROTOCOLLO")
    
    protocol_id = input("\n  ID Protocollo: ").strip()
    
    try:
        protocol_id = int(protocol_id)
        protocol = manager.get_protocol_details(protocol_id)
        
        if not protocol:
            print("\n  ❌ Protocollo non trovato")
            pause()
            return
        
        stats = manager.get_protocol_statistics(protocol_id)
        
        print("\n  " + "═" * 76)
        print(f"  Protocollo: {protocol['name']}")
        
        if stats['total_administrations'] == 0:
            print("\n  Nessuna somministrazione")
            print("  " + "═" * 76)
            pause()
            return
        
        print(f"\n  Periodo: {stats['first_date']} → {stats['last_date']}")
        print(f"  Giorni: {stats['days_active']} attivi / {stats['days_elapsed']} totali")
        print(f"  Somministrazioni: {stats['total_administrations']} / {stats['expected_administrations']}")
        print(f"  Volume: {stats['total_ml_used']:.2f}ml")
        
        adherence = stats['adherence_percentage']
        icon = '✓' if adherence >= 80 else '⚠️' if adherence >= 60 else '❌'
        print(f"\n  Aderenza: {icon} {adherence}%")
        
        print("  " + "═" * 76)
        pause()
    
    except ValueError:
        print("\n  ❌ ID non valido")
        pause()


def delete_protocol(manager):
    """Elimina protocollo."""
    draw_header("ELIMINA PROTOCOLLO")
    
    protocol_id = input("\n  ID Protocollo: ").strip()
    
    try:
        protocol_id = int(protocol_id)
        protocol = manager.get_protocol_details(protocol_id)
        
        if not protocol:
            print("\n  ❌ Protocollo non trovato")
            pause()
            return
        
        print(f"\n  ⚠️  ELIMINA: #{protocol_id} - {protocol['name']}")
        if protocol['administrations_count'] > 0:
            print(f"  Somministrazioni: {protocol['administrations_count']} (saranno scollegate)")
        
        confirm = input("\n  CONFERMARE ELIMINAZIONE? (s/n): ").strip().lower()
        
        if confirm != 's':
            print("\n  Annullato")
            pause()
            return
        
        success = manager.delete_protocol(protocol_id, unlink_administrations=True)
        if success:
            print(f"\n  ✓ Protocollo #{protocol_id} eliminato")
        pause()
    
    except ValueError:
        print("\n  ❌ ID non valido")
        pause()


# ============================================================
# MENU SUPPLIERS
# ============================================================

def menu_suppliers(manager):
    """Menu fornitori."""
    while True:
        choice = menu_choice([
            ("Lista fornitori", None),
            ("Dettagli fornitore", None),
            ("Aggiungi fornitore", None),
            ("Modifica fornitore", None),
            ("Statistiche fornitori", None),
            ("Elimina fornitore", None),
        ], "GESTIONE FORNITORI")
        
        if choice == 0:
            return
        elif choice == 1:
            list_suppliers(manager)
        elif choice == 2:
            show_supplier(manager)
        elif choice == 3:
            add_supplier(manager)
        elif choice == 4:
            edit_supplier(manager)
        elif choice == 5:
            supplier_stats(manager)
        elif choice == 6:
            delete_supplier(manager)


def list_suppliers(manager):
    """Lista fornitori."""
    draw_header("FORNITORI")
    
    suppliers = manager.get_suppliers()
    
    if not suppliers:
        print("  Nessun fornitore.\n")
        pause()
        return
    
    print(f"  Fornitori: {len(suppliers)}\n")
    print("  " + "─" * 76)
    
    for s in suppliers:
        stars = '★' * (s['reliability_rating'] or 0)
        print(f"  [#{s['id']:3}] {s['name']} ({s['country'] or 'N/A'})")
        if s['reliability_rating']:
            print(f"        Rating: {stars} ({s['reliability_rating']}/5)")
    
    print("  " + "─" * 76)
    pause()


def show_supplier(manager):
    """Dettagli fornitore."""
    draw_header("DETTAGLI FORNITORE")
    
    supplier_id = input("\n  ID Fornitore: ").strip()
    
    try:
        supplier_id = int(supplier_id)
        suppliers = manager.get_suppliers()
        supplier = next((s for s in suppliers if s['id'] == supplier_id), None)
        
        if not supplier:
            print("\n  ❌ Fornitore non trovato")
            pause()
            return
        
        cursor = manager.conn.cursor()
        cursor.execute('''
            SELECT COUNT(*), SUM(total_price), SUM(vials_count), SUM(vials_remaining)
            FROM batches WHERE supplier_id = ?
        ''', (supplier_id,))
        
        total_orders, total_spent, total_vials, vials_left = cursor.fetchone()
        stars = '★' * (supplier['reliability_rating'] or 0)
        
        print("\n  " + "═" * 76)
        print(f"  ID: #{supplier['id']}")
        print(f"  Nome: {supplier['name']}")
        print(f"  Paese: {supplier['country'] or 'N/A'}")
        if supplier['website']:
            print(f"  Website: {supplier['website']}")
        if supplier['reliability_rating']:
            print(f"  Rating: {stars} ({supplier['reliability_rating']}/5)")
        
        print(f"\n  Statistiche:")
        print(f"    Ordini: {total_orders or 0}")
        print(f"    Spesa: {total_spent or 0:.2f} EUR")
        print(f"    Fiale: {total_vials or 0} (rimaste: {vials_left or 0})")
        
        print("  " + "═" * 76)
        pause()
    
    except ValueError:
        print("\n  ❌ ID non valido")
        pause()


def add_supplier(manager):
    """Aggiungi fornitore."""
    draw_header("NUOVO FORNITORE")
    
    print("\n  Inserisci dati:\n")
    
    name = input("  Nome: ").strip()
    if not name:
        print("\n  ❌ Nome obbligatorio")
        pause()
        return
    
    country = input("  Paese: ").strip()
    website = input("  Website: ").strip()
    email = input("  Email: ").strip()
    rating = input("  Rating (1-5): ").strip()
    notes = input("  Note: ").strip()
    
    try:
        rating = int(rating) if rating else 3
        
        supplier_id = manager.add_supplier(
            name=name,
            country=country if country else None,
            website=website if website else None,
            email=email if email else None,
            rating=rating,
            notes=notes if notes else None
        )
        
        print(f"\n  ✓ Fornitore '{name}' aggiunto (ID: {supplier_id})")
        pause()
    
    except Exception as e:
        print(f"\n  ❌ Errore: {e}")
        pause()


def edit_supplier(manager):
    """Modifica fornitore."""
    draw_header("MODIFICA FORNITORE")
    
    supplier_id = input("\n  ID Fornitore: ").strip()
    
    try:
        supplier_id = int(supplier_id)
        suppliers = manager.get_suppliers()
        supplier = next((s for s in suppliers if s['id'] == supplier_id), None)
        
        if not supplier:
            print("\n  ❌ Fornitore non trovato")
            pause()
            return
        
        print(f"\n  Fornitore: {supplier['name']}")
        print("\n  Nuovi valori (INVIO per mantenere):\n")
        
        new_name = input(f"  Nome [{supplier['name']}]: ").strip()
        new_country = input(f"  Paese [{supplier['country'] or ''}]: ").strip()
        new_website = input(f"  Website [{supplier['website'] or ''}]: ").strip()
        new_email = input(f"  Email [{supplier['email'] or ''}]: ").strip()
        new_rating = input(f"  Rating [{supplier['reliability_rating'] or 3}]: ").strip()
        new_notes = input(f"  Note [{supplier['notes'] or ''}]: ").strip()
        
        changes = {}
        if new_name and new_name != supplier['name']:
            changes['name'] = new_name
        if new_country != (supplier['country'] or ''):
            changes['country'] = new_country if new_country else None
        if new_website != (supplier['website'] or ''):
            changes['website'] = new_website if new_website else None
        if new_email != (supplier['email'] or ''):
            changes['email'] = new_email if new_email else None
        if new_rating and new_rating != str(supplier['reliability_rating'] or 3):
            changes['reliability_rating'] = int(new_rating)
        if new_notes != (supplier['notes'] or ''):
            changes['notes'] = new_notes if new_notes else None
        
        if not changes:
            print("\n  ⚠️  Nessuna modifica")
            pause()
            return
        
        confirm = input("\n  Confermare? (s/n): ").strip().lower()
        if confirm != 's':
            print("\n  Annullato")
            pause()
            return
        
        manager.update_supplier(supplier_id, **changes)
        print(f"\n  ✓ Fornitore #{supplier_id} aggiornato")
        pause()
    
    except ValueError:
        print("\n  ❌ Input non valido")
        pause()


def supplier_stats(manager):
    """Statistiche fornitori."""
    draw_header("STATISTICHE FORNITORI")
    
    cursor = manager.conn.cursor()
    cursor.execute('''
        SELECT 
            s.id, s.name, s.reliability_rating,
            COUNT(b.id) as orders,
            SUM(b.total_price) as total_spent
        FROM suppliers s
        LEFT JOIN batches b ON s.id = b.supplier_id
        GROUP BY s.id
        ORDER BY total_spent DESC
    ''')
    
    stats = cursor.fetchall()
    
    if not stats:
        print("\n  Nessun fornitore.\n")
        pause()
        return
    
    print(f"\n  {len(stats)} fornitori\n")
    print("  " + "─" * 76)
    
    for sid, name, rating, orders, spent in stats:
        stars = '★' * (rating or 0) if rating else 'N/A'
        print(f"  [#{sid:3}] {name}")
        print(f"        Rating: {stars} | Ordini: {orders or 0} | Spesa: {spent or 0:.2f} EUR")
    
    print("  " + "─" * 76)
    pause()


def delete_supplier(manager):
    """Elimina fornitore."""
    draw_header("ELIMINA FORNITORE")
    
    supplier_id = input("\n  ID Fornitore: ").strip()
    
    try:
        supplier_id = int(supplier_id)
        suppliers = manager.get_suppliers()
        supplier = next((s for s in suppliers if s['id'] == supplier_id), None)
        
        if not supplier:
            print("\n  ❌ Fornitore non trovato")
            pause()
            return
        
        print(f"\n  ⚠️  ELIMINA: #{supplier_id} - {supplier['name']}")
        
        confirm = input("\n  CONFERMARE ELIMINAZIONE? (s/n): ").strip().lower()
        
        if confirm != 's':
            print("\n  Annullato")
            pause()
            return
        
        success = manager.delete_supplier(supplier_id)
        if success:
            print(f"\n  ✓ Fornitore #{supplier_id} eliminato")
        pause()
    
    except ValueError:
        print("\n  ❌ ID non valido")
        pause()


# ============================================================
# MAIN MENU
# ============================================================

def main_menu(manager):
    """Menu principale."""
    while True:
        summary = manager.get_inventory_summary()
        
        draw_header("MENU PRINCIPALE")
        
        print(f"  Database: peptide_management.db")
        print(f"  Batches: {summary['available_batches']}/{summary['total_batches']} disponibili")
        print(f"  Valore: €{summary['total_value']:.2f}")
        if summary['expiring_soon'] > 0:
            print(f"  ⚠️  {summary['expiring_soon']} batches in scadenza")
        print()
        
        choice = menu_choice([
            ("Gestione Peptidi", None),
            ("Gestione Fornitori", None),
            ("Gestione Batches", None),
            ("Gestione Preparazioni", None),
            ("Gestione Protocolli", None),
            ("Inventario Completo", None),
            ("Riepilogo Sistema", None),
        ], "MENU PRINCIPALE")
        
        if choice == 0:
            clear_screen()
            print("\n  Arrivederci!\n")
            break
        elif choice == 1:
            menu_peptides(manager)
        elif choice == 2:
            menu_suppliers(manager)
        elif choice == 3:
            menu_batches(manager)
        elif choice == 4:
            menu_preparations(manager)
        elif choice == 5:
            menu_protocols(manager)
        elif choice == 6:
            draw_header("INVENTARIO")
            manager.print_inventory(detailed=False)
            pause()
        elif choice == 7:
            draw_header("RIEPILOGO")
            print(f"\n  Batches: {summary['total_batches']} ({summary['available_batches']} disponibili)")
            print(f"  Peptidi: {summary['unique_peptides']}")
            print(f"  Valore: €{summary['total_value']:.2f}")
            if summary['expiring_soon'] > 0:
                print(f"  ⚠️  Scadenza: {summary['expiring_soon']} batches")
            pause()


# ============================================================
# ENTRY POINT
# ============================================================

def start_tui(db_path='peptide_management.db'):
    """Avvia TUI."""
    try:
        manager = PeptideManager(db_path)
        main_menu(manager)
        manager.close()
    except KeyboardInterrupt:
        clear_screen()
        print("\n  Interrotto dall'utente\n")
    except Exception as e:
        clear_screen()
        print(f"\n  ❌ Errore: {e}\n")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    start_tui()
