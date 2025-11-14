"""
Moduli legacy - Contenuto minimizzato.

NOTA: La maggior parte dei metodi è stata migrata alla nuova architettura
Repository Pattern in peptide_manager/models/. 

Questo file mantiene solo:
- check_data_integrity(): Metodo diagnostico per verificare consistenza dati

Per riferimento storico, vedi git history (commit precedenti alla pulizia).
"""

import sqlite3
from typing import Dict


class PeptideManager:
    """
    Classe legacy minimizzata per retrocompatibilità.
    Mantiene solo metodi diagnostici non ancora migrati.
    """
    
    def __init__(self, db_path='peptide_management.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
    
    def close(self):
        """Chiude la connessione al database."""
        self.conn.close()
    
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
