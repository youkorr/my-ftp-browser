#!/usr/bin/with-contenv bashio

# Obtenir la configuration depuis le fichier JSON
CONFIG_PATH=/data/options.json
FTP_USER=$(bashio::config 'username')
FTP_PASS=$(bashio::config 'password')
FTP_PORT=$(bashio::config 'port')
SSL=$(bashio::config 'ssl')
PASSIVE_MODE=$(bashio::config 'passive')
ALLOW_UPLOAD=$(bashio::config 'allow_upload')
ALLOW_DELETE=$(bashio::config 'allow_delete')

# Configurer les variables d'environnement pour l'API Python
export FTP_USER=$FTP_USER
export FTP_PASS=$FTP_PASS
export FTP_PORT=$FTP_PORT
export SSL=$SSL
export PASSIVE_MODE=$PASSIVE_MODE
export ALLOW_UPLOAD=$ALLOW_UPLOAD
export ALLOW_DELETE=$ALLOW_DELETE

# Créer les répertoires nécessaires
mkdir -p /data/ftp-browser
mkdir -p /data/ftp-browser/shares
mkdir -p /data/ftp-browser/temp

# Afficher les informations de démarrage
bashio::log.info "Démarrage du serveur FTP..."
bashio::log.info "Port FTP: $FTP_PORT"
bashio::log.info "SSL activé: $SSL"
bashio::log.info "Mode passif: $PASSIVE_MODE"
bashio::log.info "Upload autorisé: $ALLOW_UPLOAD"
bashio::log.info "Suppression autorisée: $ALLOW_DELETE"

# Démarrer le serveur API Python en arrière-plan
bashio::log.info "Démarrage de l'API serveur..."
cd /usr/share/ftpbrowser/api || { bashio::log.error "Répertoire API introuvable"; exit 1; }
python3 server.py &
SERVER_PID=$!

# Vérifier si le processus de l'API a démarré correctement
if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    bashio::log.error "Échec du démarrage de l'API serveur."
    exit 1
fi

#!/usr/bin/with-contenv bash

exec /run.sh








