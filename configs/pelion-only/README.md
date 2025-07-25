# Pelion-Only IoT Data Pipeline

A minimal IoT data pipeline that connects to Pelion Device Management cloud and streams device data to Redpanda.

## 🎯 Use Case

Connect to Pelion Device Management cloud via WebSocket and stream real-time device notifications to Redpanda for further processing.

## 🏗️ Architecture

```
Pelion Cloud (WebSocket) → Redpanda Connect → Redpanda → Applications
```

## 🚀 Quick Start

### 1. Setup Configuration

```bash
# Copy and edit the configuration
cp config.env.example config.env
# Edit config.env and set your PELION_API_KEY
```

### 2. Start the Pipeline

```bash
# Start the services
docker-compose up -d

# Check status
docker-compose ps
```

### 3. Monitor Data Flow

```bash
# View Redpanda Console
open http://localhost:8087

# Monitor Pelion data stream
docker exec pelion-redpanda rpk topic consume iot.telemetry.pelion --follow
```

## 📊 Services

- **Redpanda**: Kafka-compatible streaming platform
- **Redpanda Console**: Web UI for monitoring topics and data
- **Redpanda Connect**: Connects to Pelion WebSocket and streams to Redpanda

## 🔧 Configuration

### Environment Variables

- `PELION_API_KEY`: Your Pelion Device Management API key

### Ports

- `9093`: Redpanda Kafka API
- `8088`: Redpanda Admin API  
- `8089`: Redpanda Proxy
- `8087`: Redpanda Console
- `4196`: Redpanda Connect

## 📈 Data Flow

1. **Pelion WebSocket**: Connects to `wss://api.us.east-1.mbedcloud.com/v2/notification/websocket`
2. **Redpanda Connect**: Processes incoming WebSocket messages
3. **Redpanda Topic**: `iot.telemetry.pelion` receives device notifications
4. **Applications**: Consume data from Redpanda for processing

## 🛠️ Management

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f redpanda-connect

# Restart connector
docker-compose restart redpanda-connect
```

## 🔍 Troubleshooting

### Check Pelion Connection

```bash
# View connector logs
docker-compose logs redpanda-connect

# Check if API key is set
docker exec pelion-redpanda-connect env | grep PELION_API_KEY
```

### Verify Data Flow

```bash
# List topics
docker exec pelion-redpanda rpk topic list

# Consume data
docker exec pelion-redpanda rpk topic consume iot.telemetry.pelion -n 5
``` 