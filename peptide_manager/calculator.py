"""
Calcolatori per diluizioni peptidiche e conversioni.
"""

from typing import Dict, List, Tuple
from datetime import datetime, timedelta


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
