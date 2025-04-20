#!/command/with-contenv bashio
set -e

# Récupérer la configuration
CONFIG_PATH=/data/options.json
SERVER_CONFIG=/etc/ftpbrowser/server.json

# Créer les répertoires nécessaires
mkdir -p /etc/ftpbrowser
mkdir -p /data/ftpbrowser/shares

# Extraire les configurations pour l'API Python
jq '.' $CONFIG_PATH > $SERVER_CONFIG

# Informations de démarrage
bashio::log.info "Démarrage de l'addon FTP Browser"

# Démarrer le serveur Python directement
python3 /usr/share/ftpbrowser/api/server.py









