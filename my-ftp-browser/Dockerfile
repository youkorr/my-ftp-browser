ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:3.18
FROM ${BUILD_FROM}

# Mettre à jour l'index des paquets et installer les dépendances
RUN apk update && \
    apk add --no-cache \
    python3 \
    py3-pip \
    python3-dev \
    build-base \
    vsftpd

# Copier les fichiers
COPY rootfs /

# Installer les dépendances Python
RUN pip3 install --no-cache-dir flask pyftpdlib

# Créer le répertoire pour l'application
RUN mkdir -p /usr/share/ftpbrowser

# Rendre les scripts d'exécution exécutables
RUN chmod a+x /usr/bin/run.sh && \
    chmod a+x /etc/services.d/ftp-server/run

# Exposer les ports
EXPOSE 8099 21

# Exécuter le script de démarrage
CMD [ "/usr/bin/run.sh" ]

LABEL \
    io.hass.version="1.0.0" \
    io.hass.type="addon" \
    io.hass.arch="armhf|armv7|aarch64|amd64|i386"


