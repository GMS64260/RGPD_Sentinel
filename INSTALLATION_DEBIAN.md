# Tutoriel d'installation de RGPD Sentinel sur Debian 12

Ce guide vous explique comment installer et configurer RGPD Sentinel, un outil d'analyse qui détecte automatiquement les données personnelles dans vos documents pour faciliter la mise en conformité RGPD.

## Prérequis

- Un serveur ou une machine avec Debian 12 installé
- Accès root ou droits sudo
- Connexion internet

## 1. Mise à jour du système

Commencez par mettre à jour votre système Debian :

```bash
sudo apt update
sudo apt upgrade -y
```

## 2. Installation des dépendances système

Installez les packages système nécessaires :

```bash
sudo apt install -y python3 python3-pip python3-venv git build-essential python3-dev libpoppler-cpp-dev pkg-config
```

## 3. Clonage du dépôt Git

Clonez le dépôt RGPD Sentinel dans votre répertoire de choix :

```bash
cd /opt
sudo git clone https://github.com/GMS64260/RGPD_Sentinel.git
sudo chown -R $USER:$USER RGPD_Sentinel
cd RGPD_Sentinel
```

## 4. Création d'un environnement virtuel Python

Pour éviter les conflits de dépendances, créez un environnement virtuel Python :

```bash
python3 -m venv venv
source venv/bin/activate
```

## 5. Installation des dépendances Python

Mettez à jour pip et installez les dépendances requises :

```bash
pip install --upgrade pip wheel setuptools
pip install -r requirements.txt
```

## 6. Installation du modèle français pour Spacy

RGPD Sentinel utilise le modèle français de Spacy pour la détection d'entités nommées :

```bash
python -m spacy download fr_core_news_md
```

## 7. Configuration des dossiers nécessaires

Assurez-vous que les dossiers requis par l'application existent et ont les bonnes permissions :

```bash
mkdir -p logs saved_analyses
chmod 755 logs saved_analyses
```

## 8. Création d'un utilisateur de service (Optionnel mais recommandé)

Pour une installation plus sécurisée, vous pouvez créer un utilisateur de service dédié :

```bash
sudo useradd -r -s /bin/false rgpdsentinel
sudo chown -R rgpdsentinel:rgpdsentinel /opt/RGPD_Sentinel
```

## 9. Configuration du service systemd (Pour démarrage automatique)

Créez un fichier de service systemd pour lancer l'application automatiquement :

```bash
sudo nano /etc/systemd/system/rgpdsentinel.service
```

Ajoutez le contenu suivant :

```ini
[Unit]
Description=RGPD Sentinel Service
After=network.target

[Service]
User=rgpdsentinel
WorkingDirectory=/opt/RGPD_Sentinel
ExecStart=/opt/RGPD_Sentinel/venv/bin/streamlit run app.py --server.port=8501 --server.address=0.0.0.0
Restart=always
RestartSec=5
Environment="PATH=/opt/RGPD_Sentinel/venv/bin"

[Install]
WantedBy=multi-user.target
```

Activez et démarrez le service :

```bash
sudo systemctl daemon-reload
sudo systemctl enable rgpdsentinel
sudo systemctl start rgpdsentinel
```

## 10. Configuration du pare-feu (optionnel mais recommandé)

Si vous souhaitez accéder à l'application depuis l'extérieur, configurez le pare-feu pour autoriser le port 8501 :

```bash
sudo apt install -y ufw
sudo ufw allow 8501/tcp
sudo ufw enable
```

## 11. Configuration d'un proxy inverse avec Nginx (optionnel mais recommandé)

Pour une configuration plus robuste en production, vous pouvez configurer Nginx comme proxy inverse :

```bash
sudo apt install -y nginx

# Créez une configuration Nginx pour RGPD Sentinel
sudo nano /etc/nginx/sites-available/rgpdsentinel
```

Ajoutez le contenu suivant :

```nginx
server {
    listen 80;
    server_name votredomaine.com;  # Remplacez par votre nom de domaine

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Host $host;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }
}
```

Activez la configuration et redémarrez Nginx :

```bash
sudo ln -s /etc/nginx/sites-available/rgpdsentinel /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## 12. Accès à l'application

Vous pouvez maintenant accéder à RGPD Sentinel :

- Si vous utilisez l'application directement : http://adresse_ip_du_serveur:8501
- Si vous utilisez Nginx comme proxy : http://votredomaine.com

## 13. Mise à jour de l'application

Pour mettre à jour l'application avec les dernières modifications du dépôt GitHub :

```bash
cd /opt/RGPD_Sentinel
sudo systemctl stop rgpdsentinel
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl start rgpdsentinel
```

## 14. Dépannage

### Problèmes courants

1. **L'application ne démarre pas** :
   - Vérifiez les logs : `sudo journalctl -u rgpdsentinel`
   - Vérifiez que tous les packages sont correctement installés

2. **Erreurs liées à Spacy** :
   - Assurez-vous que le modèle français est correctement installé : `python -m spacy validate`

3. **Problèmes de permissions** :
   - Vérifiez que l'utilisateur du service a accès en lecture/écriture aux dossiers de l'application

4. **Port déjà utilisé** :
   - Modifiez le port dans le fichier de service systemd si le port 8501 est déjà utilisé

## 15. Personnalisation

Vous pouvez personnaliser l'application en modifiant les fichiers de configuration dans le dossier `config/`.

### Exclusion de noms ou de structures organisationnelles

Modifiez le fichier `config/exclusion_lists.py` pour ajouter des noms ou des structures à exclure de la détection.

## Conclusion

RGPD Sentinel est maintenant installé et configuré sur votre serveur Debian 12. Vous pouvez commencer à analyser vos documents pour détecter les données personnelles et faciliter votre conformité RGPD.

Pour toute question ou problème d'installation, n'hésitez pas à ouvrir une issue sur le dépôt GitHub : https://github.com/GMS64260/RGPD_Sentinel