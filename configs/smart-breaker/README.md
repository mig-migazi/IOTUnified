# Smart Breaker IoT Configuration

FDI-compliant smart breaker simulation with LwM2M and Sparkplug B communication for industrial IoT testing.

## 🎯 Use Case

Industrial IoT device simulation and testing with:
- **FDI (Field Device Integration)** compliance
- **LwM2M** device management
- **Sparkplug B** telemetry
- **MQTT** communication
- **Web-based device management**

## 🏗️ Architecture

```
Smart Breaker Simulator → MQTT → LwM2M Server → HTTP API → Redpanda Connect → Redpanda
                                    ↓
                              Web Demo Interface
```

## 🚀 Quick Start

### 1. Start the Environment

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps
```

### 2. Access the Web Demo

```bash
# Start the FDI web interface
python3 ../../fdi_web_demo.py

# Open browser: http://localhost:8088
```

### 3. Monitor Data Flow

```bash
# View Redpanda Console
open http://localhost:8086

# Monitor LwM2M data
docker exec iot-redpanda rpk topic consume iot.telemetry.lwm2m --follow
```

## 📊 Services

- **Smart Breaker Simulator**: Smart breaker with FDI compliance
- **LwM2M Server**: Device management and HTTP API
- **MQTT Broker**: Mosquitto for device communication
- **Redpanda**: Data streaming platform
- **Redpanda Console**: Web UI for monitoring
- **FDI Web Demo**: Interactive device management interface

## 🔧 Configuration

### Environment Variables

- `DEVICE_ID`: Smart breaker device identifier
- `MQTT_BROKER_HOST`: MQTT broker address
- `MQTT_BROKER_PORT`: MQTT broker port
- `LWM2M_SERVER_URL`: LwM2M server address

### Ports

- `1883`: MQTT Broker
- `5684`: LwM2M Server (UDP)
- `8080`: LwM2M Server HTTP API
- `8088`: FDI Web Demo
- `9092`: Redpanda Kafka API
- `8084-8086`: Redpanda services

## 📈 Data Flow

1. **Smart Breaker**: Simulates industrial circuit breaker with FDI compliance
2. **MQTT Communication**: Publishes telemetry and receives commands
3. **LwM2M Server**: Manages devices and provides HTTP API
4. **Redpanda Connect**: Streams data from HTTP API to Redpanda
5. **Web Demo**: Interactive FDI device management interface

## 🛠️ Management

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f device-simulator

# Restart specific service
docker-compose restart lwm2m-server
```

## 🔍 Troubleshooting

### Check Device Status

```bash
# View smart breaker logs
docker-compose logs device-simulator

# Check MQTT connection
docker-compose logs mosquitto

# Verify LwM2M server
curl http://localhost:8080/api/events
```

### FDI Web Demo Issues

```bash
# Check Python dependencies
pip3 install flask flask-socketio structlog

# Verify FDI file
ls -la ../../fdi/device-profiles/smart-breaker.fdi
```

## 📚 Documentation

- **Smart Breaker Details**: See `../../SMART_BREAKER_README.md`
- **FDI Integration**: See `../../FDI_COMPLETE_README.md`
- **Device Profiles**: See `../../device-profiles/`

## 🎮 Interactive Features

### FDI Web Demo

1. **Load Device**: Upload or select the smart breaker FDI file
2. **View Commands**: See available device commands
3. **Execute Commands**: Trip, close, reset, and configure the breaker
4. **Monitor Status**: Real-time device status and configuration

### Device Simulation

- **Realistic Behavior**: Simulates actual circuit breaker operations
- **FDI Compliance**: Standardized device interface
- **Multi-Protocol**: LwM2M and Sparkplug B support
- **Web Management**: Browser-based device control 