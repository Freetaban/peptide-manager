"""
Comandi per gestione protocolli di dosaggio.
"""

import click
from peptide_manager import PeptideManager
from datetime import datetime, timedelta


@click.group()
def protocols():
    """
    Gestione protocolli di dosaggio.
    
    \b
    Comandi disponibili:
      list        Lista protocolli
      add         Crea protocollo
      show        Dettagli protocollo
      edit        Modifica protocollo
      activate    Attiva protocollo
      deactivate  Disattiva protocollo
      log         Log somministrazioni
      stats       Statistiche protocollo
    """
    pass


@protocols.command('list')
@click.option('--all', 'show_all', is_flag=True, help='Mostra anche disattivati')
@click.option('--db', default='peptide_management.db', hidden=True)
def list_protocols(show_all, db):
    """Lista tutti i protocolli."""
    manager = PeptideManager(db)
    
    try:
        protos = manager.get_protocols(active_only=not show_all)
        
        if not protos:
            click.echo("Nessun protocollo trovato.")
            return
        
        status = "TUTTI" if show_all else "ATTIVI"
        click.echo(f"\n{'='*80}")
        click.echo(f"PROTOCOLLI {status} ({len(protos)})")
        click.echo(f"{'='*80}\n")
        
        for p in protos:
            status_icon = '✓' if p['active'] else '✗'
            click.echo(f"[#{p['id']}] {status_icon} {p['name']}")
            
            if p['description']:
                click.echo(f"  {p['description']}")
            
            click.echo(f"  Dose: {p['dose_ml']}ml x {p['frequency_per_day']}/giorno")
            
            if p['days_on']:
                schema = f"{p['days_on']} giorni ON"
                if p['days_off'] > 0:
                    schema += f", {p['days_off']} giorni OFF"
                click.echo(f"  Schema: {schema}")
            
            if p['cycle_duration_weeks']:
                click.echo(f"  Durata: {p['cycle_duration_weeks']} settimane")
            
            click.echo()
    finally:
        manager.close()


@protocols.command('add')
@click.option('--db', default='peptide_management.db', hidden=True)
def add_protocol(db):
    """Crea un nuovo protocollo (wizard completo)."""
    manager = PeptideManager(db)
    
    try:
        click.echo("\n=== NUOVO PROTOCOLLO ===\n")
        
        name = click.prompt('Nome protocollo')
        description = click.prompt('Descrizione (opzionale)', default='', show_default=False)
        
        click.echo("\n--- Dosaggio ---")
        dose_ml = click.prompt('Dose per somministrazione (ml)', type=float)
        frequency = click.prompt('Somministrazioni al giorno', type=int, default=1)
        
        click.echo("\n--- Schema Ciclo ---")
        has_cycle = click.confirm('Specificare schema on/off?', default=True)
        
        days_on = None
        days_off = 0
        cycle_weeks = None
        
        if has_cycle:
            days_on = click.prompt('Giorni ON (somministrazione)', type=int)
            days_off = click.prompt('Giorni OFF (pausa)', type=int, default=0)
            cycle_weeks = click.prompt('Durata totale ciclo (settimane)', type=int, default=4)
        
        click.echo("\n--- Peptidi nel Protocollo ---")
        click.echo("Inserisci i peptidi richiesti per questo protocollo")
        
        peptides = []
        peptide_num = 1
        
        while True:
            click.echo(f"\nPeptide #{peptide_num}:")
            pep_name = click.prompt('  Nome (o INVIO per terminare)', default='', show_default=False)
            
            if not pep_name:
                break
            
            target_dose = click.prompt('  Dose target (mcg)', type=float)
            peptides.append((pep_name, target_dose))
            peptide_num += 1
        
        notes = click.prompt('\nNote (opzionale)', default='', show_default=False)
        
        # Riepilogo
        click.echo("\n" + "="*80)
        click.echo("RIEPILOGO PROTOCOLLO")
        click.echo("="*80)
        click.echo(f"Nome: {name}")
        if description:
            click.echo(f"Descrizione: {description}")
        click.echo(f"Dosaggio: {dose_ml}ml x {frequency}/giorno")
        
        if days_on:
            click.echo(f"Schema: {days_on} giorni ON, {days_off} giorni OFF")
            if cycle_weeks:
                click.echo(f"Durata: {cycle_weeks} settimane")
        
        if peptides:
            click.echo("\nPeptidi richiesti:")
            for pname, pdose in peptides:
                click.echo(f"  • {pname}: {pdose}mcg")
        
        if notes:
            click.echo(f"\nNote: {notes}")
        
        click.echo("="*80)
        
        if not click.confirm('\nConfermare?'):
            click.echo("Annullato.")
            return
        
        # Crea protocollo
        protocol_id = manager.add_protocol(
            name=name,
            dose_ml=dose_ml,
            frequency_per_day=frequency,
            days_on=days_on,
            days_off=days_off,
            cycle_duration_weeks=cycle_weeks,
            peptides=peptides if peptides else None,
            description=description if description else None,
            notes=notes if notes else None
        )
        
        click.echo(f"\n✓✓✓ Protocollo #{protocol_id} creato! ✓✓✓\n")
    
    except Exception as e:
        click.echo(f"\n❌ Errore: {e}", err=True)
    finally:
        manager.close()


