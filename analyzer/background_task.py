# analyzer/background_task.py
import os
import time
import json
import threading
from pathlib import Path
import pandas as pd

class BackgroundTask:
    """
    Gestion des tâches d'analyse en arrière-plan qui continuent même si l'utilisateur change d'onglet
    """
    
    TASKS_DIR = Path("saved_analyses/tasks")
    
    @classmethod
    def ensure_dir_exists(cls):
        """S'assure que le répertoire des tâches existe"""
        if not cls.TASKS_DIR.exists():
            os.makedirs(cls.TASKS_DIR)
    
    @classmethod
    def create_task(cls, task_type, params):
        """
        Crée une nouvelle tâche en arrière-plan
        
        Args:
            task_type (str): Type de tâche (directory_analysis, files_analysis)
            params (dict): Paramètres de la tâche
            
        Returns:
            str: ID de la tâche
        """
        # S'assurer que le répertoire existe
        cls.ensure_dir_exists()
        
        # Générer un ID de tâche basé sur l'horodatage
        task_id = f"{int(time.time())}"
        task_path = cls.TASKS_DIR / f"{task_id}.json"
        
        # Préparer les données de la tâche
        task_data = {
            "id": task_id,
            "type": task_type,
            "params": params,
            "status": "created",
            "progress": 0,
            "results": None,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "message": "Tâche créée, en attente de traitement"
        }
        
        # Enregistrer la tâche dans un fichier JSON
        try:
            with open(task_path, 'w', encoding='utf-8') as f:
                json.dump(task_data, f, indent=2)
                
            # Log pour déboguer
            print(f"Tâche créée avec l'ID {task_id} dans {task_path}")
                
            # Lancer le thread qui exécutera la tâche
            thread = threading.Thread(target=cls._run_task, args=(task_id,))
            thread.daemon = True  # Le thread s'arrêtera quand le programme principal s'arrête
            thread.start()
            
            return task_id
        except Exception as e:
            # En cas d'erreur, créer un fichier d'erreur pour déboguer
            error_path = cls.TASKS_DIR / f"error_{task_id}.txt"
            try:
                with open(error_path, 'w', encoding='utf-8') as f:
                    f.write(f"Erreur lors de la création de la tâche: {str(e)}\n")
                    f.write(f"Chemin de la tâche: {task_path}\n")
                    f.write(f"Paramètres: {str(params)}\n")
            except:
                pass
                
            # Retourner quand même l'ID pour ne pas bloquer l'interface
            return task_id
    
    @classmethod
    def _run_task(cls, task_id):
        """
        Exécute une tâche en arrière-plan
        
        Args:
            task_id (str): ID de la tâche à exécuter
        """
        task_path = cls.TASKS_DIR / f"{task_id}.json"
        
        if not task_path.exists():
            return
            
        # Charger les détails de la tâche
        with open(task_path, 'r', encoding='utf-8') as f:
            task_data = json.load(f)
            
        # Mettre à jour le statut
        task_data["status"] = "running"
        task_data["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        task_data["message"] = "Analyse en cours..."
        cls._save_task_data(task_id, task_data)
        
        try:
            # Exécuter la tâche selon son type
            if task_data["type"] == "directory_analysis":
                result = cls._analyze_directory(task_id, task_data)
            elif task_data["type"] == "files_analysis":
                result = cls._analyze_files(task_id, task_data)
            else:
                raise ValueError(f"Type de tâche non reconnu: {task_data['type']}")
                
            # Mettre à jour la tâche avec les résultats
            task_data["status"] = "completed"
            task_data["progress"] = 100
            task_data["results"] = result
            task_data["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            task_data["message"] = "Analyse terminée avec succès"
            
        except Exception as e:
            # En cas d'erreur
            task_data["status"] = "error"
            task_data["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            task_data["message"] = f"Erreur: {str(e)}"
            
        # Sauvegarder les mises à jour
        cls._save_task_data(task_id, task_data)
    
    @classmethod
    def _save_task_data(cls, task_id, task_data):
        """Sauvegarde les données d'une tâche"""
        task_path = cls.TASKS_DIR / f"{task_id}.json"
        with open(task_path, 'w', encoding='utf-8') as f:
            json.dump(task_data, f, indent=2)
    
    @classmethod
    def _analyze_directory(cls, task_id, task_data):
        """Analyse un répertoire en arrière-plan"""
        from analyzer.core import analyze_file, is_supported_file, calculate_risk_scores
        from analyzer.storage import AnalysisStorage
        
        params = task_data["params"]
        directory_path = params.get("directory_path")
        max_files = params.get("max_files")
        save_analysis = params.get("save_analysis", True)
        excluded_extensions = params.get("excluded_extensions", [])
        
        # Trouver tous les fichiers à analyser
        all_files = []
        for root, _, files in os.walk(directory_path):
            for file in files:
                file_path = os.path.join(root, file)
                if is_supported_file(file_path):
                    # Vérifier si l'extension est exclue
                    if Path(file_path).suffix.lower() not in excluded_extensions:
                        all_files.append(file_path)
        
        # Limiter le nombre de fichiers si nécessaire
        if max_files and max_files > 0 and len(all_files) > max_files:
            all_files = all_files[:max_files]
            
        total_files = len(all_files)
        results = []
        skipped_files = []
        error_files = []
        
        for i, file_path in enumerate(all_files):
            try:
                result = analyze_file(file_path)
                if result:
                    results.append(result)
                else:
                    # Si le résultat est None, c'est probablement un fichier temporaire ou inaccessible
                    if Path(file_path).name.startswith("~$"):
                        skipped_files.append({"path": file_path, "reason": "Fichier temporaire"})
                    else:
                        error_files.append({"path": file_path, "reason": "Analyse impossible"})
            except Exception as e:
                error_files.append({"path": file_path, "reason": str(e)[:50] + "..."})
            
            # Mettre à jour la progression
            progress = int((i + 1) / total_files * 100)
            task_data["progress"] = progress
            task_data["message"] = f"Analyse en cours... {i+1}/{total_files} fichiers traités"
            cls._save_task_data(task_id, task_data)
        
        if not results:
            return {"error": "Aucun résultat d'analyse obtenu."}
        
        results_df = pd.DataFrame(results)
        
        # Sauvegarder l'analyse si demandé
        if save_analysis:
            storage = AnalysisStorage()
            analysis_name = f"Analyse de {os.path.basename(directory_path)}"
            analysis_id = storage.save_analysis(
                results_df, 
                name=analysis_name,
                source_path=directory_path,
                description=f"Analyse automatique de {len(results)} fichiers ({total_files - len(results)} ignorés/en erreur)"
            )
            
            # Calculer les scores de risque
            risk_analysis = calculate_risk_scores(results_df.to_dict('records'))
            
            return {
                "analysis_id": analysis_id,
                "results": results_df.to_dict('records'),
                "skipped_files": skipped_files,
                "error_files": error_files,
                "risk_analysis": risk_analysis
            }
        else:
            risk_analysis = calculate_risk_scores(results_df.to_dict('records'))
            return {
                "results": results_df.to_dict('records'),
                "skipped_files": skipped_files,
                "error_files": error_files,
                "risk_analysis": risk_analysis
            }
    
    @classmethod
    def _analyze_files(cls, task_id, task_data):
        """Analyse des fichiers téléchargés en arrière-plan"""
        from analyzer.core import analyze_file, calculate_risk_scores
        from analyzer.storage import AnalysisStorage
        import tempfile
        
        params = task_data["params"]
        file_paths = params.get("file_paths", [])
        file_names = params.get("file_names", [])
        save_analysis = params.get("save_analysis", True)
        file_contents = params.get("file_contents", [])
        
        if not file_paths or len(file_paths) != len(file_names) or len(file_paths) != len(file_contents):
            return {"error": "Paramètres de fichiers invalides"}
        
        total_files = len(file_paths)
        results = []
        
        for i, (file_path, file_name, file_content) in enumerate(zip(file_paths, file_names, file_contents)):
            try:
                # Écrire le contenu dans un fichier temporaire
                with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file_name).suffix) as tmp_file:
                    tmp_file.write(file_content.encode('utf-8'))
                    temp_path = tmp_file.name
                
                # Analyser le fichier
                result = analyze_file(temp_path)
                if result:
                    result["file_path"] = file_name  # Utiliser le nom original plutôt que le chemin temporaire
                    results.append(result)
                
                # Supprimer le fichier temporaire
                os.unlink(temp_path)
            except Exception as e:
                continue
            
            # Mettre à jour la progression
            progress = int((i + 1) / total_files * 100)
            task_data["progress"] = progress
            task_data["message"] = f"Analyse en cours... {i+1}/{total_files} fichiers traités"
            cls._save_task_data(task_id, task_data)
        
        if not results:
            return {"error": "Aucun résultat d'analyse obtenu pour les fichiers chargés."}
        
        results_df = pd.DataFrame(results)
        
        # Sauvegarder l'analyse si demandé
        if save_analysis:
            storage = AnalysisStorage()
            file_names_display = ", ".join([name for name in file_names[:3]])
            if len(file_names) > 3:
                file_names_display += f" et {len(file_names) - 3} autres"
            analysis_name = f"Analyse de fichiers: {file_names_display}"
            analysis_id = storage.save_analysis(
                results_df, 
                name=analysis_name,
                description=f"Analyse de {len(file_names)} fichiers téléchargés"
            )
            
            # Calculer les scores de risque
            risk_analysis = calculate_risk_scores(results_df.to_dict('records'))
            
            return {
                "analysis_id": analysis_id,
                "results": results_df.to_dict('records'),
                "risk_analysis": risk_analysis
            }
        else:
            risk_analysis = calculate_risk_scores(results_df.to_dict('records'))
            return {
                "results": results_df.to_dict('records'),
                "risk_analysis": risk_analysis
            }
    
    @classmethod
    def get_task_status(cls, task_id):
        """
        Obtient le statut d'une tâche
        
        Args:
            task_id (str): ID de la tâche
            
        Returns:
            dict: Données de la tâche ou None si la tâche n'existe pas
        """
        cls.ensure_dir_exists()
        
        task_path = cls.TASKS_DIR / f"{task_id}.json"
        
        if not task_path.exists():
            return None
            
        try:
            with open(task_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return None
    
    @classmethod
    def get_all_tasks(cls):
        """
        Obtient la liste de toutes les tâches
        
        Returns:
            list: Liste des données de toutes les tâches
        """
        cls.ensure_dir_exists()
        
        tasks = []
        # Vérifier que le répertoire existe
        if not cls.TASKS_DIR.exists():
            print(f"Répertoire des tâches {cls.TASKS_DIR} n'existe pas!")
            return []
        
        # Lister les fichiers de tâches disponibles
        task_files = list(cls.TASKS_DIR.glob("*.json"))
        print(f"Fichiers de tâches trouvés: {len(task_files)}")
        
        for file in task_files:
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    task_data = json.load(f)
                    tasks.append(task_data)
                    print(f"Tâche chargée: {file.name} - statut: {task_data.get('status', 'inconnu')}")
            except Exception as e:
                print(f"Erreur lors du chargement de la tâche {file}: {str(e)}")
                continue
                
        # Trier par date de création, plus récent en premier
        tasks.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        print(f"Total des tâches chargées: {len(tasks)}")
        return tasks
    
    @classmethod
    def clean_old_tasks(cls, days=7):
        """
        Nettoie les tâches anciennes
        
        Args:
            days (int): Nombre de jours après lesquels une tâche est considérée comme ancienne
        """
        cls.ensure_dir_exists()
        
        current_time = time.time()
        max_age = days * 24 * 60 * 60  # Convertir en secondes
        
        for file in cls.TASKS_DIR.glob("*.json"):
            file_time = os.path.getctime(file)
            if current_time - file_time > max_age:
                try:
                    os.remove(file)
                except:
                    continue
