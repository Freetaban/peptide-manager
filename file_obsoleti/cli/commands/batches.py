"""
Comandi per gestione batches/acquisti.
"""

import click
from peptide_manager import PeptideManager
from datetime import datetime


@click.group()
def batches():
    """
    Gestione batch e acquisti.
    
    \b
    Comandi disponibili:
      list      Lista batch disponibili
      add       Registra nuovo acquisto (wizard)
      edit      Modifica batch esistente
      show      Dettagli completi batch
      use       Usa fiale da batch
      search    Cerca batch con filtri
      expiring  Batch in scadenza
    """
    pass


@batches.command('list')
@click.option('--available/--all', default=True, help='Solo batch con fiale disponibili')
@click.option('--db', default='peptide_management.db', hidden=True)
def list_batches(available, db):
    """Lista tutti i batch nell'inventario."""
    manager = PeptideManager(db)
    
    try:
        results = manager.get_batches(only_available=available)
        
        if not results:
            click.echo("Nessun batch trovato.")
            return
        
        click.echo(f"\n{'='*80}")
        status = "DISPONIBILI" if available else "TUTTI"
        click.echo(f"BATCHES {status} ({len(results)})")
        click.echo(f"{'='*80}\n")
        
        for batch in results:
            click.echo(f"[#{batch['id']}] {batch['product_name']}")
            click.echo(f"  Fornitore: {batch['supplier_name']}")
            click.echo(f"  Fiale: {batch['vials_remaining']}/{batch['vials_count']}")
            click.echo(f"  Prezzo: {batch['total_price']:.2f} {batch['currency']}")
            click.echo()
    finally:
        manager.close()


@batches.command('add')
@click.option('--db', default='peptide_management.db', hidden=True)
def add_batch(db):
    """Registra un nuovo acquisto (wizard interattivo completo)."""
    add_batch_interactive(db)


@batches.command('show')
@click.argument('batch_id', type=int)
@click.option('--db', default='peptide_management.db', hidden=True)
def show_batch(batch_id, db):
    """Mostra dettagli completi di un batch."""
    manager = PeptideManager(db)
    
    try:
        batch = manager.get_batch_details(batch_id)
        
        if not batch:
            click.echo(f"❌ Batch #{batch_id} non trovato", err=True)
            return
        
        click.echo(f"\n{'='*80}")
        click.echo(f"BATCH #{batch_id}: {batch['product_name']}")
        click.echo(f"{'='*80}")
        click.echo(f"Fornitore: {batch['supplier_name']} ({batch['supplier_country']})")
        click.echo(f"Acquisto: {batch['purchase_date']} | Scadenza: {batch.get('expiry_date', 'N/A')}")
        click.echo(f"Fiale: {batch['vials_remaining']}/{batch['vials_count']}")
        click.echo(f"Prezzo: {batch['total_price']:.2f} {batch['currency']}")
        
        if batch.get('batch_number'):
            click.echo(f"Batch #: {batch['batch_number']}")
        if batch.get('storage_location'):
            click.echo(f"Posizione: {batch['storage_location']}")
        
        click.echo(f"\nComposizione:")
        for comp in batch['composition']:
            click.echo(f"  • {comp['name']}: {comp['mg_per_vial']}mg/fiala")
        
        if batch['certificates']:
            click.echo(f"\nCertificati ({len(batch['certificates'])}):")
            for cert in batch['certificates']:
                purity = f"{cert['purity_percentage']:.1f}%" if cert['purity_percentage'] else "N/A"
                click.echo(f"  • [{cert['certificate_type']}] {cert['lab_name']}: {purity}")
        
        if batch['preparations']:
            click.echo(f"\nPreparazioni ({len(batch['preparations'])}):")
            for prep in batch['preparations']:
                click.echo(f"  • Prep #{prep['id']}: {prep['volume_remaining_ml']:.1f}ml / {prep['volume_ml']}ml")
        
        click.echo(f"{'='*80}\n")
    finally:
        manager.close()


@batches.command('use')
@click.argument('batch_id', type=int, required=False)
@click.argument('count', type=int, required=False)
@click.option('--db', default='peptide_management.db', hidden=True)
def use_vials(batch_id, count, db):
    """
    Registra utilizzo di fiale da un batch.
    
    \b
    Esempi:
      peptide-manager batches use 1 2    # Usa 2 fiale dal batch #1
      peptide-manager batches use        # Modalità interattiva
    """
    use_vials_interactive(db, batch_id, count)


