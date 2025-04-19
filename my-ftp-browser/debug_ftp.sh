#!/bin/bash
# Vérification des services
echo "=== Services en cours d'exécution ==="
ps aux | grep -E "nginx|python|ftp"

# Vérification des ports
echo -e "\n=== Ports en écoute ==="
netstat -tulnp | grep -E "8145|5000|21"

# Vérification des connexions
echo -e "\n=== Connexions actives ==="
ss -tulnp

# Vérification des erreurs Nginx
echo -e "\n=== Logs Nginx (dernières 20 lignes) ==="
tail -n 20 /var/log/nginx/error.log

# Vérification de l'application Python
echo -e "\n=== Logs Application (dernières 20 lignes) ==="
if [ -f "/usr/share/ftpbrowser/api/server.log" ]; then
    tail -n 20 /usr/share/ftpbrowser/api/server.log
else
    journalctl -u ftp-server --no-pager -n 20
fi

# Test de connexion FTP de base
echo -e "\n=== Test de connexion FTP locale ==="
timeout 5 ftp localhost 21 || echo "Échec de connexion FTP"

# Vérification des fichiers de configuration
echo -e "\n=== Contenu de server.json ==="
jq . /etc/ftpbrowser/server.json
