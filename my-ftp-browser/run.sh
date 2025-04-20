#!/usr/bin/with-contenv bashio
set -e

# Récupérer la configuration
CONFIG_PATH=/data/options.json
SERVER_CONFIG=/etc/ftpbrowser/server.json

# Créer le répertoire de configuration s'il n'existe pas
mkdir -p /etc/ftpbrowser
mkdir -p /data/ftpbrowser
mkdir -p /data/ftpbrowser/shares

# Extraire les configurations pour l'API Python
jq '.' $CONFIG_PATH > $SERVER_CONFIG

# Définir le niveau de journalisation
LOG_LEVEL=$(jq --raw-output '.log_level' $CONFIG_PATH)
bashio::log.level "$LOG_LEVEL"

bashio::log.info "Démarrage de l'addon FTP Browser & Media Server"

# Démarrer S6 Overlay
exec /usr/bin/s6-svscan /etc/services.d










