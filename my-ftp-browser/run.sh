#!/usr/bin/with-contenv bashio
set -e

# Récupérer la configuration
CONFIG_PATH=/data/options.json
SERVER_CONFIG=/etc/ftpbrowser/server.json

# Créer les répertoires nécessaires
mkdir -p /etc/ftpbrowser
mkdir -p /data/ftpbrowser
mkdir -p /data/ftpbrowser/shares

# Charger la configuration pour l'API
if [ -f "$CONFIG_PATH" ]; then
  jq '.' "$CONFIG_PATH" > "$SERVER_CONFIG"
else
  echo '{"ftp_servers":[]}' > "$SERVER_CONFIG"
fi

# Définir le niveau de journalisation
LOG_LEVEL=$(jq --raw-output '.log_level // "info"' "$CONFIG_PATH")
bashio::log.info "Starting FTP Browser Add-on with log level: $LOG_LEVEL"

# Lancer le backend Flask en arrière-plan
bashio::log.info "Starting Flask backend..."
python3 /usr/src/app/server.py &

# Lancer Nginx en mode premier plan (nécessaire avec s6-overlay)
bashio::log.info "Starting Nginx server..."
exec nginx -g "daemon off;"







