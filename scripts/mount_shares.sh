#!/bin/bash
# Script pour monter et démonter les partages Windows sur le serveur RGPD_Sentinel
# Auteur: Claude
# Date: 2025-03-04

# Vérification des privilèges root
if [ "$EUID" -ne 0 ]; then
  echo "Ce script doit être exécuté en tant que root"
  exit 1
fi

# Configuration
CREDENTIALS_FILE="/root/.smbcredentials"
SERVER_IP="10.0.0.25"
MOUNT_BASE="/mnt"
RGPD_USER="rgpdsentinel"
RGPD_GROUP="rgpdsentinel"

# Vérification que le fichier d'identifiants existe
if [ ! -f "$CREDENTIALS_FILE" ]; then
  echo "Fichier d'identifiants non trouvé : $CREDENTIALS_FILE"
  echo "Création du fichier..."
  read -p "Nom d'utilisateur: " username
  read -sp "Mot de passe: " password
  echo ""
  read -p "Domaine (laissez vide si non applicable): " domain
  
  echo "username=$username" > $CREDENTIALS_FILE
  echo "password=$password" >> $CREDENTIALS_FILE
  if [ ! -z "$domain" ]; then
    echo "domain=$domain" >> $CREDENTIALS_FILE
  fi
  
  chmod 600 $CREDENTIALS_FILE
  echo "Fichier d'identifiants créé."
fi

# Fonction pour vérifier si un partage est monté
is_mounted() {
  mount | grep -q "$1"
  return $?
}

# Fonction pour démonter un partage
unmount_share() {
  local mount_point="$1"
  if is_mounted "$mount_point"; then
    echo "Démontage de $mount_point..."
    umount -f "$mount_point"
    if [ $? -eq 0 ]; then
      echo "Partage démonté avec succès."
    else
      echo "Erreur lors du démontage de $mount_point."
      return 1
    fi
  else
    echo "$mount_point n'est pas monté."
  fi
  return 0
}

# Fonction pour monter un partage
mount_share() {
  local share_name="$1"
  local mount_point="$MOUNT_BASE/$share_name"
  
  # Création du point de montage s'il n'existe pas
  if [ ! -d "$mount_point" ]; then
    echo "Création du point de montage $mount_point..."
    mkdir -p "$mount_point"
  fi
  
  # Montage du partage
  echo "Montage de $share_name sur $mount_point..."
  mount -t cifs "//$SERVER_IP/$share_name" "$mount_point" -o credentials=$CREDENTIALS_FILE,iocharset=utf8,vers=2.0,uid=$RGPD_USER,gid=$RGPD_GROUP
  
  if [ $? -eq 0 ]; then
    echo "Partage $share_name monté avec succès sur $mount_point."
  else
    echo "Erreur lors du montage de $share_name."
    return 1
  fi
  
  return 0
}

# Fonction pour lister les partages disponibles
list_shares() {
  echo "Tentative de liste des partages disponibles sur $SERVER_IP..."
  if [ -f "/usr/bin/smbclient" ]; then
    smbclient -L "//$SERVER_IP" -U "$(grep username $CREDENTIALS_FILE | cut -d= -f2)%$(grep password $CREDENTIALS_FILE | cut -d= -f2)"
  else
    echo "smbclient n'est pas installé. Installation en cours..."
    apt-get update && apt-get install -y smbclient
    if [ $? -eq 0 ]; then
      smbclient -L "//$SERVER_IP" -U "$(grep username $CREDENTIALS_FILE | cut -d= -f2)%$(grep password $CREDENTIALS_FILE | cut -d= -f2)"
    else
      echo "Impossible d'installer smbclient."
      return 1
    fi
  fi
}