@batches.command('search')
@click.option('--peptide', help='Filtra per peptide')
@click.option('--supplier', help='Filtra per fornitore')
@click.option('--available/--all', default=True, help='Solo con fiale disponibili')
@click.option('--db', default='peptide_management.db', hidden=True)
def search_batches(peptide, supplier, available, db):
    """Cerca batch con filtri multipli."""
    manager = PeptideManager(db)
    
    try:
        results = manager.get_batches(
            supplier=supplier,
            peptide=peptide,
            only_available=available
        )
        
        if not results:
            click.echo("Nessun batch trovato con questi filtri.")
            return
        
        filters = []
        if peptide:
            filters.append(f"peptide: {peptide}")
        if supplier:
            filters.append(f"fornitore: {supplier}")
        
        filter_str = ", ".join(filters) if filters else "nessun filtro"
        
        click.echo(f"\n{'='*80}")
        click.echo(f"RISULTATI RICERCA ({len(results)}) - {filter_str}")
        click.echo(f"{'='*80}\n")
        
        for batch in results:
            click.echo(f"[#{batch['id']}] {batch['product_name']}")
            click.echo(f"  Fornitore: {batch['supplier_name']}")
            click.echo(f"  Fiale: {batch['vials_remaining']}/{batch['vials_count']}")
            click.echo()
    finally:
        manager.close()


@batches.command('expiring')
@click.option('--days', default=60, help='Giorni di anticipo', type=int)
@click.option('--db', default='peptide_management.db', hidden=True)
def expiring_batches(days, db):
    """Mostra batch in scadenza nei prossimi N giorni."""
    manager = PeptideManager(db)
    
    try:
        cursor = manager.conn.cursor()
        
        cursor.execute(f'''
            SELECT b.id, b.product_name, b.expiry_date, b.vials_remaining, s.name as supplier
            FROM batches b
            JOIN suppliers s ON b.supplier_id = s.id
            WHERE b.expiry_date IS NOT NULL
            AND b.expiry_date <= date('now', '+{days} days')
            AND b.vials_remaining > 0
            ORDER BY b.expiry_date
        ''')
        
        expiring = cursor.fetchall()
        
        if not expiring:
            click.echo(f"\n✓ Nessun batch in scadenza nei prossimi {days} giorni\n")
            return
        
        click.echo(f"\n{'='*80}")
        click.echo(f"⚠️  BATCHES IN SCADENZA (prossimi {days} giorni)")
        click.echo(f"{'='*80}\n")
        
        for batch_id, product, expiry, vials, supplier in expiring:
            exp_date = datetime.strptime(expiry, '%Y-%m-%d')
            days_left = (exp_date - datetime.now()).days
            
            urgency = '🔴' if days_left < 30 else '🟡' if days_left < 60 else '🟢'
            
            click.echo(f"{urgency} [#{batch_id}] {product}")
            click.echo(f"   Fornitore: {supplier}")
            click.echo(f"   Scadenza: {expiry} (tra {days_left} giorni)")
            click.echo(f"   Fiale rimaste: {vials}")
            click.echo()
    finally:
        manager.close()


@batches.command('edit')
@click.argument('batch_id', type=int, required=False)
@click.option('--db', default='peptide_management.db', hidden=True)
def edit_batch(batch_id, db):
    """Modifica un batch esistente (campi limitati)."""
    from cli.utils.interactive import edit_batch_interactive
    edit_batch_interactive(db, batch_id)


# ============================================================
# HELPER FUNCTIONS (usate anche da main.py per scorciatoie)
# ============================================================

