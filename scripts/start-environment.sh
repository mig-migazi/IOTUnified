#!/bin/bash

# Start LwM2M 1.2 + Sparkplug B Unified MQTT Testing Environment
# This script sets up the complete environment with proper initialization

set -e

echo "🚀 Starting LwM2M 1.2 + Sparkplug B Unified MQTT Testing Environment"
echo "=================================================================="

# Check if Docker and Docker Compose are installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is required but not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is required but not installed. Please install Docker Compose first."
    exit 1
fi

# Generate TLS certificates if they don't exist
if [ ! -f "certs/server.crt" ]; then
    echo "🔐 Generating TLS certificates..."
    chmod +x scripts/generate-certs.sh
    ./scripts/generate-certs.sh
else
    echo "✅ TLS certificates already exist"
fi

# Generate MQTT password file if it doesn't exist
if [ ! -f "mosquitto/passwd.hashed" ]; then
    echo "🔑 Generating MQTT authentication..."
    # Use Docker to run mosquitto_passwd since it might not be installed on host
    docker run --rm -v $(pwd)/mosquitto:/mosquitto eclipse-mosquitto:2.0 \
        mosquitto_passwd -c -b /mosquitto/passwd.hashed device testpass123
    docker run --rm -v $(pwd)/mosquitto:/mosquitto eclipse-mosquitto:2.0 \
        mosquitto_passwd -b /mosquitto/passwd.hashed lwm2m-server testpass123
    docker run --rm -v $(pwd)/mosquitto:/mosquitto eclipse-mosquitto:2.0 \
        mosquitto_passwd -b /mosquitto/passwd.hashed sparkplug-host testpass123
    docker run --rm -v $(pwd)/mosquitto:/mosquitto eclipse-mosquitto:2.0 \
        mosquitto_passwd -b /mosquitto/passwd.hashed admin testpass123
    
    # Update mosquitto.conf to use the hashed password file
    sed -i '' 's|password_file /mosquitto/config/passwd|password_file /mosquitto/config/passwd.hashed|g' mosquitto/mosquitto.conf
else
    echo "✅ MQTT authentication already configured"
fi

# Set default environment variables
export DEVICE_COUNT=${DEVICE_COUNT:-5}
export TELEMETRY_INTERVAL=${TELEMETRY_INTERVAL:-5}
export LWM2M_INTERVAL=${LWM2M_INTERVAL:-30}

echo "📊 Environment Configuration:"
echo "   Device Count: $DEVICE_COUNT"
echo "   Telemetry Interval: ${TELEMETRY_INTERVAL}s"
echo "   LwM2M Update Interval: ${LWM2M_INTERVAL}s"
echo ""

# Build and start services
echo "🏗️  Building container images..."
docker-compose build --parallel

echo "🚀 Starting services..."
docker-compose up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."

# Wait for MQTT broker
echo "   Waiting for MQTT broker..."
timeout=60
while [ $timeout -gt 0 ] && ! docker-compose exec -T mosquitto mosquitto_pub -h localhost -t health -m test 2>/dev/null; do
    sleep 2
    timeout=$((timeout-2))
done

if [ $timeout -le 0 ]; then
    echo "❌ MQTT broker failed to start within 60 seconds"
    docker-compose logs mosquitto
    exit 1
fi

echo "✅ MQTT broker is ready"

# Wait for LwM2M server
echo "   Waiting for LwM2M server..."
timeout=60
while [ $timeout -gt 0 ] && ! curl -sf http://localhost:8080/api/health >/dev/null 2>&1; do
    sleep 2
    timeout=$((timeout-2))
done

if [ $timeout -le 0 ]; then
    echo "❌ LwM2M server failed to start within 60 seconds"
    docker-compose logs lwm2m-server
    exit 1
fi

echo "✅ LwM2M server is ready"

# Wait for Sparkplug host
echo "   Waiting for Sparkplug B host..."
timeout=60
while [ $timeout -gt 0 ] && ! curl -sf http://localhost:8081/health >/dev/null 2>&1; do
    sleep 2
    timeout=$((timeout-2))
done

if [ $timeout -le 0 ]; then
    echo "❌ Sparkplug B host failed to start within 60 seconds"
    docker-compose logs sparkplug-host
    exit 1
fi

echo "✅ Sparkplug B host is ready"

# Scale device simulators
if [ "$DEVICE_COUNT" -gt 1 ]; then
    echo "📱 Scaling device simulators to $DEVICE_COUNT devices..."
    docker-compose up -d --scale device-simulator=$DEVICE_COUNT
fi

echo ""
echo "🎉 Environment is ready! Access points:"
echo "   📊 Grafana Dashboard:    http://localhost:3000 (admin/admin)"
echo "   📈 Prometheus Metrics:   http://localhost:9090"
echo "   🏠 LwM2M Server Web UI:  http://localhost:8080"
echo "   📡 Sparkplug B Metrics:  http://localhost:8081"
echo "   👁️  MQTT Monitor:        http://localhost:8082"
echo ""
echo "🔧 Useful commands:"
echo "   View logs:               docker-compose logs -f"
echo "   Scale devices:           docker-compose up -d --scale device-simulator=N"
echo "   Stop environment:        docker-compose down"
echo "   Monitor MQTT traffic:    docker exec -it lwm2m-mosquitto mosquitto_sub -h localhost -t '#' -v"
echo ""
echo "📋 Testing scripts available:"
echo "   Basic connectivity:      ./scripts/test-mqtt-connection.sh"
echo "   LwM2M functionality:     ./scripts/test-lwm2m-registration.sh"
echo "   Sparkplug B telemetry:   ./scripts/test-sparkplug-telemetry.sh"
echo "   Load testing:            ./scripts/load-test.sh"
echo ""
echo "✨ Happy testing!" 