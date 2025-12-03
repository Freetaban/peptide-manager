"""
Comandi per gestione preparazioni/diluizioni.
"""

import click
from peptide_manager import PeptideManager
from peptide_manager.calculator import DilutionCalculator, print_dilution_guide
from datetime import datetime, timedelta


@click.group()
def preparations():
    """
    Gestione preparazioni e diluizioni.
    
    \b
    Comandi disponibili:
      list      Lista preparazioni attive
      add       Crea nuova preparazione
      show      Dettagli preparazione
      use       Registra utilizzo
      edit      Modifica preparazione
      expired   Preparazioni scadute
      calc      Calcolatore diluizioni
    """
    pass


@preparations.command('list')
@click.option('--active/--all', default=True, help='Solo con volume rimanente')
@click.option('--batch', type=int, help='Filtra per batch')
@click.option('--db', default='peptide_management.db', hidden=True)
def list_preparations(active, batch, db):
    """Lista tutte le preparazioni."""
    manager = PeptideManager(db)
    
    try:
        preps = manager.get_preparations(batch_id=batch, only_active=active)
        
        if not preps:
            click.echo("Nessuna preparazione trovata.")
            return
        
        status = "ATTIVE" if active else "TUTTE"
        click.echo(f"\n{'='*80}")
        click.echo(f"PREPARAZIONI {status} ({len(preps)})")
        click.echo(f"{'='*80}\n")
        
        for p in preps:
            percentage = (p['volume_remaining_ml'] / p['volume_ml'] * 100) if p['volume_ml'] > 0 else 0
            
            click.echo(f"[#{p['id']}] {p['batch_product']}")
            click.echo(f"  Data: {p['preparation_date']} | Scadenza: {p['expiry_date'] or 'N/A'}")
            click.echo(f"  Volume: {p['volume_remaining_ml']:.1f}ml / {p['volume_ml']}ml ({percentage:.0f}%)")
            click.echo(f"  Fiale usate: {p['vials_used']}")
            if p['storage_location']:
                click.echo(f"  Storage: {p['storage_location']}")
            click.echo()
    finally:
        manager.close()


