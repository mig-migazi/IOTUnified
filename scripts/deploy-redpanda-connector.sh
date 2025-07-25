#!/bin/bash
# Deploy Redpanda Connect Connectors
# This script deploys connectors for both local LwM2M testing and Pelion cloud WebSocket

set -e

# Load environment variables from config file
if [ -f "../config.env" ]; then
    export $(cat ../config.env | grep -v '^#' | xargs)
    echo "Loaded environment variables from config.env"
elif [ -f "config.env" ]; then
    export $(cat config.env | grep -v '^#' | xargs)
    echo "Loaded environment variables from config.env"
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Redpanda Connect is running
print_status "Checking Redpanda Connect status..."
if ! curl -s http://localhost:8087/connectors > /dev/null; then
    print_error "Redpanda Connect is not running. Please start the environment first."
    exit 1
fi

print_success "Redpanda Connect is running!"

# Wait for LwM2M server to be ready
print_status "Waiting for LwM2M server to be ready..."
until curl -s http://localhost:8080/api/health > /dev/null; do
    print_status "Waiting for LwM2M server..."
    sleep 5
done

print_success "LwM2M server is ready!"

# Create topics for the connectors
print_status "Creating Redpanda topics..."
docker exec iot-redpanda rpk topic create iot.telemetry.lwm2m --partitions 3 --replicas 1 || print_warning "Topic may already exist"
docker exec iot-redpanda rpk topic create iot.telemetry.pelion --partitions 3 --replicas 1 || print_warning "Topic may already exist"

print_success "Topics created!"

# Deploy local LwM2M connector
print_status "Deploying local LwM2M HTTP source connector..."

LOCAL_CONNECTOR_CONFIG='{
  "name": "lwm2m-local-source",
  "config": {
    "connector.class": "io.confluent.connect.http.HttpSourceConnector",
    "http.request.url": "http://lwm2m-server:8080/api/events",
    "http.request.method": "GET",
    "http.request.headers": "Content-Type:application/json",
    "kafka.topic": "iot.telemetry.lwm2m",
    "key.converter": "org.apache.kafka.connect.storage.StringConverter",
    "value.converter": "org.apache.kafka.connect.json.JsonConverter",
    "value.converter.schemas.enable": "false",
    "tasks.max": "1",
    "poll.interval.ms": "1000"
  }
}'

# Deploy local LwM2M connector
if curl -X POST -H "Content-Type: application/json" \
    --data "$LOCAL_CONNECTOR_CONFIG" \
    http://localhost:8087/connectors; then
    print_success "Local LwM2M connector deployed successfully!"
else
    print_warning "Failed to deploy local LwM2M connector"
fi

# Deploy Pelion cloud connector (if API key is available)
if [ -n "$PELION_API_KEY" ]; then
    print_status "Deploying Pelion cloud WebSocket connector..."
    
    # Load Pelion connector config
    PELION_CONFIG=$(cat pelion-connector-config.json)
    
    if curl -X POST -H "Content-Type: application/json" \
        --data "$PELION_CONFIG" \
        http://localhost:8087/connectors; then
        print_success "Pelion cloud connector deployed successfully!"
    else
        print_warning "Failed to deploy Pelion connector"
    fi
else
    print_warning "PELION_API_KEY not set. Skipping Pelion connector deployment."
    print_status "To enable Pelion connector, set PELION_API_KEY environment variable"
fi

# Check connector status
print_status "Checking connector status..."
sleep 5

print_status "Local LwM2M connector status:"
curl -s http://localhost:8087/connectors/lwm2m-local-source/status 2>/dev/null | jq . || print_warning "Local connector status not available"

if [ -n "$PELION_API_KEY" ]; then
    print_status "Pelion cloud connector status:"
    curl -s http://localhost:8087/connectors/pelion-websocket-source/status 2>/dev/null | jq . || print_warning "Pelion connector status not available"
fi

print_success "Redpanda Connect deployment completed!"
print_status "You can now monitor data flow with:"
echo "  docker exec iot-redpanda rpk topic consume iot.telemetry.lwm2m --follow"
echo "  docker exec iot-redpanda rpk topic consume iot.telemetry.pelion --follow" 