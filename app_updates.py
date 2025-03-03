# Modifications à apporter à app.py

# Importer le module de validation manuelle
from manual_validation import manual_validation_tab, apply_feedback_to_thresholds

# Remplacer la fonction manual_validation_tab existante par celle-ci :
def manual_validation_tab():
    from manual_validation import manual_validation_tab as mvt
    mvt()

# Modifier l'option radio dans la fonction main() :
analysis_options = st.radio("Mode d'analyse", 
                          options=["Tableau de bord", "Analyses sauvegardées", "Analyse de dossier", 
                                  "Analyse de fichiers", "Paramètres", "Validation manuelle", "Optimisation des seuils"],
                          index=0)

# Ajouter cette condition dans la partie conditionnelle de la fonction main() :
elif analysis_options == "Optimisation des seuils":
    apply_feedback_to_thresholds()
