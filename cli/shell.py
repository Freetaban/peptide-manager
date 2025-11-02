"""
Interactive shell (REPL) con menu gerarchici per Peptide Management System.
"""

import cmd
import sys
from peptide_manager import PeptideManager
from peptide_manager.calculator import DilutionCalculator
import shlex
from datetime import datetime


# ============================================================
# BASE SHELL CLASS
# ============================================================

class BaseShell(cmd.Cmd):
    """Classe base per tutte le shell."""
    
    def __init__(self, manager):
        super().__init__()
        self.manager = manager
    
    def emptyline(self):
        """Non fare nulla su linea vuota."""
        pass
    
    def default(self, line):
        """Gestisci comandi non riconosciuti."""
        print(f"\n❌ Comando '{line}' non riconosciuto")
        print("Digita 'help' per lista comandi")
    
    def do_clear(self, arg):
        """Pulisci lo schermo."""
        import os
        os.system('cls' if os.name == 'nt' else 'clear')


# ============================================================
# SUB-SHELLS (menu tematici)
# ============================================================

class PeptidesShell(BaseShell):
    """Sub-shell per gestione peptidi."""
    
    intro = "\n→ Entrato in modalità PEPTIDES (digita 'help' per comandi, 'back' per tornare)\n"
    prompt = '[PEPTIDES]> '
    
    def do_back(self, arg):
        """Torna al menu principale."""
        return True
    
    def do_list(self, arg):
        """Lista peptidi nel catalogo."""
        peptides = self.manager.get_peptides()
        
        if not peptides:
            print("\nCatalogo peptidi vuoto.")
            return
        
        print(f"\n{'='*70}")
        print(f"CATALOGO PEPTIDI ({len(peptides)})")
        print(f"{'='*70}")
        
        for p in peptides:
            print(f"[#{p['id']}] {p['name']}")
            if p['description']:
                print(f"  {p['description']}")
        
        print(f"{'='*70}")
    
    def do_show(self, arg):
        """Mostra dettagli peptide. Uso: show <id>"""
        if not arg:
            print("❌ Uso: show <id>")
            return
        
        try:
            peptide_id = int(arg)
            peptide = self.manager.get_peptide_by_id(peptide_id)
            
            if not peptide:
                print(f"\n❌ Peptide #{peptide_id} non trovato")
                return
            
            # Conta utilizzi
            cursor = self.manager.conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM batch_composition WHERE peptide_id = ?', (peptide_id,))
            batches = cursor.fetchone()[0]
            
            print(f"\n{'='*70}")
            print(f"PEPTIDE #{peptide['id']}: {peptide['name']}")
            print(f"{'='*70}")
            if peptide['description']:
                print(f"Descrizione: {peptide['description']}")
            if peptide['common_uses']:
                print(f"Usi comuni: {peptide['common_uses']}")
            if peptide['notes']:
                print(f"Note: {peptide['notes']}")
            print(f"\nPresente in {batches} batches")
            print(f"{'='*70}")
        
        except ValueError:
            print("❌ ID deve essere un numero")
    
    def do_duplicates(self, arg):
        """Trova peptidi duplicati."""
        from collections import defaultdict
        import re
        
        def normalize(name):
            name = name.strip().upper()
            name = re.sub(r'([A-Z]+)(\d+)', r'\1-\2', name)
            name = re.sub(r'\s+', '-', name)
            return re.sub(r'-+', '-', name)
        
        peptides = self.manager.get_peptides()
        groups = defaultdict(list)
        
        for p in peptides:
            normalized = normalize(p['name'])
            groups[normalized].append(p)
        
        duplicates = {k: v for k, v in groups.items() if len(v) > 1}
        
        if not duplicates:
            print("\n✓ Nessun duplicato trovato!")
            return
        
        print(f"\n{'='*70}")
        print(f"DUPLICATI TROVATI ({len(duplicates)} gruppi)")
        print(f"{'='*70}")
        
        for norm, group in duplicates.items():
            print(f"\nGruppo: {norm}")
            for p in group:
                print(f"  [#{p['id']}] {p['name']}")
            
            best = max(group, key=lambda x: (bool(x['description']), -x['id']))
            others = [p for p in group if p['id'] != best['id']]
            
            if others:
                print(f"  💡 Suggerimento:")
                print(f"     Mantieni: [#{best['id']}] {best['name']}")
                for other in others:
                    print(f"     merge {other['id']} {best['id']}")
        
        print(f"\n{'='*70}")
    
    def do_merge(self, arg):
        """Unisci peptidi duplicati. Uso: merge <source_id> <target_id>"""
        args = arg.split()
        if len(args) != 2:
            print("❌ Uso: merge <source_id> <target_id>")
            return
        
        try:
            source_id = int(args[0])
            target_id = int(args[1])
            
            source = self.manager.get_peptide_by_id(source_id)
            target = self.manager.get_peptide_by_id(target_id)
            
            if not source or not target:
                print("\n❌ Peptide non trovato")
                return
            
            print(f"\n⚠️  MERGE: {source['name']} (#{source_id}) → {target['name']} (#{target_id})")
            
            confirm = input("Confermare? (y/n): ")
            if confirm.lower() != 'y':
                print("Annullato.")
                return
            
            # Esegui merge (implementazione semplificata)
            cursor = self.manager.conn.cursor()
            
            # Sposta riferimenti
            cursor.execute('UPDATE batch_composition SET peptide_id = ? WHERE peptide_id = ?', 
                          (target_id, source_id))
            cursor.execute('DELETE FROM peptides WHERE id = ?', (source_id,))
            
            self.manager.conn.commit()
            print(f"\n✓ Merge completato")
        
        except ValueError:
            print("❌ Gli ID devono essere numeri")