def add_batch_interactive(db):
    """Wizard interattivo per aggiungere un batch."""
    manager = PeptideManager(db)
    
    try:
        # Mostra fornitori
        suppliers = manager.get_suppliers()
        if not suppliers:
            click.echo("\n⚠️  Nessun fornitore trovato. Aggiungi prima un fornitore.")
            click.echo("   Usa: peptide-manager suppliers add")
            return
        
        click.echo("\n=== FORNITORI DISPONIBILI ===")
        for s in suppliers:
            click.echo(f"  [{s['id']}] {s['name']} ({s['country'] or 'N/A'})")
        
        supplier_id = click.prompt('\nID Fornitore', type=int)
        supplier = next((s for s in suppliers if s['id'] == supplier_id), None)
        
        if not supplier:
            click.echo(f"❌ Fornitore ID {supplier_id} non trovato", err=True)
            return
        
        supplier_name = supplier['name']
        
        # Dati batch
        click.echo(f"\n=== NUOVO ACQUISTO DA {supplier_name} ===\n")
        
        product_name = click.prompt('Nome prodotto')
        batch_number = click.prompt('Numero batch (opzionale)', default='', show_default=False)
        vials_count = click.prompt('Numero fiale', type=int)
        mg_per_vial = click.prompt('mg per fiala (totali)', type=float)
        total_price = click.prompt('Prezzo totale', type=float)
        currency = click.prompt('Valuta', default='EUR')
        
        purchase_date = click.prompt(
            'Data acquisto (YYYY-MM-DD)', 
            default=datetime.now().strftime('%Y-%m-%d')
        )
        
        has_expiry = click.confirm('Specificare data scadenza?', default=True)
        expiry_date = None
        if has_expiry:
            expiry_date = click.prompt('Data scadenza (YYYY-MM-DD)', default='')
            if not expiry_date:
                expiry_date = None
        
        storage_location = click.prompt('Posizione storage', default='', show_default=False)
        notes = click.prompt('Note (opzionale)', default='', show_default=False)
        
        # Composizione
        click.echo("\n=== COMPOSIZIONE ===")
        is_blend = click.confirm('È un blend (più peptidi)?', default=False)
        
        composition = []
        
        if is_blend:
            click.echo("\nInserisci peptidi (INVIO per terminare)")
            peptide_num = 1
            
            while True:
                click.echo(f"\nPeptide #{peptide_num}:")
                peptide_name = click.prompt('  Nome (o INVIO)', default='', show_default=False)
                
                if not peptide_name:
                    break
                
                mg_amount = click.prompt('  mg per fiala', type=float)
                composition.append((peptide_name, mg_amount))
                peptide_num += 1
            
            if not composition:
                click.echo("❌ Serve almeno un peptide!", err=True)
                return
            
            total_mg = sum(mg for _, mg in composition)
            if abs(total_mg - mg_per_vial) > 0.01:
                click.echo(f"\n⚠️  Somma peptidi ({total_mg}mg) != totale ({mg_per_vial}mg)")
                if not click.confirm('Continuare?'):
                    return
        else:
            peptide_name = click.prompt('Nome peptide')
            composition = [(peptide_name, mg_per_vial)]
        
        # Riepilogo
        click.echo("\n" + "="*80)
        click.echo("RIEPILOGO")
        click.echo("="*80)
        click.echo(f"Fornitore: {supplier_name}")
        click.echo(f"Prodotto: {product_name}")
        click.echo(f"Fiale: {vials_count} x {mg_per_vial}mg")
        click.echo(f"Prezzo: {total_price:.2f} {currency}")
        click.echo("\nComposizione:")
        for pep, mg in composition:
            click.echo(f"  • {pep}: {mg}mg/fiala")
        click.echo("="*80)
        
        if not click.confirm('\nConfermare?'):
            click.echo("Annullato.")
            return
        
        # Inserisci
        batch_id = manager.add_batch(
            supplier_name=supplier_name,
            product_name=product_name,
            vials_count=vials_count,
            mg_per_vial=mg_per_vial,
            total_price=total_price,
            purchase_date=purchase_date,
            composition=composition,
            batch_number=batch_number if batch_number else None,
            expiry_date=expiry_date,
            currency=currency,
            storage_location=storage_location if storage_location else None,
            notes=notes if notes else None
        )
        
        click.echo(f"\n✓✓✓ Batch #{batch_id} registrato! ✓✓✓\n")
        
        # Chiedi certificato
        if click.confirm('Aggiungere certificato COA?', default=False):
            from cli.utils.interactive import add_certificate_interactive
            add_certificate_interactive(manager, batch_id)
        
    except Exception as e:
        click.echo(f"\n❌ Errore: {e}", err=True)
    finally:
        manager.close()


def use_vials_interactive(db, batch_id=None, count=None):
    """Helper per usare fiale (con o senza argomenti)."""
    manager = PeptideManager(db)
    
    try:
        if batch_id is None:
            batches = manager.get_batches(only_available=True)
            
            if not batches:
                click.echo("\n⚠️  Nessun batch disponibile")
                return
            
            click.echo("\n=== BATCHES DISPONIBILI ===\n")
            for b in batches[:10]:
                click.echo(f"[#{b['id']}] {b['product_name']}")
                click.echo(f"  Fiale: {b['vials_remaining']}/{b['vials_count']}")
                click.echo()
            
            if len(batches) > 10:
                click.echo(f"... e altri {len(batches) - 10}")
            
            batch_id = click.prompt('\nID Batch', type=int)
            count = click.prompt('Fiale da usare', type=int, default=1)
        
        batch_details = manager.get_batch_details(batch_id)
        if not batch_details:
            click.echo(f"\n❌ Batch #{batch_id} non trovato", err=True)
            return
        
        click.echo(f"\n[#{batch_id}] {batch_details['product_name']}")
        click.echo(f"Fiale disponibili: {batch_details['vials_remaining']}")
        
        if not click.confirm(f'\nUsare {count} fiala/e?', default=True):
            click.echo("Annullato.")
            return
        
        success = manager.use_vials(batch_id, count)
        
        if success:
            click.echo(f"\n✓ {count} fiala/e utilizzate\n")
    
    except Exception as e:
        click.echo(f"\n❌ Errore: {e}", err=True)
    finally:
        manager.close()


