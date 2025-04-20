ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:3.18
FROM ${BUILD_FROM}

# Installer les dépendances
RUN apk add --no-cache \
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

# Rendre le script d'exécution exécutable
RUN chmod a+x /usr/bin/run.sh
RUN chmod a+x /etc/services.d/ftp-server/run

# Exposer le port
EXPOSE 8099 21

# Exécuter le script de démarrage
CMD [ "/usr/bin/run.sh" ]

LABEL \
    io.hass.version="1.0.0" \
    io.hass.type="addon" \
    io.hass.arch="armhf|armv7|aarch64|amd64|i386"



