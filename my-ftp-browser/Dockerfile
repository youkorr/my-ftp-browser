ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:3.18
FROM ${BUILD_FROM}

# Mise à jour agressive et ajout d'un miroir alternatif
RUN echo "https://dl-cdn.alpinelinux.org/alpine/v3.18/main" > /etc/apk/repositories && \
    echo "https://dl-cdn.alpinelinux.org/alpine/v3.18/community" >> /etc/apk/repositories && \
    apk update --no-cache && \
    apk upgrade --no-cache

# Installation des paquets essentiels uniquement
RUN apk add --no-cache python3 py3-pip

# Copier les fichiers
COPY rootfs /

# Installer les dépendances Python
# Notez que nous n'installons plus python3-dev et build-base
# Flask et pyftpdlib sont des packages Python purs qui n'ont généralement pas besoin de compilation
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