@batches.command('adjust')
@click.argument('batch_id', type=int)
@click.argument('adjustment', type=int)
@click.option('--reason', help='Motivo correzione', default='')
@click.option('--db', default='peptide_management.db', hidden=True)
def adjust_vials_command(batch_id, adjustment, reason, db):
    """
    Corregge il conteggio fiale di un batch.
    
    Usa numeri positivi per aggiungere, negativi per rimuovere.
    
    \b
    Esempi:
      peptide-manager batches adjust 1 +1 --reason "Fiala usata per errore"
      peptide-manager batches adjust 2 -2 --reason "Fiale danneggiate"
    """
    manager = PeptideManager(db)
    
    try:
        batch = manager.get_batch_details(batch_id)
        
        if not batch:
            click.echo(f"\n❌ Batch #{batch_id} non trovato", err=True)
            return
        
        # Mostra stato attuale
        click.echo(f"\n{'='*60}")
        click.echo(f"CORREZIONE FIALE - BATCH #{batch_id}")
        click.echo(f"{'='*60}")
        click.echo(f"Prodotto: {batch['product_name']}")
        click.echo(f"Fiale attuali: {batch['vials_remaining']}/{batch['vials_count']}")
        
        action_text = "aggiungere" if adjustment > 0 else "rimuovere"
        new_count = batch['vials_remaining'] + adjustment
        
        click.echo(f"\nOperazione: {action_text} {abs(adjustment)} fiala/e")
        click.echo(f"Nuovo totale: {new_count} fiale")
        
        if reason:
            click.echo(f"Motivo: {reason}")
        
        click.echo(f"{'='*60}")
        
        if not click.confirm('\n✓ Confermare correzione?', default=True):
            click.echo("Annullato.")
            return
        
        success = manager.adjust_vials(batch_id, adjustment, reason if reason else None)
        
        if success:
            click.echo(f"\n✓ Correzione applicata con successo\n")
    
    except Exception as e:
        click.echo(f"\n❌ Errore: {e}", err=True)
    finally:
        manager.close()


@batches.command('delete')
@click.argument('batch_id', type=int)
@click.option('--force', is_flag=True, help='Forza eliminazione con preparazioni')
@click.option('--db', default='peptide_management.db', hidden=True)
def delete_batch(batch_id, force, db):
    """
    Elimina un batch.
    
    ⚠️  ATTENZIONE: Eliminerà anche preparazioni e somministrazioni!
    """
    manager = PeptideManager(db)
    
    try:
        batch = manager.get_batch_details(batch_id)
        
        if not batch:
            click.echo(f"\n❌ Batch #{batch_id} non trovato", err=True)
            return
        
        click.echo(f"\n⚠️  ELIMINAZIONE BATCH")
        click.echo(f"{'='*60}")
        click.echo(f"ID: #{batch['id']}")
        click.echo(f"Prodotto: {batch['product_name']}")
        click.echo(f"Fornitore: {batch['supplier_name']}")
        click.echo(f"Fiale: {batch['vials_remaining']}/{batch['vials_count']}")
        
        if batch['preparations']:
            click.echo(f"\n⚠️  ATTENZIONE: Ha {len(batch['preparations'])} preparazioni")
            click.echo("   Eliminare il batch eliminerà ANCHE:")
            click.echo("   - Tutte le preparazioni")
            click.echo("   - Tutte le somministrazioni")
        
        click.echo(f"{'='*60}")
        
        if not click.confirm('\n⚠️  CONFERMARE ELIMINAZIONE? (irreversibile)', default=False):
            click.echo("Annullato.")
            return
        
        success = manager.delete_batch(batch_id, force=force)
        
        if success:
            click.echo(f"\n✓ Batch #{batch_id} eliminato\n")
    
    except Exception as e:
        click.echo(f"\n❌ Errore: {e}", err=True)
    finally:
        manager.close()