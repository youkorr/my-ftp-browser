ARG BUILD_FROM
FROM $BUILD_FROM

# Install dependencies
RUN apk add --no-cache \
    nginx \
    python3 \
    py3-pip \
    py3-flask \
    py3-ftputil

# Copy root filesystem
COPY rootfs /

# Install Python dependencies
RUN pip3 install --no-cache-dir \
    flask \
    ftputil \
    python-dotenv

# Configure nginx
RUN rm /etc/nginx/http.d/default.conf

# Set permissions
RUN chmod a+x /etc/services.d/*/* /etc/cont-init.d/*

WORKDIR /usr/share/ftpbrowser
EXPOSE 80








