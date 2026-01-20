"""
Calcolatori per diluizioni peptidiche e conversioni.
"""

from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal
import json


class DilutionCalculator:
    """
    Calcolatore per diluizioni peptidiche e conversioni.
    """
    
    @staticmethod
    def calculate_dilution(mg_peptide: float, target_concentration_mg_ml: float) -> float:
        """
        Calcola il volume di diluente necessario per ottenere una concentrazione target.
        
        Args:
            mg_peptide: Quantità di peptide in mg
            target_concentration_mg_ml: Concentrazione desiderata in mg/ml
            
        Returns:
            Volume di diluente in ml
            
        Example:
            >>> DilutionCalculator.calculate_dilution(5.0, 2.5)
            2.0  # 5mg in 2ml = 2.5mg/ml
        """
        if target_concentration_mg_ml <= 0:
            raise ValueError("La concentrazione deve essere maggiore di 0")
        
        return mg_peptide / target_concentration_mg_ml
    
    @staticmethod
    def calculate_concentration(mg_peptide: float, volume_ml: float) -> float:
        """
        Calcola la concentrazione risultante.
        
        Args:
            mg_peptide: Quantità di peptide in mg
            volume_ml: Volume di diluente in ml
            
        Returns:
            Concentrazione in mg/ml
        """
        if volume_ml <= 0:
            raise ValueError("Il volume deve essere maggiore di 0")
        
        return mg_peptide / volume_ml
    
    @staticmethod
    def mcg_to_ml(target_dose_mcg: float, concentration_mg_ml: float) -> float:
        """
        Converte una dose in mcg al volume necessario in ml.
        
        Args:
            target_dose_mcg: Dose desiderata in microgrammi
            concentration_mg_ml: Concentrazione della preparazione in mg/ml
            
        Returns:
            Volume da iniettare in ml
            
        Example:
            >>> DilutionCalculator.mcg_to_ml(250, 2.5)
            0.1  # 250mcg con concentrazione 2.5mg/ml = 0.1ml
        """
        target_dose_mg = target_dose_mcg / 1000.0
        return target_dose_mg / concentration_mg_ml
    
    @staticmethod
    def ml_to_mcg(volume_ml: float, concentration_mg_ml: float) -> float:
        """
        Converte un volume in ml alla dose in mcg.
        
        Args:
            volume_ml: Volume iniettato in ml
            concentration_mg_ml: Concentrazione della preparazione in mg/ml
            
        Returns:
            Dose in microgrammi
        """
        dose_mg = volume_ml * concentration_mg_ml
        return dose_mg * 1000.0
    
    @staticmethod
    def calculate_blend_dilution(peptides: List[Tuple[str, float]], 
                                 target_concentrations: Dict[str, float]) -> float:
        """
        Calcola la diluizione per un blend di peptidi.
        
        Args:
            peptides: Lista di tuple (nome_peptide, mg_per_vial)
            target_concentrations: Dict con concentrazioni target per peptide
            
        Returns:
            Volume di diluente consigliato in ml
            
        Example:
            >>> peptides = [('BPC-157', 5.0), ('TB-500', 5.0)]
            >>> targets = {'BPC-157': 2.5, 'TB-500': 2.5}
            >>> DilutionCalculator.calculate_blend_dilution(peptides, targets)
            2.0
        """
        volumes = []
        for name, mg in peptides:
            if name in target_concentrations:
                vol = DilutionCalculator.calculate_dilution(mg, target_concentrations[name])
                volumes.append(vol)
        
        # Usa il volume massimo necessario per rispettare tutte le concentrazioni
        return max(volumes) if volumes else 0.0
    
    @staticmethod
    def doses_from_preparation(total_mg: float, volume_ml: float, 
                               dose_mcg: float) -> int:
        """
        Calcola quante dosi si possono ottenere da una preparazione.
        
        Args:
            total_mg: mg totali nella preparazione
            volume_ml: Volume totale della preparazione
            dose_mcg: Dose per somministrazione in mcg
            
        Returns:
            Numero di dosi
        """
        concentration = DilutionCalculator.calculate_concentration(total_mg, volume_ml)
        ml_per_dose = DilutionCalculator.mcg_to_ml(dose_mcg, concentration)
        return int(volume_ml / ml_per_dose)
    
    @staticmethod
    def suggested_dilution_for_dose(mg_peptide: float, target_dose_mcg: float,
                                    target_volume_ml: float = 0.2,
                                    min_doses: int = 10) -> Dict:
        """
        Suggerisce una diluizione ottimale per una dose specifica.
        Calcola il volume per ottenere almeno min_doses somministrazioni.
        
        Args:
            mg_peptide: mg di peptide disponibili
            target_dose_mcg: Dose desiderata in mcg per somministrazione
            target_volume_ml: Volume desiderato per iniezione (default 0.2ml)
            min_doses: Numero minimo di dosi desiderate
            
        Returns:
            Dict con volume_diluente_ml, concentrazione_mg_ml, dosi_totali
        """
        target_dose_mg = target_dose_mcg / 1000.0
        concentration_needed = target_dose_mg / target_volume_ml
        volume_diluente = DilutionCalculator.calculate_dilution(mg_peptide, concentration_needed)
        num_doses = int(volume_diluente / target_volume_ml)
        
        # Se non abbastanza dosi, aumenta volume
        if num_doses < min_doses:
            volume_diluente = target_volume_ml * min_doses
            concentration_needed = mg_peptide / volume_diluente
            num_doses = min_doses
        
        return {
            'volume_diluente_ml': round(volume_diluente, 2),
            'concentrazione_mg_ml': round(concentration_needed, 3),
            'volume_per_dose_ml': target_volume_ml,
            'dosi_totali': num_doses,
            'mg_per_dose': round(target_dose_mg, 3)
        }
    
    @staticmethod
    def calculate_expiry_date(preparation_date: str, peptide_type: str = 'standard') -> str:
        """
        Calcola data di scadenza suggerita per una preparazione ricostituita.
        
        Args:
            preparation_date: Data preparazione (YYYY-MM-DD)
            peptide_type: Tipo peptide (standard, fragment, modified)
            
        Returns:
            Data scadenza suggerita (YYYY-MM-DD)
            
        Note:
            - Standard peptides: 28 giorni in frigo
            - Fragment peptides: 14 giorni
            - Modified peptides: 21 giorni
        """
        prep_date = datetime.strptime(preparation_date, '%Y-%m-%d')
        
        days_map = {
            'standard': 28,
            'fragment': 14,
            'modified': 21
        }
        
        days = days_map.get(peptide_type, 28)
        expiry_date = prep_date + timedelta(days=days)
        
        return expiry_date.strftime('%Y-%m-%d')
    
    @staticmethod
    def analyze_preparation(vials_used: int, mg_per_vial: float, volume_ml: float,
                           target_dose_mcg: float = None) -> Dict:
        """
        Analizza completa una preparazione con tutti i calcoli utili.
        
        Args:
            vials_used: Numero fiale utilizzate
            mg_per_vial: mg per fiala
            volume_ml: Volume totale preparazione
            target_dose_mcg: Dose target desiderata (opzionale)
            
        Returns:
            Dict con tutti i calcoli
        """
        total_mg = vials_used * mg_per_vial
        concentration = total_mg / volume_ml
        concentration_mcg_ml = concentration * 1000
        
        result = {
            'total_mg': total_mg,
            'concentration_mg_ml': round(concentration, 3),
            'concentration_mcg_ml': round(concentration_mcg_ml, 1),
            'volume_ml': volume_ml
        }
        
        if target_dose_mcg:
            ml_per_dose = DilutionCalculator.mcg_to_ml(target_dose_mcg, concentration)
            num_doses = int(volume_ml / ml_per_dose)
            
            result.update({
                'target_dose_mcg': target_dose_mcg,
                'ml_per_dose': round(ml_per_dose, 3),
                'doses_available': num_doses
            })
        
        # Conversioni comuni
        result['conversions'] = {
            '0.1ml': round(DilutionCalculator.ml_to_mcg(0.1, concentration), 1),
            '0.2ml': round(DilutionCalculator.ml_to_mcg(0.2, concentration), 1),
            '0.25ml': round(DilutionCalculator.ml_to_mcg(0.25, concentration), 1),
            '0.5ml': round(DilutionCalculator.ml_to_mcg(0.5, concentration), 1),
            '1.0ml': round(DilutionCalculator.ml_to_mcg(1.0, concentration), 1)
        }
        
        return result
    
    @staticmethod
    def compare_dilutions(mg_peptide: float, volumes: List[float]) -> List[Dict]:
        """
        Compara diverse opzioni di diluizione.
        
        Args:
            mg_peptide: mg di peptide disponibili
            volumes: Lista di volumi da comparare
            
        Returns:
            Lista di dict con analisi per ogni volume
        """
        results = []
        
        for vol in volumes:
            conc = DilutionCalculator.calculate_concentration(mg_peptide, vol)
            
            results.append({
                'volume_ml': vol,
                'concentration_mg_ml': round(conc, 3),
                'concentration_mcg_ml': round(conc * 1000, 1),
                'doses_at_250mcg': DilutionCalculator.doses_from_preparation(mg_peptide, vol, 250),
                'doses_at_500mcg': DilutionCalculator.doses_from_preparation(mg_peptide, vol, 500),
                'ml_per_250mcg': round(DilutionCalculator.mcg_to_ml(250, conc), 3),
                'ml_per_500mcg': round(DilutionCalculator.mcg_to_ml(500, conc), 3)
            })
        
        return results


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def print_dilution_guide(mg_peptide: float, volume_ml: float, 
                        common_doses: List[int] = None):
    """
    Stampa una guida rapida per una diluizione specifica.
    
    Args:
        mg_peptide: mg totali
        volume_ml: Volume preparazione
        common_doses: Lista dosi comuni in mcg (default: [100, 250, 500, 1000])
    """
    if common_doses is None:
        common_doses = [100, 250, 500, 1000]
    
    calc = DilutionCalculator()
    concentration = calc.calculate_concentration(mg_peptide, volume_ml)
    
    print(f"\n{'='*60}")
    print(f"GUIDA DILUIZIONE")
    print(f"{'='*60}")
    print(f"Peptide: {mg_peptide}mg in {volume_ml}ml")
    print(f"Concentrazione: {concentration:.3f}mg/ml ({concentration*1000:.1f}mcg/ml)")
    print(f"\nTabella Dosaggi:")
    print(f"{'Dose':<15} {'Volume':<15} {'Dosi Disponibili'}")
    print(f"{'-'*60}")
    
    for dose_mcg in common_doses:
        ml_needed = calc.mcg_to_ml(dose_mcg, concentration)
        num_doses = calc.doses_from_preparation(mg_peptide, volume_ml, dose_mcg)
        print(f"{dose_mcg}mcg{' ':<10} {ml_needed:.3f}ml{' ':<10} {num_doses} dosi")
    
    print(f"{'='*60}\n")


