#!/usr/bin/with-contenv bashio
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
LOG_LEVEL=$(bashio::config 'log_level')
bashio::log.level "$LOG_LEVEL"

bashio::log.info "Configuration de l'addon FTP Browser & Media Server"

# Timezone configuration
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

# Configuration NGINX pour l'ingress si nécessaire
FB_BASEURL=$(bashio::addon.ingress_entry)
export FB_BASEURL
declare ADDON_PROTOCOL=http

# Generate Ingress configuration
ingress_port=$(bashio::addon.ingress_port)
ingress_interface=$(bashio::addon.ip_address)
sed -i "s|%%port%%|${ingress_port}|g" /etc/nginx/servers/ingress.conf
sed -i "s|%%interface%%|${ingress_interface}|g" /etc/nginx/servers/ingress.conf
sed -i "s|%%subpath%%|${FB_BASEURL}/|g" /etc/nginx/servers/ingress.conf

# Créer le fichier de log nginx si nécessaire
mkdir -p /var/log/nginx && touch /var/log/nginx/error.log

bashio::log.info "Configuration terminée"

