#!/bin/bash
set -e

# Récupérer la configuration
CONFIG_PATH=/data/options.json
SERVER_CONFIG=/etc/ftpbrowser/server.json

# Créer les répertoires nécessaires
mkdir -p /etc/ftpbrowser
mkdir -p /data/ftpbrowser/shares

# Extraire les configurations pour l'API Python
if [ -f "$CONFIG_PATH" ]; then
    cp "$CONFIG_PATH" "$SERVER_CONFIG"
fi

# Démarrer le serveur Python
python3 /usr/share/ftpbrowser/api/server.py









