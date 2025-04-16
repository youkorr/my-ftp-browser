#!/usr/bin/env bashio
# shellcheck shell=bash
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
LOG_LEVEL=$(bashio::config.raw 'log_level')
bashio::log.level "$LOG_LEVEL"

bashio::log.info "Démarrage de l'addon FTP Browser & Media Server"

# Timezone configuration (comme dans l'exemple)
if bashio::config.has_value 'TZ'; then
    TIMEZONE=$(bashio::config 'TZ')
    bashio::log.info "Setting timezone to $TIMEZONE"
    if [ -f /usr/share/zoneinfo/"$TIMEZONE" ]; then
        ln -snf /usr/share/zoneinfo/"$TIMEZONE" /etc/localtime
        echo "$TIMEZONE" >/etc/timezone
    else
        bashio::log.fatal "$TIMEZONE not found, are you sure it is a valid timezone?"
    fi
fi

# Configuration NGINX si nécessaire
# (ajoutez ici la configuration NGINX similaire à l'exemple si nécessaire)

# Démarrer vos services ici
# Par exemple:
/chemin/vers/votre/application --option1 --option2 &

# Attendre que le service soit prêt
bashio::net.wait_for [PORT] localhost 900 || true
bashio::log.info "Started !"

# Exécuter NGINX ou un autre processus qui restera en premier plan
exec nginx

