# manual_validation.py
import streamlit as st
import pandas as pd
import os
import json
import re
from datetime import datetime
from pathlib import Path
from analyzer.core import read_txt_file, read_docx_file, read_pdf_file, read_excel_file, get_file_type

def extract_context(file_path, value, window_size=100):
    """
    Extrait le contexte autour d'une valeur détectée dans un fichier.
    
    Args:
        file_path: Chemin du fichier contenant la valeur
        value: Valeur à rechercher dans le fichier
        window_size: Nombre de caractères à afficher avant et après la valeur
        
    Returns:
        Un tuple (contexte, position) ou (None, -1) si la valeur n'a pas été trouvée
    """
    try:
        # Déterminer le type de fichier et lire son contenu
        file_type = get_file_type(file_path)
        content = ""
        
        if file_type == 'text':
            content = read_txt_file(file_path)
        elif file_type == 'word':
            content = read_docx_file(file_path)
        elif file_type == 'pdf':
            content = read_pdf_file(file_path)
        elif file_type == 'excel':
            content = read_excel_file(file_path)
        else:
            return None, -1, -1
        
        if not content:
            return None, -1, -1
            
        # Rechercher la valeur dans le contenu (de façon insensible à la casse)
        pattern = re.escape(value)
        match = re.search(pattern, content, re.IGNORECASE)
        
        if match:
            start_pos = match.start()
            end_pos = match.end()
            
            # Calculer les positions du contexte
            context_start = max(0, start_pos - window_size)
            context_end = min(len(content), end_pos + window_size)
            
            # Extraire le contexte
            context = content[context_start:context_end]
            
            # Position relative de la valeur dans le contexte
            rel_start = start_pos - context_start
            rel_end = end_pos - context_start
            
            return context, rel_start, rel_end
        
        return None, -1, -1
    except Exception as e:
        st.error(f"Erreur lors de l'extraction du contexte : {str(e)}")
        return None, -1, -1

def highlight_context(context, start_pos, end_pos):
    """
    Met en évidence la valeur dans son contexte.
    
    Args:
        context: Texte du contexte
        start_pos: Position de début de la valeur dans le contexte
        end_pos: Position de fin de la valeur dans le contexte
        
    Returns:
        HTML avec la valeur mise en évidence
    """
    if start_pos < 0 or end_pos < 0 or start_pos >= len(context) or end_pos > len(context):
        return f"<div class='context'>{context}</div>"
    
    # Séparer le contexte en trois parties
    before = context[:start_pos]
    value = context[start_pos:end_pos]
    after = context[end_pos:]
    
    # Échapper les caractères HTML spéciaux
    before = before.replace("<", "&lt;").replace(">", "&gt;")
    value = value.replace("<", "&lt;").replace(">", "&gt;")
    after = after.replace("<", "&lt;").replace(">", "&gt;")
    
    # Générer l'HTML
    html = f"<div class='context'>{before}<span class='highlight-value'>{value}</span>{after}</div>"
    return html

# Styles CSS pour l'affichage du contexte
st.markdown("""<style>
.highlight-value {
    background-color: #FFEB3B; 
    color: black;
    font-weight: bold;
    padding: 2px 0;
}
.context {
    background-color: #f0f2f6;
    border-radius: 5px;
    padding: 10px;
    font-family: monospace;
    white-space: pre-wrap;
    word-wrap: break-word;
    margin: 10px 0;
    border: 1px solid #ddd;
    font-size: 0.9em;
    max-height: 150px;
    overflow-y: auto;
}
.subheader-mini {
    font-size: 0.9rem;
    font-weight: bold;
    color: #555;
    margin-top: 10px;
    margin-bottom: 5px;
}
</style>""", unsafe_allow_html=True)

