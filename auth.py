import streamlit as st
import hashlib
import json
import os
from pathlib import Path
import uuid
import datetime
import inspect

class Authentication:
    def __init__(self, auth_file="auth/users.json"):
        self.auth_dir = os.path.dirname(auth_file)
        self.auth_file = auth_file
        self.session_file = os.path.join(self.auth_dir, "sessions.json")
        
        # Créer le répertoire d'authentification s'il n'existe pas
        if not os.path.exists(self.auth_dir):
            os.makedirs(self.auth_dir)
        
        # Créer le fichier des utilisateurs s'il n'existe pas
        if not os.path.exists(self.auth_file):
            self._create_default_user()
        
        # Créer le fichier des sessions s'il n'existe pas
        if not os.path.exists(self.session_file):
            with open(self.session_file, "w", encoding="utf-8") as f:
                json.dump({}, f)
    
    def _create_default_user(self):
        """Crée un utilisateur administrateur par défaut"""
        default_user = {
            "admin": {
                "password": self._hash_password("admin123"),  # Mot de passe par défaut
                "role": "admin",
                "name": "Administrateur",
                "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }
        
        with open(self.auth_file, "w", encoding="utf-8") as f:
            json.dump(default_user, f, indent=4)
    
    def _hash_password(self, password):
        """Hashage sécurisé des mots de passe"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def _load_users(self):
        """Charge les utilisateurs depuis le fichier"""
        with open(self.auth_file, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def _save_users(self, users):
        """Sauvegarde les utilisateurs dans le fichier"""
        with open(self.auth_file, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=4)
    
    def _load_sessions(self):
        """Charge les sessions depuis le fichier"""
        with open(self.session_file, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def _save_sessions(self, sessions):
        """Sauvegarde les sessions dans le fichier"""
        with open(self.session_file, "w", encoding="utf-8") as f:
            json.dump(sessions, f, indent=4)
    
    def login(self, username, password):
        """Authentifie un utilisateur et crée une session"""
        users = self._load_users()
        
        if username in users and users[username]["password"] == self._hash_password(password):
            # Créer un token de session
            session_token = str(uuid.uuid4())
            
            # Enregistrer la session
            sessions = self._load_sessions()
            sessions[session_token] = {
                "username": username,
                "role": users[username]["role"],
                "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            self._save_sessions(sessions)
            
            return session_token
        
        return None
    
    def logout(self, session_token):
        """Déconnecte un utilisateur en supprimant sa session"""
        sessions = self._load_sessions()
        
        if session_token in sessions:
            del sessions[session_token]
            self._save_sessions(sessions)
            return True
        
        return False
    
    def is_authenticated(self, session_token):
        """Vérifie si un token de session est valide"""
        if not session_token:
            return False
        
        sessions = self._load_sessions()
        return session_token in sessions
    
    def get_user_info(self, session_token):
        """Récupère les informations de l'utilisateur connecté"""
        sessions = self._load_sessions()
        
        if session_token in sessions:
            username = sessions[session_token]["username"]
            users = self._load_users()
            
            if username in users:
                return {
                    "username": username,
                    "role": users[username]["role"],
                    "name": users[username]["name"]
                }
        
        return None
    
    def register_user(self, username, password, name, role="user"):
        """Enregistre un nouvel utilisateur (réservé à l'administrateur)"""
        users = self._load_users()
        
        if username in users:
            return False, "Nom d'utilisateur déjà utilisé"
        
        users[username] = {
            "password": self._hash_password(password),
            "role": role,
            "name": name,
            "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        self._save_users(users)
        return True, "Utilisateur créé avec succès"
    
    def delete_user(self, username):
        """Supprime un utilisateur (réservé à l'administrateur)"""
        users = self._load_users()
        
        if username not in users:
            return False, "Utilisateur non trouvé"
        
        if username == "admin":
            return False, "L'utilisateur admin ne peut pas être supprimé"
        
        del users[username]
        self._save_users(users)
        
        # Supprimer toutes les sessions associées à cet utilisateur
        sessions = self._load_sessions()
        sessions = {token: session for token, session in sessions.items() if session["username"] != username}
        self._save_sessions(sessions)
        
        return True, "Utilisateur supprimé avec succès"
    
    def get_all_users(self):
        """Récupère la liste de tous les utilisateurs (réservé à l'administrateur)"""
        users = self._load_users()
        
        # Masquer les mots de passe
        return {username: {**info, "password": "***"} for username, info in users.items()}
    
    def change_password(self, username, current_password, new_password):
        """Change le mot de passe d'un utilisateur"""
        users = self._load_users()
        
        if username not in users:
            return False, "Utilisateur non trouvé"
        
        if users[username]["password"] != self._hash_password(current_password):
            return False, "Mot de passe actuel incorrect"
        
        users[username]["password"] = self._hash_password(new_password)
        self._save_users(users)
        
        return True, "Mot de passe modifié avec succès"

def login_form():
    """Affiche le formulaire de connexion"""
    st.markdown('<div class="sub-header">Connexion</div>', unsafe_allow_html=True)
    
    with st.form("login_form"):
        username = st.text_input("Nom d'utilisateur")
        password = st.text_input("Mot de passe", type="password")
        submit = st.form_submit_button("Se connecter")
        
        if submit:
            auth = Authentication()
            session_token = auth.login(username, password)
            
            if session_token:
                st.session_state["auth_token"] = session_token
                st.success("Connexion réussie!")
                st.rerun()
            else:
                st.error("Nom d'utilisateur ou mot de passe incorrect")

def logout():
    """Déconnecte l'utilisateur actuel"""
    if "auth_token" in st.session_state:
        auth = Authentication()
        auth.logout(st.session_state["auth_token"])
        del st.session_state["auth_token"]
        st.rerun()

def show_admin_panel():
    """Affiche le panneau d'administration des utilisateurs"""
    st.markdown('<div class="sub-header">Gestion des utilisateurs</div>', unsafe_allow_html=True)
    
    auth = Authentication()
    
    # Afficher la liste des utilisateurs
    st.markdown("#### Liste des utilisateurs")
    users = auth.get_all_users()
    
    users_df = []
    for username, info in users.items():
        users_df.append({
            "Utilisateur": username,
            "Nom": info["name"],
            "Rôle": info["role"],
            "Date de création": info.get("created_at", "")
        })
    
    if users_df:
        st.dataframe(pd.DataFrame(users_df))
    
    # Formulaire d'ajout d'utilisateur
    st.markdown("#### Ajouter un utilisateur")
    with st.form("add_user_form"):
        new_username = st.text_input("Nom d'utilisateur")
        new_password = st.text_input("Mot de passe", type="password")
        new_name = st.text_input("Nom complet")
        new_role = st.selectbox("Rôle", options=["user", "admin"])
        
        submit = st.form_submit_button("Ajouter")
        
        if submit:
            if not new_username or not new_password or not new_name:
                st.error("Tous les champs sont obligatoires")
            else:
                success, message = auth.register_user(new_username, new_password, new_name, new_role)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
    
    # Formulaire de suppression d'utilisateur
    st.markdown("#### Supprimer un utilisateur")
    with st.form("delete_user_form"):
        del_username = st.selectbox("Utilisateur à supprimer", options=[u for u in users.keys() if u != "admin"])
        
        submit = st.form_submit_button("Supprimer")
        
        if submit and del_username:
            success, message = auth.delete_user(del_username)
            if success:
                st.success(message)
                st.rerun()
            else:
                st.error(message)

def change_password_form():
    """Affiche le formulaire de changement de mot de passe"""
    st.markdown('<div class="sub-header">Changer mon mot de passe</div>', unsafe_allow_html=True)
    
    auth = Authentication()
    user_info = auth.get_user_info(st.session_state["auth_token"])
    
    with st.form("change_password_form"):
        current_password = st.text_input("Mot de passe actuel", type="password")
        new_password = st.text_input("Nouveau mot de passe", type="password")
        confirm_password = st.text_input("Confirmer le nouveau mot de passe", type="password")
        
        submit = st.form_submit_button("Changer le mot de passe")
        
        if submit:
            if new_password != confirm_password:
                st.error("Les nouveaux mots de passe ne correspondent pas")
            elif not current_password or not new_password:
                st.error("Tous les champs sont obligatoires")
            else:
                success, message = auth.change_password(user_info["username"], current_password, new_password)
                if success:
                    st.success(message)
                else:
                    st.error(message)

def requires_auth(func):
    """Décorateur pour protéger les pages qui nécessitent une authentification"""
    def wrapper(*args, **kwargs):
        if "auth_token" not in st.session_state:
            login_form()
        else:
            auth = Authentication()
            if not auth.is_authenticated(st.session_state["auth_token"]):
                login_form()
            else:
                # L'utilisateur est authentifié, afficher le bouton de déconnexion
                user_info = auth.get_user_info(st.session_state["auth_token"])
                st.sidebar.markdown(f"**Connecté en tant que : {user_info['name']}**")
                
                # Générer une clé unique basée sur l'emplacement du bouton
                caller_frame = inspect.currentframe().f_back
                caller_info = f"{caller_frame.f_code.co_filename}_{caller_frame.f_lineno}"
                logout_key = f"logout_button_{hash(caller_info) % 10000}"
                
                st.sidebar.button("Se déconnecter", on_click=logout, key=logout_key)
                
                # Exécuter la fonction protégée
                return func(*args, **kwargs)
    
    return wrapper

def requires_admin(func):
    """Décorateur pour protéger les pages qui nécessitent des droits d'administrateur"""
    def wrapper(*args, **kwargs):
        if "auth_token" not in st.session_state:
            login_form()
            return
        
        auth = Authentication()
        if not auth.is_authenticated(st.session_state["auth_token"]):
            login_form()
            return
        
        user_info = auth.get_user_info(st.session_state["auth_token"])
        if user_info["role"] != "admin":
            st.error("Accès interdit. Vous n'avez pas les droits administrateur nécessaires.")
            return
        
        # L'utilisateur est admin, afficher le bouton de déconnexion
        st.sidebar.markdown(f"**Connecté en tant que : {user_info['name']} (Admin)**")
        
        # Générer une clé unique basée sur l'emplacement du bouton
        caller_frame = inspect.currentframe().f_back
        caller_info = f"{caller_frame.f_code.co_filename}_{caller_frame.f_lineno}"
        logout_key = f"logout_button_admin_{hash(caller_info) % 10000}"
        
        st.sidebar.button("Se déconnecter", on_click=logout, key=logout_key)
        
        # Exécuter la fonction protégée
        return func(*args, **kwargs)
    
    return wrapper

# Ajoutez ces imports pour la compatibilité avec le panneau admin
import pandas as pd
