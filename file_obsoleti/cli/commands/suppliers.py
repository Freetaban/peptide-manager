"""
Comandi per gestione fornitori.
"""

import click
from peptide_manager import PeptideManager


@click.group()
def suppliers():
    """
    Gestione fornitori.
    
    \b
    Comandi disponibili:
      list      Lista fornitori
      add       Aggiungi fornitore
      edit      Modifica fornitore
      show      Dettagli fornitore
      search    Cerca fornitori
      stats     Statistiche per fornitore
    """
    pass


@suppliers.command('list')
@click.option('--db', default='peptide_management.db', hidden=True)
def list_suppliers(db):
    """Lista tutti i fornitori."""
    manager = PeptideManager(db)
    
    try:
        suppliers_list = manager.get_suppliers()
        
        if not suppliers_list:
            click.echo("Nessun fornitore registrato.")
            return
        
        click.echo(f"\n{'='*80}")
        click.echo(f"FORNITORI ({len(suppliers_list)})")
        click.echo(f"{'='*80}\n")
        
        for s in suppliers_list:
            stars = '★' * (s['reliability_rating'] or 0)
            click.echo(f"[#{s['id']}] {s['name']}")
            click.echo(f"  Paese: {s['country'] or 'N/A'}")
            if s['website']:
                click.echo(f"  Website: {s['website']}")
            if s['reliability_rating']:
                click.echo(f"  Rating: {stars} ({s['reliability_rating']}/5)")
            click.echo()
    finally:
        manager.close()


@suppliers.command('add')
@click.option('--name', prompt='Nome fornitore')
@click.option('--country', prompt='Paese', default='')
@click.option('--website', prompt='Sito web (opzionale)', default='')
@click.option('--email', prompt='Email (opzionale)', default='')
@click.option('--rating', prompt='Affidabilità (1-5)', type=click.IntRange(1, 5), default=3)
@click.option('--notes', prompt='Note (opzionale)', default='')
@click.option('--db', default='peptide_management.db', hidden=True)
def add_supplier(name, country, website, email, rating, notes, db):
    """Aggiungi nuovo fornitore."""
    manager = PeptideManager(db)
    
    try:
        supplier_id = manager.add_supplier(
            name=name,
            country=country if country else None,
            website=website if website else None,
            email=email if email else None,
            rating=rating,
            notes=notes if notes else None
        )
        click.echo(f"\n✓ Fornitore '{name}' aggiunto (ID: {supplier_id})\n")
    except Exception as e:
        click.echo(f"\n❌ Errore: {e}", err=True)
    finally:
        manager.close()


@suppliers.command('edit')
@click.argument('supplier_id', type=int, required=False)
@click.option('--db', default='peptide_management.db', hidden=True)
def edit_supplier(supplier_id, db):
    """Modifica un fornitore esistente."""
    manager = PeptideManager(db)
    
    try:
        if supplier_id is None:
            suppliers_list = manager.get_suppliers()
            
            if not suppliers_list:
                click.echo("\n⚠️  Nessun fornitore")
                return
            
            click.echo("\n=== FORNITORI ===\n")
            for s in suppliers_list:
                click.echo(f"[#{s['id']}] {s['name']} ({s['country'] or 'N/A'})")
            
            supplier_id = click.prompt('\nID Fornitore', type=int)
        
        suppliers_list = manager.get_suppliers()
        supplier = next((s for s in suppliers_list if s['id'] == supplier_id), None)
        
        if not supplier:
            click.echo(f"\n❌ Fornitore #{supplier_id} non trovato", err=True)
            return
        
        click.echo(f"\n=== MODIFICA #{supplier_id} ===\n")
        click.echo(f"Attuale: {supplier['name']}")
        click.echo("(INVIO per mantenere)\n")
        
        new_name = click.prompt('Nome', default=supplier['name'])
        new_country = click.prompt('Paese', default=supplier['country'] or '')
        new_website = click.prompt('Website', default=supplier['website'] or '')
        new_email = click.prompt('Email', default=supplier['email'] or '')
        new_rating = click.prompt('Rating (1-5)', type=click.IntRange(1, 5), 
                                 default=supplier['reliability_rating'] or 3)
        new_notes = click.prompt('Note', default=supplier['notes'] or '')
        
        changes = {}
        if new_name != supplier['name']:
            changes['name'] = new_name
        if new_country != (supplier['country'] or ''):
            changes['country'] = new_country if new_country else None
        if new_website != (supplier['website'] or ''):
            changes['website'] = new_website if new_website else None
        if new_email != (supplier['email'] or ''):
            changes['email'] = new_email if new_email else None
        if new_rating != (supplier['reliability_rating'] or 3):
            changes['reliability_rating'] = new_rating
        if new_notes != (supplier['notes'] or ''):
            changes['notes'] = new_notes if new_notes else None
        
        if not changes:
            click.echo("\n⚠️  Nessuna modifica")
            return
        
        if not click.confirm('\nConfermare?'):
            click.echo("Annullato.")
            return
        
        manager.update_supplier(supplier_id, **changes)
        click.echo(f"\n✓ Fornitore #{supplier_id} aggiornato\n")
    
    except Exception as e:
        click.echo(f"\n❌ Errore: {e}", err=True)
    finally:
        manager.close()


