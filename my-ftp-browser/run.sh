#!/usr/bin/with-contenv bashio
set -e

# Récupérer la configuration
CONFIG_PATH=/data/options.json
SERVER_CONFIG=/etc/ftpbrowser/server.json

# Créer les répertoires nécessaires
mkdir -p /etc/ftpbrowser
mkdir -p /data/ftpbrowser
mkdir -p /data/ftpbrowser/shares

# Extraire les configurations pour l'API Python (si le fichier existe)
if [ -f "$CONFIG_PATH" ]; then
  jq '.' $CONFIG_PATH > $SERVER_CONFIG
else
  echo '{"ftp_servers":[]}' > $SERVER_CONFIG
fi

# Définir le niveau de journalisation
LOG_LEVEL=$(jq --raw-output '.log_level // "info"' $CONFIG_PATH)
bashio::log.info "Starting FTP Browser Add-on with log level: $LOG_LEVEL"

# Ne pas quitter ce script - S6 a besoin qu'il reste en cours d'exécution
exec sleep infinity