@protocols.command('show')
@click.argument('protocol_id', type=int)
@click.option('--db', default='peptide_management.db', hidden=True)
def show_protocol(protocol_id, db):
    """Mostra dettagli completi di un protocollo."""
    manager = PeptideManager(db)
    
    try:
        protocol = manager.get_protocol_details(protocol_id)
        
        if not protocol:
            click.echo(f"\n❌ Protocollo #{protocol_id} non trovato", err=True)
            return
        
        status = '✓ ATTIVO' if protocol['active'] else '✗ DISATTIVATO'
        
        click.echo(f"\n{'='*80}")
        click.echo(f"PROTOCOLLO #{protocol_id}: {protocol['name']} [{status}]")
        click.echo(f"{'='*80}")
        
        if protocol['description']:
            click.echo(f"\n{protocol['description']}")
        
        click.echo(f"\nDosaggio:")
        click.echo(f"  Dose: {protocol['dose_ml']}ml per somministrazione")
        click.echo(f"  Frequenza: {protocol['frequency_per_day']}x al giorno")
        
        if protocol['days_on']:
            click.echo(f"\nSchema Ciclo:")
            click.echo(f"  {protocol['days_on']} giorni ON, {protocol['days_off']} giorni OFF")
            if protocol['cycle_duration_weeks']:
                click.echo(f"  Durata totale: {protocol['cycle_duration_weeks']} settimane")
        
        if protocol['peptides']:
            click.echo(f"\nPeptidi Richiesti:")
            for pep in protocol['peptides']:
                click.echo(f"  • {pep['name']}: {pep['target_dose_mcg']}mcg")
        
        if protocol['administrations_count'] > 0:
            click.echo(f"\nStorico Somministrazioni:")
            click.echo(f"  Totale: {protocol['administrations_count']}")
            click.echo(f"  Prima: {protocol['first_administration']}")
            click.echo(f"  Ultima: {protocol['last_administration']}")
        
        if protocol['notes']:
            click.echo(f"\nNote:")
            click.echo(f"  {protocol['notes']}")
        
        click.echo(f"{'='*80}\n")
    
    finally:
        manager.close()


@protocols.command('edit')
@click.argument('protocol_id', type=int, required=False)
@click.option('--db', default='peptide_management.db', hidden=True)
def edit_protocol(protocol_id, db):
    """Modifica un protocollo esistente."""
    manager = PeptideManager(db)
    
    try:
        if protocol_id is None:
            protos = manager.get_protocols(active_only=False)
            
            if not protos:
                click.echo("\n⚠️  Nessun protocollo")
                return
            
            click.echo("\n=== PROTOCOLLI ===\n")
            for p in protos[:10]:
                status = '✓' if p['active'] else '✗'
                click.echo(f"[#{p['id']}] {status} {p['name']}")
            
            protocol_id = click.prompt('\nID Protocollo', type=int)
        
        protocol = manager.get_protocol_details(protocol_id)
        
        if not protocol:
            click.echo(f"\n❌ Protocollo #{protocol_id} non trovato", err=True)
            return
        
        click.echo(f"\n=== MODIFICA #{protocol_id} ===\n")
        click.echo(f"Attuale: {protocol['name']}")
        click.echo("(INVIO per mantenere)\n")
        
        new_name = click.prompt('Nome', default=protocol['name'])
        new_desc = click.prompt('Descrizione', default=protocol['description'] or '')
        new_dose = click.prompt('Dose (ml)', type=float, default=protocol['dose_ml'])
        new_freq = click.prompt('Frequenza/giorno', type=int, default=protocol['frequency_per_day'])
        new_days_on = click.prompt('Giorni ON', type=int, default=protocol['days_on'] or 0)
        new_days_off = click.prompt('Giorni OFF', type=int, default=protocol['days_off'] or 0)
        new_weeks = click.prompt('Durata (settimane)', type=int, default=protocol['cycle_duration_weeks'] or 0)
        new_notes = click.prompt('Note', default=protocol['notes'] or '')
        
        changes = {}
        if new_name != protocol['name']:
            changes['name'] = new_name
        if new_desc != (protocol['description'] or ''):
            changes['description'] = new_desc if new_desc else None
        if new_dose != protocol['dose_ml']:
            changes['dose_ml'] = new_dose
        if new_freq != protocol['frequency_per_day']:
            changes['frequency_per_day'] = new_freq
        if new_days_on != (protocol['days_on'] or 0):
            changes['days_on'] = new_days_on if new_days_on > 0 else None
        if new_days_off != (protocol['days_off'] or 0):
            changes['days_off'] = new_days_off
        if new_weeks != (protocol['cycle_duration_weeks'] or 0):
            changes['cycle_duration_weeks'] = new_weeks if new_weeks > 0 else None
        if new_notes != (protocol['notes'] or ''):
            changes['notes'] = new_notes if new_notes else None
        
        if not changes:
            click.echo("\n⚠️  Nessuna modifica")
            return
        
        if not click.confirm('\nConfermare?'):
            click.echo("Annullato.")
            return
        
        manager.update_protocol(protocol_id, **changes)
        click.echo(f"\n✓ Protocollo #{protocol_id} aggiornato\n")
    
    except Exception as e:
        click.echo(f"\n❌ Errore: {e}", err=True)
    finally:
        manager.close()