def suggest_optimal_dilution(mg_peptide: float, target_dose_mcg: float,
                            frequency_per_day: int = 1, days: int = 30):
    """
    Suggerisce diluizione ottimale basata su frequenza e durata.
    
    Args:
        mg_peptide: mg disponibili
        target_dose_mcg: Dose per somministrazione
        frequency_per_day: Somministrazioni al giorno
        days: Durata ciclo in giorni
    """
    calc = DilutionCalculator()
    
    total_doses_needed = frequency_per_day * days
    total_mg_needed = (target_dose_mcg / 1000) * total_doses_needed
    
    print(f"\n{'='*60}")
    print(f"SUGGERIMENTO DILUIZIONE OTTIMALE")
    print(f"{'='*60}")
    print(f"Peptide disponibile: {mg_peptide}mg")
    print(f"Dose target: {target_dose_mcg}mcg")
    print(f"Frequenza: {frequency_per_day}x/giorno per {days} giorni")
    print(f"Dosi totali necessarie: {total_doses_needed}")
    print(f"mg totali necessari: {total_mg_needed:.2f}mg")
    
    if total_mg_needed > mg_peptide:
        print(f"\n⚠️  ATTENZIONE: mg insufficienti!")
        print(f"   Serve: {total_mg_needed:.2f}mg")
        print(f"   Hai: {mg_peptide}mg")
        print(f"   Mancano: {total_mg_needed - mg_peptide:.2f}mg")
    else:
        print(f"\n✓ mg sufficienti")
        print(f"   Surplus: {mg_peptide - total_mg_needed:.2f}mg")
    
    # Suggerisci volumi
    suggestions = calc.suggested_dilution_for_dose(
        mg_peptide, 
        target_dose_mcg,
        target_volume_ml=0.2,
        min_doses=total_doses_needed
    )
    
    print(f"\nDiluizione suggerita:")
    print(f"  Volume diluente: {suggestions['volume_diluente_ml']}ml")
    print(f"  Concentrazione: {suggestions['concentrazione_mg_ml']:.3f}mg/ml")
    print(f"  Volume per dose: {suggestions['volume_per_dose_ml']}ml")
    print(f"  Dosi disponibili: {suggestions['dosi_totali']}")
    print(f"{'='*60}\n")


