import os
import json
import uuid
import datetime
import pandas as pd
import streamlit as st

class AnalysisStorage:
    def __init__(self, storage_dir="saved_analyses"):
        self.storage_dir = storage_dir
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)
        self.metadata_file = os.path.join(self.storage_dir, "metadata.json")
        if not os.path.exists(self.metadata_file):
            with open(self.metadata_file, "w", encoding="utf-8") as f:
                json.dump([], f)
    
    def _load_metadata(self):
        with open(self.metadata_file, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def _save_metadata(self, metadata):
        with open(self.metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=4)
    
    def save_analysis(self, df, name, source_path="", description=""):
        analysis_id = str(uuid.uuid4())
        filename = f"analysis_{analysis_id}.pkl"
        file_path = os.path.join(self.storage_dir, filename)
        df.to_pickle(file_path)
        
        metadata = self._load_metadata()
        new_entry = {
            "id": analysis_id,
            "name": name,
            "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "file_count": len(df),
            "has_sensitive_data": any((df[col] != "").any() for col in ["emails_found", "phones_found", "names_found", "secu_found", "siret_found", "postal_addresses_found", "ip_addresses_found"]),
            "source_path": source_path,
            "description": description,
            "file_path": file_path
        }
        metadata.insert(0, new_entry)
        self._save_metadata(metadata)
        return analysis_id
    
    def get_all_analyses_metadata(self):
        return self._load_metadata()
    
    def get_analysis(self, analysis_id):
        metadata = self._load_metadata()
        entry = next((item for item in metadata if item["id"] == analysis_id), None)
        if entry:
            try:
                df = pd.read_pickle(entry["file_path"])
                return df, entry
            except Exception as e:
                return None, None
        return None, None
    
    def concatenate_analyses(self, analysis_ids):
        metadata = self._load_metadata()
        dfs = []
        metadata_list = []
        for aid in analysis_ids:
            entry = next((item for item in metadata if item["id"] == aid), None)
            if entry:
                try:
                    df = pd.read_pickle(entry["file_path"])
                    dfs.append(df)
                    metadata_list.append(entry)
                except Exception as e:
                    pass
        if dfs:
            combined_df = pd.concat(dfs, ignore_index=True)
            return combined_df, metadata_list
        return None, None
    
    def delete_analysis(self, analysis_id):
        metadata = self._load_metadata()
        new_metadata = [item for item in metadata if item["id"] != analysis_id]
        entry = next((item for item in metadata if item["id"] == analysis_id), None)
        if entry:
            try:
                os.remove(entry["file_path"])
            except Exception as e:
                pass
            self._save_metadata(new_metadata)
            return True
        return False

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
    
    st.markdown('<div class="powerbi-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-header">AFFICHER UNE ANALYSE</div>', unsafe_allow_html=True)
    
    analysis_options = {a["id"]: f"{a['name']} ({a['date']})" for a in all_analyses}
    selected_analysis = st.selectbox(
        "Sélectionnez une analyse à visualiser", 
        options=list(analysis_options.keys()),
        format_func=lambda x: analysis_options[x]
    )
    
    if st.button("📊 Visualiser cette analyse"):
        if selected_analysis:
            with st.spinner("Chargement de l'analyse..."):
                results_df, metadata = storage.get_analysis(selected_analysis)
                if results_df is not None:
                    st.success(f"✅ Analyse '{metadata['name']}' chargée avec succès!")
                    # Ajouter ici l'affichage des statistiques et autres détails
                    from app import show_statistics, show_risk_analysis, show_detailed_results
                    import analyzer.core as analyzer
                    show_statistics(results_df)
                    risk_analysis = analyzer.calculate_risk_scores(results_df.to_dict('records'))
                    show_risk_analysis(risk_analysis)
                    show_detailed_results(results_df)
                else:
                    st.error("⚠️ Impossible de charger l'analyse. Les données semblent corrompues ou manquantes.")
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="powerbi-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-header">CONCATÉNER DES ANALYSES</div>', unsafe_allow_html=True)
    
    selected_analyses = st.multiselect(
        "Sélectionnez plusieurs analyses à combiner",
        options=list(analysis_options.keys()),
        format_func=lambda x: analysis_options[x]
    )
    
    if st.button("🔄 Combiner les analyses sélectionnées"):
        if selected_analyses and len(selected_analyses) > 1:
            with st.spinner("Combinaison des analyses en cours..."):
                combined_df, metadata_list = storage.concatenate_analyses(selected_analyses)
                if combined_df is not None:
                    st.success(f"✅ {len(metadata_list)} analyses combinées avec succès!")
                    # Ajouter ici l'affichage des statistiques de la combinaison
                    from app import show_statistics, show_risk_analysis, show_detailed_results
                    import analyzer.core as analyzer
                    show_statistics(combined_df)
                    risk_analysis = analyzer.calculate_risk_scores(combined_df.to_dict('records'))
                    show_risk_analysis(risk_analysis)
                    show_detailed_results(combined_df)
                else:
                    st.error("⚠️ Impossible de combiner les analyses. Certaines données peuvent être corrompues.")
        elif selected_analyses:
            st.warning("⚠️ Veuillez sélectionner au moins deux analyses à combiner.")
        else:
            st.warning("⚠️ Aucune analyse sélectionnée.")
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="powerbi-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-header">GÉRER LES ANALYSES</div>', unsafe_allow_html=True)
    
    delete_analysis = st.selectbox(
        "Sélectionnez une analyse à supprimer", 
        options=list(analysis_options.keys()),
        format_func=lambda x: analysis_options[x],
        key="delete_select"
    )
    
    if st.button("🗑️ Supprimer cette analyse", key="delete_button"):
        if delete_analysis:
            if st.checkbox("Confirmer la suppression", key="confirm_delete"):
                success = storage.delete_analysis(delete_analysis)
                if success:
                    st.success("✅ Analyse supprimée avec succès!")
                    st.experimental_rerun()
                else:
                    st.error("⚠️ Erreur lors de la suppression de l'analyse.")
            else:
                st.warning("⚠️ Veuillez confirmer la suppression en cochant la case.")
    st.markdown('</div>', unsafe_allow_html=True)
