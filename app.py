# app.py
import streamlit as st

# La commande set_page_config DOIT être la première commande Streamlit dans le script
st.set_page_config(
    page_title="Analyseur RGPD",
    page_icon="🔒",
    layout="wide",
    initial_sidebar_state="expanded"
)

import pandas as pd
import os
import tempfile
import plotly.express as px
from pathlib import Path
import sys
import datetime
from io import BytesIO
from analyzer.storage import AnalysisStorage
from analyzer.background_task import BackgroundTask

# Import du gestionnaire d'erreurs
from analyzer.error_handler import error_handler
from logger import setup_logging, show_error_logs

current_dir = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
if current_dir not in sys.path:
    sys.path.append(current_dir)

import analyzer.core as analyzer
from config.exclusion_lists import EXCLUDED_PERSONS, ORGANIZATION_UNITS
from manual_validation import manual_validation_tab, apply_feedback_to_thresholds
from auth import requires_auth, requires_admin, show_admin_panel, change_password_form
import plotly.graph_objects as go

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E3A8A;
        margin-bottom: 20px;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #1E3A8A;
        margin-top: 30px;
        margin-bottom: 10px;
    }
    .mini-header {
        font-size: 1.2rem;
        color: #1E3A8A;
        margin-top: 15px;
        margin-bottom: 5px;
        font-weight: 500;
    }
    .highlight {
        background-color: #F0F7FF;
        padding: 15px;
        border-radius: 5px;
        border-left: 5px solid #1E3A8A;
    }
    .footer {
        margin-top: 50px;
        text-align: center;
        color: #718096;
    }
    
    /* Style amélioré pour les boutons */
    div.stButton > button {
        background: linear-gradient(to right, #1E3A8A, #2563EB);
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 0.5rem;
        font-weight: 500;
        width: 100%;
        transition: all 0.3s ease;
        margin-bottom: 0.5rem;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    
    div.stButton > button:hover {
        background: linear-gradient(to right, #2563EB, #3B82F6);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        transform: translateY(-2px);
    }
    
    /* Menu latéral élégant */
    section[data-testid="stSidebar"] {
        background-color: #F8FAFC;
        border-right: 1px solid #E2E8F0;
    }
    
    section[data-testid="stSidebar"] div.stRadio label {
        background-color: #F1F5F9;
        padding: 10px;
        border-radius: 5px;
        margin: 5px 0;
        transition: all 0.2s;
    }
    
    section[data-testid="stSidebar"] div.stRadio label:hover {
        background-color: #E2E8F0;
    }
    
    /* Boutons d'action spéciaux */
    div.stButton > button[data-baseweb="button"].danger {
        background: linear-gradient(to right, #DC2626, #EF4444);
    }
    
    div.stButton > button[data-baseweb="button"].success {
        background: linear-gradient(to right, #059669, #10B981);
    }
</style>
""", unsafe_allow_html=True)

def show_statistics(results_df):
    st.markdown('<div class="sub-header">Statistiques d\'analyse</div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Fichiers analysés", len(results_df))
    with col2:
        sensitive_mask = (
            (results_df['emails_found'] != "") |
            (results_df['phones_found'] != "") |
            (results_df['names_found'] != "") |
            (results_df['secu_found'] != "") |
            (results_df['siret_found'] != "") |
            (results_df.get('postal_addresses_found', "") != "") |
            (results_df.get('ip_addresses_found', "") != "")
        )
        st.metric("Fichiers avec données personnelles", len(results_df[sensitive_mask]))
    with col3:
        st.metric("Types de fichiers", len(results_df['file_type'].unique()))
        
    # Graphique de répartition des types de données personnelles
    st.markdown('<div class="sub-header">Répartition des données personnelles détectées</div>', unsafe_allow_html=True)
    
    # Calculer le nombre de fichiers contenant chaque type de données
    data_types = {
        'Emails': results_df['emails_found'].apply(lambda x: x != '').sum(),
        'Téléphones': results_df['phones_found'].apply(lambda x: x != '').sum(),
        'Noms': results_df['names_found'].apply(lambda x: x != '').sum(),
        'Numéros Sécu.': results_df['secu_found'].apply(lambda x: x != '').sum(),
        'SIRET': results_df['siret_found'].apply(lambda x: x != '').sum()
    }
    
    # Ajouter les nouveaux types de données s'ils existent
    if 'postal_addresses_found' in results_df.columns:
        data_types['Adresses postales'] = results_df['postal_addresses_found'].apply(lambda x: x != '').sum()
    if 'ip_addresses_found' in results_df.columns:
        data_types['Adresses IP'] = results_df['ip_addresses_found'].apply(lambda x: x != '').sum()
    
    # Créer un DataFrame pour le graphique
    data_types_df = pd.DataFrame({
        'Type de données': list(data_types.keys()),
        'Nombre de fichiers': list(data_types.values())
    })
    
    # Trier par fréquence décroissante
    data_types_df = data_types_df.sort_values('Nombre de fichiers', ascending=False)
    
    # Créer le graphique
    fig1 = px.bar(data_types_df, 
                x='Type de données', 
                y='Nombre de fichiers', 
                color='Nombre de fichiers',
                color_continuous_scale=px.colors.sequential.Blues,
                title='Types de données personnelles détectées')
    
    # Améliorer le style du graphique
    fig1.update_layout(
        xaxis_title='',
        yaxis_title='Nombre de fichiers',
        font=dict(size=12),
        margin=dict(l=20, r=20, t=40, b=20),
        plot_bgcolor='rgba(240, 247, 255, 0.5)'
    )
    
    st.plotly_chart(fig1, use_container_width=True)
    
    # Ajouter un graphique camembert pour la proportion de fichiers avec données personnelles
    col1, col2 = st.columns(2)
    
    with col1:
        # Répartition par type de fichier (graphique plus petit)
        st.markdown('<div class="mini-header">Répartition par type de fichier</div>', unsafe_allow_html=True)
        file_type_counts = results_df['file_type'].value_counts().reset_index()
        file_type_counts.columns = ['Type de fichier', 'Nombre']
        fig2 = px.bar(file_type_counts, x='Type de fichier', y='Nombre', color='Nombre', color_continuous_scale=px.colors.sequential.Blues)
        fig2.update_layout(margin=dict(l=20, r=20, t=20, b=20), height=300)
        st.plotly_chart(fig2, use_container_width=True)
    
    with col2:
        # Proportions de fichiers avec/sans données personnelles
        st.markdown('<div class="mini-header">Proportion de fichiers avec données personnelles</div>', unsafe_allow_html=True)
        sensitive_count = len(results_df[results_df['emails_found'] != '']) + \
                        len(results_df[results_df['phones_found'] != '']) + \
                        len(results_df[results_df['names_found'] != '']) + \
                        len(results_df[results_df['secu_found'] != '']) + \
                        len(results_df[results_df['siret_found'] != ''])
        
        # Éviter le double comptage
        sensitive_mask = (
            (results_df['emails_found'] != '') |
            (results_df['phones_found'] != '') |
            (results_df['names_found'] != '') |
            (results_df['secu_found'] != '') |
            (results_df['siret_found'] != '')
        )
        
        # Ajouter les colonnes de nouvelles données personnelles si elles existent
        if 'postal_addresses_found' in results_df.columns:
            sensitive_mask = sensitive_mask | (results_df['postal_addresses_found'] != '')
        if 'ip_addresses_found' in results_df.columns:
            sensitive_mask = sensitive_mask | (results_df['ip_addresses_found'] != '')
            
        sensitive_count = len(results_df[sensitive_mask])
        non_sensitive_count = len(results_df) - sensitive_count
        
        fig3 = px.pie(
            values=[sensitive_count, non_sensitive_count],
            names=['Avec données personnelles', 'Sans données personnelles'],
            color_discrete_sequence=px.colors.sequential.Blues[3:5],
            hole=0.4
        )
        fig3.update_layout(margin=dict(l=20, r=20, t=20, b=20), height=300)
        fig3.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig3, use_container_width=True)

def show_detailed_results(results_df):
    st.markdown('<div class="sub-header">Résultats détaillés</div>', unsafe_allow_html=True)
    with st.expander("Filtres", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            selected_types = st.multiselect("Filtrer par type de fichier", options=sorted(results_df['file_type'].unique()), default=sorted(results_df['file_type'].unique()))
        with col2:
            data_filter = st.multiselect("Filtrer par type de données", 
                                         options=["Emails", "Téléphones", "Noms", "Numéros Sécurité Sociale", "SIRET", "Adresses postales", "Adresses IP"],
                                         default=["Emails", "Téléphones", "Noms", "Numéros Sécurité Sociale", "SIRET", "Adresses postales", "Adresses IP"])
    filtered_df = results_df[results_df['file_type'].isin(selected_types)]
    filter_conditions = []
    if "Emails" in data_filter:
        filter_conditions.append(filtered_df['emails_found'] != "")
    if "Téléphones" in data_filter:
        filter_conditions.append(filtered_df['phones_found'] != "")
    if "Noms" in data_filter:
        filter_conditions.append(filtered_df['names_found'] != "")
    if "Numéros Sécurité Sociale" in data_filter:
        filter_conditions.append(filtered_df['secu_found'] != "")
    if "SIRET" in data_filter:
        filter_conditions.append(filtered_df['siret_found'] != "")
    if "Adresses postales" in data_filter:
        filter_conditions.append(filtered_df.get('postal_addresses_found', "") != "")
    if "Adresses IP" in data_filter:
        filter_conditions.append(filtered_df.get('ip_addresses_found', "") != "")
    if filter_conditions:
        combined_filter = filter_conditions[0]
        for condition in filter_conditions[1:]:
            combined_filter = combined_filter | condition
        filtered_df = filtered_df[combined_filter]
    st.dataframe(filtered_df[['file_path', 'file_type', 'emails_found', 'phones_found', 'names_found', 'secu_found', 'siret_found',
                                'postal_addresses_found', 'ip_addresses_found']], use_container_width=True)
    if not filtered_df.empty:
        csv = filtered_df.to_csv(index=False)
        st.download_button("Télécharger les résultats au format CSV", csv, "resultats_rgpd.csv", "text/csv", key='download-csv')
        excel_buffer = BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            filtered_df.to_excel(writer, sheet_name='Résultats', index=False)
        excel_data = excel_buffer.getvalue()
        st.download_button("Télécharger les résultats au format Excel", excel_data, "resultats_rgpd.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key='download-excel')

def show_risk_analysis(risk_analysis):
    st.markdown('<div class="sub-header">Synthèse des risques</div>', unsafe_allow_html=True)
    risk_col1, risk_col2, risk_col3 = st.columns(3)
    with risk_col1:
        st.metric("Fichiers à risque élevé", risk_analysis["total_high_risk"])
    with risk_col2:
        st.metric("Fichiers à risque moyen", risk_analysis["total_medium_risk"])
    with risk_col3:
        st.metric("Fichiers à risque faible", risk_analysis["total_low_risk"])
    if risk_analysis["high_risk_files"]:
        st.markdown('<div class="sub-header">Fichiers à risque élevé</div>', unsafe_allow_html=True)
        high_risk_df = pd.DataFrame(risk_analysis["high_risk_files"])
        st.dataframe(high_risk_df, use_container_width=True)

def saved_analyses_tab():
    st.markdown('<div class="sub-header">Analyses sauvegardées</div>', unsafe_allow_html=True)
    
    storage = AnalysisStorage()
    
    all_analyses = storage.get_all_analyses_metadata()
    
    if not all_analyses:
        st.markdown('<div class="powerbi-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-header">AUCUNE ANALYSE DISPONIBLE</div>', unsafe_allow_html=True)
        st.info("Aucune analyse n'a été sauvegardée. Veuillez effectuer une analyse pour commencer.")
        st.markdown('</div>', unsafe_allow_html=True)
        return
    
    st.markdown('<div class="powerbi-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-header">ANALYSES DISPONIBLES</div>', unsafe_allow_html=True)
    
    analyses_df = pd.DataFrame(all_analyses)
    analyses_df['date_formatted'] = analyses_df['date'].apply(lambda x: x.replace('-', '/'))
    analyses_df['action'] = ""
    
    display_df = analyses_df[['name', 'date_formatted', 'file_count', 'has_sensitive_data']].copy()
    display_df.columns = ['Nom de l\'analyse', 'Date', 'Fichiers analysés', 'Données sensibles']
    
    display_df['Données sensibles'] = display_df['Données sensibles'].apply(lambda x: "✅ Oui" if x else "❌ Non")
    
    st.dataframe(display_df, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Les onglets pour différentes actions
    tab1, tab2, tab3 = st.tabs(["📊 Visualiser", "🔄 Combiner", "🗑️ Supprimer"])
    
    with tab1:
        analysis_options = {a["id"]: f"{a['name']} ({a['date']})" for a in all_analyses}
        selected_analysis = st.selectbox(
            "Sélectionnez une analyse à visualiser", 
            options=list(analysis_options.keys()),
            format_func=lambda x: analysis_options[x],
            key="view_select"
        )
        
        if st.button("📊 Visualiser cette analyse", key="view_button"):
            if selected_analysis:
                with st.spinner("Chargement de l'analyse..."):
                    results_df, metadata = storage.get_analysis(selected_analysis)
                    if results_df is not None:
                        st.success(f"✅ Analyse '{metadata['name']}' chargée avec succès!")
                        # Vous pouvez ici ajouter l'affichage des statistiques et autres détails
                    else:
                        st.error("⚠️ Impossible de charger l'analyse. Les données semblent corrompues ou manquantes.")
    
    with tab2:
        selected_analyses = st.multiselect(
            "Sélectionnez plusieurs analyses à combiner",
            options=list(analysis_options.keys()),
            format_func=lambda x: analysis_options[x],
            key="combine_select"
        )
        
        if st.button("🔄 Combiner les analyses sélectionnées", key="combine_button"):
            if selected_analyses and len(selected_analyses) > 1:
                with st.spinner("Combinaison des analyses en cours..."):
                    combined_df, metadata_list = storage.concatenate_analyses(selected_analyses)
                    if combined_df is not None:
                        st.success(f"✅ {len(metadata_list)} analyses combinées avec succès!")
                    else:
                        st.error("⚠️ Impossible de combiner les analyses. Certaines données peuvent être corrompues.")
            elif selected_analyses:
                st.warning("⚠️ Veuillez sélectionner au moins deux analyses à combiner.")
            else:
                st.warning("⚠️ Aucune analyse sélectionnée.")
    
    with tab3:
        delete_analysis = st.selectbox(
            "Sélectionnez une analyse à supprimer", 
            options=list(analysis_options.keys()),
            format_func=lambda x: analysis_options[x],
            key="delete_select"
        )
        
        col1, col2 = st.columns([1, 3])
        with col1:
            confirm_delete = st.checkbox("Confirmer", key="confirm_delete")
        with col2:
            if st.button("🗑️ Supprimer cette analyse", key="delete_button", 
                       disabled=not confirm_delete,
                       help="Confirmez d'abord en cochant la case"):
                if delete_analysis:
                    success = storage.delete_analysis(delete_analysis)
                    if success:
                        st.success("✅ Analyse supprimée avec succès!")
                        st.rerun()
                    else:
                        st.error("⚠️ Erreur lors de la suppression de l'analyse.")

def analyze_directory(directory_path, progress_bar=None, max_files=None, save_analysis=True, excluded_extensions=None):
    # Vérifier si nous devons exécuter l'analyse en arrière-plan ou de manière synchrone
    if progress_bar is None:
        # Mode arrière-plan - créer une tâche et retourner immédiatement
        task_params = {
            "directory_path": directory_path,
            "max_files": max_files,
            "save_analysis": save_analysis,
            "excluded_extensions": excluded_extensions if excluded_extensions else []
        }
        task_id = BackgroundTask.create_task("directory_analysis", task_params)
        return None, task_id
    
    # Mode synchrone - exécuter l'analyse directement
    results = []
    all_files = []
    skipped_files = []
    error_files = []
    
    for root, _, files in os.walk(directory_path):
        for file in files:
            file_path = os.path.join(root, file)
            if analyzer.is_supported_file(file_path):
                all_files.append(file_path)
    if max_files and len(all_files) > max_files:
        all_files = all_files[:max_files]
    total_files = len(all_files)
    if total_files == 0:
        st.warning("Aucun fichier compatible trouvé dans le dossier sélectionné.")
        return pd.DataFrame(), None
    
    for i, file_path in enumerate(all_files):
        # Vérifier si le fichier doit être exclu en fonction de son extension
        if excluded_extensions and Path(file_path).suffix.lower() in excluded_extensions:
            skipped_files.append({"path": file_path, "reason": "Extension exclue"})
            continue
            
        # Analyser le fichier
        try:
            result = analyzer.analyze_file(file_path)
            if result:
                results.append(result)
            else:
                # Si le résultat est None, c'est probablement un fichier temporaire ou inaccessible
                if Path(file_path).name.startswith("~$"):
                    skipped_files.append({"path": file_path, "reason": "Fichier temporaire"})
                else:
                    error_files.append({"path": file_path, "reason": "Analyse impossible"})
        except Exception as e:
            error_handler.log_error(e, file_path)
            error_files.append({"path": file_path, "reason": str(e)[:50] + "..."})
        
        progress_bar.progress((i + 1) / total_files)
    
    # Afficher un résumé des fichiers ignorés ou en erreur
    if skipped_files:
        st.info(f"{len(skipped_files)} fichiers ont été ignorés (fichiers temporaires ou extensions exclues).")
        with st.expander("Voir les fichiers ignorés"):
            st.dataframe(pd.DataFrame(skipped_files))
    
    if error_files:
        st.warning(f"{len(error_files)} fichiers n'ont pas pu être analysés en raison d'erreurs.")
        with st.expander("Voir les fichiers en erreur"):
            st.dataframe(pd.DataFrame(error_files))
            
    if not results:
        st.warning("Aucun résultat d'analyse obtenu.")
        return pd.DataFrame(), None
    
    results_df = pd.DataFrame(results)
    if save_analysis:
        from analyzer.storage import AnalysisStorage
        storage = AnalysisStorage()
        analysis_name = f"Analyse de {os.path.basename(directory_path)}"
        analysis_id = storage.save_analysis(
            results_df, 
            name=analysis_name,
            source_path=directory_path,
            description=f"Analyse automatique de {len(results)} fichiers ({total_files - len(results)} ignorés/en erreur)"
        )
        if analysis_id:
            st.success(f"Analyse sauvegardée avec l'ID: {analysis_id}")
    return results_df, None

def analyze_uploaded_files(uploaded_files, progress_bar=None, save_analysis=True):
    # Vérifier si nous devons exécuter l'analyse en arrière-plan ou de manière synchrone
    if progress_bar is None:
        # Mode arrière-plan - créer une tâche et retourner immédiatement
        file_paths = []
        file_names = []
        file_contents = []
        
        for uploaded_file in uploaded_files:
            try:
                # Lire le contenu des fichiers
                content = uploaded_file.getvalue().decode('utf-8')
                file_paths.append(uploaded_file.name)
                file_names.append(uploaded_file.name)
                file_contents.append(content)
            except UnicodeDecodeError:
                # Pour les fichiers binaires, nous ne pouvons pas les traiter en arrière-plan facilement
                # mais nous pouvons les traiter en mode synchrone
                pass
        
        task_params = {
            "file_paths": file_paths,
            "file_names": file_names,
            "file_contents": file_contents,
            "save_analysis": save_analysis
        }
        task_id = BackgroundTask.create_task("files_analysis", task_params)
        return None, task_id
    
    # Mode synchrone - exécuter l'analyse directement
    results = []
    for i, uploaded_file in enumerate(uploaded_files):
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            temp_path = tmp_file.name
        result = analyzer.analyze_file(temp_path)
        if result:
            result["file_path"] = uploaded_file.name
            results.append(result)
        os.unlink(temp_path)
        progress_bar.progress((i + 1) / len(uploaded_files))
    if not results:
        st.warning("Aucun résultat d'analyse obtenu pour les fichiers chargés.")
        return pd.DataFrame(), None
    results_df = pd.DataFrame(results)
    if save_analysis:
        from analyzer.storage import AnalysisStorage
        storage = AnalysisStorage()
        file_names = ", ".join([f.name for f in uploaded_files[:3]])
        if len(uploaded_files) > 3:
            file_names += f" et {len(uploaded_files) - 3} autres"
        analysis_name = f"Analyse de fichiers: {file_names}"
        analysis_id = storage.save_analysis(
            results_df, 
            name=analysis_name,
            description=f"Analyse de {len(uploaded_files)} fichiers téléchargés"
        )
        if analysis_id:
            st.success(f"Analyse sauvegardée avec l'ID: {analysis_id}")
    return results_df, None

@requires_admin
def user_management_tab():
    """Onglet de gestion des utilisateurs (réservé aux administrateurs)"""
    show_admin_panel()

@requires_auth
def user_settings_tab():
    """Onglet des paramètres utilisateur"""
    change_password_form()

@requires_auth
def main():
    # Configurez le logger au début
    logger = setup_logging()
    
    with st.sidebar:
        st.image("https://placehold.co/300x86?text=ACME+Corp", width=200)
        st.markdown("## Options d'analyse")
        # Utiliser session_state pour maintenir l'option sélectionnée entre les rechargements
        if 'analysis_options' not in st.session_state:
            st.session_state.analysis_options = "Tableau de bord"
            
        # Création d'une fonction de callback pour le radio button
        def on_page_change():
            # Cette fonction ne fait rien, mais force le rechargement
            pass
            
        analysis_options = st.radio("Mode d'analyse", 
                                   options=["Tableau de bord", "Analyses sauvegardées", "Analyse de dossier", 
                                           "Analyse de fichiers", "Paramètres", "Validation manuelle", 
                                           "Optimisation des seuils", "Mon compte", "Gestion utilisateurs", "Journaux d'erreurs"],
                                   index=["Tableau de bord", "Analyses sauvegardées", "Analyse de dossier", 
                                         "Analyse de fichiers", "Paramètres", "Validation manuelle", 
                                         "Optimisation des seuils", "Mon compte", "Gestion utilisateurs", "Journaux d'erreurs"].index(st.session_state.analysis_options),
                                   on_change=on_page_change,
                                   key="radio_analysis_options")
        
        # Mettre à jour la session_state avec la nouvelle valeur quand on change d'onglet
        if st.session_state.radio_analysis_options != st.session_state.analysis_options:
            st.session_state.analysis_options = st.session_state.radio_analysis_options
            st.rerun()
        
        # Pour d'autres interactions, utiliser la valeur actuellement sélectionnée
        analysis_options = st.session_state.radio_analysis_options
        if analysis_options in ["Analyse de dossier", "Tableau de bord"]:
            with st.expander("Options avancées", expanded=False):
                max_files = st.number_input("Nombre maximum de fichiers à analyser (0 = tous)", min_value=0, value=0)
                exclude_extensions = st.multiselect("Extensions à exclure", options=[".tmp", ".ini", ".log", ".dat", ".bak", ".exe", ".dll"], default=[])
        st.markdown("---")
        st.markdown("### À propos")
        st.markdown("Cette application analyse les documents pour détecter les données personnelles selon les normes RGPD, en minimisant les faux positifs.")
    
    st.markdown('<div class="main-header">Analyseur RGPD</div>', unsafe_allow_html=True)
    
    if analysis_options == "Tableau de bord":
        try:
            from analyzer.storage import AnalysisStorage
            storage = AnalysisStorage()
            all_analyses = storage.get_all_analyses_metadata()
            
            if all_analyses:
                # Sélecteur d'analyses pour le tableau de bord
                analysis_options = {a["id"]: f"{a['name']} ({a['date']})" for a in all_analyses}
                
                # Par défaut, sélectionner la dernière analyse
                default_analysis = all_analyses[0]["id"]
                
                # UI pour sélectionner une analyse
                selected_analysis_id = st.selectbox(
                    "Analyse à visualiser", 
                    options=list(analysis_options.keys()),
                    format_func=lambda x: analysis_options[x],
                    index=0,
                    key="dashboard_analysis_select"
                )
                
                results_df, metadata = storage.get_analysis(selected_analysis_id)
                if results_df is not None:
                    st.success(f"Analyse : {metadata['name']} - effectuée le {metadata['date']}")
                    show_statistics(results_df)
                    risk_analysis = analyzer.calculate_risk_scores(results_df.to_dict('records'))
                    show_risk_analysis(risk_analysis)
                    show_detailed_results(results_df)
                else:
                    st.info("L'analyse sélectionnée ne peut pas être chargée. Veuillez effectuer une nouvelle analyse.")
            else:
                st.info("Aucune analyse disponible. Veuillez effectuer une nouvelle analyse.")
        except Exception as e:
            st.error(f"Erreur lors du chargement des résultats: {str(e)}")
            st.info("Veuillez effectuer une nouvelle analyse.")
    elif analysis_options == "Analyses sauvegardées":
        saved_analyses_tab()
    elif analysis_options == "Analyse de dossier":
        st.markdown('<div class="highlight">Analysez un dossier complet pour détecter les données personnelles</div>', unsafe_allow_html=True)
        directory_path = st.text_input("Chemin du dossier à analyser", r"C:\chemin\vers\documents")
        save_option = st.checkbox("Sauvegarder cette analyse", value=True, help="Sauvegarde l'analyse pour consultation ultérieure")
        
        exclude_temp_files = st.checkbox("Ignorer les fichiers temporaires", value=True, help="Ignore les fichiers temporaires (commençant par ~$, etc.)")
        
        # Option pour l'analyse en arrière-plan
        run_in_background = st.checkbox("Exécuter en arrière-plan", value=True, 
                                      help="L'analyse continuera même si vous changez d'onglet ou fermez cette page")
        
        if st.button("Lancer l'analyse"):
            if os.path.isdir(directory_path):
                # Convertir les extensions en format standard
                excluded_exts = [ext.lower() if ext.startswith('.') else f'.{ext.lower()}' for ext in exclude_extensions]
                max_file_count = max_files if max_files > 0 else None
                
                if run_in_background:
                    # Mode arrière-plan
                    results_df, task_id = analyze_directory(directory_path, None, max_file_count, save_analysis=save_option, excluded_extensions=excluded_exts)
                    if task_id:
                        st.success(f"Analyse lancée en arrière-plan (ID: {task_id}). Vous pouvez suivre sa progression dans l'onglet 'Analyses sauvegardées > Tâches en cours'.")
                        if st.button("Aller aux tâches en cours"):
                            # Stocker l'onglet dans session_state
                            st.session_state.analysis_options = "Analyses sauvegardées"
                            # Ajouter un indicateur pour aller à l'onglet des tâches
                            st.session_state.show_tasks_tab = True
                            st.rerun()
                else:
                    # Mode synchrone
                    with st.spinner("Analyse en cours..."):
                        progress_bar = st.progress(0)
                        results_df, _ = analyze_directory(directory_path, progress_bar, max_file_count, save_analysis=save_option, excluded_extensions=excluded_exts)
                        if results_df is not None and not results_df.empty:
                            show_statistics(results_df)
                            risk_analysis = analyzer.calculate_risk_scores(results_df.to_dict('records'))
                            show_risk_analysis(risk_analysis)
                            show_detailed_results(results_df)
            else:
                st.error("Le chemin spécifié n'est pas un dossier valide.")
    elif analysis_options == "Analyse de fichiers":
        st.markdown('<div class="highlight">Chargez des fichiers individuels pour analyse</div>', unsafe_allow_html=True)
        uploaded_files = st.file_uploader("Choisissez des fichiers à analyser", 
                                          accept_multiple_files=True,
                                          type=["txt", "pdf", "docx", "doc", "xlsx", "xls", "csv", "rtf", "odt", "ods"])
        save_option = st.checkbox("Sauvegarder cette analyse", value=True, help="Sauvegarde l'analyse pour consultation ultérieure")
        
        # Option pour l'analyse en arrière-plan
        run_in_background = st.checkbox("Exécuter en arrière-plan", value=True, 
                                      help="L'analyse continuera même si vous changez d'onglet ou fermez cette page")
        
        if uploaded_files:
            if st.button("Analyser les fichiers"):
                if run_in_background:
                    # Mode arrière-plan
                    results_df, task_id = analyze_uploaded_files(uploaded_files, None, save_analysis=save_option)
                    if task_id:
                        st.success(f"Analyse lancée en arrière-plan (ID: {task_id}). Vous pouvez suivre sa progression dans l'onglet 'Analyses sauvegardées > Tâches en cours'.")
                        if st.button("Aller aux tâches en cours"):
                            st.session_state.analysis_options = "Analyses sauvegardées"
                            st.rerun()
                else:
                    # Mode synchrone
                    with st.spinner("Analyse en cours..."):
                        progress_bar = st.progress(0)
                        results_df, _ = analyze_uploaded_files(uploaded_files, progress_bar, save_analysis=save_option)
                        if results_df is not None and not results_df.empty:
                            show_statistics(results_df)
                            risk_analysis = analyzer.calculate_risk_scores(results_df.to_dict('records'))
                            show_risk_analysis(risk_analysis)
                            show_detailed_results(results_df)
    elif analysis_options == "Paramètres":
        st.markdown('<div class="sub-header">Paramètres de détection</div>', unsafe_allow_html=True)
        from config.exclusion_lists import EXCLUDED_PERSONS as current_excluded_persons, ORGANIZATION_UNITS as current_org_units
        with st.form("settings_form"):
            st.markdown("**Liste des personnes à exclure** (noms à ne pas considérer comme données personnelles)")
            excluded_persons_text = st.text_area("Un nom par ligne", value="\n".join(current_excluded_persons), height=200)
            st.markdown("**Liste des unités organisationnelles** (pour exclusion contextuelle)")
            org_units_text = st.text_area("Une unité par ligne", value="\n".join(current_org_units), height=100)
            threshold_col1, threshold_col2 = st.columns(2)
            with threshold_col1:
                name_confidence = st.slider("Seuil de confiance pour les noms", min_value=0.0, max_value=1.0, value=0.4, step=0.05)
                email_confidence = st.slider("Seuil de confiance pour les emails", min_value=0.0, max_value=1.0, value=0.7, step=0.05)
            with threshold_col2:
                phone_confidence = st.slider("Seuil de confiance pour les téléphones", min_value=0.0, max_value=1.0, value=0.7, step=0.05)
                secu_confidence = st.slider("Seuil de confiance pour les N° sécu", min_value=0.0, max_value=1.0, value=0.8, step=0.05)
            save_button = st.form_submit_button("Enregistrer les paramètres")
            if save_button:
                try:
                    new_excluded_persons = [p.strip() for p in excluded_persons_text.split("\n") if p.strip()]
                    new_org_units = [u.strip() for u in org_units_text.split("\n") if u.strip()]
                    config_path = Path(__file__).parent / "config" / "exclusion_lists.py"
                    if not config_path.exists():
                        config_path = Path("config") / "exclusion_lists.py"
                    if config_path.exists():
                        with open(config_path, 'w', encoding='utf-8') as f:
                            f.write("# config/exclusion_lists.py - Listes d'exclusion\n\n")
                            f.write("# Liste des personnes de l'organisation à exclure (dirigeants, employés fréquemment mentionnés)\n")
                            f.write("EXCLUDED_PERSONS = [\n")
                            for person in new_excluded_persons:
                                f.write(f'    "{person}",\n')
                            f.write("]\n\n")
                            f.write("# Termes professionnels qui indiquent un contexte non-personnel\n")
                            f.write("PROFESSIONAL_CONTEXT = [\n")
                            f.write('    "directeur", "dg", "responsable", "chef", "manager", \n')
                            f.write('    "signé", "signature", "contact", "coordonnées",\n')
                            f.write('    "référent", "chargé de", "administrateur", "employé",\n')
                            f.write('    "service", "département", "collègue", "équipe",\n')
                            f.write('    "salarié", "poste", "fonction", "technicien", "informatique"\n')
                            f.write("]\n\n")
                            f.write("# Termes qui indiquent que le document est un modèle/template\n")
                            f.write("TEMPLATE_INDICATORS = [\n")
                            f.write('    "exemple", "modèle", "template", "libellé", "démonstration",\n')
                            f.write('    "test", "formation", "documentation", "manuel",\n')
                            f.write('    "placeholder", "sample", "guide", "instruction"\n')
                            f.write("]\n\n")
                            f.write("# Structures de l'organisation à exclure\n")
                            f.write("ORGANIZATION_UNITS = [\n")
                            for unit in new_org_units:
                                f.write(f'    "{unit}",\n')
                            f.write("]\n")
                        try:
                            import importlib
                            from config import exclusion_lists
                            importlib.reload(exclusion_lists)
                        except Exception as e:
                            st.error(f"Erreur lors du rechargement du module: {str(e)}")
                        st.success("Paramètres sauvegardés avec succès! Les modifications seront appliquées lors des prochaines analyses.")
                    else:
                        st.error("Erreur : Impossible de trouver le fichier de configuration. Veuillez vérifier la structure des dossiers.")
                except Exception as e:
                    st.error(f"Erreur lors de la sauvegarde: {str(e)}")
                    st.error("Détails techniques pour le support IT : " + str(config_path))
        if st.button("Recharger l'application pour appliquer les changements"):
            st.rerun()
    elif analysis_options == "Validation manuelle":
        manual_validation_tab()
    elif analysis_options == "Optimisation des seuils":
        apply_feedback_to_thresholds()
    elif analysis_options == "Mon compte":
        user_settings_tab()
    elif analysis_options == "Gestion utilisateurs":
        user_management_tab()
    elif analysis_options == "Journaux d'erreurs":
        show_error_logs()

if __name__ == "__main__":
    main()
