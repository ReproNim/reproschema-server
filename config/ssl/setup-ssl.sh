#!/bin/bash
# config/ssl/setup-ssl.sh

set -e

SSL_DIR="/etc/nginx/ssl"
DAYS_VALID=365

# Create SSL directory if it doesn't exist
mkdir -p $SSL_DIR

# Function to generate self-signed certificate
generate_self_signed() {
    echo "Generating self-signed certificate..."
    openssl req -x509 -nodes -days $DAYS_VALID \
        -newkey rsa:2048 \
        -keyout $SSL_DIR/key.pem \
        -out $SSL_DIR/cert.pem \
        -subj "/CN=localhost" \
        -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
}

# Function to install provided certificate
install_provided_cert() {
    echo "Installing provided certificate..."
    cp /run/secrets/ssl_cert $SSL_DIR/cert.pem
    cp /run/secrets/ssl_key $SSL_DIR/key.pem
}

# Check if certificates are provided via Docker secrets
if [ -f "/run/secrets/ssl_cert" ] && [ -f "/run/secrets/ssl_key" ]; then
    install_provided_cert
else
    # Check if we need to generate new self-signed certs
    if [ ! -f "$SSL_DIR/cert.pem" ] || [ ! -f "$SSL_DIR/key.pem" ]; then
        generate_self_signed
    fi
fi

# Set proper permissions
chmod 600 $SSL_DIR/key.pem
chmod 644 $SSL_DIR/cert.pem