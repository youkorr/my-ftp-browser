ARG BUILD_FROM=ghcr.io/hassio-addons/base:13.0.0
FROM ${BUILD_FROM}

# Installation des dépendances
RUN apk add --no-cache \
    python3 \
    py3-pip \
    nginx \
    curl \
    tzdata

# Installation des packages Python
RUN pip3 install --no-cache-dir \
    Flask==2.0.1 \
    requests==2.26.0 \
    PyJWT==2.1.0 \
    python-dateutil==2.8.2

# Copie des fichiers dans l'image
COPY rootfs /

# Rendre les scripts exécutables
RUN chmod +x /etc/services.d/ftp-server/run \
    && chmod +x /run.sh

# Port d'exposition pour l'interface web
EXPOSE 8099

# Labels pour la documentation
LABEL \
    io.hass.name="FTP Browser & Media Server" \
    io.hass.description="Access FTP servers with a user-friendly web interface, share files, and stream media" \
    io.hass.type="addon" \
    io.hass.version="${BUILD_VERSION}" \
    maintainer="Your Name <your.email@example.com>"









