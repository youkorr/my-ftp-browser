ARG BUILD_FROM=ghcr.io/hassio-addons/base:13.0.0
FROM ${BUILD_FROM}

# Installation des dépendances système
RUN apk add --no-cache \
    python3 \
    py3-pip \
    nginx \
    tzdata

# Installer les dépendances Python en une seule couche
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir \
    Flask==2.0.1 \
    Werkzeug==2.0.3 \
    requests==2.26.0 \
    PyJWT==2.1.0 \
    python-dateutil==2.8.2

# Copie des fichiers dans l'image
COPY rootfs /
COPY run.sh /

# Modifier les permissions pour les scripts
RUN chmod a+x \
    /run.sh \
    /etc/services.d/nginx/run \
    /etc/services.d/ftp-server/run \
    /usr/share/ftpbrowser/api/server.py

# Port d'exposition pour l'interface web
EXPOSE 8145

# S6-Overlay comme point d'entrée
ENTRYPOINT ["/init"]

# Labels pour la documentation
LABEL \
    io.hass.name="FTP Browser & Media Server" \
    io.hass.description="Access FTP servers with a user-friendly web interface, share files, and stream media" \
    io.hass.type="addon" \
    io.hass.version="${BUILD_VERSION}" \
    maintainer="Your Name <your.email@example.com>"


