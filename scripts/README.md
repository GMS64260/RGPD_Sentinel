# Scripts pour RGPD Sentinel

Ce dossier contient des scripts utilitaires pour faciliter l'installation et la gestion de RGPD Sentinel.

## Script de gestion des partages Windows

Le script `mount_shares.sh` permet de gérer facilement les montages des partages Windows sur votre serveur Debian.

### Installation

```bash
# Rendre le script exécutable
chmod +x mount_shares.sh
```

### Utilisation

Le script peut être utilisé en mode interactif ou avec des arguments en ligne de commande.

#### Mode interactif

```bash
sudo ./mount_shares.sh
```

Cela affichera un menu interactif avec les options suivantes:
- Lister les partages disponibles
- Monter un partage spécifique
- Démonter un partage spécifique
- Démonter tous les partages
- Configurer les montages automatiques
- Vérifier les montages actuels

#### Mode ligne de commande

```bash
# Lister les partages disponibles
sudo ./mount_shares.sh list

# Monter un partage spécifique
sudo ./mount_shares.sh mount NomDuPartage

# Démonter un partage spécifique
sudo ./mount_shares.sh unmount NomDuPartage

# Démonter tous les partages
sudo ./mount_shares.sh unmount-all

# Configurer des montages automatiques pour plusieurs partages
sudo ./mount_shares.sh setup Partage1 Partage2 Partage3

# Spécifiquement pour démonter le partage actuel (Castilla)
sudo ./mount_shares.sh unmount-castilla
```

### Connexion aux partages depuis RGPD Sentinel

Une fois les partages montés, vous pouvez y accéder depuis l'interface web de RGPD Sentinel en spécifiant le chemin `/mnt/NomDuPartage` dans l'option "Analyse de dossier".

### Automatisation du montage

Le script peut configurer les partages pour qu'ils soient montés automatiquement au démarrage du système. Utilisez l'option "Configurer les montages automatiques" dans le menu interactif ou la commande `setup` en ligne de commande.
