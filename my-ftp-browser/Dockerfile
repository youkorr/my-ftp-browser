# Utiliser l'image de base de Hass.io addons
FROM ghcr.io/hassio-addons/base:13.0.0

# Installer les dépendances et les modules Python nécessaires
RUN apk add --no-cache \
    python3 \                     # Installation de Python 3
    py3-pip \                     # Installation de pip pour Python
    nginx \                        # Installation de NGINX
    netcat-openbsd                # Outil de diagnostic réseau (facultatif)

# Installer les packages Python nécessaires
RUN pip3 install --no-cache-dir flask  # Installation de Flask

# Copier les fichiers de configuration et le script de démarrage
COPY rootfs/ /  # Copier la structure du système dans le conteneur
COPY run.sh /   # Copier le script de démarrage

# Modifier les permissions pour les scripts
RUN chmod +x /run.sh \           # Autoriser l'exécution du script de démarrage
    && chmod +x /etc/services.d/nginx/run \  # Autoriser l'exécution du script NGINX
    && chmod +x /etc/services.d/ftp-server/run \  # Autoriser l'exécution du script du serveur FTP
    && chmod +x /usr/share/ftpbrowser/api/server.py  # Autoriser l'exécution du script de l'API FTP

# Créer les répertoires nécessaires
RUN mkdir -p /etc/ftpbrowser /data/ftpbrowser/shares  # Création des répertoires de configuration et de partages

# Exposer le port utilisé par l'application
EXPOSE 8099  # Exposition du port où l'application écoute

# Point d'entrée du conteneur
ENTRYPOINT ["/init"]  # Point d'entrée du conteneur

















