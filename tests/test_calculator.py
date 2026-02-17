"""
Test per DilutionCalculator.
"""

import unittest
from datetime import datetime, timedelta
from peptide_manager.calculator import DilutionCalculator


class TestDilutionCalculator(unittest.TestCase):

    def test_calculate_dilution(self):
        """Test calcolo diluizione."""
        result = DilutionCalculator.calculate_dilution(5.0, 2.5)
        self.assertEqual(result, 2.0)

    def test_calculate_dilution_zero_concentration_raises(self):
        """ValueError when target concentration <= 0."""
        with self.assertRaises(ValueError):
            DilutionCalculator.calculate_dilution(5.0, 0)
        with self.assertRaises(ValueError):
            DilutionCalculator.calculate_dilution(5.0, -1.0)

    def test_calculate_concentration(self):
        """Test calcolo concentrazione."""
        result = DilutionCalculator.calculate_concentration(5.0, 2.0)
        self.assertEqual(result, 2.5)

    def test_calculate_concentration_zero_volume_raises(self):
        """ValueError when volume <= 0."""
        with self.assertRaises(ValueError):
            DilutionCalculator.calculate_concentration(5.0, 0)
        with self.assertRaises(ValueError):
            DilutionCalculator.calculate_concentration(5.0, -1.0)

    def test_mcg_to_ml(self):
        """Test conversione mcg a ml."""
        result = DilutionCalculator.mcg_to_ml(250, 2.5)
        self.assertAlmostEqual(result, 0.1, places=2)

    def test_ml_to_mcg(self):
        """Test conversione ml a mcg."""
        result = DilutionCalculator.ml_to_mcg(0.1, 2.5)
        self.assertAlmostEqual(result, 250.0, places=1)

    def test_calculate_blend_dilution(self):
        """Blend dilution returns max volume across peptides."""
        peptides = [('BPC-157', 5.0), ('TB-500', 10.0)]
        targets = {'BPC-157': 2.5, 'TB-500': 2.5}
        # BPC-157: 5/2.5 = 2.0ml, TB-500: 10/2.5 = 4.0ml → max = 4.0
        result = DilutionCalculator.calculate_blend_dilution(peptides, targets)
        self.assertEqual(result, 4.0)

    def test_calculate_blend_dilution_empty(self):
        """Blend dilution returns 0.0 for empty input."""
        result = DilutionCalculator.calculate_blend_dilution([], {})
        self.assertEqual(result, 0.0)

    def test_doses_from_preparation(self):
        """Dose count from preparation parameters."""
        # 5mg in 2ml = 2.5mg/ml. Dose = 250mcg = 0.25mg. ml_per_dose = 0.1ml.
        # 2.0 / 0.1 = 20 doses
        result = DilutionCalculator.doses_from_preparation(5.0, 2.0, 250)
        self.assertEqual(result, 20)

    def test_suggested_dilution_for_dose(self):
        """Returns correct dict structure and values."""
        result = DilutionCalculator.suggested_dilution_for_dose(
            mg_peptide=5.0,
            target_dose_mcg=250,
            target_volume_ml=0.1
        )
        self.assertIn('volume_diluente_ml', result)
        self.assertIn('concentrazione_mg_ml', result)
        self.assertIn('volume_per_dose_ml', result)
        self.assertIn('dosi_totali', result)
        self.assertIn('mg_per_dose', result)
        self.assertEqual(result['volume_per_dose_ml'], 0.1)
        self.assertEqual(result['mg_per_dose'], 0.25)

    def test_suggested_dilution_min_doses_adjusts(self):
        """When natural dose count < min_doses, volume is increased."""
        # 5mg peptide, 250mcg dose, 0.1ml per injection
        # concentration_needed = 0.25mg / 0.1ml = 2.5mg/ml
        # volume_diluente = 5.0 / 2.5 = 2.0ml → num_doses = 2.0/0.1 = 20
        # With min_doses=50, 20 < 50, so volume adjusts to 0.1 * 50 = 5.0ml
        result = DilutionCalculator.suggested_dilution_for_dose(
            mg_peptide=5.0,
            target_dose_mcg=250,
            target_volume_ml=0.1,
            min_doses=50
        )
        self.assertEqual(result['dosi_totali'], 50)
        self.assertEqual(result['volume_diluente_ml'], 5.0)

    def test_calculate_expiry_date_standard(self):
        """Standard peptides get 28 days."""
        result = DilutionCalculator.calculate_expiry_date('2025-06-01', 'standard')
        self.assertEqual(result, '2025-06-29')

    def test_calculate_expiry_date_fragment(self):
        """Fragment peptides get 14 days."""
        result = DilutionCalculator.calculate_expiry_date('2025-06-01', 'fragment')
        self.assertEqual(result, '2025-06-15')

    def test_calculate_expiry_date_modified(self):
        """Modified peptides get 21 days."""
        result = DilutionCalculator.calculate_expiry_date('2025-06-01', 'modified')
        self.assertEqual(result, '2025-06-22')

    def test_analyze_preparation_basic(self):
        """Analyze preparation returns expected structure."""
        result = DilutionCalculator.analyze_preparation(
            vials_used=1, mg_per_vial=5.0, volume_ml=2.0
        )
        self.assertEqual(result['total_mg'], 5.0)
        self.assertEqual(result['concentration_mg_ml'], 2.5)
        self.assertEqual(result['concentration_mcg_ml'], 2500.0)
        self.assertEqual(result['volume_ml'], 2.0)
        self.assertIn('conversions', result)
        self.assertNotIn('target_dose_mcg', result)

    def test_analyze_preparation_with_target_dose(self):
        """Analyze preparation with target dose includes dose calculations."""
        result = DilutionCalculator.analyze_preparation(
            vials_used=1, mg_per_vial=5.0, volume_ml=2.0, target_dose_mcg=250
        )
        self.assertEqual(result['target_dose_mcg'], 250)
        self.assertIn('ml_per_dose', result)
        self.assertIn('doses_available', result)
        # 2.5mg/ml concentration, 250mcg=0.25mg dose, ml_per_dose = 0.25/2.5 = 0.1
        self.assertAlmostEqual(result['ml_per_dose'], 0.1, places=3)
        # 2.0ml / 0.1ml = 20 doses
        self.assertEqual(result['doses_available'], 20)


if __name__ == '__main__':
    unittest.main()
