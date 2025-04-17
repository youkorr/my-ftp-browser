FROM ghcr.io/hassio-addons/base:13.0.0

# Installer les dépendances
RUN apk add --no-cache \
    python3 \
    py3-pip \
    nginx

# Installer les packages Python nécessaires
RUN pip3 install --no-cache-dir flask

# Copier les fichiers
COPY rootfs /
COPY run.sh /

# Permissions
RUN chmod +x /run.sh \
    && chmod +x /etc/services.d/nginx/run \
    && chmod +x /etc/services.d/ftp-server/run \
    && chmod +x /usr/share/ftpbrowser/api/server.py

# Créer les répertoires nécessaires
RUN mkdir -p /etc/ftpbrowser /data/ftpbrowser/shares

# Exposer le port
EXPOSE 8099

# Point d'entrée
ENTRYPOINT ["/init"]