@protocols.command('activate')
@click.argument('protocol_id', type=int)
@click.option('--db', default='peptide_management.db', hidden=True)
def activate(protocol_id, db):
    """Attiva un protocollo."""
    manager = PeptideManager(db)
    
    try:
        success = manager.activate_protocol(protocol_id)
        if success:
            click.echo(f"\n✓ Protocollo #{protocol_id} attivato\n")
    finally:
        manager.close()


@protocols.command('deactivate')
@click.argument('protocol_id', type=int)
@click.option('--db', default='peptide_management.db', hidden=True)
def deactivate(protocol_id, db):
    """Disattiva un protocollo."""
    manager = PeptideManager(db)
    
    try:
        success = manager.deactivate_protocol(protocol_id)
        if success:
            click.echo(f"\n✓ Protocollo #{protocol_id} disattivato\n")
    finally:
        manager.close()


@protocols.command('log')
@click.option('--protocol', 'protocol_id', type=int, help='Filtra per protocollo')
@click.option('--days', type=int, default=7, help='Ultimi N giorni')
@click.option('--db', default='peptide_management.db', hidden=True)
def log_administrations(protocol_id, days, db):
    """Mostra log somministrazioni."""
    manager = PeptideManager(db)
    
    try:
        administrations = manager.get_administrations(
            protocol_id=protocol_id,
            days_back=days
        )
        
        if not administrations:
            click.echo(f"\nNessuna somministrazione negli ultimi {days} giorni.\n")
            return
        
        click.echo(f"\n{'='*80}")
        title = f"SOMMINISTRAZIONI (ultimi {days} giorni)"
        if protocol_id:
            click.echo(f"{title} - Protocollo #{protocol_id}")
        else:
            click.echo(title)
        click.echo(f"{'='*80}\n")
        
        for admin in administrations:
            admin_date = datetime.strptime(admin['administration_datetime'], '%Y-%m-%d %H:%M:%S')
            date_str = admin_date.strftime('%Y-%m-%d %H:%M')
            
            click.echo(f"[#{admin['id']}] {date_str}")
            
            if admin['protocol_name']:
                click.echo(f"  Protocollo: {admin['protocol_name']}")
            
            if admin['batch_product']:
                click.echo(f"  Preparazione: #{admin['preparation_id']} ({admin['batch_product']})")
            
            click.echo(f"  Dose: {admin['dose_ml']}ml")
            
            if admin['injection_site']:
                click.echo(f"  Sito: {admin['injection_site']}")
            
            if admin['notes']:
                click.echo(f"  Note: {admin['notes']}")
            
            if admin['side_effects']:
                click.echo(f"  ⚠️  Side effects: {admin['side_effects']}")
            
            click.echo()
        
        click.echo(f"Totale: {len(administrations)} somministrazioni")
        click.echo(f"{'='*80}\n")
    
    finally:
        manager.close()


