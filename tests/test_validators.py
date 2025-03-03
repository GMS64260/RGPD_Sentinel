# tests/test_validators.py
import sys
import os
import unittest
from pathlib import Path

# Ajouter le répertoire parent au chemin pour permettre l'importation
parent_dir = str(Path(__file__).resolve().parent.parent)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from analyzer.validators import (
    validate_email, validate_phone, validate_date, 
    validate_secu, validate_siret, validate_person_name,
    validate_postal_address, validate_ip_address
)

class TestValidators(unittest.TestCase):
    def test_validate_email(self):
        # Cas valides
        self.assertTrue(validate_email("test@example.com"))
        self.assertTrue(validate_email("user.name+tag@example.co.uk"))
        self.assertTrue(validate_email("x@y.z"))
        
        # Cas invalides
        self.assertFalse(validate_email(""))
        self.assertFalse(validate_email("test@ogfa.com"))  # Email de l'organisation
        self.assertFalse(validate_email("test@example"))  # Pas de TLD
        self.assertFalse(validate_email("test.example.com"))  # Pas de @
        self.assertFalse(validate_email("@example.com"))  # Pas de nom local
        
    def test_validate_phone(self):
        # Cas valides
        self.assertTrue(validate_phone("0612345678"))
        self.assertTrue(validate_phone("06 12 34 56 78"))
        self.assertTrue(validate_phone("06.12.34.56.78"))
        self.assertTrue(validate_phone("06-12-34-56-78"))
        self.assertTrue(validate_phone("+33612345678"))
        self.assertTrue(validate_phone("+33 6 12 34 56 78"))
        self.assertTrue(validate_phone("0033612345678"))
        
        # Cas invalides
        self.assertFalse(validate_phone(""))
        self.assertFalse(validate_phone("0512345678"))  # Commence par 05, pas un mobile
        self.assertFalse(validate_phone("061234567"))  # Trop court
        self.assertFalse(validate_phone("abc1234567"))  # Contient des lettres
        
    def test_validate_date(self):
        # Cas valides
        self.assertTrue(validate_date("01/01/2020"))
        self.assertTrue(validate_date("31/12/2020"))
        self.assertTrue(validate_date("29/02/2020"))  # Année bissextile
        self.assertTrue(validate_date("01-01-2020"))
        self.assertTrue(validate_date("31.12.2020"))
        
        # Cas invalides
        self.assertFalse(validate_date(""))
        self.assertFalse(validate_date("32/01/2020"))  # Jour invalide
        self.assertFalse(validate_date("29/02/2021"))  # Pas bissextile
        self.assertFalse(validate_date("01/13/2020"))  # Mois invalide
        self.assertFalse(validate_date("01/01/1800"))  # Année trop ancienne
        
    def test_validate_secu(self):
        # Cas valides
        self.assertTrue(validate_secu("196123456789012"))  # Homme né en décembre 1961
        self.assertTrue(validate_secu("295073123456712"))  # Femme née en juillet 1995
        self.assertTrue(validate_secu("1540239123456"))     # Format sans clé
        
        # Cas invalides
        self.assertFalse(validate_secu(""))
        self.assertFalse(validate_secu("12345"))  # Trop court
        self.assertFalse(validate_secu("496123456789012"))  # Premier chiffre invalide
        self.assertFalse(validate_secu("195139123456712"))  # Mois 13 invalide
        
    def test_validate_siret(self):
        # Cas valides - numéros de test respectant l'algorithme de Luhn
        self.assertTrue(validate_siret("73282932000074"))
        self.assertTrue(validate_siret("35600000000048"))
        
        # Cas invalides
        self.assertFalse(validate_siret(""))
        self.assertFalse(validate_siret("1234567890"))  # Trop court
        self.assertFalse(validate_siret("73282932000075"))  # Clé invalide
        self.assertFalse(validate_siret("12345678901234567"))  # Trop long
    
    def test_validate_postal_address(self):
        # Cas valides
        self.assertTrue(validate_postal_address("12 Rue de la Paix, 75002"))
        self.assertTrue(validate_postal_address("1 Avenue des Champs-Élysées, 75008 Paris"))
        self.assertTrue(validate_postal_address("42, Boulevard Haussmann - 75009 PARIS"))
        self.assertTrue(validate_postal_address("8 place du Commerce 44000 Nantes"))
        
        # Cas invalides
        self.assertFalse(validate_postal_address(""))
        self.assertFalse(validate_postal_address("Rue de la Paix"))  # Pas de numéro ni code postal
        self.assertFalse(validate_postal_address("12, 75001"))  # Pas de nom de rue
        self.assertFalse(validate_postal_address("12 Rue de la Paix, 750"))  # Code postal invalide
    
    def test_validate_ip_address(self):
        # Cas valides IPv4
        self.assertTrue(validate_ip_address("192.168.1.1"))
        self.assertTrue(validate_ip_address("127.0.0.1"))
        self.assertTrue(validate_ip_address("8.8.8.8"))
        self.assertTrue(validate_ip_address("255.255.255.255"))
        
        # Cas valides IPv6
        self.assertTrue(validate_ip_address("2001:0db8:85a3:0000:0000:8a2e:0370:7334"))
        self.assertTrue(validate_ip_address("fe80::1"))
        self.assertTrue(validate_ip_address("::1"))
        
        # Cas invalides
        self.assertFalse(validate_ip_address(""))
        self.assertFalse(validate_ip_address("192.168.1"))  # IPv4 incomplète
        self.assertFalse(validate_ip_address("192.168.1.300"))  # Valeur d'octet invalide
        self.assertFalse(validate_ip_address("2001:0db8:gggg::1"))  # Caractères invalides dans IPv6
    
    def test_validate_person_name(self):
        # Préparation du texte de contexte
        context = "Bonjour, je m'appelle Jean Dupont. Je travaille avec Marie Martin de l'équipe RH. Contactez-moi au 0612345678."
        
        # Cas valides
        valid, confidence = validate_person_name("Jean Dupont", context)
        self.assertTrue(valid)
        self.assertGreaterEqual(confidence, 0.3)
        
        valid, confidence = validate_person_name("Marie Martin", context)
        self.assertTrue(valid)
        self.assertGreaterEqual(confidence, 0.3)
        
        # Cas invalides
        valid, confidence = validate_person_name("", context)
        self.assertFalse(valid)
        
        valid, confidence = validate_person_name("JP", context)  # Trop court
        self.assertFalse(valid)
        
        valid, confidence = validate_person_name("Département RH", context)  # Organisation, pas une personne
        self.assertFalse(valid)
        
        # Nom en majuscules (acronyme)
        valid, confidence = validate_person_name("OGFA", context)
        self.assertFalse(valid)
        
        # Nom avec caractères spéciaux
        valid, confidence = validate_person_name("Jean@Dupont", context)
        self.assertFalse(valid)
        
        # Contexte professionnel
        prof_context = "Le Directeur M. Pierre Durand a signé le document. Veuillez contacter le service RH."
        valid, confidence = validate_person_name("Pierre Durand", prof_context)
        # Doit être valide mais avec un score de confiance possiblement réduit
        self.assertTrue(valid)

if __name__ == "__main__":
    unittest.main()