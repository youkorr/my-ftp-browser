ARG BUILD_FROM=alpine:3.18
FROM ${BUILD_FROM}

# Fixes SSL and repo errors
RUN apk update && apk add --no-cache \
    ca-certificates \
    curl \
    python3 \
    py3-pip \
    python3-dev \
    build-base \
    vsftpd

# Met à jour les certificats
RUN update-ca-certificates

# Crée un utilisateur pour la sécurité (optionnel)
RUN adduser -D -H ftpuser

# Installe les dépendances Python
RUN pip3 install --no-cache-dir flask pyftpdlib

# Crée le répertoire pour les fichiers FTP
RUN mkdir -p /usr/share/ftpbrowser

# Copie les fichiers locaux
COPY rootfs /

# Rends les scripts exécutables
RUN chmod +x /usr/bin/run.sh
RUN chmod +x /etc/services.d/ftp-server/run

# Expose les ports HTTP et FTP
EXPOSE 8099 21

# Démarre le script principal
CMD [ "/usr/bin/run.sh" ]

# Metadata Home Assistant
LABEL \
    io.hass.version="1.0.0" \
    io.hass.type="addon" \
    io.hass.arch="armhf|armv7|aarch64|amd64|i386"