@preparations.command('add')
@click.option('--db', default='peptide_management.db', hidden=True)
def add_preparation(db):
    """Crea una nuova preparazione (wizard completo)."""
    manager = PeptideManager(db)
    
    try:
        # Mostra batches disponibili
        batches = manager.get_batches(only_available=True)
        
        if not batches:
            click.echo("\n⚠️  Nessun batch disponibile")
            return
        
        click.echo("\n=== BATCHES DISPONIBILI ===\n")
        for b in batches[:10]:
            click.echo(f"[#{b['id']}] {b['product_name']}")
            click.echo(f"  Fiale disponibili: {b['vials_remaining']}/{b['vials_count']}")
            click.echo(f"  {b['mg_per_vial']}mg/fiala")
            click.echo()
        
        if len(batches) > 10:
            click.echo(f"... e altri {len(batches) - 10}\n")
        
        # Selezione batch
        batch_id = click.prompt('ID Batch', type=int)
        
        batch_details = manager.get_batch_details(batch_id)
        if not batch_details:
            click.echo(f"\n❌ Batch #{batch_id} non trovato", err=True)
            return
        
        if batch_details['vials_remaining'] == 0:
            click.echo(f"\n❌ Nessuna fiala disponibile", err=True)
            return
        
        click.echo(f"\n=== NUOVA PREPARAZIONE DA BATCH #{batch_id} ===")
        click.echo(f"Prodotto: {batch_details['product_name']}")
        click.echo(f"Fiale disponibili: {batch_details['vials_remaining']}")
        click.echo(f"mg per fiala: {batch_details['mg_per_vial']}")
        
        # Mostra composizione
        click.echo("\nComposizione:")
        for comp in batch_details['composition']:
            click.echo(f"  • {comp['name']}: {comp['mg_per_vial']}mg/fiala")
        
        # Parametri preparazione
        click.echo("\n" + "="*60)
        vials_used = click.prompt('Fiale da usare', type=int, default=1)
        
        if vials_used > batch_details['vials_remaining']:
            click.echo(f"\n❌ Fiale insufficienti", err=True)
            return
        
        total_mg = batch_details['mg_per_vial'] * vials_used
        
        click.echo(f"\nmg totali: {total_mg}mg ({vials_used} x {batch_details['mg_per_vial']}mg)")
        
        # Suggerimenti diluizione
        if click.confirm('\nVuoi un suggerimento per la diluizione?', default=True):
            target_dose = click.prompt('Dose target (mcg)', type=float, default=250)
            
            calc = DilutionCalculator()
            suggestion = calc.suggested_dilution_for_dose(total_mg, target_dose, 0.2)
            
            click.echo(f"\n💡 SUGGERIMENTO:")
            click.echo(f"  Volume diluente: {suggestion['volume_diluente_ml']}ml")
            click.echo(f"  Concentrazione: {suggestion['concentrazione_mg_ml']}mg/ml")
            click.echo(f"  Volume per dose ({target_dose}mcg): {suggestion['volume_per_dose_ml']}ml")
            click.echo(f"  Dosi disponibili: {suggestion['dosi_totali']}")
            
            if click.confirm('\nUsare questo volume?', default=True):
                volume_ml = suggestion['volume_diluente_ml']
            else:
                volume_ml = click.prompt('Volume diluente (ml)', type=float)
        else:
            volume_ml = click.prompt('Volume diluente (ml)', type=float)
        
        # Calcola concentrazione
        concentration = total_mg / volume_ml
        click.echo(f"\nConcentrazione finale: {concentration:.3f}mg/ml ({concentration*1000:.1f}mcg/ml)")
        
        # Altri parametri
        diluent = click.prompt('Diluente', default='BAC Water')
        
        prep_date = click.prompt(
            'Data preparazione (YYYY-MM-DD)',
            default=datetime.now().strftime('%Y-%m-%d')
        )
        
        # Calcola scadenza suggerita (28 giorni)
        suggested_expiry = (datetime.strptime(prep_date, '%Y-%m-%d') + timedelta(days=28)).strftime('%Y-%m-%d')
        expiry_date = click.prompt('Data scadenza', default=suggested_expiry)
        
        storage = click.prompt('Posizione storage', default='Frigo', show_default=False)
        notes = click.prompt('Note (opzionale)', default='', show_default=False)
        
        # Riepilogo
        click.echo("\n" + "="*80)
        click.echo("RIEPILOGO PREPARAZIONE")
        click.echo("="*80)
        click.echo(f"Batch: #{batch_id} - {batch_details['product_name']}")
        click.echo(f"Fiale: {vials_used} x {batch_details['mg_per_vial']}mg = {total_mg}mg")
        click.echo(f"Volume: {volume_ml}ml")
        click.echo(f"Concentrazione: {concentration:.3f}mg/ml ({concentration*1000:.1f}mcg/ml)")
        click.echo(f"Data: {prep_date} → {expiry_date}")
        click.echo(f"Storage: {storage}")
        click.echo("="*80)
        
        if not click.confirm('\nConfermare?'):
            click.echo("Annullato.")
            return
        
        # Crea preparazione
        prep_id = manager.add_preparation(
            batch_id=batch_id,
            vials_used=vials_used,
            volume_ml=volume_ml,
            preparation_date=prep_date,
            diluent=diluent,
            expiry_date=expiry_date,
            storage_location=storage if storage else None,
            notes=notes if notes else None
        )
        
        click.echo(f"\n✓✓✓ Preparazione #{prep_id} creata! ✓✓✓")
        
        # Mostra guida dosaggi
        if click.confirm('\nMostrare guida dosaggi?', default=True):
            print_dilution_guide(total_mg, volume_ml)
    
    except Exception as e:
        click.echo(f"\n❌ Errore: {e}", err=True)
        import traceback
        traceback.print_exc()
    finally:
        manager.close()


