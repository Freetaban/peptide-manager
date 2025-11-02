"""
Peptide Management System - CLI Entry Point
"""

import click
from peptide_manager import PeptideManager
from peptide_manager.database import init_database


@click.group(invoke_without_command=True)
@click.version_option(version='0.1.0')
@click.option('--db', default='peptide_management.db', help='Percorso database')
@click.pass_context
def cli(ctx, db):
    """
    ╔════════════════════════════════════════════════════════════╗
    ║          PEPTIDE MANAGEMENT SYSTEM v0.1.0                  ║
    ╚════════════════════════════════════════════════════════════╝
    
    Sistema completo per gestione peptidi: acquisti, inventario,
    preparazioni, protocolli e somministrazioni.
    
    \b
    MODALITÀ:
      peptide-manager           Interfaccia TUI interattiva (DOS-style)
      peptide-manager <comando> Esegui comando specifico
    
    \b
    Comandi disponibili:
      peptides      Gestione catalogo peptidi
      suppliers     Gestione fornitori
      batches       Gestione batch/acquisti
      preparations  Gestione preparazioni
      protocols     Gestione protocolli
    
    \b
    Quick commands:
      init          Inizializza database
      inventory     Mostra inventario completo
      summary       Riepilogo rapido
    """
    ctx.ensure_object(dict)
    ctx.obj['db'] = db
    
    # Se nessun comando specificato, lancia TUI
    if ctx.invoked_subcommand is None:
        from cli.tui import start_tui
        start_tui(db)


# ============================================================
# COMANDI BASE
# ============================================================

@cli.command()
@click.pass_context
def init(ctx):
    """Inizializza il database."""
    db_path = ctx.obj['db']
    init_database(db_path)
    click.echo(f"✓ Database inizializzato: {db_path}")


@cli.command()
@click.option('--detailed/--no-detailed', default=False, help='Mostra certificati e dettagli')
@click.pass_context
def inventory(ctx, detailed):
    """Mostra inventario completo di tutti i batch."""
    manager = PeptideManager(ctx.obj['db'])
    try:
        manager.print_inventory(detailed=detailed)
    finally:
        manager.close()


@cli.command()
@click.pass_context
def summary(ctx):
    """Riepilogo rapido dell'inventario."""
    manager = PeptideManager(ctx.obj['db'])
    try:
        summary = manager.get_inventory_summary()
        
        click.echo(f"\n{'='*60}")
        click.echo(f"RIEPILOGO INVENTARIO")
        click.echo(f"{'='*60}")
        click.echo(f"Batches attivi: {summary['available_batches']}/{summary['total_batches']}")
        click.echo(f"Peptidi unici: {summary['unique_peptides']}")
        click.echo(f"Valore totale: EUR {summary['total_value']:.2f}")
        
        if summary['expiring_soon'] > 0:
            click.echo(f"⚠️  In scadenza (60gg): {summary['expiring_soon']} batches")
        
        click.echo(f"{'='*60}\n")
    finally:
        manager.close()


@cli.command()
@click.pass_context
def tui(ctx):
    """Lancia interfaccia TUI interattiva."""
    from cli.tui import start_tui
    start_tui(ctx.obj['db'])


# ============================================================
# IMPORT MENU COMMANDS
# ============================================================

from cli.commands.peptides import peptides
from cli.commands.suppliers import suppliers
from cli.commands.batches import batches
from cli.commands.preparations import preparations
from cli.commands.protocols import protocols

cli.add_command(peptides)
cli.add_command(suppliers)
cli.add_command(batches)
cli.add_command(preparations)
cli.add_command(protocols)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == '__main__':
    cli(obj={})