@protocols.command('stats')
@click.argument('protocol_id', type=int)
@click.option('--db', default='peptide_management.db', hidden=True)
def protocol_stats(protocol_id, db):
    """Mostra statistiche di aderenza al protocollo."""
    manager = PeptideManager(db)
    
    try:
        protocol = manager.get_protocol_details(protocol_id)
        
        if not protocol:
            click.echo(f"\n❌ Protocollo #{protocol_id} non trovato", err=True)
            return
        
        stats = manager.get_protocol_statistics(protocol_id)
        
        click.echo(f"\n{'='*80}")
        click.echo(f"STATISTICHE PROTOCOLLO #{protocol_id}: {protocol['name']}")
        click.echo(f"{'='*80}")
        
        if stats['total_administrations'] == 0:
            click.echo("\nNessuna somministrazione registrata per questo protocollo.\n")
            return
        
        click.echo(f"\nPeriodo:")
        click.echo(f"  Inizio: {stats['first_date']}")
        click.echo(f"  Fine: {stats['last_date']}")
        click.echo(f"  Giorni trascorsi: {stats['days_elapsed']}")
        click.echo(f"  Giorni attivi: {stats['days_active']}")
        
        click.echo(f"\nSomministrazioni:")
        click.echo(f"  Effettuate: {stats['total_administrations']}")
        click.echo(f"  Previste: {stats['expected_administrations']}")
        click.echo(f"  Volume totale: {stats['total_ml_used']:.2f}ml")
        
        adherence = stats['adherence_percentage']
        adherence_icon = '✓' if adherence >= 80 else '⚠️' if adherence >= 60 else '❌'
        
        click.echo(f"\nAderenza:")
        click.echo(f"  {adherence_icon} {adherence}%")
        
        if adherence < 80:
            missed = stats['expected_administrations'] - stats['total_administrations']
            click.echo(f"  Dosi mancate: {missed}")
        
        # Calcola media giornaliera
        if stats['days_active'] > 0:
            avg_per_day = stats['total_administrations'] / stats['days_active']
            click.echo(f"\nMedia:")
            click.echo(f"  {avg_per_day:.1f} somministrazioni/giorno attivo")
        
        click.echo(f"{'='*80}\n")
    
    finally:
        manager.close()


