ARG BUILD_FROM=ghcr.io/hassio-addons/base:13.0.0

FROM ${BUILD_FROM}

# Installation des dépendances précompilées Alpine
RUN apk add --no-cache \
    python3 \
    py3-flask \
    py3-requests \
    py3-werkzeug \
    py3-click \
    py3-itsdangerous \
    py3-jinja2 \
    py3-markupsafe \
    py3-dateutil \
    nginx \
    tzdata

# Copie des fichiers
COPY rootfs /
COPY run.sh /

# Rendre les scripts exécutables
RUN chmod a+x /run.sh && \
    find /etc/services.d -type f -name run -exec chmod a+x {} \; && \
    find /etc/services.d -type f -name finish -exec chmod a+x {} \;

# Créer les dossiers nécessaires
RUN mkdir -p /etc/ftpbrowser /data/ftpbrowser/shares

# Port d'exposition
EXPOSE 8099

# S6-Overlay comme point d'entrée
ENTRYPOINT ["/init"]

# Labels
LABEL \
    io.hass.name="FTP Browser & Media Server" \
    io.hass.description="Access FTP servers with a user-friendly web interface" \
    io.hass.type="addon" \
    io.hass.version="${BUILD_VERSION}" \
    maintainer="Your Name <your.email@example.com>"