@suppliers.command('show')
@click.argument('supplier_id', type=int)
@click.option('--db', default='peptide_management.db', hidden=True)
def show_supplier(supplier_id, db):
    """Mostra dettagli fornitore e storico acquisti."""
    manager = PeptideManager(db)
    
    try:
        suppliers_list = manager.get_suppliers()
        supplier = next((s for s in suppliers_list if s['id'] == supplier_id), None)
        
        if not supplier:
            click.echo(f"\n❌ Fornitore #{supplier_id} non trovato", err=True)
            return
        
        cursor = manager.conn.cursor()
        
        # Statistiche acquisti
        cursor.execute('''
            SELECT COUNT(*), SUM(total_price), SUM(vials_count), SUM(vials_remaining)
            FROM batches
            WHERE supplier_id = ?
        ''', (supplier_id,))
        
        total_orders, total_spent, total_vials, vials_left = cursor.fetchone()
        
        stars = '★' * (supplier['reliability_rating'] or 0)
        
        click.echo(f"\n{'='*60}")
        click.echo(f"FORNITORE #{supplier_id}: {supplier['name']}")
        click.echo(f"{'='*60}")
        click.echo(f"Paese: {supplier['country'] or 'N/A'}")
        
        if supplier['website']:
            click.echo(f"Website: {supplier['website']}")
        if supplier['email']:
            click.echo(f"Email: {supplier['email']}")
        if supplier['reliability_rating']:
            click.echo(f"Rating: {stars} ({supplier['reliability_rating']}/5)")
        if supplier['notes']:
            click.echo(f"Note: {supplier['notes']}")
        
        click.echo(f"\nStatistiche Acquisti:")
        click.echo(f"  Ordini totali: {total_orders or 0}")
        click.echo(f"  Spesa totale: EUR {total_spent or 0:.2f}")
        click.echo(f"  Fiale acquistate: {total_vials or 0}")
        click.echo(f"  Fiale rimanenti: {vials_left or 0}")
        
        click.echo(f"{'='*60}\n")
    
    finally:
        manager.close()


@suppliers.command('search')
@click.argument('query')
@click.option('--db', default='peptide_management.db', hidden=True)
def search_suppliers(query, db):
    """Cerca fornitori per nome o paese."""
    manager = PeptideManager(db)
    
    try:
        results = manager.get_suppliers(search=query)
        
        if not results:
            click.echo(f"Nessun fornitore trovato per '{query}'")
            return
        
        click.echo(f"\nRisultati per '{query}' ({len(results)}):\n")
        for s in results:
            click.echo(f"[#{s['id']}] {s['name']} ({s['country'] or 'N/A'})")
            if s['website']:
                click.echo(f"  {s['website']}")
            click.echo()
    finally:
        manager.close()


@suppliers.command('stats')
@click.option('--db', default='peptide_management.db', hidden=True)
def supplier_stats(db):
    """Statistiche comparative tra fornitori."""
    manager = PeptideManager(db)
    
    try:
        cursor = manager.conn.cursor()
        
        cursor.execute('''
            SELECT 
                s.id,
                s.name,
                s.reliability_rating,
                COUNT(b.id) as orders,
                SUM(b.total_price) as total_spent,
                SUM(b.vials_count) as total_vials
            FROM suppliers s
            LEFT JOIN batches b ON s.id = b.supplier_id
            GROUP BY s.id
            ORDER BY total_spent DESC
        ''')
        
        stats = cursor.fetchall()
        
        if not stats:
            click.echo("Nessun fornitore.")
            return
        
        click.echo(f"\n{'='*80}")
        click.echo("STATISTICHE FORNITORI")
        click.echo(f"{'='*80}\n")
        
        for sid, name, rating, orders, spent, vials in stats:
            stars = '★' * (rating or 0) if rating else 'N/A'
            click.echo(f"[#{sid}] {name}")
            click.echo(f"  Rating: {stars}")
            click.echo(f"  Ordini: {orders or 0}")
            click.echo(f"  Spesa: EUR {spent or 0:.2f}")
            click.echo(f"  Fiale: {vials or 0}")
            if orders and spent:
                avg = spent / orders
                click.echo(f"  Media/ordine: EUR {avg:.2f}")
            click.echo()
        
        click.echo(f"{'='*80}\n")
    
    finally:
        manager.close()

@suppliers.command('delete')
@click.argument('supplier_id', type=int)
@click.option('--force', is_flag=True, help='Forza eliminazione anche con batches')
@click.option('--db', default='peptide_management.db', hidden=True)
def delete_supplier(supplier_id, force, db):
    """
    Elimina un fornitore.
    
    ⚠️  ATTENZIONE: Operazione irreversibile!
    """
    manager = PeptideManager(db)
    
    try:
        suppliers_list = manager.get_suppliers()
        supplier = next((s for s in suppliers_list if s['id'] == supplier_id), None)
        
        if not supplier:
            click.echo(f"\n❌ Fornitore #{supplier_id} non trovato", err=True)
            return
        
        click.echo(f"\n⚠️  ELIMINAZIONE FORNITORE")
        click.echo(f"{'='*60}")
        click.echo(f"ID: #{supplier['id']}")
        click.echo(f"Nome: {supplier['name']}")
        click.echo(f"Paese: {supplier['country'] or 'N/A'}")
        click.echo(f"{'='*60}")
        
        if not click.confirm('\n⚠️  CONFERMARE ELIMINAZIONE? (irreversibile)', default=False):
            click.echo("Annullato.")
            return
        
        success = manager.delete_supplier(supplier_id, force=force)
        
        if success:
            click.echo(f"\n✓ Fornitore #{supplier_id} eliminato\n")
    
    except Exception as e:
        click.echo(f"\n❌ Errore: {e}", err=True)
    finally:
        manager.close()