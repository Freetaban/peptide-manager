"""
Comandi per gestione catalogo peptidi.
"""

import click
from peptide_manager import PeptideManager
import re
from collections import defaultdict


def normalize_peptide_name(name: str) -> str:
    """Normalizza nome peptide (BPC157 -> BPC-157)."""
    name = name.strip().upper()
    name = re.sub(r'([A-Z]+)(\d+)', r'\1-\2', name)
    name = re.sub(r'\s+', '-', name)
    name = re.sub(r'-+', '-', name)
    return name


def find_similar_peptides(manager, name: str) -> list:
    """Trova peptidi simili."""
    all_peptides = manager.get_peptides()
    normalized_name = normalize_peptide_name(name)
    
    similar = []
    for p in all_peptides:
        p_normalized = normalize_peptide_name(p['name'])
        if p_normalized == normalized_name:
            return [p]
        if p_normalized in normalized_name or normalized_name in p_normalized:
            similar.append(p)
    
    return similar


@click.group()
def peptides():
    """
    Gestione catalogo peptidi.
    
    \b
    Comandi disponibili:
      list        Lista peptidi
      add         Aggiungi peptide
      edit        Modifica peptide
      show        Dettagli peptide
      search      Cerca peptidi
      duplicates  Trova duplicati
      merge       Unisci duplicati
    """
    pass


@peptides.command('list')
@click.option('--db', default='peptide_management.db', hidden=True)
def list_peptides(db):
    """Lista tutti i peptidi nel catalogo."""
    manager = PeptideManager(db)
    
    try:
        peptides_list = manager.get_peptides()
        
        if not peptides_list:
            click.echo("Catalogo peptidi vuoto.")
            return
        
        click.echo(f"\n{'='*80}")
        click.echo(f"CATALOGO PEPTIDI ({len(peptides_list)})")
        click.echo(f"{'='*80}\n")
        
        for p in peptides_list:
            click.echo(f"[#{p['id']}] {p['name']}")
            if p['description']:
                click.echo(f"  {p['description']}")
            if p['common_uses']:
                click.echo(f"  Usi: {p['common_uses']}")
            click.echo()
    finally:
        manager.close()


@peptides.command('add')
@click.option('--name', prompt='Nome peptide')
@click.option('--description', prompt='Descrizione (opzionale)', default='')
@click.option('--uses', prompt='Usi comuni (opzionale)', default='')
@click.option('--notes', prompt='Note (opzionale)', default='')
@click.option('--db', default='peptide_management.db', hidden=True)
def add_peptide(name, description, uses, notes, db):
    """Aggiungi nuovo peptide al catalogo (con anti-duplicati)."""
    manager = PeptideManager(db)
    
    try:
        normalized_name = normalize_peptide_name(name)
        
        if normalized_name != name:
            click.echo(f"\n📝 Nome normalizzato: '{name}' -> '{normalized_name}'")
        
        similar = find_similar_peptides(manager, normalized_name)
        
        if similar:
            click.echo("\n⚠️  ATTENZIONE: Peptidi simili già presenti:")
            for p in similar:
                click.echo(f"  [#{p['id']}] {p['name']}")
                if p['description']:
                    click.echo(f"      {p['description']}")
            
            exact_match = any(normalize_peptide_name(p['name']) == normalized_name for p in similar)
            
            if exact_match:
                click.echo(f"\n❌ Peptide '{normalized_name}' già esistente!")
                click.echo("   Usa 'peptide-manager peptides edit' per modificarlo.")
                return
            
            if not click.confirm('\nProcedere comunque?', default=False):
                click.echo("Annullato.")
                return
        
        peptide_id = manager.add_peptide(
            name=normalized_name,
            description=description if description else None,
            common_uses=uses if uses else None,
            notes=notes if notes else None
        )
        click.echo(f"\n✓ Peptide '{normalized_name}' aggiunto (ID: {peptide_id})\n")
    
    except Exception as e:
        click.echo(f"\n❌ Errore: {e}", err=True)
    finally:
        manager.close()