@preparations.command('show')
@click.argument('prep_id', type=int)
@click.option('--db', default='peptide_management.db', hidden=True)
def show_preparation(prep_id, db):
    """Mostra dettagli completi di una preparazione."""
    manager = PeptideManager(db)
    
    try:
        prep = manager.get_preparation_details(prep_id)
        
        if not prep:
            click.echo(f"\n❌ Preparazione #{prep_id} non trovata", err=True)
            return
        
        percentage = (prep['volume_remaining_ml'] / prep['volume_ml'] * 100) if prep['volume_ml'] > 0 else 0
        
        click.echo(f"\n{'='*80}")
        click.echo(f"PREPARAZIONE #{prep_id}")
        click.echo(f"{'='*80}")
        click.echo(f"Batch: #{prep['batch_id']} - {prep['product_name']}")
        click.echo(f"Fornitore: {prep['supplier_name']}")
        click.echo(f"\nPreparazione:")
        click.echo(f"  Data: {prep['preparation_date']}")
        click.echo(f"  Scadenza: {prep['expiry_date'] or 'N/A'}")
        click.echo(f"  Fiale usate: {prep['vials_used']} x {prep['mg_per_vial']}mg = {prep['total_mg']}mg")
        click.echo(f"  Volume: {prep['volume_ml']}ml ({prep['diluent']})")
        click.echo(f"  Storage: {prep['storage_location'] or 'N/A'}")
        
        click.echo(f"\nConcentrazione:")
        click.echo(f"  Totale: {prep['concentration_mg_ml']:.3f}mg/ml ({prep['concentration_mg_ml']*1000:.1f}mcg/ml)")
        
        if len(prep['peptides']) > 1:
            click.echo(f"  Per peptide:")
            for pep in prep['peptides']:
                click.echo(f"    • {pep['name']}: {pep['concentration_mg_ml']:.3f}mg/ml")
        
        click.echo(f"\nUtilizzo:")
        click.echo(f"  Volume rimanente: {prep['volume_remaining_ml']:.1f}ml / {prep['volume_ml']}ml ({percentage:.0f}%)")
        click.echo(f"  Volume utilizzato: {prep['ml_used']:.1f}ml")
        click.echo(f"  Somministrazioni: {prep['administrations_count']}")
        
        if prep['notes']:
            click.echo(f"\nNote: {prep['notes']}")
        
        # Conversioni comuni
        click.echo(f"\nTabella Conversioni:")
        calc = DilutionCalculator()
        volumes = [0.1, 0.2, 0.25, 0.5, 1.0]
        for vol in volumes:
            mcg = calc.ml_to_mcg(vol, prep['concentration_mg_ml'])
            click.echo(f"  {vol}ml = {mcg:.1f}mcg")
        
        click.echo(f"{'='*80}\n")
    
    finally:
        manager.close()


