#!/bin/bash

# Pelion-Only IoT Data Pipeline Setup Script

set -e

echo "🚀 Setting up Pelion-Only IoT Data Pipeline..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop first."
    exit 1
fi

# Check if config.env exists
if [ ! -f "config.env" ]; then
    echo "📝 Creating config.env from example..."
    cp config.env.example config.env
    echo "⚠️  Please edit config.env and set your PELION_API_KEY"
    echo "   Then run this script again."
    exit 1
fi

# Load environment variables
source config.env

# Check if PELION_API_KEY is set
if [ "$PELION_API_KEY" = "your_actual_api_key_here" ] || [ -z "$PELION_API_KEY" ]; then
    echo "❌ PELION_API_KEY not set in config.env"
    echo "   Please edit config.env and set your actual Pelion API key"
    exit 1
fi

echo "✅ Configuration looks good!"

# Start the services
echo "🐳 Starting Docker services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check service status
echo "📊 Checking service status..."
docker-compose ps

# Create topics
echo "📝 Creating Redpanda topics..."
docker exec pelion-redpanda rpk topic create iot.telemetry.pelion --partitions 3 --replicas 1

echo "🎉 Setup complete!"
echo ""
echo "📊 Monitor your data:"
echo "   Redpanda Console: http://localhost:8087"
echo "   Pelion data: docker exec pelion-redpanda rpk topic consume iot.telemetry.pelion --follow"
echo ""
echo "🛠️  Management commands:"
echo "   Stop: docker-compose down"
echo "   Logs: docker-compose logs -f redpanda-connect"
echo "   Restart: docker-compose restart" 