@peptides.command('edit')
@click.argument('peptide_id', type=int, required=False)
@click.option('--db', default='peptide_management.db', hidden=True)
def edit_peptide(peptide_id, db):
    """Modifica un peptide esistente."""
    manager = PeptideManager(db)
    
    try:
        if peptide_id is None:
            peptides_list = manager.get_peptides()
            
            if not peptides_list:
                click.echo("\n⚠️  Catalogo vuoto")
                return
            
            click.echo("\n=== PEPTIDI ===\n")
            for p in peptides_list[:15]:
                click.echo(f"[#{p['id']}] {p['name']}")
            
            if len(peptides_list) > 15:
                click.echo(f"\n... e altri {len(peptides_list) - 15}")
            
            peptide_id = click.prompt('\nID Peptide', type=int)
        
        peptide = manager.get_peptide_by_id(peptide_id)
        
        if not peptide:
            click.echo(f"\n❌ Peptide #{peptide_id} non trovato", err=True)
            return
        
        click.echo(f"\n=== MODIFICA #{peptide_id} ===\n")
        click.echo(f"Attuale: {peptide['name']}")
        click.echo("(INVIO per mantenere)\n")
        
        new_name = click.prompt('Nome', default=peptide['name'])
        new_desc = click.prompt('Descrizione', default=peptide['description'] or '')
        new_uses = click.prompt('Usi', default=peptide['common_uses'] or '')
        new_notes = click.prompt('Note', default=peptide['notes'] or '')
        
        changes = {}
        if new_name != peptide['name']:
            changes['name'] = normalize_peptide_name(new_name)
        if new_desc != (peptide['description'] or ''):
            changes['description'] = new_desc if new_desc else None
        if new_uses != (peptide['common_uses'] or ''):
            changes['common_uses'] = new_uses if new_uses else None
        if new_notes != (peptide['notes'] or ''):
            changes['notes'] = new_notes if new_notes else None
        
        if not changes:
            click.echo("\n⚠️  Nessuna modifica")
            return
        
        if not click.confirm('\nConfermare?'):
            click.echo("Annullato.")
            return
        
        manager.update_peptide(peptide_id, **changes)
        click.echo(f"\n✓ Peptide #{peptide_id} aggiornato\n")
    
    except Exception as e:
        click.echo(f"\n❌ Errore: {e}", err=True)
    finally:
        manager.close()