# Fonction pour configurer les montages automatiques
configure_automount() {
  local shares=("$@")
  
  # Vérifier si des entrées existent déjà dans fstab
  grep -q "$SERVER_IP" /etc/fstab
  local fstab_has_entries=$?
  
  if [ $fstab_has_entries -eq 0 ]; then
    echo "Des entrées de partage existent déjà dans /etc/fstab."
    read -p "Voulez-vous les remplacer? (o/n): " answer
    if [ "$answer" != "o" ]; then
      echo "Opération annulée."
      return 1
    fi
    
    # Supprimer les anciennes entrées
    sed -i "/\/\/$SERVER_IP\//d" /etc/fstab
  fi
  
  # Ajouter les nouvelles entrées
  echo "Configuration des montages automatiques..."
  for share in "${shares[@]}"; do
    echo "//$SERVER_IP/$share $MOUNT_BASE/$share cifs credentials=$CREDENTIALS_FILE,iocharset=utf8,vers=2.0,uid=$RGPD_USER,gid=$RGPD_GROUP 0 0" >> /etc/fstab
    echo "Ajout du partage $share dans fstab."
  done
  
  # Recharger systemd
  systemctl daemon-reload
  echo "Configuration terminée. Utilisez 'mount -a' pour monter tous les partages."
}

# Menu principal
show_menu() {
  echo "=========================================================="
  echo "         GESTIONNAIRE DE PARTAGES WINDOWS POUR RGPD       "
  echo "=========================================================="
  echo "1. Lister les partages disponibles"
  echo "2. Monter un partage spécifique"
  echo "3. Démonter un partage spécifique"
  echo "4. Démonter tous les partages"
  echo "5. Configurer les montages automatiques"
  echo "6. Vérifier les montages actuels"
  echo "7. Quitter"
  echo "=========================================================="
  read -p "Choisissez une option: " choice
  
  case $choice in
    1)
      list_shares
      ;;
    2)
      read -p "Nom du partage à monter: " share_name
      mount_share "$share_name"
      ;;
    3)
      read -p "Nom du partage à démonter: " share_name
      unmount_share "$MOUNT_BASE/$share_name"
      ;;
    4)
      echo "Démontage de tous les partages CIFS..."
      umount -a -t cifs
      echo "Opération terminée."
      ;;
    5)
      echo "Saisissez les noms des partages à configurer (séparés par des espaces):"
      read -a share_list
      configure_automount "${share_list[@]}"
      ;;
    6)
      echo "Partages actuellement montés:"
      mount | grep cifs
      ;;
    7)
      exit 0
      ;;
    *)
      echo "Option invalide!"
      ;;
  esac
}

# Action immédiate pour éjecter Castilla
if [ "$1" == "unmount-castilla" ]; then
  echo "Démontage du partage Castilla..."
  unmount_share "/mnt/srv-fichiers"
  exit 0
fi

# Si aucun argument n'est passé, afficher le menu
if [ $# -eq 0 ]; then
  while true; do
    show_menu
    echo ""
    read -p "Appuyez sur Entrée pour continuer..."
    clear
  done
fi

# Traitement des arguments
case "$1" in
  list)
    list_shares
    ;;
  mount)
    if [ -z "$2" ]; then
      echo "Erreur: Vous devez spécifier un nom de partage à monter."
      exit 1
    fi
    mount_share "$2"
    ;;
  unmount|umount)
    if [ -z "$2" ]; then
      echo "Erreur: Vous devez spécifier un nom de partage à démonter."
      exit 1
    fi
    unmount_share "$MOUNT_BASE/$2"
    ;;
  unmount-all|umount-all)
    echo "Démontage de tous les partages CIFS..."
    umount -a -t cifs
    echo "Opération terminée."
    ;;
  setup)
    shift
    if [ $# -eq 0 ]; then
      echo "Erreur: Vous devez spécifier au moins un nom de partage."
      exit 1
    fi
    configure_automount "$@"
    ;;
  *)
    echo "Usage: $0 [list|mount SHARE|unmount SHARE|unmount-all|setup SHARE1 SHARE2...]"
    echo "       $0 (sans arguments pour le mode interactif)"
    exit 1
    ;;
esac

exit 0
