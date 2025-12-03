"""
Helper functions interattive condivise.
"""

import click
from datetime import datetime


def add_certificate_interactive(manager, batch_id):
    """Helper per aggiungere certificato interattivamente."""
    click.echo(f"\n=== CERTIFICATO BATCH #{batch_id} ===\n")
    
    cert_types = {'1': 'manufacturer', '2': 'third_party', '3': 'personal'}
    
    click.echo("Tipo:")
    click.echo("  1) Produttore")
    click.echo("  2) Third-party")
    click.echo("  3) Personale")
    
    choice = click.prompt('Tipo', type=click.Choice(['1', '2', '3']))
    cert_type = cert_types[choice]
    
    lab_name = click.prompt('Laboratorio')
    test_date = click.prompt('Data test (YYYY-MM-DD)', 
                            default=datetime.now().strftime('%Y-%m-%d'))
    purity = click.prompt('Purezza % (opzionale)', type=float, default=0.0, show_default=False)
    file_path = click.prompt('Path PDF (opzionale)', default='', show_default=False)
    notes = click.prompt('Note (opzionale)', default='', show_default=False)
    
    try:
        cert_id = manager.add_certificate(
            batch_id=batch_id,
            certificate_type=cert_type,
            lab_name=lab_name,
            test_date=test_date,
            purity_percentage=purity if purity > 0 else None,
            file_path=file_path if file_path else None,
            notes=notes if notes else None
        )
        click.echo(f"\n✓ Certificato #{cert_id} aggiunto")
    except Exception as e:
        click.echo(f"\n❌ Errore: {e}", err=True)


def edit_batch_interactive(db, batch_id):
    """Modifica batch (implementazione da completare)."""
    from peptide_manager import PeptideManager
    
    manager = PeptideManager(db)
    
    try:
        batch = manager.get_batch_details(batch_id)
        
        if not batch:
            click.echo(f"\n❌ Batch #{batch_id} non trovato", err=True)
            return
        
        click.echo(f"\n=== MODIFICA BATCH #{batch_id} ===\n")
        click.echo(f"Prodotto: {batch['product_name']}")
        click.echo("(INVIO per mantenere)\n")
        
        # Campi modificabili
        new_storage = click.prompt('Storage location', default=batch.get('storage_location', ''))
        new_notes = click.prompt('Note', default=batch.get('notes', ''))
        
        # Costruisci dizionario modifiche
        changes = {}
        if new_storage != (batch.get('storage_location') or ''):
            changes['storage_location'] = new_storage if new_storage else None
        if new_notes != (batch.get('notes') or ''):
            changes['notes'] = new_notes if new_notes else None
        
        if not changes:
            click.echo("\n⚠️  Nessuna modifica")
            return
        
        if not click.confirm('\nConfermare modifiche?'):
            click.echo("Annullato.")
            return
        
        # Aggiorna batch
        manager.update_batch(batch_id, **changes)
        click.echo(f"\n✓ Batch #{batch_id} aggiornato\n")
    
    except Exception as e:
        click.echo(f"\n❌ Errore: {e}", err=True)
    finally:
        manager.close()