@peptides.command('show')
@click.argument('peptide_id', type=int)
@click.option('--db', default='peptide_management.db', hidden=True)
def show_peptide(peptide_id, db):
    """Mostra dettagli peptide e dove è utilizzato."""
    manager = PeptideManager(db)
    
    try:
        peptide = manager.get_peptide_by_id(peptide_id)
        
        if not peptide:
            click.echo(f"\n❌ Peptide #{peptide_id} non trovato", err=True)
            return
        
        cursor = manager.conn.cursor()
        
        # Conta utilizzi
        cursor.execute('''
            SELECT COUNT(DISTINCT bc.batch_id)
            FROM batch_composition bc
            WHERE bc.peptide_id = ?
        ''', (peptide_id,))
        batch_count = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT COUNT(*)
            FROM protocol_peptides pp
            WHERE pp.peptide_id = ?
        ''', (peptide_id,))
        protocol_count = cursor.fetchone()[0]
        
        click.echo(f"\n{'='*60}")
        click.echo(f"PEPTIDE #{peptide_id}: {peptide['name']}")
        click.echo(f"{'='*60}")
        
        if peptide['description']:
            click.echo(f"Descrizione: {peptide['description']}")
        if peptide['common_uses']:
            click.echo(f"Usi comuni: {peptide['common_uses']}")
        if peptide['notes']:
            click.echo(f"Note: {peptide['notes']}")
        
        click.echo(f"\nUtilizzo:")
        click.echo(f"  Batches: {batch_count}")
        click.echo(f"  Protocolli: {protocol_count}")
        click.echo(f"{'='*60}\n")
    
    finally:
        manager.close()


@peptides.command('search')
@click.argument('query')
@click.option('--db', default='peptide_management.db', hidden=True)
def search_peptides(query, db):
    """Cerca peptidi per nome o descrizione."""
    manager = PeptideManager(db)
    
    try:
        results = manager.get_peptides(search=query)
        
        if not results:
            click.echo(f"Nessun peptide trovato per '{query}'")
            return
        
        click.echo(f"\nRisultati per '{query}' ({len(results)}):\n")
        for p in results:
            click.echo(f"[#{p['id']}] {p['name']}")
            if p['description']:
                click.echo(f"  {p['description']}")
            click.echo()
    finally:
        manager.close()


@peptides.command('duplicates')
@click.option('--db', default='peptide_management.db', hidden=True)
def find_duplicates(db):
    """Trova peptidi potenzialmente duplicati."""
    manager = PeptideManager(db)
    
    try:
        peptides_list = manager.get_peptides()
        
        if not peptides_list:
            click.echo("\n⚠️  Catalogo vuoto")
            return
        
        groups = defaultdict(list)
        
        for p in peptides_list:
            normalized = normalize_peptide_name(p['name'])
            groups[normalized].append(p)
        
        duplicates = {k: v for k, v in groups.items() if len(v) > 1}
        
        if not duplicates:
            click.echo(f"\n✓ Nessun duplicato! ({len(peptides_list)} peptidi univoci)\n")
            return
        
        click.echo(f"\n{'='*80}")
        click.echo("DUPLICATI TROVATI")
        click.echo(f"{'='*80}\n")
        
        cursor = manager.conn.cursor()
        
        for norm, group in duplicates.items():
            click.echo(f"Gruppo: {norm} ({len(group)} duplicati)\n")
            
            for p in group:
                cursor.execute('SELECT COUNT(*) FROM batch_composition WHERE peptide_id = ?', (p['id'],))
                batches = cursor.fetchone()[0]
                
                click.echo(f"  [#{p['id']}] {p['name']}")
                click.echo(f"      Batches: {batches}")
                click.echo()
            
            best = max(group, key=lambda x: (bool(x['description']), -x['id']))
            others = [p for p in group if p['id'] != best['id']]
            
            click.echo(f"  💡 Mantieni: [#{best['id']}] {best['name']}")
            for other in others:
                click.echo(f"     Comando: peptide-manager peptides merge {other['id']} {best['id']}")
            click.echo("\n" + "-"*80 + "\n")
        
        click.echo(f"Totale: {len(duplicates)} gruppi, {sum(len(g)-1 for g in duplicates.values())} da unire\n")
    
    finally:
        manager.close()


@peptides.command('merge')
@click.argument('source_id', type=int)
@click.argument('target_id', type=int)
@click.option('--db', default='peptide_management.db', hidden=True)
def merge_peptides(source_id, target_id, db):
    """
    Unisci peptidi duplicati.
    
    SOURCE viene eliminato, TARGET mantenuto.
    Tutti i riferimenti vengono aggiornati.
    """
    manager = PeptideManager(db)
    
    try:
        if source_id == target_id:
            click.echo("\n❌ Source e target devono essere diversi!")
            return
        
        source = manager.get_peptide_by_id(source_id)
        target = manager.get_peptide_by_id(target_id)
        
        if not source or not target:
            click.echo("\n❌ Peptide non trovato")
            return
        
        cursor = manager.conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM batch_composition WHERE peptide_id = ?', (source_id,))
        batch_refs = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM protocol_peptides WHERE peptide_id = ?', (source_id,))
        protocol_refs = cursor.fetchone()[0]
        
        click.echo(f"\n{'='*60}")
        click.echo("MERGE PEPTIDI")
        click.echo(f"{'='*60}")
        click.echo(f"\nELIMINA: [#{source['id']}] {source['name']}")
        click.echo(f"  Batch: {batch_refs} | Protocolli: {protocol_refs}")
        click.echo(f"\nMANTIENE: [#{target['id']}] {target['name']}")
        click.echo(f"{'='*60}")
        
        if not click.confirm('\n⚠️  CONFERMARE? (irreversibile)', default=False):
            click.echo("Annullato.")
            return
        
        click.echo("\n🔄 Merge...")
        
        # Batch
        cursor.execute('SELECT DISTINCT batch_id FROM batch_composition WHERE peptide_id = ?', (source_id,))
        batches = [r[0] for r in cursor.fetchall()]
        
        updated = skipped = 0
        for bid in batches:
            cursor.execute('SELECT COUNT(*) FROM batch_composition WHERE batch_id=? AND peptide_id=?', 
                          (bid, target_id))
            if cursor.fetchone()[0] > 0:
                cursor.execute('DELETE FROM batch_composition WHERE batch_id=? AND peptide_id=?',
                              (bid, source_id))
                skipped += 1
            else:
                cursor.execute('UPDATE batch_composition SET peptide_id=? WHERE batch_id=? AND peptide_id=?',
                              (target_id, bid, source_id))
                updated += 1
        
        click.echo(f"  ✓ Batch: {updated} aggiornati, {skipped} duplicati rimossi")
        
        # Protocols
        cursor.execute('SELECT DISTINCT protocol_id FROM protocol_peptides WHERE peptide_id = ?', (source_id,))
        protocols = [r[0] for r in cursor.fetchall()]
        
        updated_p = skipped_p = 0
        for pid in protocols:
            cursor.execute('SELECT COUNT(*) FROM protocol_peptides WHERE protocol_id=? AND peptide_id=?',
                          (pid, target_id))
            if cursor.fetchone()[0] > 0:
                cursor.execute('DELETE FROM protocol_peptides WHERE protocol_id=? AND peptide_id=?',
                              (pid, source_id))
                skipped_p += 1
            else:
                cursor.execute('UPDATE protocol_peptides SET peptide_id=? WHERE protocol_id=? AND peptide_id=?',
                              (target_id, pid, source_id))
                updated_p += 1
        
        click.echo(f"  ✓ Protocolli: {updated_p} aggiornati, {skipped_p} duplicati rimossi")
        
        cursor.execute('DELETE FROM peptides WHERE id = ?', (source_id,))
        
        manager.conn.commit()
        
        click.echo(f"\n✓✓✓ MERGE COMPLETATO ✓✓✓")
        click.echo(f"Tutto punta ora a: [#{target['id']}] {target['name']}\n")
    
    except Exception as e:
        click.echo(f"\n❌ Errore: {e}", err=True)
    finally:
        manager.close()

@peptides.command('delete')
@click.argument('peptide_id', type=int)
@click.option('--force', is_flag=True, help='Forza eliminazione anche con riferimenti')
@click.option('--db', default='peptide_management.db', hidden=True)
def delete_peptide(peptide_id, force, db):
    """
    Elimina un peptide dal catalogo.
    
    ⚠️  ATTENZIONE: Operazione irreversibile!
    """
    manager = PeptideManager(db)
    
    try:
        peptide = manager.get_peptide_by_id(peptide_id)
        
        if not peptide:
            click.echo(f"\n❌ Peptide #{peptide_id} non trovato", err=True)
            return
        
        click.echo(f"\n⚠️  ELIMINAZIONE PEPTIDE")
        click.echo(f"{'='*60}")
        click.echo(f"ID: #{peptide['id']}")
        click.echo(f"Nome: {peptide['name']}")
        if peptide['description']:
            click.echo(f"Descrizione: {peptide['description']}")
        click.echo(f"{'='*60}")
        
        if not click.confirm('\n⚠️  CONFERMARE ELIMINAZIONE? (irreversibile)', default=False):
            click.echo("Annullato.")
            return
        
        success = manager.delete_peptide(peptide_id, force=force)
        
        if success:
            click.echo(f"\n✓ Peptide #{peptide_id} eliminato\n")
    
    except Exception as e:
        click.echo(f"\n❌ Errore: {e}", err=True)
    finally:
        manager.close()
