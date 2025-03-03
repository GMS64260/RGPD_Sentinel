# tests/test_functional.py
import sys
import os
import unittest
from pathlib import Path
import pandas as pd
import tempfile

# Ajouter le répertoire parent au chemin pour permettre l'importation
parent_dir = str(Path(__file__).resolve().parent.parent)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from analyzer.core import (
    detect_personal_data, 
    is_likely_organizational_name,
    validate_email, 
    validate_phone,
    validate_postal_address,
    validate_ip_address
)

class TestFunctionalIntegration(unittest.TestCase):
    """Tests fonctionnels pour vérifier l'intégration des nouvelles fonctionnalités."""
    
    def setUp(self):
        """Prépare des exemples de contenu pour tester les fonctions."""
        self.test_content_with_personal_data = """
        Bonjour,
        
        Je m'appelle Jean Dupont et je travaille pour la société XYZ.
        Vous pouvez me contacter par email à jean.dupont@example.com ou par téléphone au 06 12 34 56 78.
        Mon adresse est 12 rue de la Paix, 75002 Paris.
        Mon numéro de sécurité sociale est 1850775123456 12.
        Notre numéro SIRET est 12345678901234.
        
        Je vous transmets l'adresse IP du serveur : 192.168.1.1
        
        Cordialement,
        Jean Dupont
        Directeur Commercial
        """
        
        self.test_content_with_organization_context = """
        RAPPORT INTERNE
        
        Document rédigé par Marie Martin, responsable du service RH.
        Veuillez contacter l'équipe informatique à admin@ogfa.fr pour tout problème.
        La direction OGFA peut être jointe à l'adresse 5 avenue des Lilas, 75020 Paris.
        
        Pour tout contact, veuillez appeler le standard au 01 23 45 67 89 ou contacter notre agent d'accueil
        Veuillez contacter Pierre Durand (Responsable informatique) en cas de problème technique.
        """
        
        self.test_content_template = """
        EXEMPLE DE DOCUMENT
        
        Nom: [Prénom NOM]
        Email: xxx@example.com
        Téléphone: 06 12 34 56 78
        Adresse: 10 rue de l'exemple, 75001 Paris
        IP: 192.168.0.1
        
        Monsieur X,
        
        Ceci est un exemple de document.
        
        Cordialement,
        [Signature]
        """

    def test_detect_personal_data_includes_new_types(self):
        """Vérifie que la fonction detect_personal_data détecte bien les nouveaux types de données."""
        results = detect_personal_data(self.test_content_with_personal_data)
        
        # Vérifier que les champs traditionnels sont détectés
        self.assertIn("emails", results)
        self.assertIn("phones", results)
        self.assertIn("names", results)
        
        # Vérifier que les nouveaux types sont bien présents et détectés
        self.assertIn("postal_addresses", results)
        self.assertIn("ip_addresses", results)
        
        # Vérifier les détections spécifiques
        emails_found = [item["value"] for item in results["emails"]]
        self.assertIn("jean.dupont@example.com", emails_found)
        
        phones_found = [item["value"] for item in results["phones"]]
        self.assertTrue(any("06 12 34 56 78" in phone for phone in phones_found))
        
        addresses_found = [item["value"] for item in results["postal_addresses"]]
        self.assertTrue(any("12 rue de la Paix, 75002" in addr for addr in addresses_found))
        
        ips_found = [item["value"] for item in results["ip_addresses"]]
        self.assertIn("192.168.1.1", ips_found)

    def test_improved_context_analysis(self):
        """Vérifie que l'analyse contextuelle distingue bien les contextes personnels et organisationnels."""
        # Tester si un nom dans un contexte organisationnel est correctement identifié
        self.assertTrue(
            is_likely_organizational_name(
                self.test_content_with_organization_context, 
                "Marie Martin"
            )
        )
        
        # Vérifier qu'un nom en contexte personnel n'est pas identifié comme organisationnel
        self.assertFalse(
            is_likely_organizational_name(
                self.test_content_with_personal_data,
                "Jean Dupont"
            )
        )
        
        # Vérifier que les services/départements sont identifiés comme organisationnels
        self.assertTrue(
            is_likely_organizational_name(
                self.test_content_with_organization_context,
                "service RH"
            )
        )

    def test_template_detection(self):
        """Vérifie que les détections dans les templates ont des scores de confiance réduits."""
        # Détections dans un contenu standard
        std_results = detect_personal_data(self.test_content_with_personal_data)
        # Détections dans un template
        template_results = detect_personal_data(self.test_content_template)
        
        # Vérifier que les emails dans les templates ont un score de confiance plus bas
        if std_results["emails"] and template_results["emails"]:
            std_email_confidence = std_results["emails"][0]["confidence"]
            template_email_confidence = template_results["emails"][0]["confidence"]
            self.assertGreater(std_email_confidence, template_email_confidence)
        
        # Vérifier que certaines détections sont filtrées dans les templates
        template_names = [item["value"] for item in template_results.get("names", [])]
        self.assertNotIn("Monsieur X", template_names)

    def test_validation_functions(self):
        """Vérifie que les fonctions de validation améliorées fonctionnent correctement."""
        # Tests pour les emails
        self.assertTrue(validate_email("user.name+tag@example.com"))
        self.assertFalse(validate_email("test@ogfa.fr"))  # Domaine de l'organisation
        
        # Tests pour les téléphones
        self.assertTrue(validate_phone("06-12-34-56-78"))
        self.assertTrue(validate_phone("+33 6 12 34 56 78"))
        self.assertFalse(validate_phone("0612345"))  # Trop court
        
        # Tests pour les adresses postales
        self.assertTrue(validate_postal_address("12 rue de la Paix, 75002 Paris"))
        self.assertTrue(validate_postal_address("1, Avenue des Champs-Élysées 75008"))
        self.assertFalse(validate_postal_address("rue de la Paix, 75002"))  # Pas de numéro
        
        # Tests pour les adresses IP
        self.assertTrue(validate_ip_address("192.168.1.1"))
        self.assertTrue(validate_ip_address("2001:0db8:85a3:0000:0000:8a2e:0370:7334"))
        self.assertFalse(validate_ip_address("192.168.1"))  # Incomplète

    def test_integration_with_file_analysis(self):
        """Vérifie l'intégration des nouvelles détections dans l'analyse de fichier."""
        # Créer un fichier temporaire pour les tests
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w", encoding="utf-8") as tmp_file:
            tmp_file.write(self.test_content_with_personal_data)
            temp_path = tmp_file.name
        
        try:
            # Importer uniquement ici pour éviter les dépendances lors des autres tests
            from analyzer.core import analyze_file
            
            # Analyser le fichier temporaire
            result = analyze_file(temp_path)
            
            # Vérifier que l'analyse inclut les nouveaux types de données
            self.assertIn("postal_addresses_found", result)
            self.assertIn("ip_addresses_found", result)
            
            # Vérifier que les risques sont calculés pour ces types
            self.assertIn("postal_addresses_risk", result)
            self.assertIn("ip_addresses_risk", result)
            
        finally:
            # Nettoyer
            if os.path.exists(temp_path):
                os.unlink(temp_path)


if __name__ == "__main__":
    unittest.main()