# ============================================================
# RESOURCE PLANNER - Multi-Phase Treatment Planning
# ============================================================

class ResourcePlanner:
    """
    Calcolatore risorse per piani di trattamento multi-fase.
    
    Calcola peptidi, materiali consumabili necessari per un piano completo.
    """
    
    # Configurazione materiali standard
    SYRINGE_BUFFER_PERCENTAGE = 10  # 10% extra siringhe
    CONSUMABLES_CONFIG = {
        'syringe_1ml': {
            'name': 'Syringe 1ml Insulin',
            'unit': 'units',
            'buffer_percentage': 10
        },
        'needle_31g': {
            'name': 'Needle 31G 8mm',
            'unit': 'units',
            'buffer_percentage': 10
        },
        'alcohol_swabs': {
            'name': 'Alcohol Swabs',
            'unit': 'units',
            'buffer_percentage': 15
        },
        'sharps_container': {
            'name': 'Sharps Container 1L',
            'unit': 'units',
            'per_injections': 50  # 1 contenitore ogni 50 iniezioni
        }
    }
    
    def __init__(self, db=None):
        """
        Args:
            db: Database connection (opzionale, per inventory check)
        """
        self.db = db
        self.calculator = DilutionCalculator()
    
    def calculate_phase_requirements(
        self,
        phase_config: Dict[str, Any],
        inventory_check: bool = True
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Calcola risorse necessarie per una singola fase.
        
        Args:
            phase_config: Configurazione fase con struttura:
                {
                    'phase_name': str,
                    'duration_weeks': int,
                    'peptides': [
                        {
                            'peptide_id': int,
                            'peptide_name': str,
                            'dose_mcg': float,
                            'mg_per_vial': float (opzionale, default 5mg)
                        }
                    ],
                    'daily_frequency': int,
                    'five_two_protocol': bool
                }
            inventory_check: Se True, controlla inventario disponibile
            
        Returns:
            Dict con chiavi 'peptides', 'consumables' contenenti liste di requirements
        """
        duration_weeks = phase_config['duration_weeks']
        peptides_list = phase_config['peptides']
        daily_frequency = phase_config.get('daily_frequency', 1)
        five_two = phase_config.get('five_two_protocol', False)
        
        # Calcola giorni on
        if five_two:
            on_days = duration_weeks * 5  # 5 giorni a settimana
        else:
            on_days = duration_weeks * 7  # Tutti i giorni
        
        # Totale iniezioni
        total_injections = on_days * daily_frequency
        
        # Calcola peptidi
        peptide_requirements = []
        for peptide in peptides_list:
            peptide_id = peptide.get('peptide_id')
            peptide_name = peptide['peptide_name']
            dose_mcg = peptide['dose_mcg']
            mg_per_vial = peptide.get('mg_per_vial', 5.0)  # Default 5mg
            
            # Calcola mg totali necessari
            total_mg_needed = (dose_mcg / 1000.0) * total_injections
            
            # Calcola vials necessari (arrotonda per eccesso)
            vials_needed = int((total_mg_needed / mg_per_vial) + 0.9999)
            
            # Inventory check se richiesto
            vials_available = 0
            if inventory_check and self.db and peptide_id:
                vials_available = self._get_available_vials(peptide_id)
            
            peptide_requirements.append({
                'resource_type': 'peptide',
                'resource_id': peptide_id,
                'resource_name': peptide_name,
                'dose_mcg': dose_mcg,
                'injections': total_injections,
                'mg_needed': round(total_mg_needed, 2),
                'mg_per_vial': mg_per_vial,
                'vials_needed': vials_needed,
                'vials_available': vials_available,
                'vials_gap': max(0, vials_needed - vials_available),
                'quantity_needed': vials_needed,
                'quantity_available': vials_available,
                'quantity_unit': 'vials'
            })
        
        # Calcola diluente (bacteriostatic water)
        # Assumo 2ml per vial in media
        total_vials = sum(p['vials_needed'] for p in peptide_requirements)
        diluent_ml = total_vials * 2.0
        
        diluent_requirement = {
            'resource_type': 'diluent',
            'resource_name': 'Bacteriostatic Water',
            'quantity_needed': round(diluent_ml, 1),
            'quantity_unit': 'ml',
            'vials_30ml_needed': int((diluent_ml / 30.0) + 0.9999)  # Flaconi da 30ml
        }
        
        # Calcola consumabili
        consumable_requirements = self._calculate_consumables(total_injections)
        consumable_requirements.append(diluent_requirement)
        
        return {
            'peptides': peptide_requirements,
            'consumables': consumable_requirements,
            'summary': {
                'total_injections': total_injections,
                'duration_weeks': duration_weeks,
                'on_days': on_days,
                'daily_frequency': daily_frequency
            }
        }
    
    def calculate_total_plan_resources(
        self,
        phases: List[Dict[str, Any]],
        inventory_check: bool = True
    ) -> Dict[str, Any]:
        """
        Calcola risorse aggregate per intero piano multi-fase.
        
        Args:
            phases: Lista di configurazioni fasi
            inventory_check: Se True, controlla inventario
            
        Returns:
            Dict con risorse aggregate e breakdown per fase
        """
        phase_breakdowns = []
        
        # Aggregatori
        peptides_agg = {}  # peptide_id -> requirement dict
        consumables_agg = {}  # resource_name -> requirement dict
        
        for idx, phase_config in enumerate(phases, 1):
            phase_req = self.calculate_phase_requirements(phase_config, inventory_check=False)
            
            phase_breakdowns.append({
                'phase_number': idx,
                'phase_name': phase_config.get('phase_name', f'Phase {idx}'),
                'requirements': phase_req
            })
            
            # Aggrega peptidi
            for peptide in phase_req['peptides']:
                peptide_id = peptide.get('resource_id')
                key = peptide_id if peptide_id else peptide['resource_name']
                
                if key not in peptides_agg:
                    peptides_agg[key] = peptide.copy()
                else:
                    # Somma quantità in mg (non vials, perché le fiale possono avere dimensioni diverse!)
                    peptides_agg[key]['injections'] += peptide['injections']
                    peptides_agg[key]['mg_needed'] += peptide['mg_needed']
                    # Non sommare vials_needed direttamente se mg_per_vial è diverso
                    # Verrà ricalcolato dopo basandoci sul mg_needed totale
            
            # Aggrega consumabili
            for consumable in phase_req['consumables']:
                name = consumable['resource_name']
                
                if name not in consumables_agg:
                    consumables_agg[name] = consumable.copy()
                else:
                    consumables_agg[name]['quantity_needed'] += consumable['quantity_needed']
        
        # Ricalcola vials_needed per ogni peptide aggregato basandosi sul mg_needed totale
        for key, peptide in peptides_agg.items():
            mg_per_vial = peptide.get('mg_per_vial', 5.0)  # Usa la dimensione della prima occorrenza
            total_mg = peptide['mg_needed']
            # Ricalcola vials con arrotondamento per eccesso
            vials_needed = int((total_mg / mg_per_vial) + 0.9999)
            peptides_agg[key]['vials_needed'] = vials_needed
            peptides_agg[key]['quantity_needed'] = vials_needed
        
        # Inventory check su totali se richiesto
        if inventory_check and self.db:
            for key, peptide in peptides_agg.items():
                if peptide.get('resource_id'):
                    vials_available = self._get_available_vials(peptide['resource_id'])
                    peptide['vials_available'] = vials_available
                    peptide['quantity_available'] = vials_available
                    peptide['vials_gap'] = max(0, peptide['vials_needed'] - vials_available)
        
        return {
            'total_peptides': list(peptides_agg.values()),
            'total_consumables': list(consumables_agg.values()),
            'phase_breakdown': phase_breakdowns,
            'summary': {
                'total_phases': len(phases),
                'total_duration_weeks': sum(p['duration_weeks'] for p in phases),
                'total_injections': sum(p['requirements']['summary']['total_injections'] 
                                       for p in phase_breakdowns)
            }
        }
    
    def check_inventory_coverage(
        self,
        peptide_requirements: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analizza gap inventario vs requisiti.
        
        Args:
            peptide_requirements: Lista requirements da calculate_phase_requirements
            
        Returns:
            Dict con analisi gap e raccomandazioni ordini
        """
        if not self.db:
            raise ValueError("Database connection richiesto per inventory check")
        
        analysis = {
            'has_gaps': False,
            'peptides_analysis': [],
            'ordering_recommendations': []
        }
        
        for peptide in peptide_requirements:
            peptide_id = peptide.get('resource_id')
            if not peptide_id:
                continue
            
            vials_needed = peptide['vials_needed']
            vials_available = self._get_available_vials(peptide_id)
            gap = vials_needed - vials_available
            
            peptide_analysis = {
                'peptide_id': peptide_id,
                'peptide_name': peptide['resource_name'],
                'vials_needed': vials_needed,
                'vials_available': vials_available,
                'vials_gap': gap,
                'has_gap': gap > 0,
                'coverage_percentage': round((vials_available / vials_needed * 100), 1) if vials_needed > 0 else 100
            }
            
            analysis['peptides_analysis'].append(peptide_analysis)
            
            if gap > 0:
                analysis['has_gaps'] = True
                
                # Calcola quando ordinare (es. ordina per settimana 2 se serve per settimana 4)
                # Buffer di 2 settimane per shipping
                order_by_week = max(1, (peptide.get('start_week', 1) - 2))
                
                analysis['ordering_recommendations'].append({
                    'peptide_name': peptide['resource_name'],
                    'vials_to_order': gap,
                    'order_by_week': order_by_week,
                    'priority': 'high' if gap > 5 else 'medium',
                    'estimated_cost': self._estimate_peptide_cost(peptide_id, gap)
                })
        
        return analysis
    
    def _calculate_consumables(self, total_injections: int) -> List[Dict[str, Any]]:
        """Calcola materiali consumabili necessari."""
        consumables = []
        
        # Siringhe
        syringes_needed = int(total_injections * (1 + self.SYRINGE_BUFFER_PERCENTAGE / 100.0))
        consumables.append({
            'resource_type': 'syringe',
            'resource_name': self.CONSUMABLES_CONFIG['syringe_1ml']['name'],
            'quantity_needed': syringes_needed,
            'quantity_unit': 'units'
        })
        
        # Aghi
        needles_needed = int(total_injections * (1 + self.CONSUMABLES_CONFIG['needle_31g']['buffer_percentage'] / 100.0))
        consumables.append({
            'resource_type': 'needle',
            'resource_name': self.CONSUMABLES_CONFIG['needle_31g']['name'],
            'quantity_needed': needles_needed,
            'quantity_unit': 'units'
        })
        
        # Alcohol swabs
        swabs_needed = int(total_injections * (1 + self.CONSUMABLES_CONFIG['alcohol_swabs']['buffer_percentage'] / 100.0))
        consumables.append({
            'resource_type': 'consumable',
            'resource_name': self.CONSUMABLES_CONFIG['alcohol_swabs']['name'],
            'quantity_needed': swabs_needed,
            'quantity_unit': 'units'
        })
        
        # Sharps container
        containers_needed = int((total_injections / self.CONSUMABLES_CONFIG['sharps_container']['per_injections']) + 0.9999)
        consumables.append({
            'resource_type': 'consumable',
            'resource_name': self.CONSUMABLES_CONFIG['sharps_container']['name'],
            'quantity_needed': containers_needed,
            'quantity_unit': 'units'
        })
        
        return consumables
    
    def _get_available_vials(self, peptide_id: int) -> int:
        """
        Query inventario per vials disponibili.
        
        Args:
            peptide_id: ID peptide
            
        Returns:
            Numero vials disponibili
        """
        if not self.db:
            return 0
        
        cursor = self.db.conn.cursor()
        
        # Query batches attivi per peptide
        cursor.execute("""
            SELECT COALESCE(SUM(vials_remaining), 0) as total_vials
            FROM batches
            WHERE deleted_at IS NULL
            AND (expiry_date IS NULL OR expiry_date > DATE('now'))
            AND vials_remaining > 0
            AND id IN (
                SELECT DISTINCT batch_id 
                FROM batch_composition 
                WHERE peptide_id = ?
            )
        """, (peptide_id,))
        
        result = cursor.fetchone()
        return int(result[0]) if result else 0
    
    def _estimate_peptide_cost(self, peptide_id: int, vials: int) -> Optional[Decimal]:
        """
        Stima costo basato su ultimi acquisti.
        
        Args:
            peptide_id: ID peptide
            vials: Numero vials da ordinare
            
        Returns:
            Costo stimato o None
        """
        if not self.db:
            return None
        
        cursor = self.db.conn.cursor()
        
        # Media prezzo per vial da ultimi 3 acquisti
        cursor.execute("""
            SELECT AVG(price_per_vial) as avg_price
            FROM batches
            WHERE deleted_at IS NULL
            AND price_per_vial IS NOT NULL
            AND id IN (
                SELECT DISTINCT batch_id 
                FROM batch_composition 
                WHERE peptide_id = ?
            )
            ORDER BY purchase_date DESC
            LIMIT 3
        """, (peptide_id,))
        
        result = cursor.fetchone()
        if result and result[0]:
            avg_price = Decimal(str(result[0]))
            return round(avg_price * vials, 2)
        
        return None

