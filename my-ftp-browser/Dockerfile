ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:3.18
FROM ${BUILD_FROM}

# Installer les certificats pour éviter les erreurs SSL
RUN apk add --no-cache ca-certificates

# Mettre à jour les certificats (facultatif mais recommandé)
RUN update-ca-certificates

# Installer les dépendances système
RUN apk add --no-cache \
    python3 \
    py3-pip \
    python3-dev \
    build-base \
    vsftpd

# Copier les fichiers nécessaires dans le conteneur
COPY rootfs /

# Installer les dépendances Python
RUN pip3 install --no-cache-dir flask pyftpdlib

# Créer le répertoire pour l'application
RUN mkdir -p /usr/share/ftpbrowser

# Rendre les scripts exécutables
RUN chmod a+x /usr/bin/run.sh
RUN chmod a+x /etc/services.d/ftp-server/run

# Exposer les ports nécessaires
EXPOSE 8099 21

# Script de démarrage
CMD [ "/usr/bin/run.sh" ]

# Metadata pour Home Assistant
LABEL \
    io.hass.version="1.0.0" \
    io.hass.type="addon" \
    io.hass.arch="armhf|armv7|aarch64|amd64|i386"