class SuppliersShell(BaseShell):
    """Sub-shell per gestione fornitori."""
    
    intro = "\n→ Entrato in modalità SUPPLIERS (digita 'help' per comandi, 'back' per tornare)\n"
    prompt = '[SUPPLIERS]> '
    
    def do_back(self, arg):
        """Torna al menu principale."""
        return True
    
    def do_list(self, arg):
        """Lista fornitori."""
        suppliers = self.manager.get_suppliers()
        
        if not suppliers:
            print("\nNessun fornitore registrato.")
            return
        
        print(f"\n{'='*70}")
        print(f"FORNITORI ({len(suppliers)})")
        print(f"{'='*70}")
        
        for s in suppliers:
            stars = '★' * (s['reliability_rating'] or 0)
            print(f"[#{s['id']}] {s['name']} ({s['country'] or 'N/A'})")
            if s['reliability_rating']:
                print(f"  Rating: {stars} ({s['reliability_rating']}/5)")
        
        print(f"{'='*70}")
    
    def do_show(self, arg):
        """Mostra dettagli fornitore. Uso: show <id>"""
        if not arg:
            print("❌ Uso: show <id>")
            return
        
        try:
            supplier_id = int(arg)
            suppliers = self.manager.get_suppliers()
            supplier = next((s for s in suppliers if s['id'] == supplier_id), None)
            
            if not supplier:
                print(f"\n❌ Fornitore #{supplier_id} non trovato")
                return
            
            cursor = self.manager.conn.cursor()
            cursor.execute('''
                SELECT COUNT(*), SUM(total_price)
                FROM batches WHERE supplier_id = ?
            ''', (supplier_id,))
            orders, spent = cursor.fetchone()
            
            print(f"\n{'='*70}")
            print(f"FORNITORE #{supplier['id']}: {supplier['name']}")
            print(f"{'='*70}")
            print(f"Paese: {supplier['country'] or 'N/A'}")
            if supplier['website']:
                print(f"Website: {supplier['website']}")
            if supplier['reliability_rating']:
                stars = '★' * supplier['reliability_rating']
                print(f"Rating: {stars} ({supplier['reliability_rating']}/5)")
            print(f"\nOrdini: {orders or 0}")
            print(f"Spesa totale: €{spent or 0:.2f}")
            print(f"{'='*70}")
        
        except ValueError:
            print("❌ ID deve essere un numero")
    
    def do_stats(self, arg):
        """Mostra statistiche comparative."""
        cursor = self.manager.conn.cursor()
        
        cursor.execute('''
            SELECT s.id, s.name, s.reliability_rating,
                   COUNT(b.id) as orders, SUM(b.total_price) as spent
            FROM suppliers s
            LEFT JOIN batches b ON s.id = b.supplier_id
            GROUP BY s.id
            ORDER BY spent DESC
        ''')
        
        stats = cursor.fetchall()
        
        print(f"\n{'='*70}")
        print("STATISTICHE FORNITORI")
        print(f"{'='*70}")
        
        for sid, name, rating, orders, spent in stats:
            stars = '★' * (rating or 0) if rating else 'N/A'
            print(f"[#{sid}] {name}")
            print(f"  Rating: {stars} | Ordini: {orders or 0} | Spesa: €{spent or 0:.2f}")
        
        print(f"{'='*70}")


