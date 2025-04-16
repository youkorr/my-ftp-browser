FROM linuxserver/nginx:latest

# Installer les dépendances
RUN apk add --no-cache \
    python3 \
    py3-pip \
    lftp \
    curl

# Installer les packages Python nécessaires
RUN pip3 install flask requests

# Créer les répertoires nécessaires
RUN mkdir -p /app/ftpbrowser/api /config

# Copier les fichiers 
COPY rootfs/ /

# Créer l'utilisateur ftpbrowser
RUN adduser -D -H ftpbrowser

# Permissions
RUN chmod +x /etc/s6-overlay/s6-rc.d/*/run \
    && chmod +x /etc/s6-overlay/s6-rc.d/*/finish \
    && chmod +x /app/ftpbrowser/api/server.py

# Exposer le port
EXPOSE 8099

# Démarrer avec S6
ENTRYPOINT ["/init"]



