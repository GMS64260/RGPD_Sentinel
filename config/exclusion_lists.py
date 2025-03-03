# config/exclusion_lists.py - Listes d'exclusion

# Liste des personnes de l'organisation à exclure (dirigeants, employés fréquemment mentionnés)
EXCLUDED_PERSONS = [
    "John Doe",
    "Doe",
    "John",
    "Jane Smith",
    "Smith",
    "Jane",
    "Robert Johnson",
    "Johnson",
    "Robert",
    "Emily Davis",
    "Davis",
    "Emily",
    "Michael Wilson",
    "Wilson",
    "Michael",
    "Sarah Brown",
    "Brown",
    "Sarah",
    "David Miller",
    "Miller",
    "David",
]

# Termes professionnels qui indiquent un contexte non-personnel
PROFESSIONAL_CONTEXT = [
    "directeur", "dg", "responsable", "chef", "manager", 
    "signé", "signature", "contact", "coordonnées",
    "référent", "chargé de", "administrateur", "employé",
    "service", "département", "collègue", "équipe",
    "salarié", "poste", "fonction", "technicien", "informatique"
]

# Termes qui indiquent que le document est un modèle/template
TEMPLATE_INDICATORS = [
    "exemple", "modèle", "template", "libellé", "démonstration",
    "test", "formation", "documentation", "manuel",
    "placeholder", "sample", "guide", "instruction"
]

# Structures de l'organisation à exclure
ORGANIZATION_UNITS = [
    "ACME",
    "Service Clients",
    "Service Technique",
    "Ressources Humaines",
    "Service Juridique",
    "Service Informatique",
    "Service Comptabilité",
    "Direction Générale",
]