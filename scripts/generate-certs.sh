#!/bin/bash

# Generate TLS Certificates for MQTT Broker
# Self-signed certificates for testing environment

set -e

CERT_DIR="certs"
COUNTRY="US"
STATE="California" 
CITY="San Francisco"
ORG="IoT Testing"
UNIT="Engineering"
COMMON_NAME="mosquitto"

echo "Generating TLS certificates for MQTT broker..."

# Create certificate directory
mkdir -p $CERT_DIR

# Generate CA private key
openssl genrsa -out $CERT_DIR/ca.key 4096

# Generate CA certificate
openssl req -new -x509 -days 365 -key $CERT_DIR/ca.key -out $CERT_DIR/ca.crt -subj "/C=$COUNTRY/ST=$STATE/L=$CITY/O=$ORG/OU=$UNIT/CN=TestCA"

# Generate server private key
openssl genrsa -out $CERT_DIR/server.key 4096

# Generate server certificate signing request
openssl req -new -key $CERT_DIR/server.key -out $CERT_DIR/server.csr -subj "/C=$COUNTRY/ST=$STATE/L=$CITY/O=$ORG/OU=$UNIT/CN=$COMMON_NAME"

# Create extensions file for server certificate
cat > $CERT_DIR/server.ext << EOF
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment
subjectAltName = @alt_names

[alt_names]
DNS.1 = mosquitto
DNS.2 = localhost
DNS.3 = lwm2m-mosquitto
IP.1 = 127.0.0.1
IP.2 = 172.20.0.2
EOF

# Generate server certificate signed by CA
openssl x509 -req -in $CERT_DIR/server.csr -CA $CERT_DIR/ca.crt -CAkey $CERT_DIR/ca.key -CAcreateserial -out $CERT_DIR/server.crt -days 365 -extfile $CERT_DIR/server.ext

# Generate client certificates for devices (optional)
openssl genrsa -out $CERT_DIR/client.key 4096
openssl req -new -key $CERT_DIR/client.key -out $CERT_DIR/client.csr -subj "/C=$COUNTRY/ST=$STATE/L=$CITY/O=$ORG/OU=$UNIT/CN=client"
openssl x509 -req -in $CERT_DIR/client.csr -CA $CERT_DIR/ca.crt -CAkey $CERT_DIR/ca.key -CAcreateserial -out $CERT_DIR/client.crt -days 365

# Set appropriate permissions
chmod 600 $CERT_DIR/*.key
chmod 644 $CERT_DIR/*.crt

# Clean up temporary files
rm $CERT_DIR/*.csr $CERT_DIR/*.ext

echo "Certificates generated successfully in $CERT_DIR/"
echo "CA Certificate: $CERT_DIR/ca.crt"
echo "Server Certificate: $CERT_DIR/server.crt"
echo "Server Private Key: $CERT_DIR/server.key"
echo "Client Certificate: $CERT_DIR/client.crt"
echo "Client Private Key: $CERT_DIR/client.key" 