class BatchesShell(BaseShell):
    """Sub-shell per gestione batch."""
    
    intro = "\n→ Entrato in modalità BATCHES (digita 'help' per comandi, 'back' per tornare)\n"
    prompt = '[BATCHES]> '
    
    def do_back(self, arg):
        """Torna al menu principale."""
        return True
    
    def do_list(self, arg):
        """Lista batch disponibili. Uso: list [--all]"""
        only_available = '--all' not in arg
        batches = self.manager.get_batches(only_available=only_available)
        
        if not batches:
            print("\nNessun batch trovato.")
            return
        
        status = "DISPONIBILI" if only_available else "TUTTI"
        print(f"\n{'='*70}")
        print(f"BATCHES {status} ({len(batches)})")
        print(f"{'='*70}")
        
        for b in batches:
            print(f"[#{b['id']}] {b['product_name']}")
            print(f"  Fornitore: {b['supplier_name']}")
            print(f"  Fiale: {b['vials_remaining']}/{b['vials_count']} | €{b['total_price']:.2f}")
        
        print(f"{'='*70}")
    
    def do_show(self, arg):
        """Mostra dettagli batch. Uso: show <id>"""
        if not arg:
            print("❌ Uso: show <id>")
            return
        
        try:
            batch_id = int(arg)
            batch = self.manager.get_batch_details(batch_id)
            
            if not batch:
                print(f"\n❌ Batch #{batch_id} non trovato")
                return
            
            print(f"\n{'='*70}")
            print(f"BATCH #{batch['id']}: {batch['product_name']}")
            print(f"{'='*70}")
            print(f"Fornitore: {batch['supplier_name']} ({batch['supplier_country']})")
            print(f"Fiale: {batch['vials_remaining']}/{batch['vials_count']}")
            print(f"Prezzo: €{batch['total_price']:.2f} {batch['currency']}")
            print(f"Acquisto: {batch['purchase_date']} | Scadenza: {batch.get('expiry_date', 'N/A')}")
            
            print(f"\nComposizione:")
            for comp in batch['composition']:
                print(f"  • {comp['name']}: {comp['mg_per_vial']}mg/fiala")
            
            if batch['certificates']:
                print(f"\nCertificati: {len(batch['certificates'])}")
            
            if batch['preparations']:
                print(f"Preparazioni: {len(batch['preparations'])}")
            
            print(f"{'='*70}")
        
        except ValueError:
            print("❌ ID deve essere un numero")
    
    def do_expiring(self, arg):
        """Mostra batch in scadenza (60 giorni)."""
        cursor = self.manager.conn.cursor()
        cursor.execute('''
            SELECT b.id, b.product_name, b.expiry_date, b.vials_remaining
            FROM batches b
            WHERE b.expiry_date <= date('now', '+60 days')
            AND b.vials_remaining > 0
            ORDER BY b.expiry_date
        ''')
        
        expiring = cursor.fetchall()
        
        if not expiring:
            print("\n✓ Nessun batch in scadenza (60 giorni)")
            return
        
        print(f"\n{'='*70}")
        print("⚠️  BATCHES IN SCADENZA")
        print(f"{'='*70}")
        
        for bid, product, expiry, vials in expiring:
            exp_date = datetime.strptime(expiry, '%Y-%m-%d')
            days_left = (exp_date - datetime.now()).days
            print(f"[#{bid}] {product}")
            print(f"  Scadenza: {expiry} (tra {days_left} giorni) | Fiale: {vials}")
        
        print(f"{'='*70}")


