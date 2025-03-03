# analyzer/error_handler.py
import logging
import os
import json
import traceback
from datetime import datetime
from pathlib import Path

class ErrorHandler:
    """
    Gestionnaire d'erreurs pour l'analyseur RGPD.
    Permet de centraliser, classer et traiter les erreurs.
    """
    
    def __init__(self, log_dir="logs"):
        self.log_dir = log_dir
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        self.error_log_file = os.path.join(log_dir, f"error_log_{datetime.now().strftime('%Y%m%d')}.json")
        self.summary_file = os.path.join(log_dir, "error_summary.json")
        
        # Catégories d'erreurs
        self.error_categories = {
            "file_access": "Problèmes d'accès aux fichiers",
            "file_read": "Problèmes de lecture de fichiers",
            "file_format": "Problèmes de format de fichiers",
            "network": "Problèmes d'accès réseau",
            "memory": "Problèmes de mémoire",
            "permissions": "Problèmes de permissions",
            "other": "Autres erreurs"
        }
        
        # Initialiser ou charger le résumé des erreurs
        self._init_error_summary()
    
    def _init_error_summary(self):
        """Initialise ou charge le résumé des erreurs."""
        if not os.path.exists(self.summary_file):
            summary = {
                "total_errors": 0,
                "categories": {cat: 0 for cat in self.error_categories.keys()},
                "most_common_errors": {},
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            with open(self.summary_file, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=4)
    
    def _update_error_summary(self, category, error_type, error_message):
        """Met à jour le résumé des erreurs."""
        try:
            # Charger le résumé actuel
            with open(self.summary_file, "r", encoding="utf-8") as f:
                summary = json.load(f)
            
            # Mettre à jour les compteurs
            summary["total_errors"] += 1
            summary["categories"][category] = summary["categories"].get(category, 0) + 1
            
            # Mettre à jour les erreurs les plus courantes
            error_key = f"{error_type}: {error_message[:50]}"  # Tronquer les messages trop longs
            summary["most_common_errors"][error_key] = summary["most_common_errors"].get(error_key, 0) + 1
            
            # Limiter aux 10 erreurs les plus courantes
            summary["most_common_errors"] = dict(sorted(
                summary["most_common_errors"].items(), 
                key=lambda item: item[1], 
                reverse=True
            )[:10])
            
            # Mettre à jour la date
            summary["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Sauvegarder le résumé mis à jour
            with open(self.summary_file, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=4)
                
        except Exception as e:
            logging.error(f"Erreur lors de la mise à jour du résumé des erreurs: {str(e)}")
    
    def log_error(self, error, file_path=None, category="other", additional_info=None):
        """
        Enregistre une erreur dans le journal.
        
        Args:
            error (Exception): L'exception à enregistrer
            file_path (str, optional): Le chemin du fichier concerné
            category (str, optional): La catégorie de l'erreur
            additional_info (dict, optional): Informations supplémentaires
        """
        try:
            # Créer l'entrée d'erreur
            error_entry = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "error_type": type(error).__name__,
                "error_message": str(error),
                "traceback": traceback.format_exc(),
                "category": category,
                "file_path": file_path
            }
            
            # Ajouter des informations supplémentaires si présentes
            if additional_info:
                error_entry.update(additional_info)
            
            # Enregistrer dans le fichier journal
            try:
                with open(self.error_log_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(error_entry) + "\n")
            except FileNotFoundError:
                with open(self.error_log_file, "w", encoding="utf-8") as f:
                    f.write(json.dumps(error_entry) + "\n")
            
            # Mettre à jour le résumé
            self._update_error_summary(category, error_entry["error_type"], error_entry["error_message"])
            
            # Enregistrer également dans le journal standard
            logging.error(f"{category.upper()}: {error_entry['error_type']} - {error_entry['error_message']} - Fichier: {file_path}")
            
        except Exception as e:
            # En cas d'erreur pendant le traitement, utiliser le logging standard
            logging.error(f"Erreur lors de l'enregistrement de l'erreur: {str(e)}")
    
    def categorize_error(self, error, file_path=None):
        """
        Catégorise automatiquement une erreur.
        
        Args:
            error (Exception): L'exception à catégoriser
            file_path (str, optional): Le chemin du fichier concerné
            
        Returns:
            str: La catégorie de l'erreur
        """
        error_str = str(error).lower()
        error_type = type(error).__name__
        
        # Vérifier par type d'erreur
        if error_type in ["FileNotFoundError", "NotADirectoryError"]:
            return "file_access"
        
        if error_type in ["PermissionError", "AccessDenied"]:
            return "permissions"
        
        if error_type in ["MemoryError", "OverflowError"]:
            return "memory"
        
        # Vérifier par contenu du message d'erreur
        if any(term in error_str for term in ["permission", "accès refusé", "denied"]):
            return "permissions"
            
        if any(term in error_str for term in ["not found", "does not exist", "no such file", "introuvable"]):
            return "file_access"
            
        if any(term in error_str for term in ["read", "open", "load", "lecture"]):
            return "file_read"
            
        if any(term in error_str for term in ["format", "invalid", "corrupt", "broken", "damaged"]):
            return "file_format"
            
        if any(term in error_str for term in ["network", "connection", "timeout", "réseau", "connexion"]):
            return "network"
        
        # Par défaut
        return "other"
    
    def get_error_summary(self):
        """
        Retourne un résumé des erreurs.
        
        Returns:
            dict: Résumé des erreurs
        """
        try:
            with open(self.summary_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Erreur lors de la lecture du résumé des erreurs: {str(e)}")
            return {
                "total_errors": 0,
                "categories": {cat: 0 for cat in self.error_categories.keys()},
                "most_common_errors": {},
                "error_reading_summary": str(e)
            }
    
    def get_recent_errors(self, limit=50):
        """
        Retourne les erreurs les plus récentes.
        
        Args:
            limit (int, optional): Nombre maximum d'erreurs à retourner
            
        Returns:
            list: Liste des erreurs récentes
        """
        try:
            recent_errors = []
            if os.path.exists(self.error_log_file):
                with open(self.error_log_file, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            error = json.loads(line.strip())
                            recent_errors.append(error)
                        except:
                            continue
            
            # Trier par timestamp (le plus récent d'abord) et limiter
            recent_errors.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            return recent_errors[:limit]
            
        except Exception as e:
            logging.error(f"Erreur lors de la récupération des erreurs récentes: {str(e)}")
            return []

# Instance globale du gestionnaire d'erreurs
error_handler = ErrorHandler()

def handle_error(func):
    """
    Décorateur pour gérer les erreurs dans les fonctions.
    Capture et enregistre les erreurs, puis renvoie une valeur par défaut.
    
    Args:
        func: La fonction à décorer
        
    Returns:
        wrapper: La fonction décorée
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Déterminer le chemin du fichier s'il est présent dans les arguments
            file_path = None
            for arg in args:
                if isinstance(arg, str) and os.path.exists(arg):
                    file_path = arg
                    break
            
            # Catégoriser et enregistrer l'erreur
            category = error_handler.categorize_error(e, file_path)
            error_handler.log_error(e, file_path, category)
            
            # Renvoyer une valeur par défaut adaptée au type de retour attendu
            if func.__name__ == "read_txt_file" or func.__name__ == "read_docx_file" or \
               func.__name__ == "read_excel_file" or func.__name__ == "read_pdf_file":
                return ""
            elif func.__name__ == "analyze_file":
                return None
            else:
                return None
    
    return wrapper
