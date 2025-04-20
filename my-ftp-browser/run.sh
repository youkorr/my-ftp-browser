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

# Débogage
bashio::log.info "------------------------------------"
bashio::log.info "Vérification des fichiers de configuration:"
ls -la /etc/ftpbrowser/
bashio::log.info "------------------------------------"
bashio::log.info "Vérification des services S6:"
ls -la /etc/services.d/
bashio::log.info "------------------------------------"
bashio::log.info "Vérification des services FTP-Server:"
ls -la /etc/services.d/ftp-server/
bashio::log.info "------------------------------------"

# Le processus S6 va démarrer automatiquement les services









