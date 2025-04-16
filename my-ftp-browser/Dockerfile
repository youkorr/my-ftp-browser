ARG BUILD_FROM=ghcr.io/hassio-addons/base:13.0.0
FROM ${BUILD_FROM}

# Installation des dépendances précompilées Alpine
RUN apk add --no-cache \
    python3 \
    py3-flask \
    py3-requests \
    nginx \
    tzdata

# Copier tous les fichiers dans l'image
COPY rootfs /

# Rendre les scripts S6 exécutables
RUN chmod a+x /etc/s6-overlay/s6-rc.d/*/run \
    && chmod a+x /etc/s6-overlay/s6-rc.d/*/finish \
    && chmod a+x /etc/s6-overlay/scripts/*

# Créer un utilisateur non-root pour accroître la sécurité
# RUN adduser -D -H -s /sbin/nologin ftpuser

# Préparer le dossier web
RUN mkdir -p /usr/share/ftpbrowser/api /var/www/localhost/htdocs

# Exposer le port utilisé par NGINX
EXPOSE 8099

# Point d'entrée S6 Overlay
ENTRYPOINT ["/init"]