@preparations.command('use')
@click.argument('prep_id', type=int, required=False)
@click.argument('ml_used', type=float, required=False)
@click.option('--db', default='peptide_management.db', hidden=True)
def use_preparation(prep_id, ml_used, db):
    """
    Registra utilizzo di una preparazione.
    
    \b
    Esempi:
      peptide-manager preparations use 1 0.25
      peptide-manager preparations use  (interattivo)
    """
    manager = PeptideManager(db)
    
    try:
        if prep_id is None:
            preps = manager.get_preparations(only_active=True)
            
            if not preps:
                click.echo("\n⚠️  Nessuna preparazione attiva")
                return
            
            click.echo("\n=== PREPARAZIONI ATTIVE ===\n")
            for p in preps[:10]:
                click.echo(f"[#{p['id']}] {p['batch_product']}")
                click.echo(f"  Volume: {p['volume_remaining_ml']:.1f}ml / {p['volume_ml']}ml")
                click.echo()
            
            prep_id = click.prompt('\nID Preparazione', type=int)
        
        prep = manager.get_preparation_details(prep_id)
        
        if not prep:
            click.echo(f"\n❌ Preparazione #{prep_id} non trovata", err=True)
            return
        
        if prep['volume_remaining_ml'] <= 0:
            click.echo(f"\n❌ Preparazione esaurita", err=True)
            return
        
        click.echo(f"\n[#{prep_id}] {prep['product_name']}")
        click.echo(f"Volume disponibile: {prep['volume_remaining_ml']:.1f}ml")
        click.echo(f"Concentrazione: {prep['concentration_mg_ml']:.3f}mg/ml ({prep['concentration_mg_ml']*1000:.1f}mcg/ml)")
        
        if ml_used is None:
            # Suggerisci dosi comuni
            click.echo("\nDosi comuni:")
            calc = DilutionCalculator()
            for mcg in [100, 250, 500]:
                ml = calc.mcg_to_ml(mcg, prep['concentration_mg_ml'])
                if ml <= prep['volume_remaining_ml']:
                    click.echo(f"  {mcg}mcg = {ml:.3f}ml")
            
            ml_used = click.prompt('\nml da utilizzare', type=float)
        
        # Calcola dose in mcg
        calc = DilutionCalculator()
        dose_mcg = calc.ml_to_mcg(ml_used, prep['concentration_mg_ml'])
        
        click.echo(f"\nDose: {ml_used}ml = {dose_mcg:.1f}mcg")
        
        # Dati somministrazione
        injection_site = click.prompt('Sito iniezione (opzionale)', default='', show_default=False)
        notes = click.prompt('Note (opzionale)', default='', show_default=False)
        
        if not click.confirm('\nConfermare utilizzo?', default=True):
            click.echo("Annullato.")
            return
        
        # Registra
        admin_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        success = manager.use_preparation(
            prep_id,
            ml_used,
            administration_datetime=admin_datetime,
            injection_site=injection_site if injection_site else None,
            notes=notes if notes else None
        )
        
        if success:
            click.echo(f"\n✓ Somministrazione registrata")
            click.echo(f"  Dose: {dose_mcg:.1f}mcg ({ml_used}ml)")
            click.echo(f"  Data/ora: {admin_datetime}\n")
    
    except Exception as e:
        click.echo(f"\n❌ Errore: {e}", err=True)
    finally:
        manager.close()


@preparations.command('expired')
@click.option('--db', default='peptide_management.db', hidden=True)
def expired_preparations(db):
    """Mostra preparazioni scadute con volume rimanente."""
    manager = PeptideManager(db)
    
    try:
        expired = manager.get_expired_preparations()
        
        if not expired:
            click.echo("\n✓ Nessuna preparazione scaduta\n")
            return
        
        click.echo(f"\n{'='*80}")
        click.echo(f"⚠️  PREPARAZIONI SCADUTE ({len(expired)})")
        click.echo(f"{'='*80}\n")
        
        for p in expired:
            days_expired = (datetime.now() - datetime.strptime(p['expiry_date'], '%Y-%m-%d')).days
            
            click.echo(f"[#{p['id']}] {p['product_name']}")
            click.echo(f"  Scaduta: {p['expiry_date']} ({days_expired} giorni fa)")
            click.echo(f"  Volume rimanente: {p['volume_remaining_ml']:.1f}ml")
            click.echo()
        
        click.echo(f"{'='*80}\n")
    
    finally:
        manager.close()


