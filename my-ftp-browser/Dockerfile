ARG BUILD_FROM
FROM $BUILD_FROM

# Install system dependencies first
RUN apk update && apk add --no-cache \
    nginx \
    python3 \
    py3-pip \
    tzdata

# Install Python packages using pip
RUN pip3 install --no-cache-dir \
    flask \
    ftputil \
    python-dotenv \
    requests \
    werkzeug \
    click \
    itsdangerous \
    jinja2 \
    markupsafe \
    python-dateutil \
    pyjwt

# Copy root filesystem
COPY rootfs /

# Configure nginx
RUN rm -f /etc/nginx/http.d/default.conf && \
    mkdir -p /run/nginx && \
    chown -R nginx:nginx /run/nginx

# Set permissions
RUN chmod a+x /etc/services.d/*/* /etc/cont-init.d/*

WORKDIR /usr/share/ftpbrowser
EXPOSE 80








