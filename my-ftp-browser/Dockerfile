ARG BUILD_FROM=ghcr.io/hassio-addons/base:13.0.0
FROM ${BUILD_FROM}

# Mise à jour des dépôts et installation des packages de base
RUN apk update && \
    apk upgrade && \
    apk add --no-cache \
        python3 \
        py3-pip \
        nginx \
        tzdata \
        build-base \
        python3-dev

# Installation des packages Python via pip pour assurer la compatibilité
RUN pip3 install --no-cache-dir \
    Flask==2.0.1 \
    requests==2.26.0 \
    Werkzeug \
    click \
    itsdangerous \
    Jinja2 \
    MarkupSafe \
    python-dateutil==2.8.2 \
    PyJWT==2.1.0

# Nettoyage des outils de compilation pour réduire la taille de l'image
RUN apk del build-base python3-dev

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







