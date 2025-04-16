FROM python:3.9-alpine

# Installer les dépendances système
RUN apk add --no-cache nginx supervisor lftp

# Créer les répertoires
RUN mkdir -p /app/ftpbrowser/api /app/ftpbrowser/css /app/ftpbrowser/js /var/log/nginx /run/nginx

# Installer les packages Python
RUN pip install --no-cache-dir flask requests

# Copier les fichiers
COPY rootfs/ /

# Permissions des fichiers
RUN chmod +x /app/ftpbrowser/api/server.py

# Configurer Supervisor
COPY supervisor.conf /etc/supervisor/conf.d/supervisord.conf

# Exposer le port
EXPOSE 8099

# Point d'entrée
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]