class PreparationsShell(BaseShell):
    """Sub-shell per gestione preparazioni."""
    
    intro = "\n→ Entrato in modalità PREPARATIONS (digita 'help' per comandi, 'back' per tornare)\n"
    prompt = '[PREPARATIONS]> '
    
    def do_back(self, arg):
        """Torna al menu principale."""
        return True
    
    def do_list(self, arg):
        """Lista preparazioni attive. Uso: list [--all]"""
        only_active = '--all' not in arg
        preps = self.manager.get_preparations(only_active=only_active)
        
        if not preps:
            print("\nNessuna preparazione trovata.")
            return
        
        status = "ATTIVE" if only_active else "TUTTE"
        print(f"\n{'='*70}")
        print(f"PREPARAZIONI {status} ({len(preps)})")
        print(f"{'='*70}")
        
        for p in preps:
            percentage = (p['volume_remaining_ml'] / p['volume_ml'] * 100) if p['volume_ml'] > 0 else 0
            print(f"[#{p['id']}] {p['batch_product']}")
            print(f"  Volume: {p['volume_remaining_ml']:.1f}/{p['volume_ml']}ml ({percentage:.0f}%)")
            print(f"  Data: {p['preparation_date']} | Scadenza: {p['expiry_date'] or 'N/A'}")
        
        print(f"{'='*70}")
    
    def do_show(self, arg):
        """Mostra dettagli preparazione. Uso: show <id>"""
        if not arg:
            print("❌ Uso: show <id>")
            return
        
        try:
            prep_id = int(arg)
            prep = self.manager.get_preparation_details(prep_id)
            
            if not prep:
                print(f"\n❌ Preparazione #{prep_id} non trovata")
                return
            
            percentage = (prep['volume_remaining_ml'] / prep['volume_ml'] * 100) if prep['volume_ml'] > 0 else 0
            
            print(f"\n{'='*70}")
            print(f"PREPARAZIONE #{prep['id']}")
            print(f"{'='*70}")
            print(f"Batch: #{prep['batch_id']} - {prep['product_name']}")
            print(f"Fiale usate: {prep['vials_used']} x {prep['mg_per_vial']}mg = {prep['total_mg']}mg")
            print(f"Volume: {prep['volume_remaining_ml']:.1f}/{prep['volume_ml']}ml ({percentage:.0f}%)")
            print(f"Concentrazione: {prep['concentration_mg_ml']:.3f}mg/ml ({prep['concentration_mg_ml']*1000:.1f}mcg/ml)")
            print(f"Data: {prep['preparation_date']} | Scadenza: {prep['expiry_date'] or 'N/A'}")
            print(f"Somministrazioni: {prep['administrations_count']}")
            
            print(f"\nConversioni comuni:")
            calc = DilutionCalculator()
            for ml in [0.1, 0.2, 0.25, 0.5]:
                mcg = calc.ml_to_mcg(ml, prep['concentration_mg_ml'])
                print(f"  {ml}ml = {mcg:.1f}mcg")
            
            print(f"{'='*70}")
        
        except ValueError:
            print("❌ ID deve essere un numero")
    
    def do_expired(self, arg):
        """Mostra preparazioni scadute."""
        expired = self.manager.get_expired_preparations()
        
        if not expired:
            print("\n✓ Nessuna preparazione scaduta")
            return
        
        print(f"\n{'='*70}")
        print(f"⚠️  PREPARAZIONI SCADUTE ({len(expired)})")
        print(f"{'='*70}")
        
        for p in expired:
            days_expired = (datetime.now() - datetime.strptime(p['expiry_date'], '%Y-%m-%d')).days
            print(f"[#{p['id']}] {p['product_name']}")
            print(f"  Scaduta: {p['expiry_date']} ({days_expired} giorni fa)")
            print(f"  Volume rimanente: {p['volume_remaining_ml']:.1f}ml")
        
        print(f"{'='*70}")