@preparations.command('calc')
@click.option('--mg', type=float, help='mg peptide disponibili')
@click.option('--volume', type=float, help='Volume diluente (ml)')
@click.option('--dose', type=float, help='Dose target (mcg)')
def calculator(mg, volume, dose):
    """
    Calcolatore diluizioni interattivo.
    
    \b
    Modalità:
      1. mg + volume → concentrazione e tabella dosi
      2. mg + dose → suggerimento diluizione ottimale
    """
    calc = DilutionCalculator()
    
    if mg and volume:
        # Modalità 1: Analisi preparazione
        concentration = calc.calculate_concentration(mg, volume)
        
        click.echo(f"\n{'='*60}")
        click.echo(f"ANALISI DILUIZIONE")
        click.echo(f"{'='*60}")
        click.echo(f"Peptide: {mg}mg in {volume}ml")
        click.echo(f"Concentrazione: {concentration:.3f}mg/ml ({concentration*1000:.1f}mcg/ml)")
        
        click.echo(f"\nTabella Dosaggi:")
        click.echo(f"{'Dose':<15} {'Volume':<15} {'Dosi Totali'}")
        click.echo(f"{'-'*60}")
        
        for dose_mcg in [100, 250, 500, 1000]:
            ml_needed = calc.mcg_to_ml(dose_mcg, concentration)
            num_doses = calc.doses_from_preparation(mg, volume, dose_mcg)
            click.echo(f"{dose_mcg}mcg{' ':<10} {ml_needed:.3f}ml{' ':<10} {num_doses}")
        
        click.echo(f"{'='*60}\n")
    
    elif mg and dose:
        # Modalità 2: Suggerimento
        suggestion = calc.suggested_dilution_for_dose(mg, dose, 0.2)
        
        click.echo(f"\n{'='*60}")
        click.echo(f"SUGGERIMENTO DILUIZIONE")
        click.echo(f"{'='*60}")
        click.echo(f"Peptide disponibile: {mg}mg")
        click.echo(f"Dose target: {dose}mcg")
        
        click.echo(f"\nDiluizione suggerita:")
        click.echo(f"  Volume diluente: {suggestion['volume_diluente_ml']}ml")
        click.echo(f"  Concentrazione: {suggestion['concentrazione_mg_ml']}mg/ml")
        click.echo(f"  Volume per dose: {suggestion['volume_per_dose_ml']}ml")
        click.echo(f"  Dosi totali: {suggestion['dosi_totali']}")
        click.echo(f"{'='*60}\n")
    
    else:
        # Modalità interattiva
        click.echo("\nCalcolatore Diluizioni\n")
        click.echo("Scegli modalità:")
        click.echo("  1) Ho già diluito - calcola concentrazione")
        click.echo("  2) Devo diluire - suggerisci volume")
        
        mode = click.prompt('Modalità', type=click.Choice(['1', '2']))
        
        if mode == '1':
            mg = click.prompt('mg peptide', type=float)
            volume = click.prompt('ml totali', type=float)
            print_dilution_guide(mg, volume)
        else:
            mg = click.prompt('mg peptide disponibili', type=float)
            dose = click.prompt('Dose target (mcg)', type=float, default=250)
            
            suggestion = calc.suggested_dilution_for_dose(mg, dose, 0.2)
            
            click.echo(f"\n💡 Usa {suggestion['volume_diluente_ml']}ml di diluente")
            click.echo(f"   Concentrazione: {suggestion['concentrazione_mg_ml']}mg/ml")
            click.echo(f"   Inietta {suggestion['volume_per_dose_ml']}ml per {dose}mcg")
            click.echo(f"   Dosi disponibili: {suggestion['dosi_totali']}\n")


@preparations.command('delete')
@click.argument('prep_id', type=int)
@click.option('--restore-vials', is_flag=True, help='Ripristina fiale al batch')
@click.option('--db', default='peptide_management.db', hidden=True)
def delete_preparation(prep_id, restore_vials, db):
    """
    Elimina una preparazione.
    
    Usa --restore-vials per riaggiungere le fiale al batch.
    """
    manager = PeptideManager(db)
    
    try:
        prep = manager.get_preparation_details(prep_id)
        
        if not prep:
            click.echo(f"\n❌ Preparazione #{prep_id} non trovata", err=True)
            return
        
        click.echo(f"\n⚠️  ELIMINAZIONE PREPARAZIONE")
        click.echo(f"{'='*60}")
        click.echo(f"ID: #{prep['id']}")
        click.echo(f"Batch: {prep['product_name']}")
        click.echo(f"Fiale usate: {prep['vials_used']}")
        click.echo(f"Volume: {prep['volume_remaining_ml']:.1f}ml / {prep['volume_ml']}ml")
        click.echo(f"Somministrazioni: {prep['administrations_count']}")
        
        if restore_vials:
            click.echo(f"\n→ Ripristinerà {prep['vials_used']} fiale al batch #{prep['batch_id']}")
        
        click.echo(f"{'='*60}")
        
        if not click.confirm('\n⚠️  CONFERMARE ELIMINAZIONE?', default=False):
            click.echo("Annullato.")
            return
        
        success = manager.delete_preparation(prep_id, restore_vials=restore_vials)
        
        if success:
            click.echo(f"\n✓ Preparazione #{prep_id} eliminata\n")
    
    except Exception as e:
        click.echo(f"\n❌ Errore: {e}", err=True)
    finally:
        manager.close()