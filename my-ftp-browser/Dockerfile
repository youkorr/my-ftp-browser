ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:3.18
FROM ${BUILD_FROM}

# Mettre à jour l'index des paquets
RUN apk update

# Installer les dépendances une par une pour mieux identifier d'éventuels problèmes
RUN apk add --no-cache python3
RUN apk add --no-cache py3-pip
RUN apk add --no-cache python3-dev
RUN apk add --no-cache build-base
# Essayer d'installer vsftpd ou utiliser pyftpdlib comme alternative
# Si vsftpd ne fonctionne pas, vous pouvez commenter cette ligne
# puisque vous utilisez déjà pyftpdlib
RUN apk add --no-cache vsftpd || echo "Utilisation de pyftpdlib comme alternative"

# Copier les fichiers
COPY rootfs /

# Installer les dépendances Python
RUN pip3 install --no-cache-dir flask pyftpdlib

# Créer le répertoire pour l'application
RUN mkdir -p /usr/share/ftpbrowser

# Rendre les scripts exécutables
RUN chmod a+x /usr/bin/run.sh
RUN chmod a+x /etc/services.d/ftp-server/run

# Exposer les ports
EXPOSE 8099 21

# Exécuter le script de démarrage
CMD [ "/usr/bin/run.sh" ]

LABEL \
    io.hass.version="1.0.0" \
    io.hass.type="addon" \
    io.hass.arch="armhf|armv7|aarch64|amd64|i386"







