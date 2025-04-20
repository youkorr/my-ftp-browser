ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base-debian:bullseye
FROM ${BUILD_FROM}

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    build-essential \
    vsftpd \
 && apt-get clean

COPY rootfs /

RUN pip3 install --no-cache-dir flask pyftpdlib

RUN mkdir -p /usr/share/ftpbrowser
RUN chmod a+x /usr/bin/run.sh
RUN chmod a+x /etc/services.d/ftp-server/run

EXPOSE 8099 21

CMD [ "/usr/bin/run.sh" ]

LABEL \
    io.hass.version="1.0.0" \
    io.hass.type="addon" \
    io.hass.arch="armhf|armv7|aarch64|amd64|i386"