@protocols.command('link-admin')
@click.argument('admin_id', type=int, required=False)
@click.argument('protocol_id', type=int, required=False)
@click.option('--db', default='peptide_management.db', hidden=True)
def link_administration(admin_id, protocol_id, db):
    """
    Collega una somministrazione esistente a un protocollo.
    
    Utile quando hai già registrato somministrazioni prima
    di creare il protocollo.
    
    \b
    Esempio:
      peptide-manager protocols link-admin 1 2
      (collega somministrazione #1 a protocollo #2)
    """
    manager = PeptideManager(db)
    
    try:
        # Modalità interattiva se mancano argomenti
        if admin_id is None or protocol_id is None:
            click.echo("\n=== COLLEGA SOMMINISTRAZIONE A PROTOCOLLO ===\n")
            
            # Mostra somministrazioni senza protocollo
            cursor = manager.conn.cursor()
            cursor.execute('''
                SELECT a.id, a.administration_datetime, a.dose_ml,
                       prep.batch_id, b.product_name
                FROM administrations a
                JOIN preparations prep ON a.preparation_id = prep.id
                JOIN batches b ON prep.batch_id = b.id
                WHERE a.protocol_id IS NULL
                ORDER BY a.administration_datetime DESC
                LIMIT 20
            ''')
            
            unlinked = cursor.fetchall()
            
            if not unlinked:
                click.echo("✓ Tutte le somministrazioni sono già collegate a protocolli.\n")
                return
            
            click.echo(f"Somministrazioni NON collegate a protocolli ({len(unlinked)}):\n")
            for aid, adate, dose, bid, product in unlinked:
                date_str = datetime.strptime(adate, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M')
                click.echo(f"[#{aid}] {date_str} - {dose}ml ({product})")
            
            click.echo()
            admin_id = click.prompt('ID Somministrazione da collegare', type=int)
            
            # Mostra protocolli disponibili
            protocols = manager.get_protocols(active_only=False)
            
            if not protocols:
                click.echo("\n⚠️  Nessun protocollo. Creane uno prima con 'protocols add'")
                return
            
            click.echo("\nProtocolli disponibili:\n")
            for p in protocols:
                status = '✓' if p['active'] else '✗'
                click.echo(f"[#{p['id']}] {status} {p['name']}")
            
            click.echo()
            protocol_id = click.prompt('ID Protocollo', type=int)
        
        # Esegui collegamento
        success = manager.link_administration_to_protocol(admin_id, protocol_id)
        
        if success:
            click.echo(f"\n✓ Somministrazione #{admin_id} ora fa parte del protocollo #{protocol_id}\n")
    
    except Exception as e:
        click.echo(f"\n❌ Errore: {e}", err=True)
    finally:
        manager.close()


@protocols.command('link-batch')
@click.option('--protocol', 'protocol_id', type=int, prompt='ID Protocollo')
@click.option('--preparation', 'prep_id', type=int, help='Collega tutte le admin da questa preparazione')
@click.option('--days', type=int, help='Collega admin degli ultimi N giorni')
@click.option('--db', default='peptide_management.db', hidden=True)
def link_batch_administrations(protocol_id, prep_id, days, db):
    """
    Collega in batch più somministrazioni a un protocollo.
    
    \b
    Esempi:
      # Tutte le somministrazioni da preparazione #1
      peptide-manager protocols link-batch --protocol 1 --preparation 1
      
      # Tutte le somministrazioni degli ultimi 7 giorni
      peptide-manager protocols link-batch --protocol 1 --days 7
    """
    manager = PeptideManager(db)
    
    try:
        cursor = manager.conn.cursor()
        
        # Query per trovare somministrazioni
        query = '''
            SELECT id, administration_datetime, dose_ml
            FROM administrations
            WHERE protocol_id IS NULL
        '''
        params = []
        
        if prep_id:
            query += ' AND preparation_id = ?'
            params.append(prep_id)
        
        if days:
            query += ' AND administration_datetime >= datetime("now", ?)'
            params.append(f'-{days} days')
        
        query += ' ORDER BY administration_datetime'
        
        cursor.execute(query, params)
        admins = cursor.fetchall()
        
        if not admins:
            click.echo("\n⚠️  Nessuna somministrazione trovata con questi criteri.\n")
            return
        
        # Mostra riepilogo
        click.echo(f"\n{'='*60}")
        click.echo(f"SOMMINISTRAZIONI DA COLLEGARE: {len(admins)}")
        click.echo(f"{'='*60}\n")
        
        for aid, adate, dose in admins[:10]:
            date_str = datetime.strptime(adate, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M')
            click.echo(f"[#{aid}] {date_str} - {dose}ml")
        
        if len(admins) > 10:
            click.echo(f"... e altre {len(admins) - 10}")
        
        click.echo(f"\n{'='*60}")
        
        if not click.confirm(f'\nCollegare tutte al protocollo #{protocol_id}?'):
            click.echo("Annullato.")
            return
        
        # Collega
        admin_ids = [a[0] for a in admins]
        updated = manager.link_multiple_administrations_to_protocol(admin_ids, protocol_id)
        
        click.echo(f"\n✓ {updated} somministrazioni collegate al protocollo #{protocol_id}\n")
    
    except Exception as e:
        click.echo(f"\n❌ Errore: {e}", err=True)
    finally:
        manager.close()


@protocols.command('delete')
@click.argument('protocol_id', type=int)
@click.option('--keep-admins', is_flag=True, help='Mantieni somministrazioni (scollegate)')
@click.option('--db', default='peptide_management.db', hidden=True)
def delete_protocol(protocol_id, keep_admins, db):
    """
    Elimina un protocollo.
    
    Default: scollega somministrazioni (non le elimina).
    """
    manager = PeptideManager(db)
    
    try:
        protocol = manager.get_protocol_details(protocol_id)
        
        if not protocol:
            click.echo(f"\n❌ Protocollo #{protocol_id} non trovato", err=True)
            return
        
        click.echo(f"\n⚠️  ELIMINAZIONE PROTOCOLLO")
        click.echo(f"{'='*60}")
        click.echo(f"ID: #{protocol['id']}")
        click.echo(f"Nome: {protocol['name']}")
        click.echo(f"Somministrazioni: {protocol['administrations_count']}")
        
        if protocol['administrations_count'] > 0:
            click.echo(f"\n→ Le somministrazioni verranno SCOLLEGATE (non eliminate)")
        
        click.echo(f"{'='*60}")
        
        if not click.confirm('\n⚠️  CONFERMARE ELIMINAZIONE?', default=False):
            click.echo("Annullato.")
            return
        
        success = manager.delete_protocol(protocol_id, unlink_administrations=True)
        
        if success:
            click.echo(f"\n✓ Protocollo #{protocol_id} eliminato\n")
    
    except Exception as e:
        click.echo(f"\n❌ Errore: {e}", err=True)
    finally:
        manager.close()