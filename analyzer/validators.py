# analyzer/validators.py
import re
from typing import Tuple
import logging

# Module de configuration
from config.exclusion_lists import EXCLUDED_PERSONS, ORGANIZATION_UNITS, PROFESSIONAL_CONTEXT, TEMPLATE_INDICATORS

def validate_email(email: str) -> bool:
    """Valide un email avec des règles plus strictes."""
    if not email or len(email) > 254:
        return False
    if not re.match(r'^[a-zA-Z0-9][^@]*@[^@]+\.[^@]+$', email):
        return False
    
    # Exclure les emails de l'organisation
    if any(org.lower() in email.lower() for org in ["@ogfa.", "ogfa@"]):
        return False
        
    return True

def validate_phone(phone: str) -> bool:
    """Valide un numéro de téléphone français avec gestion des formats internationaux."""
    # Supprime les espaces et caractères de formatage
    cleaned = re.sub(r'[\s.\-_()]', '', phone)
    
    # Forme canonique française
    if cleaned.startswith('0') and len(cleaned) == 10:
        return re.match(r'^0[1-9]\d{8}$', cleaned) is not None
    
    # Format international +33
    elif cleaned.startswith('+33'):
        if len(cleaned) == 11:  # +33 suivi de 9 chiffres
            return re.match(r'^\+33[1-9]\d{8}$', cleaned) is not None
        elif len(cleaned) == 12 and cleaned[3] == '0':  # +330 au lieu de +33
            return re.match(r'^\+330[1-9]\d{7}$', cleaned) is not None
    
    # Format 0033
    elif cleaned.startswith('0033'):
        if len(cleaned) == 12:  # 0033 suivi de 9 chiffres
            return re.match(r'^0033[1-9]\d{8}$', cleaned) is not None
        elif len(cleaned) == 13 and cleaned[4] == '0':  # 00330 au lieu de 0033
            return re.match(r'^00330[1-9]\d{7}$', cleaned) is not None
    
    return False

def validate_date(date_str: str) -> bool:
    """Valide une date au format français."""
    try:
        if not date_str:
            return False
        # Séparateur peut être /, - ou .
        day, month, year = re.split(r'[/-.]', date_str)
        day, month, year = int(day), int(month), int(year)
        # Validations de base
        if not (1 <= month <= 12 and 1900 <= year <= 2025):
            return False
        # Validation des jours selon le mois
        days_in_month = {
            1: 31, 2: 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
            3: 31, 4: 30, 5: 31, 6: 30, 7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31
        }
        return 1 <= day <= days_in_month[month]
    except:
        return False

def validate_secu(secu: str) -> bool:
    """Valide un numéro de sécurité sociale français avec la clé de contrôle."""
    if not secu:
        return False
        
    # Vérifier la longueur et le format de base
    base_pattern = r'^[123]\d{13}$'
    if not re.match(base_pattern, secu):
        # Si format incomplet (sans clé), vérifier le format de base
        if re.match(r'^[123]\d{12}$', secu):
            return True  # Accepter sans vérifier la clé si 13 chiffres seulement
        return False
        
    try:
        # Extraire les 13 premiers chiffres et la clé (2 derniers)
        numero = int(secu[:13])
        cle = int(secu[13:])
        
        # Calculer la clé attendue: 97 - (numero % 97)
        cle_attendue = 97 - (numero % 97)
        
        return cle == cle_attendue
    except:
        return False

def validate_siret(siret: str) -> bool:
    """Valide un numéro SIRET avec la clé de Luhn."""
    if not siret or len(siret) != 14:
        return False
        
    try:
        # Vérification avec la clé de Luhn
        total = 0
        for i, digit in enumerate(reversed(siret)):
            n = int(digit)
            if i % 2:
                n *= 2
                if n > 9:
                    n -= 9
            total += n
        return total % 10 == 0
    except:
        return False

def validate_person_name(name: str, text: str) -> Tuple[bool, float]:
    """
    Valide un nom de personne avec des règles strictes et retourne un score de confiance.
    Amélioré pour réduire les faux positifs et mieux comprendre le contexte.
    
    Returns:
        Tuple[bool, float]: (Est valide, Score de confiance)
    """
    # Score initial
    confidence = 0.5
    
    # Vérification basique
    if not name or len(name) < 3:  # Moins restrictif sur la longueur pour les noms courts
        return False, 0.0
    
    # Exclusion des noms de l'organisation
    if any(excluded.lower() in name.lower() for excluded in EXCLUDED_PERSONS):
        return False, 0.0
    
    # Détection des acronymes et acronymes d'entreprises
    if name.isupper() and len(name.split()) == 1 and len(name) <= 5:  # Ex: IBM, OGFA
        return False, 0.0
        
    # Exclure les noms avec caractères spéciaux typiques des entités non-humaines
    if re.search(r'[\@\#\$\%\*\+\=\_\|\<\>\{\}\[\]\^\/\\]', name):
        return False, 0.0
    
    # Doit contenir au moins deux mots (prénom et nom)
    words = name.split()
    if len(words) < 2:
        confidence -= 0.2
    else:
        confidence += 0.1
    
    # Chaque mot doit commencer par une majuscule et ne pas contenir de chiffres
    capital_words = 0
    for word in words:
        if not word:
            continue
        if word[0].isupper() and not any(char.isdigit() for char in word):
            capital_words += 1
            confidence += 0.05
        else:
            confidence -= 0.1
    
    # Au moins 2 mots doivent commencer par une majuscule pour un nom valide
    if capital_words < 2 and len(words) >= 2:
        confidence -= 0.2
    
    # Vérifier la fréquence dans le texte
    occurrences = text.lower().count(name.lower())
    if occurrences > 3:
        confidence -= min(0.5, occurrences * 0.05)
    
    # Tester les préfixes et suffixes typiques des noms
    name_lower = name.lower()
    prefixes = ["m.", "mme", "dr", "prof", "monsieur", "madame", "docteur", "professeur"]
    if any(name_lower.startswith(prefix) for prefix in prefixes):
        confidence += 0.15
        
    # Vérifier le contexte (est-ce dans un contexte professionnel?)
    context_score = analyze_name_context(name, text)
    confidence -= context_score  # Réduit le score si contexte professionnel
    
    # Mots spécifiques aux organisations qui ne devraient pas être dans des noms de personnes
    org_indicators = ["service", "équipe", "groupe", "département", "direction", "pôle"]
    if any(indicator in name_lower for indicator in org_indicators):
        confidence -= 0.3
    
    # Validation finale basée sur le score de confiance
    is_valid = confidence >= 0.3
    
    return is_valid, min(1.0, max(0.0, confidence))

