# Utiliser l'image de base de Hass.io addons
FROM ghcr.io/hassio-addons/base:13.0.0

# Installer les dépendances et les modules Python nécessaires
RUN apk add --no-cache \
    python3 \
    py3-pip \
    nginx \
    netcat-openbsd

# Installer les packages Python nécessaires
RUN pip3 install --no-cache-dir flask

# Copier les fichiers de configuration et le script de démarrage
COPY rootfs/ /
COPY run.sh /

# Modifier les permissions pour les scripts
RUN chmod +x /run.sh && \
    chmod +x /etc/services.d/nginx/run && \
    chmod +x /etc/services.d/ftp-server/run && \
    chmod +x /usr/share/ftpbrowser/api/server.py

# Créer les répertoires nécessaires
RUN mkdir -p /etc/ftpbrowser /data/ftpbrowser/shares

# Exposer le port utilisé par l'application
EXPOSE 8099

# Point d'entrée du conteneur
ENTRYPOINT ["/init"]

