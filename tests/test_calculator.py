"""
Test per DilutionCalculator.
"""

import unittest
from peptide_manager.calculator import DilutionCalculator


class TestDilutionCalculator(unittest.TestCase):
    
    def test_calculate_dilution(self):
        """Test calcolo diluizione."""
        result = DilutionCalculator.calculate_dilution(5.0, 2.5)
        self.assertEqual(result, 2.0)
    
    def test_mcg_to_ml(self):
        """Test conversione mcg a ml."""
        result = DilutionCalculator.mcg_to_ml(250, 2.5)
        self.assertAlmostEqual(result, 0.1, places=2)
    
    def test_ml_to_mcg(self):
        """Test conversione ml a mcg."""
        result = DilutionCalculator.ml_to_mcg(0.1, 2.5)
        self.assertAlmostEqual(result, 250.0, places=1)


if __name__ == '__main__':
    unittest.main()
