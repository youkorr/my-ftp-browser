ARG BUILD_FROM=ghcr.io/hassio-addons/base:13.0.0
FROM ${BUILD_FROM}

# Set shell
SHELL ["/bin/ash", "-o", "pipefail", "-c"]

# Install dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip \
    nginx \
    curl \
    tzdata \
    vsftpd \
    && pip3 install --no-cache-dir \
    Flask==2.0.1 \
    requests==2.26.0 \
    PyJWT==2.1.0 \
    python-dateutil==2.8.2

# Copy root filesystem
COPY rootfs /

# Set working directory
WORKDIR /app

# Make scripts executable
RUN chmod a+x /run.sh \
    && chmod a+x /etc/services.d/ftp-server/run \
    && chmod a+x /etc/services.d/web/run

# Expose ports
EXPOSE 8099 21

# Health check
HEALTHCHECK --interval=30s --timeout=5s \
    CMD curl -f http://localhost:8099/health || exit 1

# Labels
LABEL \
    io.hass.name="FTP Browser & Media Server" \
    io.hass.description="Access FTP servers with a user-friendly web interface, share files, and stream media" \
    io.hass.type="addon" \
    io.hass.version="${BUILD_VERSION}" \
    maintainer="Your Name <your.email@example.com>"

# Start s6-overlay
ENTRYPOINT ["/init"]