def analyze_name_context(name: str, text: str) -> float:
    """
    Analyse le contexte autour d'un nom pour déterminer s'il s'agit d'un contexte professionnel.
    
    Returns:
        float: Score de contexte professionnel (plus élevé = plus professionnel)
    """
    context_score = 0.0
    
    try:
        # Rechercher le nom dans le texte
        name_pos = text.lower().find(name.lower())
        if name_pos == -1:
            return 0.0
            
        # Extraire une fenêtre de texte autour du nom (100 caractères avant et après)
        start = max(0, name_pos - 100)
        end = min(len(text), name_pos + len(name) + 100)
        context = text[start:end].lower()
        
        # Vérifier les termes professionnels dans le contexte
        for term in PROFESSIONAL_CONTEXT:
            if term in context:
                context_score += 0.15
        
        # Vérifier si le nom est précédé ou suivi par un titre
        titles = ["m.", "mme.", "mr.", "dr.", "monsieur", "madame", "docteur", "prof.", "professeur"]
        name_parts = name.lower().split()
        for title in titles:
            if title in context:
                context_score += 0.1
        
        # Vérifier si le texte contient des indicateurs de modèle/template
        for indicator in TEMPLATE_INDICATORS:
            if indicator in context:
                context_score += 0.2
    except Exception as e:
        logging.error(f"Erreur lors de l'analyse du contexte: {str(e)}")
    
    return min(1.0, context_score)

# ===========================
# Nouvelles fonctions de validation
# ===========================

def validate_postal_address(address: str) -> bool:
    """
    Valide une adresse postale française avec différents formats possibles.
    L'adresse doit comporter un numéro, le nom de la rue et un code postal français à 5 chiffres.
    
    Exemples valides :
    - "12 Rue de la Paix, 75002"
    - "12 Rue de la Paix, 75002 Paris"
    - "12, Rue de la Paix - 75002 PARIS"
    """
    if not address:
        return False
    
    # Vérifie la présence d'un code postal français (5 chiffres)
    postal_code_match = re.search(r'\b\d{5}\b', address.strip())
    if not postal_code_match:
        return False
    
    # Vérifie la présence d'un numéro de rue suivi d'un nom de rue
    street_match = re.search(r'\b\d{1,4}\s*[,]?\s+[\w\s\-\'\À-ÿ]+', address.strip())
    if not street_match:
        return False
    
    # Vérification supplémentaire pour éliminer les faux positifs
    potential_street_name = street_match.group(0).split(',')[0].strip()
    if len(potential_street_name.split()) < 2:  # Au moins un numéro et un mot
        return False
    
    return True

def validate_ip_address(ip: str) -> bool:
    """
    Valide une adresse IPv4 ou IPv6 en utilisant des expressions régulières robustes.
    
    Exemples valides : 
    - IPv4: "192.168.1.1"
    - IPv6: "2001:0db8:85a3:0000:0000:8a2e:0370:7334"
    """
    if not ip:
        return False
    
    # Validation IPv4
    ipv4_pattern = re.compile(r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$')
    if ipv4_pattern.match(ip.strip()):
        return True
    
    # Validation IPv6 (forme complète et abrégée)
    ipv6_pattern = re.compile(r'^(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$|'
                             r'^::(?:[0-9a-fA-F]{1,4}:){0,6}[0-9a-fA-F]{1,4}$|'
                             r'^[0-9a-fA-F]{1,4}::(?:[0-9a-fA-F]{1,4}:){0,5}[0-9a-fA-F]{1,4}$|'
                             r'^[0-9a-fA-F]{1,4}:[0-9a-fA-F]{1,4}::(?:[0-9a-fA-F]{1,4}:){0,4}[0-9a-fA-F]{1,4}$|'
                             r'^(?:[0-9a-fA-F]{1,4}:){0,2}[0-9a-fA-F]{1,4}::(?:[0-9a-fA-F]{1,4}:){0,3}[0-9a-fA-F]{1,4}$|'
                             r'^(?:[0-9a-fA-F]{1,4}:){0,3}[0-9a-fA-F]{1,4}::(?:[0-9a-fA-F]{1,4}:){0,2}[0-9a-fA-F]{1,4}$|'
                             r'^(?:[0-9a-fA-F]{1,4}:){0,4}[0-9a-fA-F]{1,4}::(?:[0-9a-fA-F]{1,4}:)?[0-9a-fA-F]{1,4}$|'
                             r'^(?:[0-9a-fA-F]{1,4}:){0,5}[0-9a-fA-F]{1,4}::[0-9a-fA-F]{1,4}$|'
                             r'^(?:[0-9a-fA-F]{1,4}:){0,6}[0-9a-fA-F]{1,4}::$')
    return bool(ipv6_pattern.match(ip.strip()))