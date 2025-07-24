#!/bin/bash
# Deploy Redpanda Connect Connector for LwM2M WebSocket Interface
# This script deploys a connector to consume from LwM2M server WebSocket

set -e

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

# Create topics for the connector
print_status "Creating Redpanda topics..."
docker exec iot-redpanda rpk topic create iot.telemetry.lwm2m.websocket --partitions 3 --replicas 1 || print_warning "Topic may already exist"
docker exec iot-redpanda rpk topic create iot.telemetry.lwm2m.http --partitions 3 --replicas 1 || print_warning "Topic may already exist"

print_success "Topics created!"

# Deploy the connector
print_status "Deploying LwM2M HTTP source connector..."

# First, let's try a simple HTTP source connector
CONNECTOR_CONFIG='{
  "name": "lwm2m-http-source",
  "config": {
    "connector.class": "io.confluent.connect.http.HttpSourceConnector",
    "http.request.url": "http://lwm2m-server:8080/api/websocket/events",
    "http.request.method": "GET",
    "http.request.headers": "Content-Type:application/json",
    "kafka.topic": "iot.telemetry.lwm2m.http",
    "key.converter": "org.apache.kafka.connect.storage.StringConverter",
    "value.converter": "org.apache.kafka.connect.json.JsonConverter",
    "value.converter.schemas.enable": "false",
    "tasks.max": "1",
    "poll.interval.ms": "5000"
  }
}'

# Deploy the connector
if curl -X POST -H "Content-Type: application/json" \
    --data "$CONNECTOR_CONFIG" \
    http://localhost:8087/connectors; then
    print_success "Connector deployed successfully!"
else
    print_warning "Failed to deploy connector. Checking available connectors..."
    
    # List available connectors
    print_status "Available connectors:"
    curl -s http://localhost:8087/connector-plugins | jq '.[].class' 2>/dev/null || echo "No connectors available"
    
    print_status "Trying alternative approach with custom connector..."
    
    # Alternative: Use a simple HTTP polling approach
    print_status "Creating a simple HTTP polling connector..."
    
    SIMPLE_CONFIG='{
      "name": "lwm2m-simple-source",
      "config": {
        "connector.class": "org.apache.kafka.connect.source.SourceConnector",
        "tasks.max": "1",
        "topic": "iot.telemetry.lwm2m.simple",
        "http.url": "http://lwm2m-server:8080/api/websocket/events",
        "poll.interval.ms": "10000"
      }
    }'
    
    if curl -X POST -H "Content-Type: application/json" \
        --data "$SIMPLE_CONFIG" \
        http://localhost:8087/connectors; then
        print_success "Simple connector deployed!"
    else
        print_error "Failed to deploy any connector. Manual configuration required."
        print_status "Please check Redpanda Connect logs and configure manually."
    fi
fi

# Check connector status
print_status "Checking connector status..."
sleep 5
curl -s http://localhost:8087/connectors/lwm2m-http-source/status 2>/dev/null | jq . || \
curl -s http://localhost:8087/connectors/lwm2m-simple-source/status 2>/dev/null | jq . || \
print_warning "Connector status not available"

print_success "Redpanda Connect deployment completed!"
print_status "You can now monitor data flow with:"
echo "  docker exec iot-redpanda rpk topic consume iot.telemetry.lwm2m.http --follow"
echo "  docker exec iot-redpanda rpk topic consume iot.telemetry.lwm2m.simple --follow" 