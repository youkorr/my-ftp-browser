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
    pip3 install --no-cache-dir Werkzeug==2.0.3 && \
    pip3 install --no-cache-dir requests==2.26.0 && \
    pip3 install --no-cache-dir PyJWT==2.1.0 && \
    pip3 install --no-cache-dir python-dateutil==2.8.2
# Copie des fichiers dans l'image
COPY rootfs /
COPY run.sh /
# Modifier les permissions pour les scripts
RUN chmod +x /run.sh \
    && chmod +x /etc/services.d/nginx/run \
    && chmod +x /etc/services.d/ftp-server/run \
    && chmod +x /usr/share/ftpbrowser/api/server.py  # Ajout des droits d'exécution
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


