import os
import logging
from datetime import datetime

def setup_logging():
    """Configure le système de journalisation"""
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    log_file = os.path.join(log_dir, f"app_{datetime.now().strftime('%Y-%m-%d')}.log")
    
    # Spécifier explicitement l'encodage
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger("rgpd_analyzer")

def show_error_logs():
    """Affiche les logs d'erreur dans l'interface Streamlit"""
    import streamlit as st
    
    st.markdown('<div class="sub-header">Journaux d\'erreurs</div>', unsafe_allow_html=True)
    
    log_dir = "logs"
    if not os.path.exists(log_dir):
        st.info("Aucun journal disponible.")
        return
    
    log_files = sorted([f for f in os.listdir(log_dir) if f.startswith("app_")], reverse=True)
    
    if not log_files:
        st.info("Aucun journal disponible.")
        return
    
    selected_log = st.selectbox("Sélectionner un journal", options=log_files, key="log_select")
    
    if selected_log:
        log_path = os.path.join(log_dir, selected_log)
        try:
            # Essayer différents encodages
            encodings = ["utf-8", "latin-1", "cp1252", "iso-8859-1"]
            log_content = []
            encoding_used = None
            
            for encoding in encodings:
                try:
                    with open(log_path, "r", encoding=encoding) as f:
                        log_content = f.readlines()
                        encoding_used = encoding
                        break
                except UnicodeDecodeError:
                    continue
            
            if not log_content:
                st.error("Impossible de lire le fichier journal avec les encodages disponibles.")
                return
                
            st.info(f"Fichier journal lu avec l'encodage : {encoding_used}")
            
            # Filtrer uniquement les erreurs
            error_logs = [line for line in log_content if "ERROR" in line]
            
            if error_logs:
                st.markdown("### Erreurs détectées")
                log_text = "".join(error_logs)
                st.text_area("Journal des erreurs", log_text, height=400, key="error_log")
                
                if st.button("Télécharger le journal complet", key="download_log"):
                    full_log = "".join(log_content)
                    st.download_button(
                        "Confirmer le téléchargement",
                        full_log,
                        file_name=selected_log,
                        mime="text/plain",
                        key="confirm_download_log"
                    )
            else:
                st.success("Aucune erreur trouvée dans ce journal.")
        except Exception as e:
            st.error(f"Erreur lors de la lecture du journal: {str(e)}")
            import traceback
            st.error(traceback.format_exc())