class ProtocolsShell(BaseShell):
    """Sub-shell per gestione protocolli."""
    
    intro = "\n→ Entrato in modalità PROTOCOLS (digita 'help' per comandi, 'back' per tornare)\n"
    prompt = '[PROTOCOLS]> '
    
    def do_back(self, arg):
        """Torna al menu principale."""
        return True
    
    def do_list(self, arg):
        """Lista protocolli attivi. Uso: list [--all]"""
        active_only = '--all' not in arg
        protocols = self.manager.get_protocols(active_only=active_only)
        
        if not protocols:
            print("\nNessun protocollo trovato.")
            return
        
        status = "ATTIVI" if active_only else "TUTTI"
        print(f"\n{'='*70}")
        print(f"PROTOCOLLI {status} ({len(protocols)})")
        print(f"{'='*70}")
        
        for p in protocols:
            status_icon = '✓' if p['active'] else '✗'
            print(f"[#{p['id']}] {status_icon} {p['name']}")
            print(f"  Dose: {p['dose_ml']}ml x {p['frequency_per_day']}/giorno")
            if p['days_on']:
                print(f"  Schema: {p['days_on']} giorni ON, {p['days_off']} giorni OFF")
        
        print(f"{'='*70}")
    
    def do_show(self, arg):
        """Mostra dettagli protocollo. Uso: show <id>"""
        if not arg:
            print("❌ Uso: show <id>")
            return
        
        try:
            protocol_id = int(arg)
            protocol = self.manager.get_protocol_details(protocol_id)
            
            if not protocol:
                print(f"\n❌ Protocollo #{protocol_id} non trovato")
                return
            
            status = '✓ ATTIVO' if protocol['active'] else '✗ DISATTIVATO'
            
            print(f"\n{'='*70}")
            print(f"PROTOCOLLO #{protocol['id']}: {protocol['name']} [{status}]")
            print(f"{'='*70}")
            
            if protocol['description']:
                print(f"\n{protocol['description']}")
            
            print(f"\nDosaggio: {protocol['dose_ml']}ml x {protocol['frequency_per_day']}/giorno")
            
            if protocol['days_on']:
                print(f"Schema: {protocol['days_on']} giorni ON, {protocol['days_off']} giorni OFF")
            
            if protocol['peptides']:
                print(f"\nPeptidi richiesti:")
                for pep in protocol['peptides']:
                    print(f"  • {pep['name']}: {pep['target_dose_mcg']}mcg")
            
            if protocol['administrations_count'] > 0:
                print(f"\nSomministrazioni: {protocol['administrations_count']}")
            
            print(f"{'='*70}")
        
        except ValueError:
            print("❌ ID deve essere un numero")
    
    def do_stats(self, arg):
        """Mostra statistiche aderenza. Uso: stats <id>"""
        if not arg:
            print("❌ Uso: stats <id>")
            return
        
        try:
            protocol_id = int(arg)
            protocol = self.manager.get_protocol_details(protocol_id)
            
            if not protocol:
                print(f"\n❌ Protocollo #{protocol_id} non trovato")
                return
            
            stats = self.manager.get_protocol_statistics(protocol_id)
            
            print(f"\n{'='*70}")
            print(f"STATISTICHE PROTOCOLLO #{protocol_id}: {protocol['name']}")
            print(f"{'='*70}")
            
            if stats['total_administrations'] == 0:
                print("\nNessuna somministrazione registrata.")
                print(f"{'='*70}")
            
            except ValueError:
                print("\n❌ Uso: calc dose <mcg> <mg/ml>")
        
        else:
            print("\n❌ Comando non riconosciuto")
            print("Digita 'help calc' per info")
    
    # ============================================================
    # OVERRIDE CMD METHODS
    # ============================================================
    
    def cmdloop(self, intro=None):
        """Override cmdloop per gestire Ctrl+C."""
        try:
            super().cmdloop(intro)
        except KeyboardInterrupt:
            print("\n\nUsa 'exit' o 'quit' per uscire")
            self.cmdloop('')


def start_shell(db_path='peptide_management.db'):
    """Avvia la shell interattiva."""
    shell = PeptideShell(db_path)
    shell.cmdloop()


if __name__ == '__main__':
    start_shell()*70}")
                return
            
            print(f"Periodo: {stats['first_date']} → {stats['last_date']}")
            print(f"Giorni: {stats['days_elapsed']} trascorsi, {stats['days_active']} attivi")
            print(f"\nSomministrazioni: {stats['total_administrations']} / {stats['expected_administrations']} previste")
            print(f"Volume totale: {stats['total_ml_used']:.2f}ml")
            
            adherence = stats['adherence_percentage']
            icon = '✓' if adherence >= 80 else '⚠️' if adherence >= 60 else '❌'
            print(f"\nAderenza: {icon} {adherence}%")
            
            print(f"{'='*70}")
        
        except ValueError:
            print("❌ ID deve essere un numero")


# ============================================================
# MAIN SHELL
# ============================================================