def load_feedback_data():
    """Charge les données de feedback précédentes."""
    feedback_path = Path("saved_analyses/feedback.json")
    if not feedback_path.exists():
        if not feedback_path.parent.exists():
            os.makedirs(feedback_path.parent)
        with open(feedback_path, "w", encoding="utf-8") as f:
            json.dump([], f)
        return []
    
    try:
        with open(feedback_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Erreur lors du chargement des données de feedback: {str(e)}")
        return []

def save_feedback_data(feedback):
    """Sauvegarde les données de feedback."""
    feedback_path = Path("saved_analyses/feedback.json")
    try:
        with open(feedback_path, "w", encoding="utf-8") as f:
            json.dump(feedback, f, indent=4)
        return True
    except Exception as e:
        st.error(f"Erreur lors de la sauvegarde des données de feedback: {str(e)}")
        return False

def manual_validation_tab():
    """Interface de validation manuelle des détections."""
    st.markdown('<div class="sub-header">Validation manuelle des détections</div>', unsafe_allow_html=True)
    
    # Initialisation des structures de données
    from analyzer.storage import AnalysisStorage
    storage = AnalysisStorage()
    analyses = storage.get_all_analyses_metadata()
    
    if not analyses:
        st.info("Aucune analyse sauvegardée pour valider.")
        return
    
    # Sélection de l'analyse
    analysis_options = {a["id"]: f"{a['name']} ({a['date']})" for a in analyses}
    selected_analysis = st.selectbox(
        "Sélectionnez une analyse à valider", 
        options=list(analysis_options.keys()),
        format_func=lambda x: analysis_options[x],
        key="validation_analysis_select"
    )
    
    if not selected_analysis:
        st.warning("Veuillez sélectionner une analyse à valider.")
        return
    
    # Chargement de l'analyse sélectionnée
    results_df, metadata = storage.get_analysis(selected_analysis)
    if results_df is None:
        st.error("Impossible de charger l'analyse sélectionnée.")
        return
    
    # Afficher les informations sur l'analyse
    st.markdown("#### Informations sur l'analyse")
    st.write(f"**Nom de l'analyse:** {metadata['name']}")
    st.write(f"**Date de l'analyse:** {metadata['date']}")
    st.write(f"**Nombre de fichiers analysés:** {metadata['file_count']}")
    
    # Chargement des feedbacks précédents
    all_feedback = load_feedback_data()
    
    # Filtrer les feedbacks pour cette analyse
    existing_feedback = [item for item in all_feedback if item.get("analysis_id") == selected_analysis]
    
    # Créer un dictionnaire pour un accès rapide aux feedbacks existants
    feedback_dict = {}
    for item in existing_feedback:
        key = f"{item['file_path']}_{item['data_type']}_{item['value']}"
        feedback_dict[key] = item
    
    st.markdown(f"#### Valider les détections")
    st.markdown("""Pour chaque détection, évaluez si l'information est correctement identifiée comme donnée personnelle, 
en vous basant sur le contexte. La validation aide à améliorer la qualité des détections futures.
""")
    
    # Interface de filtrage
    col1, col2 = st.columns(2)
    with col1:
        selected_types = st.multiselect(
            "Types de données à valider",
            ["emails", "phones", "names", "secu", "siret", "postal_addresses", "ip_addresses"],
            default=["emails", "phones", "names", "secu"]
        )
    with col2:
        min_confidence = st.slider(
            "Niveau de confiance minimum",
            0.0, 1.0, 0.5, 0.1, 
            help="Filtrer les détections selon leur niveau de confiance"
        )
    
    # Option pour n'afficher que les détections non validées
    show_only_unvalidated = st.checkbox("Afficher uniquement les détections non validées", value=True)
    
    # Créer un formulaire pour soumettre toutes les validations en une fois
    with st.form(key="validation_form"):
        feedback_updated = False
        new_feedback = []
        
        # Pour chaque type de données sélectionné
        for data_type in selected_types:
            column_name = f"{data_type}_found"
            confidence_col = f"{data_type}_confidence"
            
            if column_name not in results_df.columns:
                continue
            
            st.markdown(f"##### {data_type.capitalize()}")
            
            # Filtrer les fichiers avec des détections
            files_with_data = results_df[results_df[column_name] != ""]
            
            if files_with_data.empty:
                st.info(f"Aucune détection de {data_type} dans cette analyse.")
                continue
            
            # Créer des checkboxes pour chaque détection
            for idx, row in files_with_data.iterrows():
                file_path = row["file_path"]
                file_name = os.path.basename(file_path)
                
                # Extraire les valeurs et les scores de confiance
                values = row[column_name].split(", ")
                confidences = row[confidence_col].split(", ") if confidence_col in row and row[confidence_col] else ["0.50"] * len(values)
                
                for i, (value, conf) in enumerate(zip(values, confidences)):
                    conf_float = float(conf)
                    if conf_float < min_confidence:
                        continue
                    
                    # Vérifier si cette détection a déjà été validée
                    key = f"{file_path}_{data_type}_{value}"
                    existing = feedback_dict.get(key)
                    
                    # Si on affiche uniquement les détections non validées et que celle-ci est déjà validée
                    if show_only_unvalidated and existing:
                        continue
                    
                    # Extraire le contexte
                    context, start_pos, end_pos = extract_context(file_path, value)
                    
                    # Afficher les informations
                    st.markdown(f"**Fichier:** {file_name}")
                    st.markdown(f"**Valeur:** {value}")
                    st.markdown(f"**Confiance:** {conf_float:.2f}")
                    
                    # Afficher le contexte avec la valeur mise en évidence
                    if context:
                        st.markdown("<div class='subheader-mini'>Contexte :</div>", unsafe_allow_html=True)
                        html_context = highlight_context(context, start_pos, end_pos)
                        st.markdown(html_context, unsafe_allow_html=True)
                    else:
                        st.info("Impossible d'extraire le contexte pour cette valeur.")
                    
                    # Checkbox pour validation
                    col_a, col_b = st.columns([1, 1])
                    
                    with col_b:
                        # Définir la valeur par défaut selon l'existence d'un feedback
                        default_value = existing.get("is_valid", True) if existing else True
                        is_valid = st.checkbox(
                            "Détection valide", 
                            value=default_value,
                            key=f"valid_{data_type}_{idx}_{i}"
                        )
                        correction = st.text_input(
                            "Correction (si nécessaire)", 
                            value="" if existing is None else existing.get("correction", ""),
                            key=f"corr_{data_type}_{idx}_{i}"
                        )
                    
                    # Enregistrer le feedback
                    feedback_item = {
                        "analysis_id": selected_analysis,
                        "file_path": file_path,
                        "data_type": data_type,
                        "value": value,
                        "confidence": conf_float,
                        "is_valid": is_valid,
                        "correction": correction,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    new_feedback.append(feedback_item)
                    
                    # Si ce feedback est différent de l'existant, marquer comme mis à jour
                    if existing and (existing.get("is_valid") != is_valid or existing.get("correction") != correction):
                        feedback_updated = True
                    
                    st.markdown("---")
        
        # Bouton de soumission
        submit_button = st.form_submit_button(label="Enregistrer les validations")
        
        if submit_button:
            # Mettre à jour les feedbacks existants et ajouter les nouveaux
            updated_feedback = []
            
            # Ajouter les feedbacks qui n'ont pas été modifiés
            for item in all_feedback:
                key = f"{item['file_path']}_{item['data_type']}_{item['value']}"
                matching_new = next((fb for fb in new_feedback if f"{fb['file_path']}_{fb['data_type']}_{fb['value']}" == key), None)
                if not matching_new:
                    updated_feedback.append(item)
            
            # Ajouter tous les nouveaux feedbacks
            updated_feedback.extend(new_feedback)
            
            # Sauvegarder
            if save_feedback_data(updated_feedback):
                st.success("Validations enregistrées avec succès!")
                # Mettre à jour la liste des feedbacks
                all_feedback = updated_feedback
            else:
                st.error("Erreur lors de l'enregistrement des validations.")
    
    # Afficher les statistiques de validation
    if existing_feedback:
        st.markdown("#### Statistiques de validation")
        
        total_validations = len(existing_feedback)
        valid_count = sum(1 for item in existing_feedback if item.get("is_valid", True))
        invalid_count = total_validations - valid_count
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total des validations", total_validations)
        with col2:
            st.metric("Détections correctes", valid_count)
        with col3:
            st.metric("Faux positifs", invalid_count)
        
        # Répartition par type de données
        type_stats = {}
        for item in existing_feedback:
            data_type = item.get("data_type", "unknown")
            if data_type not in type_stats:
                type_stats[data_type] = {"total": 0, "valid": 0}
            
            type_stats[data_type]["total"] += 1
            if item.get("is_valid", True):
                type_stats[data_type]["valid"] += 1
        
        st.markdown("##### Répartition par type de données")
        stats_data = []
        for data_type, stats in type_stats.items():
            stats_data.append({
                "Type": data_type,
                "Total": stats["total"],
                "Valides": stats["valid"],
                "Faux positifs": stats["total"] - stats["valid"],
                "% Précision": round(stats["valid"] / stats["total"] * 100, 2) if stats["total"] > 0 else 0
            })
        
        stats_df = pd.DataFrame(stats_data)
        st.dataframe(stats_df, use_container_width=True)

        # Option pour exporter les données de validation
        if st.button("Exporter les données de validation (CSV)"):
            csv = pd.DataFrame(existing_feedback).to_csv(index=False)
            st.download_button(
                "Télécharger le CSV",
                csv,
                "validation_feedback.csv",
                "text/csv",
                key="download_feedback"
            )

def _display_detections(row, idx, column_name, confidence_column, selected_type, feedback, validated_items, rejected_items):
    """Fonction utilitaire pour afficher les détections et contrôles de validation"""
    detections = row[column_name]
    confidences = row.get(confidence_column, "").split(", ") if confidence_column in row and row[confidence_column] else []
    
    detection_list = detections.split(", ")
    for j, det in enumerate(detection_list):
        if not det.strip():
            continue
            
        confidence = float(confidences[j]) if j < len(confidences) else None
        confidence_display = f" (Confiance: {confidence:.2f})" if confidence is not None else ""
        
        key = f"{idx}_{selected_type}_{det}"
        current_status = "✅" if feedback.get(key, None) is True else "❌" if feedback.get(key, None) is False else "⬜"
        
        col1, col2, col3, col4 = st.columns([5, 1, 1, 1])
        with col1:
            st.text(f"{det}{confidence_display}")
        with col2:
            st.text(f"Statut: {current_status}")
        with col3:
            valid = st.button("✅ Valide", key=f"valid_{key}")
            if valid:
                feedback[key] = True
                validated_items.append(det)
        with col4:
            invalid = st.button("❌ Faux positif", key=f"invalid_{key}")
            if invalid:
                feedback[key] = False
                rejected_items.append(det)

def apply_feedback_to_thresholds():
    """
    Analyse les feedbacks pour suggérer des ajustements aux seuils de confiance
    et aux patterns de détection.
    """
    st.markdown('<div class="sub-header">Optimisation des seuils de détection</div>', unsafe_allow_html=True)
    
    # Charger les feedbacks
    all_feedback = load_feedback_data()
    
    if not all_feedback:
        st.info("Aucune donnée de validation disponible. Veuillez d'abord valider des détections.")
        return
    
    st.markdown("#### Analyse des feedbacks de validation")
    st.markdown("""
    Cette section analyse les validations manuelles pour suggérer des ajustements 
    aux seuils de confiance et améliorer la qualité des détections.
    """)
    
    # Analyser les seuils par type de données
    data_types = ["emails", "phones", "names", "secu", "siret", "postal_addresses", "ip_addresses"]
    current_thresholds = {
        "emails": 0.7,
        "phones": 0.7,
        "dates": 0.5,
        "names": 0.4,
        "secu": 0.8,
        "siret": 0.8,
        "postal_addresses": 0.7,
        "ip_addresses": 0.7
    }
    
    threshold_analysis = []
    patterns_to_exclude = []
    
    for data_type in data_types:
        feedbacks = [item for item in all_feedback if item.get("data_type") == data_type]
        
        if not feedbacks:
            continue
        
        # Calculer le taux de précision actuel
        total = len(feedbacks)
        valid = sum(1 for item in feedbacks if item.get("is_valid", True))
        accuracy = (valid / total) * 100 if total > 0 else 0
        
        # Trouver le seuil optimal
        confidences = [(item.get("confidence", 0), item.get("is_valid", True)) for item in feedbacks]
        confidences.sort(key=lambda x: x[0])
        
        best_threshold = current_thresholds.get(data_type, 0.5)
        best_f1 = 0
        
        if confidences:
            # Tester différents seuils et calculer le score F1
            for i, (conf, _) in enumerate(confidences):
                threshold = conf
                
                # Calculer les vrais positifs, faux positifs, etc.
                true_positives = sum(1 for c, v in confidences if c >= threshold and v)
                false_positives = sum(1 for c, v in confidences if c >= threshold and not v)
                false_negatives = sum(1 for c, v in confidences if c < threshold and v)
                
                # Calculer précision et rappel
                precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
                recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
                
                # Calculer le score F1
                f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
                
                if f1 > best_f1:
                    best_f1 = f1
                    best_threshold = threshold
        
        # Arrondir le seuil optimal à 1 décimale
        best_threshold = round(best_threshold * 10) / 10
        
        # Ajouter à l'analyse
        threshold_analysis.append({
            "data_type": data_type,
            "current_threshold": current_thresholds.get(data_type, 0.5),
            "suggested_threshold": best_threshold,
            "accuracy": accuracy,
            "sample_size": total
        })
        
        # Trouver les motifs récurrents dans les faux positifs
        false_positives = [item.get("value", "") for item in feedbacks if not item.get("is_valid", True)]
        for fp in false_positives:
            if len(fp) > 3:  # Ignorer les valeurs trop courtes
                patterns_to_exclude.append({
                    "data_type": data_type,
                    "pattern": fp,
                    "occurrences": false_positives.count(fp)
                })
    
    # Éliminer les doublons dans les patterns
    unique_patterns = []
    added_patterns = set()
    for p in patterns_to_exclude:
        if p["pattern"] not in added_patterns and p["occurrences"] > 1:
            unique_patterns.append(p)
            added_patterns.add(p["pattern"])
    
    # Trier par nombre d'occurrences
    unique_patterns.sort(key=lambda x: x["occurrences"], reverse=True)
    
    # Afficher l'analyse des seuils
    st.markdown("##### Analyse des seuils de confiance")
    
    if threshold_analysis:
        threshold_df = pd.DataFrame(threshold_analysis)
        threshold_df["accuracy"] = threshold_df["accuracy"].round(2)
        col_order = ["data_type", "current_threshold", "suggested_threshold", "accuracy", "sample_size"]
        st.dataframe(threshold_df[col_order], use_container_width=True)
        
        # Suggérer des modifications
        st.markdown("##### Suggestions d'ajustement des seuils")
        
        for row in threshold_analysis:
            current = row["current_threshold"]
            suggested = row["suggested_threshold"]
            
            if abs(current - suggested) >= 0.1:
                if suggested > current:
                    st.info(f"Pour le type {row['data_type']}, augmenter le seuil de {current} à {suggested} pour réduire les faux positifs")
                else:
                    st.info(f"Pour le type {row['data_type']}, réduire le seuil de {current} à {suggested} pour éviter de manquer des détections")
    else:
        st.warning("Pas assez de données pour analyser les seuils.")
    
    # Afficher les motifs récurrents dans les faux positifs
    if unique_patterns:
        st.markdown("##### Motifs récurrents dans les faux positifs")
        st.markdown("Ces motifs pourraient être ajoutés à la liste d'exclusion pour réduire les faux positifs.")
        
        for pattern in unique_patterns[:10]:  # Limiter à 10 pour ne pas surcharger
            st.markdown(f"- **{pattern['pattern']}** ({pattern['occurrences']} occurrences, type: {pattern['data_type']})")
    
    # Bouton pour mettre à jour les seuils automatiquement
    if threshold_analysis and st.button("Appliquer les ajustements de seuils suggérés"):
        try:
            # Chemin vers le module core.py
            core_path = Path("analyzer/core.py")
            
            if core_path.exists():
                with open(core_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # Trouver et remplacer le bloc de seuils de confiance
                threshold_block = "confidence_thresholds = {"
                end_block = "}"
                
                start_idx = content.find(threshold_block)
                if start_idx != -1:
                    end_idx = content.find(end_block, start_idx) + 1
                    
                    # Construire le nouveau bloc
                    new_block = "confidence_thresholds = {\n"
                    for row in threshold_analysis:
                        new_block += f'        "{row["data_type"]}": {row["suggested_threshold"]},\n'
                    new_block += "    }"
                    
                    # Remplacer
                    new_content = content[:start_idx] + new_block + content[end_idx:]
                    
                    with open(core_path, "w", encoding="utf-8") as f:
                        f.write(new_content)
                    
                    st.success("Seuils de confiance mis à jour avec succès!")
                else:
                    st.error("Impossible de trouver le bloc de seuils de confiance dans core.py")
            else:
                st.error(f"Fichier core.py non trouvé à l'emplacement: {core_path}")
        except Exception as e:
            st.error(f"Erreur lors de la mise à jour des seuils: {str(e)}")
