ARG BUILD_FROM=ghcr.io/hassio-addons/base:13.0.0

FROM ${BUILD_FROM}

# Installation des dépendances système
RUN apk add --no-cache \
    python3 \
    py3-pip \
    py3-wheel \
    py3-setuptools \
    nginx \
    curl \
    tzdata

# Installer les dépendances Python en séparant chaque commande pour une meilleure visibilité des erreurs
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir Flask==2.0.1 && \
    pip3 install --no-cache-dir requests==2.26.0 && \
    pip3 install --no-cache-dir PyJWT==2.1.0 && \
    pip3 install --no-cache-dir python-dateutil==2.8.2

# Copie des fichiers dans l'image
COPY rootfs /
COPY run.sh /

# Rendre les scripts exécutables
RUN chmod a+x /run.sh && \
    find /etc/services.d -type f -name run -exec chmod a+x {} \;

# Port d'exposition pour l'interface web
EXPOSE 8099

# S6-Overlay comme point d'entrée
ENTRYPOINT ["/init"]

# Labels pour la documentation
LABEL \
    io.hass.name="FTP Browser & Media Server" \
    io.hass.description="Access FTP servers with a user-friendly web interface, share files, and stream media" \
    io.hass.type="addon" \
    io.hass.version="${BUILD_VERSION}" \
    maintainer="Your Name <your.email@example.com>"










