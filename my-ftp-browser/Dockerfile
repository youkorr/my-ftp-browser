# Installation des dépendances système
RUN apk add --no-cache \
    python3 \
    py3-pip \
    py3-wheel \
    py3-setuptools \
    nginx \
    curl \
    tzdata

# Mise à jour de pip et installation des dépendances Python
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir \
        Flask==2.0.1 \
        requests==2.26.0 \
        PyJWT==2.1.0 \
        python-dateutil==2.8.2 \
        werkzeug==2.0.3

# Copie des fichiers de configuration et scripts
COPY rootfs/ /

# Script d'exécution principal
COPY run.sh /run.sh
RUN chmod +x /run.sh && \
    find /etc/services.d -type f -name run -exec chmod +x {} \;

# Port exposé pour l'interface web
EXPOSE 8099

# Point d'entrée supervisé par S6
ENTRYPOINT ["/init"]

# Métadonnées
LABEL \
    io.hass.name="FTP Browser & Media Server" \
    io.hass.description="Access FTP servers with a user-friendly web interface, share files, and stream media" \
    io.hass.type="addon" \
    io.hass.version="${BUILD_VERSION}" \
    maintainer="Your Name <your.email@example.com>"
