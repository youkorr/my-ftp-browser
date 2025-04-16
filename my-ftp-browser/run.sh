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

# Installer Gunicorn si nécessaire
if ! command -v gunicorn &> /dev/null; then
  bashio::log.info "Gunicorn n'est pas installé, installation en cours..."
  pip3 install --no-cache-dir gunicorn
fi

# Démarrer Gunicorn pour l'API Flask (sur 0.0.0.0 pour écouter sur toutes les interfaces)
exec gunicorn --bind 0.0.0.0:5000 --workers 4 --access-logfile - --error-logfile - server:app






