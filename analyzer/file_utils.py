# analyzer/file_utils.py
import os
import logging
from pathlib import Path
import re

def is_temp_file(file_path: str) -> bool:
    """
    Détecte si un fichier est un fichier temporaire ou de verrouillage 
    qui ne devrait pas être analysé.
    """
    # Fichiers de verrouillage de Microsoft Office (Word, Excel, etc.)
    if os.path.basename(file_path).startswith('~$'):
        return True
    
    # Fichiers temporaires courants
    temp_patterns = [
        r'\.tmp$',          # Fichiers temporaires Windows
        r'\.bak$',          # Fichiers de sauvegarde
        r'\.swp$',          # Fichiers temporaires de Vim
        r'\.temp$',         # Autres fichiers temporaires
        r'~$',              # Fichiers de sauvegarde avec ~ à la fin
        r'^\.#',            # Certains fichiers temporaires sur Unix
        r'\.part$',         # Fichiers de téléchargement partiels
        r'_temp',           # Fichiers avec "_temp" dans le nom
    ]
    
    for pattern in temp_patterns:
        if re.search(pattern, file_path, re.IGNORECASE):
            return True
    
    return False

def should_skip_file(file_path: str, excluded_extensions: list = None) -> bool:
    """
    Détermine si un fichier doit être ignoré basé sur son extension ou s'il est temporaire.
    """
    if is_temp_file(file_path):
        logging.info(f"Ignoring temporary file: {file_path}")
        return True
        
    if excluded_extensions:
        file_ext = Path(file_path).suffix.lower()
        if file_ext in excluded_extensions:
            logging.info(f"Ignoring excluded extension {file_ext}: {file_path}")
            return True
    
    # Vérifier les noms de fichiers qui commencent par un point (fichiers cachés)
    if os.path.basename(file_path).startswith('.'):
        logging.info(f"Ignoring hidden file: {file_path}")
        return True
    
    # Vérifier si le fichier est trop volumineux (> 50 Mo)
    try:
        if os.path.getsize(file_path) > 50 * 1024 * 1024:  # 50 Mo
            logging.warning(f"Skipping large file (>50MB): {file_path}")
            return True
    except OSError as e:
        logging.warning(f"Could not check size of {file_path}: {str(e)}")
        return True
        
    return False

def ensure_readable(file_path: str) -> bool:
    """
    Vérifie si un fichier est lisible et accessible.
    """
    try:
        # Vérifier que le fichier existe
        if not os.path.exists(file_path):
            logging.warning(f"File does not exist: {file_path}")
            return False
            
        # Vérifier que c'est un fichier (et non un dossier)
        if not os.path.isfile(file_path):
            logging.warning(f"Not a file: {file_path}")
            return False
            
        # Vérifier que le fichier est accessible en lecture
        if not os.access(file_path, os.R_OK):
            logging.warning(f"File not readable: {file_path}")
            return False
            
        # Vérifier que le fichier n'est pas vide
        if os.path.getsize(file_path) == 0:
            logging.warning(f"File is empty: {file_path}")
            return False
            
        return True
    except Exception as e:
        logging.warning(f"Error checking file {file_path}: {str(e)}")
        return False

def fix_network_path(file_path: str) -> str:
    """
    Corrige les chemins réseau pour les rendre plus robustes.
    """
    # Vérifier si le chemin est un chemin UNC (réseau)
    if file_path.startswith('\\\\'):
        # Essayer de convertir les chemins UNC en plus robustes
        try:
            # Utiliser des slashes au lieu de backslashes
            robust_path = file_path.replace('\\', '/')
            return robust_path
        except Exception as e:
            logging.warning(f"Failed to fix network path {file_path}: {str(e)}")
    
    return file_path
