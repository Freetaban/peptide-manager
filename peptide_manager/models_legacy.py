"""
Modelli e operazioni CRUD per il database.
Include la classe principale PeptideManager.
"""

import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple


class PeptideManager:
    """
    Classe per gestire tutte le operazioni CRUD del database peptidi.
    """
    
    def __init__(self, db_path='peptide_management.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row  # Per accedere ai risultati come dizionari
    
    def close(self):
        """Chiude la connessione al database."""
        self.conn.close()
    
    # ==================== SUPPLIERS ====================
    
    def add_supplier(self, name: str, country: str = None, website: str = None, 
                     email: str = None, notes: str = None, rating: int = None) -> int:
        """
        Aggiunge un nuovo fornitore.
        
        Returns:
            ID del fornitore creato
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO suppliers (name, country, website, email, notes, reliability_rating)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, country, website, email, notes, rating))
        
        self.conn.commit()
        print(f"Fornitore '{name}' aggiunto (ID: {cursor.lastrowid})")
        return cursor.lastrowid
    
    def get_suppliers(self, search: str = None) -> List[Dict]:
        """
        Recupera tutti i fornitori, opzionalmente filtrati per nome.
        """
        cursor = self.conn.cursor()
        
        if search:
            cursor.execute('''
                SELECT * FROM suppliers 
                WHERE name LIKE ? OR country LIKE ?
                ORDER BY name
            ''', (f'%{search}%', f'%{search}%'))
        else:
            cursor.execute('SELECT * FROM suppliers ORDER BY name')
        
        return [dict(row) for row in cursor.fetchall()]
    
    def update_supplier(self, supplier_id: int, **kwargs) -> bool:
        """
        Aggiorna un fornitore. Accetta parametri dinamici.
        Esempio: update_supplier(1, rating=5, notes="Ottimo servizio")
        """
        allowed_fields = ['name', 'country', 'website', 'email', 'notes', 'reliability_rating']
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not updates:
            print("Nessun campo valido da aggiornare")
            return False
        
        set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [supplier_id]
        
        cursor = self.conn.cursor()
        cursor.execute(f'UPDATE suppliers SET {set_clause} WHERE id = ?', values)
        self.conn.commit()
        
        print(f"Fornitore ID {supplier_id} aggiornato")
        return True
    
    def delete_supplier(self, supplier_id: int, force: bool = False) -> bool:
        """Elimina un fornitore."""
        cursor = self.conn.cursor()
    
        suppliers = self.get_suppliers()
        supplier = next((s for s in suppliers if s['id'] == supplier_id), None)
    
        if not supplier:
            print(f"Fornitore #{supplier_id} non trovato")
            return False
    
        # Controlla batches
        cursor.execute('SELECT COUNT(*) FROM batches WHERE supplier_id = ?', (supplier_id,))
        batch_count = cursor.fetchone()[0]
    
        if batch_count > 0 and not force:
            print(f"❌ Impossibile eliminare fornitore '{supplier['name']}'")
            print(f"   Ha {batch_count} batches associati")
            print(f"   Usa force=True per eliminare comunque (sconsigliato)")
            return False
    
        cursor.execute('DELETE FROM suppliers WHERE id = ?', (supplier_id,))
        self.conn.commit()
    
        print(f"✓ Fornitore #{supplier_id} '{supplier['name']}' eliminato")
        return True
    # ==================== PEPTIDES ====================
    
    def add_peptide(self, name: str, description: str = None, 
                    common_uses: str = None, notes: str = None) -> int:
        """
        Aggiunge un nuovo peptide al catalogo.
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO peptides (name, description, common_uses, notes)
            VALUES (?, ?, ?, ?)
        ''', (name, description, common_uses, notes))
        
        self.conn.commit()
        print(f"Peptide '{name}' aggiunto al catalogo (ID: {cursor.lastrowid})")
        return cursor.lastrowid
    
    def get_peptides(self, search: str = None) -> List[Dict]:
        """
        Recupera tutti i peptidi dal catalogo.
        """
        cursor = self.conn.cursor()
        
        if search:
            cursor.execute('''
                SELECT * FROM peptides 
                WHERE name LIKE ? OR description LIKE ?
                ORDER BY name
            ''', (f'%{search}%', f'%{search}%'))
        else:
            cursor.execute('SELECT * FROM peptides ORDER BY name')
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_peptide_by_name(self, name: str) -> Optional[Dict]:
        """
        Recupera un peptide specifico per nome.
        """
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM peptides WHERE name = ?', (name,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_peptide_by_id(self, peptide_id: int) -> Optional[Dict]:
        """
        Recupera un peptide specifico per ID.
        """
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM peptides WHERE id = ?', (peptide_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def update_peptide(self, peptide_id: int, **kwargs) -> bool:
        """
        Aggiorna un peptide. Accetta parametri dinamici.
        Esempio: update_peptide(1, name="BPC-157", description="Updated desc")
        """
        allowed_fields = ['name', 'description', 'common_uses', 'notes']
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not updates:
            print("Nessun campo valido da aggiornare")
            return False
        
        set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [peptide_id]
        
        cursor = self.conn.cursor()
        cursor.execute(f'UPDATE peptides SET {set_clause} WHERE id = ?', values)
        self.conn.commit()
        
        print(f"Peptide ID {peptide_id} aggiornato")
        return True
    
    def delete_peptide(self, peptide_id: int, force: bool = False) -> bool:
        """
        Elimina un peptide.
    
        Args:
            peptide_id: ID peptide da eliminare
            force: Se True, elimina anche con riferimenti esistenti
    
        Returns:
            True se eliminato con successo
        """
        cursor = self.conn.cursor()
    
        # Verifica esistenza
        peptide = self.get_peptide_by_id(peptide_id)
        if not peptide:
            print(f"Peptide #{peptide_id} non trovato")
            return False
    
        # Controlla riferimenti
        cursor.execute('SELECT COUNT(*) FROM batch_composition WHERE peptide_id = ?', (peptide_id,))
        batch_refs = cursor.fetchone()[0]
    
        cursor.execute('SELECT COUNT(*) FROM protocol_peptides WHERE peptide_id = ?', (peptide_id,))
        protocol_refs = cursor.fetchone()[0]
    
        if (batch_refs > 0 or protocol_refs > 0) and not force:
            print(f"❌ Impossibile eliminare peptide '{peptide['name']}'")
            print(f"   Riferimenti in batch: {batch_refs}")
            print(f"   Riferimenti in protocolli: {protocol_refs}")
            print(f"   Usa force=True per eliminare comunque (sconsigliato)")
            return False
    
        # Elimina (CASCADE eliminerà automaticamente da batch_composition e protocol_peptides)
        cursor.execute('DELETE FROM peptides WHERE id = ?', (peptide_id,))
        self.conn.commit()
    
        print(f"✓ Peptide #{peptide_id} '{peptide['name']}' eliminato")
        return True
    
    # ==================== BATCHES ====================
    
    def add_batch(self, supplier_name: str, product_name: str, vials_count: int,
                  mg_per_vial: float, total_price: float, purchase_date: str,
                  composition: List[Tuple[str, float]], batch_number: str = None,
                  expiry_date: str = None, currency: str = 'EUR',
                  storage_location: str = None, notes: str = None) -> int:
        """
        Aggiunge un nuovo batch con la sua composizione.
        
        Args:
            composition: Lista di tuple (peptide_name, mg_per_vial)
                        Es: [('BPC-157', 5.0), ('TB-500', 5.0)]
        
        Returns:
            ID del batch creato
        """
        cursor = self.conn.cursor()
        
        # Ottieni supplier_id
        cursor.execute('SELECT id FROM suppliers WHERE name = ?', (supplier_name,))
        supplier = cursor.fetchone()
        
        if not supplier:
            raise ValueError(f"Fornitore '{supplier_name}' non trovato. Aggiungilo prima.")
        
        supplier_id = supplier[0]
        
        # Inserisci batch
        cursor.execute('''
            INSERT INTO batches (
                supplier_id, product_name, batch_number, vials_count, mg_per_vial,
                total_price, currency, purchase_date, expiry_date, 
                vials_remaining, storage_location, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (supplier_id, product_name, batch_number, vials_count, mg_per_vial,
              total_price, currency, purchase_date, expiry_date, 
              vials_count, storage_location, notes))
        
        batch_id = cursor.lastrowid
        
        # Aggiungi composizione
        for peptide_name, mg_amount in composition:
            cursor.execute('SELECT id FROM peptides WHERE name = ?', (peptide_name,))
            peptide = cursor.fetchone()
            
            if not peptide:
                # Se il peptide non esiste, crealo automaticamente
                cursor.execute('''
                    INSERT INTO peptides (name) VALUES (?)
                ''', (peptide_name,))
                peptide_id = cursor.lastrowid
                print(f"  Peptide '{peptide_name}' aggiunto automaticamente al catalogo")
            else:
                peptide_id = peptide[0]
            
            cursor.execute('''
                INSERT INTO batch_composition (batch_id, peptide_id, mg_per_vial)
                VALUES (?, ?, ?)
            ''', (batch_id, peptide_id, mg_amount))
        
        self.conn.commit()
        
        price_per_vial = total_price / vials_count
        print(f"Batch '{product_name}' aggiunto (ID: {batch_id})")
        print(f"  {vials_count} fiale x {mg_per_vial}mg = {vials_count * mg_per_vial}mg totali")
        print(f"  Prezzo: {total_price:.2f} {currency} ({price_per_vial:.2f} {currency}/fiala)")
        
        return batch_id
    
    def get_batches(self, supplier: str = None, peptide: str = None, 
                    only_available: bool = False) -> List[Dict]:
        """
        Recupera batches con filtri opzionali.
        
        Args:
            supplier: Filtra per nome fornitore
            peptide: Filtra per peptide nella composizione
            only_available: Solo batches con fiale rimanenti
        """
        cursor = self.conn.cursor()
        
        query = '''
            SELECT b.*, s.name as supplier_name, s.country as supplier_country
            FROM batches b
            JOIN suppliers s ON b.supplier_id = s.id
            WHERE 1=1
        '''
        params = []
        
        if supplier:
            query += ' AND s.name LIKE ?'
            params.append(f'%{supplier}%')
        
        if peptide:
            query += '''
                AND b.id IN (
                    SELECT bc.batch_id FROM batch_composition bc
                    JOIN peptides p ON bc.peptide_id = p.id
                    WHERE p.name LIKE ?
                )
            '''
            params.append(f'%{peptide}%')
        
        if only_available:
            query += ' AND b.vials_remaining > 0'
        
        query += ' ORDER BY b.purchase_date DESC'
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def get_batch_details(self, batch_id: int) -> Dict:
        """
        Recupera dettagli completi di un batch inclusa composizione e certificati.
        """
        cursor = self.conn.cursor()
        
        # Info batch
        cursor.execute('''
            SELECT b.*, s.name as supplier_name, s.country as supplier_country,
                   s.website as supplier_website
            FROM batches b
            JOIN suppliers s ON b.supplier_id = s.id
            WHERE b.id = ?
        ''', (batch_id,))
        
        batch = cursor.fetchone()
        if not batch:
            return None
        
        result = dict(batch)
        
        # Composizione
        cursor.execute('''
            SELECT p.id, p.name, bc.mg_per_vial
            FROM batch_composition bc
            JOIN peptides p ON bc.peptide_id = p.id
            WHERE bc.batch_id = ?
        ''', (batch_id,))
        result['composition'] = [dict(row) for row in cursor.fetchall()]
        
        # Certificati
        cursor.execute('''
            SELECT * FROM certificates
            WHERE batch_id = ?
            ORDER BY test_date DESC
        ''', (batch_id,))
        result['certificates'] = [dict(row) for row in cursor.fetchall()]
        
        # Preparazioni
        cursor.execute('''
            SELECT * FROM preparations
            WHERE batch_id = ?
            ORDER BY preparation_date DESC
        ''', (batch_id,))
        result['preparations'] = [dict(row) for row in cursor.fetchall()]
        
        return result
    
    def use_vials(self, batch_id: int, count: int) -> bool:
        """
        Decrementa il numero di fiale disponibili quando vengono usate.
        """
        cursor = self.conn.cursor()
        
        cursor.execute('SELECT vials_remaining FROM batches WHERE id = ?', (batch_id,))
        result = cursor.fetchone()
        
        if not result:
            print(f"Batch ID {batch_id} non trovato")
            return False
        
        vials_remaining = result[0]
        
        if vials_remaining < count:
            print(f"Fiale insufficienti (disponibili: {vials_remaining}, richieste: {count})")
            return False
        
        cursor.execute('''
            UPDATE batches SET vials_remaining = vials_remaining - ?
            WHERE id = ?
        ''', (count, batch_id))
        
        self.conn.commit()
        print(f"{count} fiala/e usate dal batch {batch_id} (rimaste: {vials_remaining - count})")
        return True
    
    def update_batch(self, batch_id: int, **kwargs) -> bool:
        """
        Aggiorna informazioni di un batch.
        
        Campi supportati:
        - product_name, batch_number, expiry_date, storage_location, notes
        - vials_remaining, vials_count
        - supplier_id, total_price, purchase_date, mg_per_vial
        - composition: dict {peptide_id: mg_per_vial} per aggiornare composizione
        """
        cursor = self.conn.cursor()
        
        # Campi normali della tabella batches
        allowed_fields = [
            'product_name', 'batch_number', 'expiry_date', 
            'storage_location', 'notes', 'vials_remaining',
            'supplier_id', 'vials_count', 'total_price',
            'purchase_date', 'mg_per_vial'
        ]
        
        # Separa composition dagli altri campi
        composition = kwargs.pop('composition', None)
        
        # Update campi normali
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if updates:
            set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
            values = list(updates.values()) + [batch_id]
            
            cursor.execute(f'UPDATE batches SET {set_clause} WHERE id = ?', values)
            print(f"Batch #{batch_id} - Updated fields: {list(updates.keys())}")
        
        # Update composizione se fornita
        if composition is not None:
            print(f"Batch #{batch_id} - Updating composition: {composition}")
            
            # Cancella composizione esistente
            cursor.execute('DELETE FROM batch_composition WHERE batch_id = ?', (batch_id,))
            
            # Inserisci nuova composizione
            for peptide_id, mg in composition.items():
                cursor.execute('''
                    INSERT INTO batch_composition (batch_id, peptide_id, mg_per_vial)
                    VALUES (?, ?, ?)
                ''', (batch_id, peptide_id, mg))
                print(f"  - Peptide #{peptide_id}: {mg}mg")
            
            # Ricalcola mg_per_vial totale
            total_mg = sum(composition.values())
            cursor.execute('UPDATE batches SET mg_per_vial = ? WHERE id = ?', 
                         (total_mg, batch_id))
            print(f"  - Total mg_per_vial: {total_mg}")
        
        self.conn.commit()
        
        if not updates and composition is None:
            print("Nessun campo valido da aggiornare")
            return False
        
        print(f"✓ Batch #{batch_id} aggiornato con successo")
        return True
    
    def adjust_vials(self, batch_id: int, adjustment: int, reason: str = None) -> bool:
        """
        Corregge il conteggio fiale di un batch (positivo o negativo).
        
        Args:
            batch_id: ID del batch
            adjustment: Numero fiale da aggiungere (+) o rimuovere (-)
            reason: Motivo della correzione (opzionale, per tracciamento)
        
        Returns:
            True se successo
            
        Examples:
            >>> manager.adjust_vials(1, +1, "Fiala usata per errore")
            >>> manager.adjust_vials(2, -2, "Fiale danneggiate")
        """
        cursor = self.conn.cursor()
        
        # Verifica batch esistente
        cursor.execute('SELECT vials_remaining, vials_count, product_name FROM batches WHERE id = ?', (batch_id,))
        result = cursor.fetchone()
        
        if not result:
            print(f"❌ Batch #{batch_id} non trovato")
            return False
        
        current_vials = result[0]
        total_vials = result[1]
        product_name = result[2]
        new_vials = current_vials + adjustment
        
        # Validazione
        if new_vials < 0:
            print(f"❌ Impossibile: fiale diventerebbero negative ({new_vials})")
            return False
        
        if new_vials > total_vials:
            print(f"⚠️  ATTENZIONE: Fiale disponibili ({new_vials}) > fiale originali ({total_vials})")
            confirm = input("Continuare comunque? (y/n): ")
            if confirm.lower() != 'y':
                print("Operazione annullata")
                return False
        
        # Aggiorna
        cursor.execute('''
            UPDATE batches SET vials_remaining = ?
            WHERE id = ?
        ''', (new_vials, batch_id))
        
        self.conn.commit()
        
        # Messaggio
        action = "aggiunte" if adjustment > 0 else "rimosse"
        print(f"\n✓ Batch #{batch_id} '{product_name}':")
        print(f"  Fiale {action}: {abs(adjustment)}")
        print(f"  {current_vials} → {new_vials} fiale")
        if reason:
            print(f"  Motivo: {reason}")
        
        return True
    
    def delete_batch(self, batch_id: int, force: bool = False) -> bool:
        """
        Elimina un batch.
        ATTENZIONE: Eliminerà anche preparazioni e somministrazioni collegate!
        """
        cursor = self.conn.cursor()
    
        batch = self.get_batch_details(batch_id)
        if not batch:
            print(f"Batch #{batch_id} non trovato")
            return False
    
        # Controlla preparazioni
        cursor.execute('SELECT COUNT(*) FROM preparations WHERE batch_id = ?', (batch_id,))
        prep_count = cursor.fetchone()[0]
    
        if prep_count > 0 and not force:
            print(f"❌ Impossibile eliminare batch #{batch_id}")
            print(f"   Ha {prep_count} preparazioni associate")
            print(f"   Eliminare il batch eliminerà ANCHE le preparazioni e le somministrazioni!")
            print(f"   Usa force=True se sei sicuro")
            return False
    
        # Elimina (CASCADE eliminerà preparazioni e composizioni)
        cursor.execute('DELETE FROM batches WHERE id = ?', (batch_id,))
        self.conn.commit()
    
        print(f"✓ Batch #{batch_id} eliminato")
        if prep_count > 0:
            print(f"  (eliminate anche {prep_count} preparazioni e relative somministrazioni)")
    
        return True
    
    # ==================== CERTIFICATES ====================
    
    def add_certificate(self, batch_id: int, certificate_type: str, 
                       lab_name: str = None, test_date: str = None,
                       file_path: str = None, file_name: str = None,
                       purity_percentage: float = None, endotoxin_level: str = None,
                       notes: str = None, details: List[Dict] = None) -> int:
        """
        Aggiunge un certificato di analisi a un batch.
        
        Args:
            certificate_type: 'manufacturer', 'third_party', o 'personal'
            details: Lista di dict con test dettagliati
                    [{'parameter': 'Purity', 'value': '98.5', 'unit': '%', 
                      'specification': '>95%', 'pass_fail': 'pass'}, ...]
        
        Returns:
            ID del certificato creato
        """
        cursor = self.conn.cursor()
        
        cursor.execute('''
            INSERT INTO certificates (
                batch_id, certificate_type, lab_name, test_date,
                file_path, file_name, purity_percentage, endotoxin_level, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (batch_id, certificate_type, lab_name, test_date, file_path, 
              file_name, purity_percentage, endotoxin_level, notes))
        
        cert_id = cursor.lastrowid
        
        # Aggiungi dettagli se presenti
        if details:
            for detail in details:
                cursor.execute('''
                    INSERT INTO certificate_details (
                        certificate_id, test_parameter, result_value,
                        unit, specification, pass_fail
                    ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (cert_id, detail.get('parameter'), detail.get('value'),
                      detail.get('unit'), detail.get('specification'),
                      detail.get('pass_fail')))
        
        self.conn.commit()
        
        type_label = {
            'manufacturer': 'Produttore',
            'third_party': 'Third-party',
            'personal': 'Personale'
        }.get(certificate_type, certificate_type)
        
        print(f"Certificato [{type_label}] aggiunto al batch {batch_id} (ID: {cert_id})")
        return cert_id
    
    def get_certificates(self, batch_id: int) -> List[Dict]:
        """
        Recupera tutti i certificati di un batch con i loro dettagli.
        """
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT * FROM certificates
            WHERE batch_id = ?
            ORDER BY test_date DESC
        ''', (batch_id,))
        
        certificates = [dict(row) for row in cursor.fetchall()]
        
        # Aggiungi dettagli per ogni certificato
        for cert in certificates:
            cursor.execute('''
                SELECT * FROM certificate_details
                WHERE certificate_id = ?
            ''', (cert['id'],))
            cert['details'] = [dict(row) for row in cursor.fetchall()]
        
        return certificates

  
    
    # ==================== INVENTORY REPORTS ====================
    
    def get_inventory_summary(self) -> Dict:
        """
        Restituisce un riepilogo completo dell'inventario.
        """
        cursor = self.conn.cursor()
        
        # Totale batches
        cursor.execute('SELECT COUNT(*) FROM batches')
        total_batches = cursor.fetchone()[0]
        
        # Batches con fiale disponibili
        cursor.execute('SELECT COUNT(*) FROM batches WHERE vials_remaining > 0')
        available_batches = cursor.fetchone()[0]
        
        # Valore totale inventario
        cursor.execute('''
            SELECT SUM(total_price * vials_remaining / vials_count) as total_value
            FROM batches
        ''')
        total_value = cursor.fetchone()[0] or 0
        
        # Peptidi unici in stock
        cursor.execute('''
            SELECT COUNT(DISTINCT p.id)
            FROM peptides p
            JOIN batch_composition bc ON p.id = bc.peptide_id
            JOIN batches b ON bc.batch_id = b.id
            WHERE b.vials_remaining > 0
        ''')
        unique_peptides = cursor.fetchone()[0]
        
        # Batches in scadenza (prossimi 60 giorni)
        cursor.execute('''
            SELECT COUNT(*)
            FROM batches
            WHERE expiry_date IS NOT NULL
            AND expiry_date <= date('now', '+60 days')
            AND vials_remaining > 0
        ''')
        expiring_soon = cursor.fetchone()[0]
        
        return {
            'total_batches': total_batches,
            'available_batches': available_batches,
            'total_value': total_value,
            'unique_peptides': unique_peptides,
            'expiring_soon': expiring_soon
        }
    
    def print_inventory(self, detailed: bool = False):
        """
        Stampa l'inventario in formato leggibile.
        """
        summary = self.get_inventory_summary()
        batches = self.get_batches(only_available=True)
        
        print("\n" + "="*80)
        print("INVENTARIO PEPTIDI")
        print("="*80)
        print(f"Batches attivi: {summary['available_batches']}/{summary['total_batches']}")
        print(f"Peptidi unici in stock: {summary['unique_peptides']}")
        print(f"Valore inventario: EUR {summary['total_value']:.2f}")
        if summary['expiring_soon'] > 0:
            print(f"Batches in scadenza (60gg): {summary['expiring_soon']}")
        print("="*80)
        
        for batch in batches:
            batch_details = self.get_batch_details(batch['id'])
            
            print(f"\n[#{batch['id']}] {batch['product_name']}")
            print(f"  Fornitore: {batch['supplier_name']} ({batch['supplier_country']})")
            print(f"  Acquisto: {batch['purchase_date']} | Scadenza: {batch.get('expiry_date', 'N/A')}")
            print(f"  Fiale: {batch['vials_remaining']}/{batch['vials_count']} | " +
                  f"{batch['mg_per_vial']}mg/fiala")
            
            price_per_vial = batch['total_price'] / batch['vials_count']
            remaining_value = price_per_vial * batch['vials_remaining']
            print(f"  Prezzo: {batch['total_price']:.2f} {batch['currency']} " +
                  f"({price_per_vial:.2f}/fiala) | Valore residuo: {remaining_value:.2f}")
            
            print("  Composizione:")
            for comp in batch_details['composition']:
                print(f"    - {comp['name']}: {comp['mg_per_vial']}mg/fiala")
            
            if detailed and batch_details['certificates']:
                print("  Certificati:")
                for cert in batch_details['certificates']:
                    type_label = {
                        'manufacturer': 'Produttore',
                        'third_party': 'Third-party',
                        'personal': 'Personale'
                    }.get(cert['certificate_type'])
                    purity = f"{cert['purity_percentage']:.1f}%" if cert['purity_percentage'] else "N/A"
                    print(f"    - [{type_label}] {cert['lab_name']} | Purezza: {purity}")
        
        print("\n" + "="*80 + "\n")
    # ==================== PREPARATIONS ====================
    
    def add_preparation(self, batch_id: int, vials_used: int, volume_ml: float,
                       preparation_date: str, diluent: str = 'BAC Water',
                       expiry_date: str = None, storage_location: str = None,
                       notes: str = None) -> int:
        """
        Crea una nuova preparazione da un batch.
        
        Args:
            batch_id: ID del batch da cui prelevare
            vials_used: Numero di fiale utilizzate
            volume_ml: Volume totale di diluente aggiunto
            preparation_date: Data preparazione (YYYY-MM-DD)
            diluent: Tipo diluente (default: BAC Water)
            expiry_date: Data scadenza preparazione
            storage_location: Dove conservata
            notes: Note aggiuntive
        
        Returns:
            ID della preparazione creata
        """
        cursor = self.conn.cursor()
        
        # Verifica batch esiste e ha fiale sufficienti
        cursor.execute('SELECT vials_remaining, mg_per_vial FROM batches WHERE id = ?', (batch_id,))
        result = cursor.fetchone()
        
        if not result:
            raise ValueError(f"Batch #{batch_id} non trovato")
        
        vials_remaining, mg_per_vial = result
        
        if vials_remaining < vials_used:
            raise ValueError(f"Fiale insufficienti (disponibili: {vials_remaining}, richieste: {vials_used})")
        
        # Calcola mg totali nella preparazione
        total_mg = mg_per_vial * vials_used
        
        # Inserisci preparazione
        cursor.execute('''
            INSERT INTO preparations (
                batch_id, vials_used, volume_ml, diluent,
                preparation_date, expiry_date, volume_remaining_ml,
                storage_location, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (batch_id, vials_used, volume_ml, diluent,
              preparation_date, expiry_date, volume_ml,
              storage_location, notes))
        
        prep_id = cursor.lastrowid
        
        # Decrementa fiale dal batch
        cursor.execute('''
            UPDATE batches SET vials_remaining = vials_remaining - ?
            WHERE id = ?
        ''', (vials_used, batch_id))
        
        self.conn.commit()
        
        concentration = total_mg / volume_ml
        print(f"Preparazione #{prep_id} creata")
        print(f"  {vials_used} fiale x {mg_per_vial}mg = {total_mg}mg in {volume_ml}ml")
        print(f"  Concentrazione: {concentration:.2f}mg/ml")
        
        return prep_id
    
    def get_preparations(self, batch_id: int = None, only_active: bool = False) -> List[Dict]:
        """
        Recupera preparazioni con filtri opzionali.
        
        Args:
            batch_id: Filtra per batch specifico
            only_active: Solo preparazioni con volume rimanente > 0
        """
        cursor = self.conn.cursor()
        
        query = '''
            SELECT p.*, b.product_name as batch_product
            FROM preparations p
            JOIN batches b ON p.batch_id = b.id
            WHERE 1=1
        '''
        params = []
        
        if batch_id:
            query += ' AND p.batch_id = ?'
            params.append(batch_id)
        
        if only_active:
            query += ' AND p.volume_remaining_ml > 0'
        
        query += ' ORDER BY p.preparation_date DESC'
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def get_preparation_details(self, prep_id: int) -> Dict:
        """
        Recupera dettagli completi di una preparazione.
        Include composizione peptidi dal batch.
        """
        cursor = self.conn.cursor()
        
        # Info preparazione
        cursor.execute('''
            SELECT p.*, b.product_name, b.mg_per_vial, s.name as supplier_name
            FROM preparations p
            JOIN batches b ON p.batch_id = b.id
            JOIN suppliers s ON b.supplier_id = s.id
            WHERE p.id = ?
        ''', (prep_id,))
        
        prep = cursor.fetchone()
        if not prep:
            return None
        
        result = dict(prep)
        
        # Composizione peptidi (dal batch)
        cursor.execute('''
            SELECT p.id, p.name, bc.mg_per_vial
            FROM batch_composition bc
            JOIN peptides p ON bc.peptide_id = p.id
            WHERE bc.batch_id = ?
        ''', (result['batch_id'],))
        result['peptides'] = [dict(row) for row in cursor.fetchall()]
        
        # Calcola concentrazioni
        total_mg = result['mg_per_vial'] * result['vials_used']
        result['total_mg'] = total_mg
        result['concentration_mg_ml'] = total_mg / result['volume_ml']
        
        # Concentrazione per peptide
        for peptide in result['peptides']:
            peptide_total_mg = peptide['mg_per_vial'] * result['vials_used']
            peptide['concentration_mg_ml'] = peptide_total_mg / result['volume_ml']
        
        # Somministrazioni attive da questa preparazione
        cursor.execute('''
            SELECT COUNT(*), SUM(dose_ml)
            FROM administrations
            WHERE preparation_id = ? AND deleted_at IS NULL
        ''', (prep_id,))
        
        admin_count, total_used = cursor.fetchone()
        result['administrations_count'] = admin_count or 0
        result['ml_used'] = total_used or 0.0
        
        return result
    
    def use_preparation(self, prep_id: int, ml_used: float, 
                       administration_datetime: str = None,
                       injection_site: str = None, 
                       injection_method: str = 'SubQ',  # ✅ NUOVO: SubQ o IM
                       notes: str = None,
                       protocol_id: int = None, # inserito per utilizzo in GUI
                       ) -> bool:
        """
        Registra utilizzo di una preparazione (decrementa volume).
        Crea anche record in administrations.
        
        Args:
            prep_id: ID preparazione
            ml_used: Millilitri utilizzati
            administration_datetime: Timestamp somministrazione
            injection_site: Sito iniezione anatomico (es: Addome, Gluteo)
            injection_method: Modalità iniezione - 'SubQ' o 'IM' (default: SubQ)
            notes: Note
            protocol_id: ID protocollo associato (opzionale)
        """
        print("Argomenti passati:", locals())  # Stampa un dizionario con tutti gli argomenti
        cursor = self.conn.cursor()
        
        cursor.execute('SELECT volume_remaining_ml FROM preparations WHERE id = ?', (prep_id,))
        result = cursor.fetchone()
        
        if not result:
            print(f"Preparazione #{prep_id} non trovata")
            return False
        

        volume_remaining = result[0]
        
        # Arrotonda per evitare errori float
        volume_rounded = round(volume_remaining, 3)
        ml_used_rounded = round(ml_used, 3)
        
        if volume_rounded < ml_used_rounded:
            print(f"Volume insufficiente (disponibile: {volume_rounded:.3f}ml, richiesto: {ml_used_rounded:.3f}ml)")
            return False
        
        # Log se esaurisce preparazione
        if volume_rounded == ml_used_rounded:
            print(f"⚠️  Questa somministrazione esaurirà la preparazione #{prep_id}")
        
        # Aggiorna volume rimanente
        cursor.execute('''
            UPDATE preparations SET volume_remaining_ml = volume_remaining_ml - ?
            WHERE id = ?
        ''', (ml_used, prep_id))
        
        # Registra somministrazione
        if administration_datetime is None:
            administration_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute('''
            INSERT INTO administrations (
                preparation_id, administration_datetime, dose_ml,
                injection_site, injection_method, notes, protocol_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (prep_id, administration_datetime, ml_used, injection_site, injection_method, notes, protocol_id))
        
        self.conn.commit()
        
        new_remaining = volume_remaining - ml_used
        print(f"{ml_used}ml utilizzati da preparazione #{prep_id}")
        print(f"  Sito: {injection_site} ({injection_method})")
        print(f"  Volume rimanente: {new_remaining:.2f}ml")
        
        return True
    
    def update_preparation(self, prep_id: int, **kwargs) -> bool:
        """
        Aggiorna una preparazione.
        
        Campi supportati:
        - expiry_date, volume_remaining_ml, storage_location, notes
        - batch_id, vials_used, volume_ml, diluent, preparation_date
        
        ⚠️ NOTA: Se modifichi batch_id o vials_used, le fiale NON vengono 
        automaticamente ripristinate/prelevate. Gestisci manualmente se necessario.
        """
        cursor = self.conn.cursor()
        
        # Tutti i campi ora supportati
        allowed_fields = [
            'expiry_date', 'volume_remaining_ml', 'storage_location', 'notes',
            'batch_id', 'vials_used', 'volume_ml', 'diluent', 'preparation_date'
        ]
        
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not updates:
            print("Nessun campo valido da aggiornare")
            return False
        
        # Warning se cambia batch_id o vials_used
        if 'batch_id' in updates or 'vials_used' in updates:
            print("⚠️ WARNING: batch_id o vials_used modificati.")
            print("   Le fiale NON vengono automaticamente ripristinate/prelevate.")
            print("   Verifica manualmente il conteggio fiale se necessario.")
        
        set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [prep_id]
        
        cursor.execute(f'UPDATE preparations SET {set_clause} WHERE id = ?', values)
        self.conn.commit()
        
        print(f"✓ Preparazione #{prep_id} aggiornata")
        print(f"  Updated fields: {list(updates.keys())}")
        return True
    
    def delete_preparation(self, prep_id: int, restore_vials: bool = False) -> bool:
        """
        Elimina una preparazione.
    
        Args:
            prep_id: ID preparazione
            restore_vials: Se True, riaggiunge le fiale al batch
        """
        cursor = self.conn.cursor()
    
        prep = self.get_preparation_details(prep_id)
        if not prep:
            print(f"Preparazione #{prep_id} non trovata")
            return False
    
        # Controlla somministrazioni attive
        cursor.execute('SELECT COUNT(*) FROM administrations WHERE preparation_id = ? AND deleted_at IS NULL', (prep_id,))
        admin_count = cursor.fetchone()[0]
    
        if admin_count > 0:
            print(f"❌ Impossibile eliminare preparazione #{prep_id}")
            print(f"   Ha {admin_count} somministrazioni registrate")
            print(f"   Elimina prima le somministrazioni")
            return False
    
        # Ripristina fiale se richiesto
        if restore_vials:
            cursor.execute('''
                UPDATE batches 
                SET vials_remaining = vials_remaining + ?
                WHERE id = ?
            ''', (prep['vials_used'], prep['batch_id']))
            print(f"  ✓ Ripristinate {prep['vials_used']} fiale al batch #{prep['batch_id']}")
    
        # Elimina
        cursor.execute('DELETE FROM preparations WHERE id = ?', (prep_id,))
        self.conn.commit()
    
        print(f"✓ Preparazione #{prep_id} eliminata")
        return True
    
    def get_expired_preparations(self) -> List[Dict]:
        """
        Recupera preparazioni scadute.
        """
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT p.*, b.product_name
            FROM preparations p
            JOIN batches b ON p.batch_id = b.id
            WHERE p.expiry_date IS NOT NULL
            AND p.expiry_date < date('now')
            AND p.volume_remaining_ml > 0
            ORDER BY p.expiry_date
        ''')
        
        return [dict(row) for row in cursor.fetchall()]
        
# ==================== PROTOCOLS ====================
    
    def add_protocol(self, name: str, dose_ml: float, frequency_per_day: int = 1,
                    days_on: int = None, days_off: int = 0, cycle_duration_weeks: int = None,
                    peptides: List[Tuple[str, float]] = None,
                    description: str = None, notes: str = None) -> int:
        """Crea un nuovo protocollo di dosaggio."""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            INSERT INTO protocols (
                name, description, dose_ml, frequency_per_day,
                days_on, days_off, cycle_duration_weeks, notes, active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
        ''', (name, description, dose_ml, frequency_per_day,
              days_on, days_off, cycle_duration_weeks, notes))
        
        protocol_id = cursor.lastrowid
        
        # Aggiungi peptidi al protocollo
        if peptides:
            for peptide_name, target_dose_mcg in peptides:
                cursor.execute('SELECT id FROM peptides WHERE name = ?', (peptide_name,))
                peptide = cursor.fetchone()
                
                if not peptide:
                    cursor.execute('INSERT INTO peptides (name) VALUES (?)', (peptide_name,))
                    peptide_id = cursor.lastrowid
                else:
                    peptide_id = peptide[0]
                
                cursor.execute('''
                    INSERT INTO protocol_peptides (protocol_id, peptide_id, target_dose_mcg)
                    VALUES (?, ?, ?)
                ''', (protocol_id, peptide_id, target_dose_mcg))
        
        self.conn.commit()
        
        print(f"Protocollo '{name}' creato (ID: {protocol_id})")
        print(f"  Dose: {dose_ml}ml x {frequency_per_day}/giorno")
        if days_on:
            print(f"  Schema: {days_on} giorni ON, {days_off} giorni OFF")
        
        return protocol_id
    
    def get_protocols(self, active_only: bool = True) -> List[Dict]:
        """Recupera protocolli."""
        cursor = self.conn.cursor()
        
        query = 'SELECT * FROM protocols'
        if active_only:
            query += ' WHERE active = 1'
        query += ' ORDER BY created_at DESC'
        
        cursor.execute(query)
        return [dict(row) for row in cursor.fetchall()]
    
    def get_protocol_details(self, protocol_id: int) -> Dict:
        """Recupera dettagli completi di un protocollo."""
        cursor = self.conn.cursor()
        
        cursor.execute('SELECT * FROM protocols WHERE id = ?', (protocol_id,))
        protocol = cursor.fetchone()
        
        if not protocol:
            return None
        
        result = dict(protocol)
        
        # Peptidi nel protocollo
        cursor.execute('''
            SELECT p.id, p.name, pp.target_dose_mcg
            FROM protocol_peptides pp
            JOIN peptides p ON pp.peptide_id = p.id
            WHERE pp.protocol_id = ?
        ''', (protocol_id,))
        result['peptides'] = [dict(row) for row in cursor.fetchall()]
        
        # Somministrazioni attive
        cursor.execute('''
            SELECT COUNT(*), MIN(administration_datetime), MAX(administration_datetime)
            FROM administrations
            WHERE protocol_id = ? AND deleted_at IS NULL
        ''', (protocol_id,))
        
        count, first_date, last_date = cursor.fetchone()
        result['administrations_count'] = count or 0
        result['first_administration'] = first_date
        result['last_administration'] = last_date
        
        return result
    
    def update_protocol(self, protocol_id: int, **kwargs) -> bool:
        """Aggiorna un protocollo."""
        allowed_fields = ['name', 'description', 'dose_ml', 'frequency_per_day',
                         'days_on', 'days_off', 'cycle_duration_weeks', 'notes', 'active']
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not updates:
            print("Nessun campo valido da aggiornare")
            return False
        
        set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [protocol_id]
        
        cursor = self.conn.cursor()
        cursor.execute(f'UPDATE protocols SET {set_clause} WHERE id = ?', values)
        self.conn.commit()
        
        print(f"Protocollo ID {protocol_id} aggiornato")
        return True
    
    def activate_protocol(self, protocol_id: int) -> bool:
        """Attiva un protocollo."""
        return self.update_protocol(protocol_id, active=1)
    
    def deactivate_protocol(self, protocol_id: int) -> bool:
        """Disattiva un protocollo."""
        return self.update_protocol(protocol_id, active=0)
    
    def get_administrations(self, protocol_id: int = None, preparation_id: int = None,
                           days_back: int = None) -> List[Dict]:
        """Recupera log somministrazioni."""
        cursor = self.conn.cursor()
        
        query = '''
            SELECT a.*, pr.name as protocol_name, prep.batch_id,
                   b.product_name as batch_product
            FROM administrations a
            LEFT JOIN protocols pr ON a.protocol_id = pr.id
            LEFT JOIN preparations prep ON a.preparation_id = prep.id
            LEFT JOIN batches b ON prep.batch_id = b.id
            WHERE a.deleted_at IS NULL
        '''
        params = []
        
        if protocol_id:
            query += ' AND a.protocol_id = ?'
            params.append(protocol_id)
        
        if preparation_id:
            query += ' AND a.preparation_id = ?'
            params.append(preparation_id)
        
        if days_back:
            query += ' AND a.administration_datetime >= datetime("now", ?)'
            params.append(f'-{days_back} days')
        
        query += ' ORDER BY a.administration_datetime DESC'
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def get_protocol_statistics(self, protocol_id: int) -> Dict:
        """Calcola statistiche per un protocollo."""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*), SUM(dose_ml), 
                   MIN(administration_datetime), MAX(administration_datetime)
            FROM administrations
            WHERE protocol_id = ? AND deleted_at IS NULL
        ''', (protocol_id,))
        
        total_admin, total_ml, first_date, last_date = cursor.fetchone()
        
        cursor.execute('''
            SELECT COUNT(DISTINCT DATE(administration_datetime))
            FROM administrations
            WHERE protocol_id = ? AND deleted_at IS NULL
        ''', (protocol_id,))
        
        days_active = cursor.fetchone()[0]
        
        protocol = self.get_protocol_details(protocol_id)
        
        if first_date and last_date and protocol:
            start = datetime.strptime(first_date, '%Y-%m-%d %H:%M:%S')
            end = datetime.strptime(last_date, '%Y-%m-%d %H:%M:%S')
            days_elapsed = (end - start).days + 1
            
            expected_admin = days_elapsed * protocol['frequency_per_day']
            adherence = (total_admin / expected_admin * 100) if expected_admin > 0 else 0
        else:
            days_elapsed = 0
            expected_admin = 0
            adherence = 0
        
        return {
            'total_administrations': total_admin or 0,
            'total_ml_used': total_ml or 0.0,
            'first_date': first_date,
            'last_date': last_date,
            'days_active': days_active or 0,
            'days_elapsed': days_elapsed,
            'expected_administrations': expected_admin,
            'adherence_percentage': round(adherence, 1)
        }
    
    def delete_protocol(self, protocol_id: int, unlink_administrations: bool = True) -> bool:
        """
        Elimina un protocollo.
    
        Args:
            protocol_id: ID protocollo
            unlink_administrations: Se True, scollega le somministrazioni (non le elimina)
        """
        cursor = self.conn.cursor()
    
        protocol = self.get_protocol_details(protocol_id)
        if not protocol:
            print(f"Protocollo #{protocol_id} non trovato")
            return False
    
        # Controlla somministrazioni attive
        cursor.execute('SELECT COUNT(*) FROM administrations WHERE protocol_id = ? AND deleted_at IS NULL', (protocol_id,))
        admin_count = cursor.fetchone()[0]
    
        if admin_count > 0:
            if unlink_administrations:
                # Scollega somministrazioni (protocol_id → NULL)
                cursor.execute('''
                    UPDATE administrations 
                    SET protocol_id = NULL 
                    WHERE protocol_id = ?
                ''', (protocol_id,))
                print(f"  ✓ Scollegate {admin_count} somministrazioni (non eliminate)")
            else:
                print(f"❌ Impossibile eliminare protocollo #{protocol_id}")
                print(f"   Ha {admin_count} somministrazioni collegate")
                print(f"   Usa unlink_administrations=True per scollegarle")
                return False
    
        # Elimina (CASCADE eliminerà da protocol_peptides)
        cursor.execute('DELETE FROM protocols WHERE id = ?', (protocol_id,))
        self.conn.commit()
    
        print(f"✓ Protocollo #{protocol_id} '{protocol['name']}' eliminato")
        return True

    def delete_administration(self, admin_id: int, restore_volume: bool = False) -> bool:
        """
        Elimina una somministrazione.
    
        Args:
            admin_id: ID somministrazione
            restore_volume: Se True, riaggiunge il volume alla preparazione
        """
        cursor = self.conn.cursor()
    
        cursor.execute('SELECT * FROM administrations WHERE id = ?', (admin_id,))
        admin = cursor.fetchone()
    
        if not admin:
            print(f"Somministrazione #{admin_id} non trovata")
            return False
    
        admin_dict = dict(admin)
    
        # Ripristina volume se richiesto
        if restore_volume and admin_dict['preparation_id']:
            cursor.execute('''
                UPDATE preparations 
                SET volume_remaining_ml = volume_remaining_ml + ?
                WHERE id = ?
            ''', (admin_dict['dose_ml'], admin_dict['preparation_id']))
            print(f"  ✓ Ripristinati {admin_dict['dose_ml']}ml alla preparazione #{admin_dict['preparation_id']}")
    
        # Elimina
        cursor.execute('DELETE FROM administrations WHERE id = ?', (admin_id,))
        self.conn.commit()
    
        print(f"✓ Somministrazione #{admin_id} eliminata")
        return True
    
    def link_administration_to_protocol(self, admin_id: int, protocol_id: int) -> bool:
        """
        Collega una somministrazione esistente a un protocollo.
        Utile per registrare retroattivamente somministrazioni in un protocollo.
    
        Args:
            admin_id: ID somministrazione
            protocol_id: ID protocollo
    
        Returns:
            True se successo
        """
        cursor = self.conn.cursor()
    
        # Verifica esistenza
        cursor.execute('SELECT id FROM administrations WHERE id = ?', (admin_id,))
        if not cursor.fetchone():
            print(f"Somministrazione #{admin_id} non trovata")
            return False
    
        cursor.execute('SELECT id FROM protocols WHERE id = ?', (protocol_id,))
        if not cursor.fetchone():
            print(f"Protocollo #{protocol_id} non trovato")
            return False
    
        # Aggiorna
        cursor.execute('''
            UPDATE administrations 
            SET protocol_id = ? 
            WHERE id = ?
        ''', (protocol_id, admin_id))
    
        self.conn.commit()
    
        print(f"✓ Somministrazione #{admin_id} collegata a protocollo #{protocol_id}")
        return True

    def link_multiple_administrations_to_protocol(self, admin_ids: List[int], 
                                                protocol_id: int) -> int:
        """
        Collega più somministrazioni a un protocollo (bulk operation).
    
        Returns:
            Numero di somministrazioni collegate
        """
        cursor = self.conn.cursor()
    
        # Verifica protocollo
        cursor.execute('SELECT id FROM protocols WHERE id = ?', (protocol_id,))
        if not cursor.fetchone():
            print(f"Protocollo #{protocol_id} non trovato")
            return 0
    
        updated = 0
        for admin_id in admin_ids:
            cursor.execute('''
                UPDATE administrations 
                SET protocol_id = ? 
                WHERE id = ?
            ''', (protocol_id, admin_id))
        
            if cursor.rowcount > 0:
                updated += 1
    
        self.conn.commit()
    
        print(f"✓ {updated} somministrazioni collegate a protocollo #{protocol_id}")
        return updated
    
    def update_administration(self, admin_id: int, **kwargs) -> bool:
        """
        Aggiorna informazioni di una somministrazione.
        
        Campi modificabili:
        - preparation_id: ID preparazione
        - administration_datetime: Data e ora somministrazione (YYYY-MM-DD HH:MM:SS)
        - dose_ml: Dose in ml
        - injection_site: Sito iniezione anatomico
        - injection_method: Modalità iniezione (SubQ o IM)
        - protocol_id: ID protocollo (opzionale)
        - notes: Note
        
        Returns:
            True se aggiornato con successo
        """
        allowed_fields = ['preparation_id', 'administration_datetime', 'dose_ml', 
                         'injection_site', 'injection_method', 'protocol_id', 'notes']
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not updates:
            print("Nessun campo valido da aggiornare")
            return False
        
        cursor = self.conn.cursor()
        
        # Recupera valori attuali
        cursor.execute('''
            SELECT preparation_id, dose_ml 
            FROM administrations 
            WHERE id = ?
        ''', (admin_id,))
        current = cursor.fetchone()
        
        if not current:
            print(f"Somministrazione #{admin_id} non trovata")
            return False
        
        old_prep_id, old_dose = current
        
        # Update administration
        set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [admin_id]
        
        cursor.execute(f'UPDATE administrations SET {set_clause} WHERE id = ?', values)
        self.conn.commit()
        
        print(f"✓ Somministrazione #{admin_id} aggiornata")
        
        # Ricalcola volumi se cambiate dose o preparazione
        if 'dose_ml' in updates or 'preparation_id' in updates:
            preps_to_recalc = {old_prep_id}
            
            if 'preparation_id' in updates:
                new_prep_id = updates['preparation_id']
                preps_to_recalc.add(new_prep_id)
            
            # Ricalcola volumi di tutte le preparazioni coinvolte
            for prep_id in preps_to_recalc:
                if prep_id:
                    self._recalculate_preparation_volume(prep_id)
        
        return True
    
    def get_all_administrations_df(self):
        """
        Recupera TUTTE le somministrazioni come DataFrame pandas.
        
        Carica tutti i dati con JOIN necessari, pronto per analytics.
        Approccio: carica tutto in memoria, poi filtra con pandas (velocissimo).
        
        Returns:
            pandas.DataFrame con colonne:
                - id, preparation_id, protocol_id, batch_id
                - dose_ml, dose_mcg (calcolato)
                - administration_datetime (già convertito in datetime)
                - date, time (colonne separate)
                - injection_site, injection_method
                - notes
                - batch_product (nome prodotto batch)
                - protocol_name
                - peptide_names (stringa con nomi peptidi, comma-separated)
                - concentration_mg_ml
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas non installato. Installa con: pip install pandas")
        
        cursor = self.conn.cursor()
        
        query = '''
            SELECT 
                a.id,
                a.preparation_id,
                a.protocol_id,
                a.dose_ml,
                COALESCE(
                    a.dose_ml * (prep.vials_used * b.mg_per_vial / prep.volume_ml) * 1000, 
                    0
                ) as dose_mcg,
                a.administration_datetime,
                a.injection_site,
                a.injection_method,
                a.notes,
                prep.batch_id,
                COALESCE(
                    prep.vials_used * b.mg_per_vial / prep.volume_ml,
                    0
                ) as concentration_mg_ml,
                b.product_name as batch_product,
                pr.name as protocol_name,
                GROUP_CONCAT(DISTINCT p.name) as peptide_names
            FROM administrations a
            LEFT JOIN preparations prep ON a.preparation_id = prep.id
            LEFT JOIN batches b ON prep.batch_id = b.id
            LEFT JOIN protocols pr ON a.protocol_id = pr.id
            LEFT JOIN batch_composition bc ON b.id = bc.batch_id
            LEFT JOIN peptides p ON bc.peptide_id = p.id
            WHERE a.deleted_at IS NULL
            GROUP BY a.id
            ORDER BY a.administration_datetime DESC
        '''
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        # Converti in DataFrame
        df = pd.DataFrame(rows, columns=[
            'id', 'preparation_id', 'protocol_id', 'dose_ml', 'dose_mcg',
            'administration_datetime', 'injection_site', 'injection_method', 
            'notes', 'batch_id', 'concentration_mg_ml', 'batch_product',
            'protocol_name', 'peptide_names'
        ])
        
        if len(df) == 0:
            # DataFrame vuoto ma con le colonne corrette
            return df
        
        # Converti datetime
        df['administration_datetime'] = pd.to_datetime(df['administration_datetime'])
        
        # Aggiungi colonne derivate per comodità
        df['date'] = df['administration_datetime'].dt.date
        df['time'] = df['administration_datetime'].dt.time
        df['year'] = df['administration_datetime'].dt.year
        df['month'] = df['administration_datetime'].dt.month
        df['day_of_week'] = df['administration_datetime'].dt.day_name()
        
        # Sostituisci None con stringhe vuote per filtri
        df['injection_site'] = df['injection_site'].fillna('')
        df['injection_method'] = df['injection_method'].fillna('')
        df['notes'] = df['notes'].fillna('')
        df['protocol_name'] = df['protocol_name'].fillna('Nessuno')
        df['peptide_names'] = df['peptide_names'].fillna('N/A')
        
        return df
    
    # ==================== SOFT DELETE & VOLUME RECONCILIATION ====================
    
    def _recalculate_preparation_volume(self, prep_id: int) -> bool:
        """
        Ricalcola il volume rimanente di una preparazione basandosi sulle 
        somministrazioni ATTIVE (non eliminate).
        
        Args:
            prep_id: ID della preparazione
            
        Returns:
            True se successo
        """
        cursor = self.conn.cursor()
        
        # Recupera volume iniziale
        cursor.execute('SELECT volume_ml FROM preparations WHERE id = ?', (prep_id,))
        result = cursor.fetchone()
        
        if not result:
            print(f"⚠️ Preparazione #{prep_id} non trovata")
            return False
        
        volume_initial = result[0]
        
        # Somma tutte le dosi delle somministrazioni ATTIVE
        cursor.execute('''
            SELECT COALESCE(SUM(dose_ml), 0)
            FROM administrations
            WHERE preparation_id = ? AND deleted_at IS NULL
        ''', (prep_id,))
        
        total_used = cursor.fetchone()[0]
        
        # Calcola volume rimanente
        volume_remaining = volume_initial - total_used
        
        # Aggiorna preparazione
        cursor.execute('''
            UPDATE preparations
            SET volume_remaining_ml = ?
            WHERE id = ?
        ''', (volume_remaining, prep_id))
        
        self.conn.commit()
        
        print(f"✓ Prep #{prep_id}: Ricalcolato volume = {volume_remaining:.2f}ml "
              f"(iniziale: {volume_initial:.2f}ml, usato: {total_used:.2f}ml)")
        
        return True
    
    def soft_delete_administration(self, admin_id: int) -> bool:
        """
        Elimina (soft delete) una somministrazione e ricalcola automaticamente 
        il volume della preparazione associata.
        
        Args:
            admin_id: ID somministrazione
            
        Returns:
            True se successo
        """
        cursor = self.conn.cursor()
        
        # Recupera info somministrazione
        cursor.execute('''
            SELECT preparation_id, dose_ml
            FROM administrations
            WHERE id = ?
        ''', (admin_id,))
        
        result = cursor.fetchone()
        
        if not result:
            print(f"⚠️ Somministrazione #{admin_id} non trovata")
            return False
        
        prep_id, dose_ml = result
        
        # Soft delete somministrazione
        cursor.execute('''
            UPDATE administrations
            SET deleted_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (admin_id,))
        
        self.conn.commit()
        
        print(f"✓ Somministrazione #{admin_id} eliminata (soft delete)")
        
        # Ricalcola volume preparazione
        if prep_id:
            self._recalculate_preparation_volume(prep_id)
        
        return True
    
    def restore_administration(self, admin_id: int) -> bool:
        """
        Ripristina una somministrazione eliminata e ricalcola automaticamente
        il volume della preparazione associata.
        
        Args:
            admin_id: ID somministrazione
            
        Returns:
            True se successo
        """
        cursor = self.conn.cursor()
        
        # Recupera info somministrazione
        cursor.execute('''
            SELECT preparation_id, dose_ml
            FROM administrations
            WHERE id = ?
        ''', (admin_id,))
        
        result = cursor.fetchone()
        
        if not result:
            print(f"⚠️ Somministrazione #{admin_id} non trovata")
            return False
        
        prep_id, dose_ml = result
        
        # Restore (rimuovi deleted_at)
        cursor.execute('''
            UPDATE administrations
            SET deleted_at = NULL
            WHERE id = ?
        ''', (admin_id,))
        
        self.conn.commit()
        
        print(f"✓ Somministrazione #{admin_id} ripristinata")
        
        # Ricalcola volume preparazione
        if prep_id:
            self._recalculate_preparation_volume(prep_id)
        
        return True
    
    def get_deleted_administrations(self) -> List[Dict]:
        """
        Recupera tutte le somministrazioni eliminate (soft delete).
        
        Returns:
            Lista di dizionari con le somministrazioni eliminate
        """
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT 
                a.id,
                a.administration_datetime,
                a.dose_ml,
                a.deleted_at,
                b.product_name,
                GROUP_CONCAT(DISTINCT p.name) as peptide_names
            FROM administrations a
            LEFT JOIN preparations prep ON a.preparation_id = prep.id
            LEFT JOIN batches b ON prep.batch_id = b.id
            LEFT JOIN batch_composition bc ON b.id = bc.batch_id
            LEFT JOIN peptides p ON bc.peptide_id = p.id
            WHERE a.deleted_at IS NOT NULL
            GROUP BY a.id
            ORDER BY a.deleted_at DESC
        ''')
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def reconcile_preparation_volumes(self, prep_id: int = None) -> Dict:
        """
        Riconcilia i volumi delle preparazioni con le somministrazioni attive.
        Corregge eventuali inconsistenze dovute a:
        - Eliminazioni manuali nel database
        - Bug passati
        - Migrazioni
        
        Args:
            prep_id: Se specificato, riconcilia solo questa preparazione.
                    Se None, riconcilia TUTTE le preparazioni.
        
        Returns:
            Dizionario con statistiche:
            {
                'checked': int,        # Preparazioni controllate
                'fixed': int,          # Preparazioni corrette
                'total_diff': float,   # Differenza totale (ml)
                'details': [           # Dettagli per ogni correzione
                    {
                        'prep_id': int,
                        'product_name': str,
                        'old_volume': float,
                        'new_volume': float,
                        'difference': float
                    }
                ]
            }
        """
        cursor = self.conn.cursor()
        
        # Query preparazioni da controllare
        if prep_id:
            cursor.execute('''
                SELECT p.id, p.volume_ml, p.volume_remaining_ml, b.product_name
                FROM preparations p
                JOIN batches b ON p.batch_id = b.id
                WHERE p.id = ? AND p.deleted_at IS NULL
            ''', (prep_id,))
        else:
            cursor.execute('''
                SELECT p.id, p.volume_ml, p.volume_remaining_ml, b.product_name
                FROM preparations p
                JOIN batches b ON p.batch_id = b.id
                WHERE p.deleted_at IS NULL
            ''')
        
        preparations = cursor.fetchall()
        
        stats = {
            'checked': 0,
            'fixed': 0,
            'total_diff': 0.0,
            'details': []
        }
        
        for prep_id, volume_initial, volume_current, product_name in preparations:
            stats['checked'] += 1
            
            # Calcola volume corretto
            cursor.execute('''
                SELECT COALESCE(SUM(dose_ml), 0)
                FROM administrations
                WHERE preparation_id = ? AND deleted_at IS NULL
            ''', (prep_id,))
            
            total_used = cursor.fetchone()[0]
            volume_correct = volume_initial - total_used
            
            # Confronta con tolleranza di 0.001 ml
            difference = volume_current - volume_correct
            
            if abs(difference) > 0.001:
                # Inconsistenza trovata!
                cursor.execute('''
                    UPDATE preparations
                    SET volume_remaining_ml = ?
                    WHERE id = ?
                ''', (volume_correct, prep_id))
                
                stats['fixed'] += 1
                stats['total_diff'] += abs(difference)
                stats['details'].append({
                    'prep_id': prep_id,
                    'product_name': product_name,
                    'old_volume': volume_current,
                    'new_volume': volume_correct,
                    'difference': difference
                })
                
                print(f"🔧 Prep #{prep_id} ({product_name}): "
                      f"{volume_current:.2f}ml → {volume_correct:.2f}ml "
                      f"({difference:+.2f}ml)")
        
        self.conn.commit()
        
        if stats['fixed'] == 0:
            print(f"✅ Tutte le {stats['checked']} preparazioni sono consistenti!")
        else:
            print(f"🔧 Corrette {stats['fixed']}/{stats['checked']} preparazioni "
                  f"(diff totale: {stats['total_diff']:.2f}ml)")
        
        return stats
    
    def check_data_integrity(self) -> Dict:
        """
        Verifica l'integrità dei dati senza correggere.
        Utile per diagnostica o check on startup.
        
        Returns:
            Dizionario con:
            {
                'preparations_ok': int,
                'preparations_inconsistent': int,
                'inconsistent_details': [...]
            }
        """
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT p.id, p.volume_ml, p.volume_remaining_ml, b.product_name
            FROM preparations p
            JOIN batches b ON p.batch_id = b.id
            WHERE p.deleted_at IS NULL
        ''')
        
        preparations = cursor.fetchall()
        
        result = {
            'preparations_ok': 0,
            'preparations_inconsistent': 0,
            'inconsistent_details': []
        }
        
        for prep_id, volume_initial, volume_current, product_name in preparations:
            # Calcola volume atteso
            cursor.execute('''
                SELECT COALESCE(SUM(dose_ml), 0)
                FROM administrations
                WHERE preparation_id = ? AND deleted_at IS NULL
            ''', (prep_id,))
            
            total_used = cursor.fetchone()[0]
            volume_expected = volume_initial - total_used
            
            difference = volume_current - volume_expected
            
            if abs(difference) > 0.001:
                # Inconsistenza
                result['preparations_inconsistent'] += 1
                result['inconsistent_details'].append({
                    'prep_id': prep_id,
                    'product_name': product_name,
                    'current_volume': volume_current,
                    'expected_volume': volume_expected,
                    'difference': difference
                })
            else:
                result['preparations_ok'] += 1
        
        return result

