ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:3.15
FROM ${BUILD_FROM}

# Installation des dépendances
RUN apk add --no-cache \
    python3 \
    py3-pip \
    nginx \
    nodejs \
    npm

# Installation des dépendances Python
RUN pip3 install --no-cache-dir \
    ftplib \
    flask \
    flask-cors \
    schedule \
    pytz

# Copie des fichiers
COPY rootfs /
COPY run.sh /
RUN chmod a+x /run.sh

# Construction de l'interface web
WORKDIR /usr/share/ftpbrowser
RUN npm install

# Configuration de S6-Overlay
ENTRYPOINT ["/init"]
CMD ["/run.sh"]

# Labels
LABEL \
    io.hass.name="FTP Browser" \
    io.hass.description="Navigateur de fichiers FTP avec fonctionnalités de partage programmable" \
    io.hass.version="${BUILD_VERSION}" \
    io.hass.type="addon" \
    io.hass.arch="${BUILD_ARCH}"


