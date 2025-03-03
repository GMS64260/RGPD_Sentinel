#!/usr/bin/env python
"""
Script d'exemple qui démontre la détection de données personnelles
dans un fichier texte en utilisant les nouvelles fonctionnalités.
"""
import sys
from pathlib import Path
import pandas as pd
import json

# Ajouter le répertoire parent au chemin pour permettre l'importation
parent_dir = str(Path(__file__).resolve().parent)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from analyzer.core import detect_personal_data

def main():
    """Fonction principale du script de démonstration"""
    # Vérifier si un fichier a été fourni
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        filename = "example_data.txt"  # Fichier de démo par défaut
    
    print(f"Analyse du fichier: {filename}")
    try:
        # Lire le fichier
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Détecter les données personnelles
        results = detect_personal_data(content, filename)
        
        # Afficher les résultats
        print("\n--- Données personnelles détectées ---\n")
        
        # Créer un dataframe pour un affichage plus lisible
        rows = []
        for data_type, items in results.items():
            for item in items:
                rows.append({
                    "Type": data_type,
                    "Valeur": item["value"],
                    "Confiance": f"{item['confidence']:.2f}"
                })
        
        if rows:
            df = pd.DataFrame(rows)
            print(df.to_string(index=False))
            print(f"\nTotal: {len(rows)} détections")
            
            # Enregistrer au format JSON
            output_file = f"{Path(filename).stem}_detections.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"\nRésultats détaillés enregistrés dans: {output_file}")
        else:
            print("Aucune donnée personnelle détectée.")
    
    except FileNotFoundError:
        print(f"Erreur: Le fichier '{filename}' n'a pas été trouvé.")
        return 1
    except Exception as e:
        print(f"Erreur lors de l'analyse: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
