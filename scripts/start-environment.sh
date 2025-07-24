#!/bin/bash
# IoT Environment Startup Script with Redpanda Integration
# This script starts the complete IoT environment with WebSocket support

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

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker first."
    exit 1
fi

print_success "Docker is running!"

# Generate certificates if they don't exist
if [ ! -f "certs/ca.crt" ]; then
    print_status "Generating certificates..."
    ./scripts/generate-certs.sh
fi

# Start the environment
print_status "Starting IoT environment with WebSocket support..."

# Start core services first
print_status "Starting Redpanda and core services..."
docker-compose up -d redpanda redpanda-console

# Wait for Redpanda to be ready
print_status "Waiting for Redpanda to be ready..."
until curl -s http://localhost:8084/subjects > /dev/null 2>&1; do
    print_status "Waiting for Redpanda..."
    sleep 5
done

print_success "Redpanda is ready!"

# Start LwM2M server with WebSocket support
print_status "Starting LwM2M server with WebSocket support..."
docker-compose up -d lwm2m-server

# Wait for LwM2M server to be ready
print_status "Waiting for LwM2M server..."
until curl -s http://localhost:8080/api/health > /dev/null 2>&1; do
    print_status "Waiting for LwM2M server..."
    sleep 5
done

print_success "LwM2M server is ready!"

# Start Redpanda Connect
print_status "Starting Redpanda Connect..."
docker-compose up -d redpanda-connect

# Wait for Redpanda Connect to be ready
print_status "Waiting for Redpanda Connect..."
until curl -s http://localhost:8087/ready > /dev/null 2>&1; do
    print_status "Waiting for Redpanda Connect..."
    sleep 5
done

print_success "Redpanda Connect is ready!"

# Redpanda Connect is configured via config file
print_status "Redpanda Connect configured with WebSocket input and Kafka output"

# Start remaining services
print_status "Starting remaining IoT services..."
docker-compose up -d

# Wait for all services to be ready
print_status "Waiting for services to be ready..."
sleep 10

# Check service health
print_status "Checking service health..."

# Check Redpanda Console
if curl -s http://localhost:8086 > /dev/null 2>&1; then
    print_success "Redpanda Console: http://localhost:8086"
else
    print_warning "Redpanda Console not accessible"
fi

# Check LwM2M Server
if curl -s http://localhost:8080/api/health > /dev/null 2>&1; then
    print_success "LwM2M Server: http://localhost:8080"
else
    print_warning "LwM2M Server not accessible"
fi

# Check Redpanda Connect
if curl -s http://localhost:8087/ready > /dev/null 2>&1; then
    print_success "Redpanda Connect: http://localhost:8087"
else
    print_warning "Redpanda Connect not accessible"
fi

# Check Grafana
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    print_success "Grafana: http://localhost:3000 (admin/admin)"
else
    print_warning "Grafana not accessible"
fi

print_success "IoT environment started successfully!"
print_status ""
print_status "🌐 Service URLs:"
echo "  • Redpanda Console: http://localhost:8086"
echo "  • LwM2M Server: http://localhost:8080"
echo "  • Redpanda Connect: http://localhost:8087"
echo "  • Grafana: http://localhost:3000 (admin/admin)"
echo "  • Prometheus: http://localhost:9090"
print_status ""
print_status "📊 Monitoring:"
echo "  • Monitor data flow: ./scripts/monitor-redpanda-data.sh"
echo "  • Check connector status: curl http://localhost:8087/connectors"
echo "  • View topics: docker exec iot-redpanda rpk topic list"
print_status ""
print_status "🔧 Next Steps:"
echo "  1. Open Redpanda Console to view topics and data"
echo "  2. Check Grafana for dashboards"
echo "  3. Monitor WebSocket events in real-time" 