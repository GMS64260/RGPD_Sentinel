#!/usr/bin/env python
import unittest
import sys
from pathlib import Path

def run_tests():
    """Exécuter tous les tests unitaires et fonctionnels"""
    # Ajouter le répertoire parent au chemin pour permettre l'importation
    parent_dir = str(Path(__file__).resolve().parent)
    if parent_dir not in sys.path:
        sys.path.append(parent_dir)
    
    # Découvrir et exécuter tous les tests
    test_suite = unittest.defaultTestLoader.discover('tests')
    test_runner = unittest.TextTestRunner(verbosity=2)
    result = test_runner.run(test_suite)
    
    # Retourner un code d'erreur si des tests ont échoué
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(run_tests())
