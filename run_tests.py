# Crea script di test

import unittest
import sys

if __name__ == '__main__':
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Aggiungi test esplicitamente
    suite.addTests(loader.loadTestsFromName('tests.test_models.test_supplier'))
    suite.addTests(loader.loadTestsFromName('tests.test_models.test_peptide'))
    suite.addTests(loader.loadTestsFromName('tests.test_adapter'))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    sys.exit(0 if result.wasSuccessful() else 1)