class PeptideShell(BaseShell):
    """Shell principale."""
    
    intro = """
╔════════════════════════════════════════════════════════════════════════════╗
║                    PEPTIDE MANAGEMENT SYSTEM v0.1.0                        ║
║                         Interactive Shell Mode                             ║
╚════════════════════════════════════════════════════════════════════════════╝

Digita 'help' o '?' per lista comandi
Digita '<menu>' per entrare in un menu tematico (es: 'batches', 'preparations')
Digita 'exit' o 'quit' per uscire

"""
    
    prompt = '\n[PEPTIDE-MGR]> '
    
    def __init__(self, db_path='peptide_management.db'):
        self.db_path = db_path
        self.manager = None
        self._connect_db()
        super().__init__(self.manager)
    
    def _connect_db(self):
        """Connette al database."""
        try:
            self.manager = PeptideManager(self.db_path)
            print(f"✓ Connesso a database: {self.db_path}")
        except Exception as e:
            print(f"❌ Errore connessione database: {e}")
            sys.exit(1)
    
    def _close_db(self):
        """Chiude connessione database."""
        if self.manager:
            self.manager.close()
    
    # ============================================================
    # COMANDI BASE
    # ============================================================
    
    def do_exit(self, arg):
        """Esci dalla shell."""
        print("\n✓ Arrivederci!\n")
        self._close_db()
        return True
    
    def do_quit(self, arg):
        """Esci dalla shell."""
        return self.do_exit(arg)
    
    def do_status(self, arg):
        """Mostra stato del sistema."""
        summary = self.manager.get_inventory_summary()
        
        print(f"\n{'='*70}")
        print("STATO SISTEMA")
        print(f"{'='*70}")
        print(f"Database: {self.db_path}")
        print(f"Batches attivi: {summary['available_batches']}/{summary['total_batches']}")
        print(f"Peptidi unici: {summary['unique_peptides']}")
        print(f"Valore inventario: €{summary['total_value']:.2f}")
        if summary['expiring_soon'] > 0:
            print(f"⚠️  In scadenza: {summary['expiring_soon']} batches")
        print(f"{'='*70}")
    
    def do_inventory(self, arg):
        """Mostra inventario completo. Uso: inventory [--detailed]"""
        detailed = '--detailed' in arg
        self.manager.print_inventory(detailed=detailed)
    
    def do_summary(self, arg):
        """Riepilogo rapido inventario."""
        self.do_status(arg)
    
    # ============================================================
    # MENU TEMATICI (entra in sub-shell)
    # ============================================================
    
    def do_peptides(self, arg):
        """Entra nel menu PEPTIDES."""
        PeptidesShell(self.manager).cmdloop()
    
    def do_suppliers(self, arg):
        """Entra nel menu SUPPLIERS."""
        SuppliersShell(self.manager).cmdloop()
    
    def do_batches(self, arg):
        """Entra nel menu BATCHES."""
        BatchesShell(self.manager).cmdloop()
    
    def do_preparations(self, arg):
        """Entra nel menu PREPARATIONS."""
        PreparationsShell(self.manager).cmdloop()
    
    def do_protocols(self, arg):
        """Entra nel menu PROTOCOLS."""
        ProtocolsShell(self.manager).cmdloop()
    
    # ============================================================
    # CALCULATOR
    # ============================================================
    
    def do_calc(self, arg):
        """
        Calcolatore diluizioni.
        
        Uso:
          calc <mg> <ml>         - Calcola concentrazione
          calc dose <mcg> <conc> - Calcola volume per dose
        
        Esempio:
          calc 5 2               - 5mg in 2ml
          calc dose 250 2.5      - 250mcg con 2.5mg/ml
        """
        args = shlex.split(arg)
        calc = DilutionCalculator()
        
        if len(args) == 2:
            try:
                mg = float(args[0])
                ml = float(args[1])
                conc = calc.calculate_concentration(mg, ml)
                
                print(f"\n{'='*70}")
                print("DILUIZIONE")
                print(f"{'='*70}")
                print(f"Peptide: {mg}mg in {ml}ml")
                print(f"Concentrazione: {conc:.3f}mg/ml ({conc*1000:.1f}mcg/ml)")
                print(f"{'='*70}")
            
            except ValueError:
                print("\n❌ Uso: calc <mg> <ml>")
        
        elif len(args) == 3 and args[0] == 'dose':
            try:
                mcg = float(args[1])
                conc = float(args[2])
                ml = calc.mcg_to_ml(mcg, conc)
                
                print(f"\n{'='*70}")
                print("DOSE")
                print(f"{'='*70}")
                print(f"Dose target: {mcg}mcg")
                print(f"Concentrazione: {conc}mg/ml")
                print(f"→ Volume da iniettare: {ml:.3f}ml")
                print(f"{'='