# Full Stack IoT Environment

Complete IoT development environment with multiple protocols, monitoring, and device simulators for comprehensive IoT testing and development.

## 🎯 Use Case

Comprehensive IoT development and testing with:
- **Multi-protocol support** (LwM2M, MQTT, Sparkplug B)
- **Device simulation** (Smart breakers, sensors, actuators)
- **Cloud integration** (Pelion Device Management)
- **Monitoring and analytics** (Grafana, Prometheus)
- **Data streaming** (Redpanda with connectors)

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Device Sims   │    │   MQTT Broker   │    │   LwM2M Server  │
│ (Smart Breaker, │───▶│   (Mosquitto)   │───▶│   (HTTP API)    │
│  Sensors, etc.) │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                       │
                                ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Pelion Cloud   │    │ Redpanda Connect│    │    Redpanda     │
│  (WebSocket)    │───▶│   (Connectors)  │───▶│  (Data Stream)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    Grafana      │    │   Prometheus    │    │   Applications  │
│  (Dashboards)   │◀───│   (Metrics)     │◀───│  (Consumers)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### 1. Setup Configuration

```bash
# Copy and edit configuration
cp config.env.example config.env
# Edit config.env with your settings
```

### 2. Start the Environment

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps
```

### 3. Deploy Connectors

```bash
# Deploy Redpanda connectors
../../scripts/deploy-redpanda-connector.sh
```

### 4. Access Services

```bash
# Redpanda Console
open http://localhost:8086

# Grafana (if enabled)
open http://localhost:3000

# FDI Web Demo
python3 ../../fdi_web_demo.py
# Then open http://localhost:8088
```

## 📊 Services

### Core Services
- **Redpanda**: Kafka-compatible streaming platform
- **Redpanda Console**: Web UI for monitoring
- **Redpanda Connect**: Data pipeline connectors
- **MQTT Broker**: Mosquitto for device communication
- **LwM2M Server**: Device management and HTTP API

### Device Simulation
- **Device Simulator**: Multi-protocol device simulation
- **Smart Breaker**: FDI-compliant circuit breaker
- **Sparkplug Host**: Edge device interoperability

### Cloud Integration
- **Pelion Connector**: WebSocket connection to Pelion cloud
- **LwM2M Connector**: HTTP connection to local LwM2M server

### Monitoring (Optional)
- **Grafana**: Dashboards and visualization
- **Prometheus**: Metrics collection
- **MQTT Monitor**: Edge device monitoring

## 🔧 Configuration

### Environment Variables

- `PELION_API_KEY`: Pelion Device Management API key
- `DEVICE_ID`: Device simulator identifier
- `MQTT_BROKER_HOST`: MQTT broker address
- `LWM2M_SERVER_URL`: LwM2M server address
- `REDPANDA_BROKERS`: Redpanda broker addresses

### Ports

- `1883`: MQTT Broker
- `5684`: LwM2M Server (UDP)
- `8080`: LwM2M Server HTTP API
- `8088`: FDI Web Demo
- `9092`: Redpanda Kafka API
- `8084-8086`: Redpanda services
- `4195`: Redpanda Connect
- `3000`: Grafana (if enabled)
- `9090`: Prometheus (if enabled)

## 📈 Data Flow

### Local Device Data
1. **Device Simulator**: Generates telemetry and device events
2. **MQTT Communication**: Publishes to MQTT topics
3. **LwM2M Server**: Processes device management operations
4. **HTTP API**: Provides REST endpoint for data access
5. **Redpanda Connect**: Streams data to Redpanda topics

### Cloud Data
1. **Pelion WebSocket**: Connects to Pelion Device Management
2. **Redpanda Connect**: Processes cloud notifications
3. **Redpanda Topics**: Stores cloud device data

### Monitoring
1. **Prometheus**: Collects metrics from all services
2. **Grafana**: Visualizes data and creates dashboards
3. **MQTT Monitor**: Monitors edge device communication

## 🛠️ Management

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f

# Restart specific service
docker-compose restart redpanda-connect

# Scale services
docker-compose up -d --scale device-simulator=3
```

## 🔍 Monitoring

### Redpanda Console
- **URL**: http://localhost:8086
- **Features**: Topic monitoring, data consumption, connector status

### Grafana Dashboards
- **URL**: http://localhost:3000 (if enabled)
- **Dashboards**: LwM2M flow, HTTP bridge, edge interoperability

### Topic Monitoring
```bash
# Monitor LwM2M data
docker exec iot-redpanda rpk topic consume iot.telemetry.lwm2m --follow

# Monitor Pelion data
docker exec iot-redpanda rpk topic consume iot.telemetry.pelion --follow

# List all topics
docker exec iot-redpanda rpk topic list
```

## 🔍 Troubleshooting

### Check Service Status
```bash
# View all container status
docker-compose ps

# Check specific service logs
docker-compose logs redpanda-connect
docker-compose logs device-simulator
```

### Verify Data Flow
```bash
# Test LwM2M server
curl http://localhost:8080/api/events

# Check MQTT connection
docker-compose logs mosquitto

# Verify Redpanda topics
docker exec iot-redpanda rpk topic list
```

### Connector Issues
```bash
# Check connector status
docker-compose logs redpanda-connect

# Restart connectors
../../scripts/deploy-redpanda-connector.sh
```

## 📚 Documentation

- **Smart Breaker**: See `../../SMART_BREAKER_README.md`
- **FDI Integration**: See `../../FDI_COMPLETE_README.md`
- **Redpanda Connectors**: See `../../REDPANDA_CONNECTORS_README.md`
- **Device Simulator**: See `../../device-simulator/`

## 🎮 Interactive Features

### FDI Web Demo
- **URL**: http://localhost:8088
- **Features**: Device configuration, command execution, real-time monitoring

### Redpanda Console
- **URL**: http://localhost:8086
- **Features**: Topic management, data exploration, connector monitoring

### Grafana Dashboards
- **URL**: http://localhost:3000 (if enabled)
- **Features**: Real-time metrics, performance monitoring, alerting 