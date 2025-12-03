"""
Entry point principale CLI con supporto GUI
"""
import click
from cli.tui import start_tui

# Import comandi
from cli.commands.peptides import peptides
from cli.commands.suppliers import suppliers
from cli.commands.batches import batches
from cli.commands.preparations import preparations
from cli.commands.protocols import protocols


@click.group(invoke_without_command=True)
@click.option('--db', default='peptide_management.db', help='Path file database')
@click.pass_context
def cli(ctx, db):
    """
    Peptide Management System
    
    Sistema completo per gestione peptidi, batches, fornitori e protocolli.
    
    Uso:
    
    - Senza argomenti: Apre TUI interattiva
    
    - Con comandi: Usa CLI tradizionale
    
    - Con --db: Specifica database custom
    
    Esempi:
    
      peptide-manager              # Apre TUI (DB default)
      
      peptide-manager --db dev.db gui          # GUI con DB dev
      
      peptide-manager --db prod.db batches list # CLI con DB prod
    """
    # Salva db path nel context per tutti i comandi
    ctx.ensure_object(dict)
    ctx.obj['db_path'] = db
    
    if ctx.invoked_subcommand is None:
        # Nessun comando = apri TUI
        start_tui(db)


@cli.command()
@click.pass_context
def gui(ctx):
    """Avvia interfaccia grafica (GUI Flet)."""
    db_path = ctx.obj.get('db_path', 'peptide_management.db')
    
    try:
        import sys
        import os
        # Aggiungi root del progetto al path
        cli_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(cli_dir)
        if root_dir not in sys.path:
            sys.path.insert(0, root_dir)
        
        from gui import start_gui
        click.echo(f"🚀 Avvio GUI (Database: {db_path})...")
        start_gui(db_path)
    except ImportError as e:
        click.echo("❌ Errore: Flet non installato!")
        click.echo("Installa con: pip install flet")
        click.echo(f"Dettagli: {e}")
    except Exception as e:
        click.echo(f"❌ Errore GUI: {e}")


@cli.command()
@click.pass_context
def tui(ctx):
    """Avvia interfaccia testuale (TUI DOS-style)."""
    db_path = ctx.obj.get('db_path', 'peptide_management.db')
    start_tui(db_path)


@cli.command()
@click.pass_context
def init(ctx):
    """Inizializza database."""
    db_path = ctx.obj.get('db_path', 'peptide_management.db')
    
    try:
        manager = PeptideManager(db_path)
        click.echo(f"✓ Database '{db_path}' inizializzato con successo!")
        manager.close()
    except Exception as e:
        click.echo(f"✗ Errore inizializzazione: {e}")


@cli.command()
@click.pass_context
def inventory(ctx):
    """Mostra inventario completo."""
    db_path = ctx.obj.get('db_path', 'peptide_management.db')
    
    manager = PeptideManager(db_path)
    try:
        summary = manager.get_inventory_summary()
        
        click.echo(f"\n{'='*60}")
        click.echo(f"  INVENTARIO PEPTIDI (DB: {db_path})")
        click.echo(f"{'='*60}")
        click.echo(f"  Batches totali:     {summary['total_batches']}")
        click.echo(f"  Batches disponibili: {summary['available_batches']}")
        click.echo(f"  Peptidi unici:      {summary['unique_peptides']}")
        click.echo(f"  Valore totale:      €{summary['total_value']:.2f}")
        click.echo(f"  In scadenza (60gg): {summary['expiring_soon']}")
        click.echo(f"{'='*60}\n")
        
    finally:
        manager.close()


@cli.command()
@click.pass_context
def summary(ctx):
    """Riepilogo rapido."""
    db_path = ctx.obj.get('db_path', 'peptide_management.db')
    
    manager = PeptideManager(db_path)
    try:
        summary = manager.get_inventory_summary()
        
        click.echo(f"\n📦 Batches: {summary['available_batches']}/{summary['total_batches']}")
        click.echo(f"🧪 Peptidi: {summary['unique_peptides']}")
        click.echo(f"💰 Valore: €{summary['total_value']:.2f}")
        
        if summary['expiring_soon'] > 0:
            click.echo(f"⚠️  In scadenza: {summary['expiring_soon']}")
        else:
            click.echo("✓ Nessun batch in scadenza")
        
        click.echo(f"📂 Database: {db_path}\n")
        
    finally:
        manager.close()


# Registra gruppi comandi
cli.add_command(peptides)
cli.add_command(suppliers)
cli.add_command(batches)
cli.add_command(preparations)
cli.add_command(protocols)


if __name__ == '__main__':
    cli()
