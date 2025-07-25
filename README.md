# Unified IoT Testing Environment: LwM2M + Sparkplug B + FDI + Pelion Cloud

This project demonstrates a **comprehensive IoT architecture** that supports multiple protocols and use cases:

- **MQTT + Sparkplug B**: High-throughput telemetry for edge device interoperability
- **LwM2M over MQTT**: High-throughput device management and cloud streaming
- **FDI (Field Device Integration)**: Standardized device configuration and management
- **Pelion Device Management**: Cloud-based IoT platform integration
- **Smart Breaker Simulator**: Realistic industrial IoT device simulation

## 🎯 **Key Innovation: High-Throughput Dual-Path Optimization**

**For Edge Device Interoperability:**
- **High-Throughput Path**: MQTT + Sparkplug B for real-time device-to-device communication
- **Edge-Only**: Device interoperability, no cloud streaming
- **Performance**: 1000+ msg/sec per device

**For Cloud Streaming:**
- **High-Throughput Path**: LwM2M over MQTT with bulk messaging for cloud analytics
- **Cloud Streaming**: HTTP endpoint for cloud data processing and monitoring
- **Performance**: 1000+ msg/sec per device (with bulk operations)

## Architecture Overview

```
┌─────────────────────────┐    ┌──────────────────┐    ┌─────────────────────────┐
│     IoT Devices         │    │   MQTT Broker    │    │   Cloud Layer           │
│  (Dual-Path Protocol)   │    │  (Mosquitto)     │    │                         │
│                         │    │                  │    │ ┌─────────────────────┐ │
│ ┌─────────────────────┐ │    │                  │    │ │   LwM2M Server      │ │
│ │    LwM2M over      │◄┼────┼── MQTT Topics ───┼────┤ │ (MQTT Subscriber)   │ │
│ │    MQTT Transport  │ │    │  lwm2m/{id}/reg  │    │ │ Device Management   │ │
│ │ (High Throughput)  │ │    │  lwm2m/{id}/upd  │    │ │ ┌─────────────────┐ │ │
│ │   Bulk Messaging   │ │    │  lwm2m/{id}/bulk │    │ │ │ HTTP API        │ │ │
│ └─────────────────────┘ │    │                  │    │ │ │ /api/events    │ │ │
│ ┌─────────────────────┐ │    │                  │    │ │ │ Cloud Stream   │ │ │
│ │   Sparkplug B      │◄┼────┼── MQTT Topics ───┼────┤ │ │ │ Bulk Data      │ │ │
│ │   Telemetry        │ │    │  spBv1.0/IIoT/*  │    │ │ └─────────────────┘ │ │
│ │ (High Throughput)  │ │    │                  │    │ └─────────────────────┘ │
│ │  Edge Interop      │ │    │   Single TLS     │    │ ┌─────────────────────┐ │
│ └─────────────────────┘ │    │   Connection     │    │ │  MQTT Monitor       │ │
│                         │    │                  │    │ │ Edge Interop        │ │
│      Same Device        │    │                  │    │ └─────────────────────┘ │
│      Same Connection    │    │                  │    │                         │
└─────────────────────────┘    └──────────────────┘    └──┴─────────────────────┴─┘
                                        │
                                        ▼
┌─────────────────────────┐    ┌──────────────────┐    ┌─────────────────────────┐
│   Cloud Streaming       │    │  Data Processing │    │   Monitoring & Analytics│
│                         │    │                  │    │                         │
│ ┌─────────────────────┐ │    │ ┌───────────────┐ │    │ ┌─────────────────────┐ │
│ │  Redpanda Connect   │ │    │ │   Redpanda    │ │    │ │     Grafana         │ │
│ │  (HTTP Source)      │◄┼────┼─┤  (Kafka API)  │◄┼────┼─┤   Dashboards        │ │
│ │  /api/events        │ │    │ │               │ │    │ │ • LwM2M Cloud Flow  │ │
│ │  LwM2M Bulk Data    │ │    │ │               │ │    │ │ • HTTP Bridge       │ │
│ └─────────────────────┘ │    │ └───────────────┘ │    │ │ • Edge Interop      │ │
│                         │    │                  │    │ │ • Bulk Performance  │ │
│                         │    │ ┌───────────────┐ │    │ └─────────────────────┘ │
│                         │    │ │   Prometheus  │ │    │ ┌─────────────────────┐ │
│                         │    │ │   Metrics     │◄┼────┼─┤   Real-time Alerts  │ │
│                         │    │ │               │ │    │ │   & Monitoring      │ │
│                         │    │ └───────────────┘ │    │ └─────────────────────┘ │
└─────────────────────────┘    └──────────────────┘    └─────────────────────────┘
```

## 🚀 Updated High-Throughput Results ("Go For Broke" Test)

- **LwM2M Bulk Operations Processed**: 941,177
- **Events Endpoint Calls**: 82,539
- **Bulk Size**: 10 operations per message
- **LwM2M Interval**: 0.005s (200 msg/sec per device)
- **Redpanda Connect**: Fast polling, 10 concurrent requests, snappy compression
- **Devices**: 7 simulated
- **System**: Stable at high load, HTTP response time ~10ms

### **Configuration for Maximum Throughput**

- **device-simulator/main.py**:
  - `lwm2m_interval = 0.005`  # 200 msg/sec per device
  - `bulk_size = 10`         # 10 operations per bulk message
  - `bulk_interval = 0.05`   # 50ms max wait per bulk
- **redpanda-connect-config.yaml**:
  - `timeout: "1s"`
  - `max_in_flight: 10`
  - `compression: "snappy"`

### **Performance Summary**
- **Achieved**: Nearly 1 million LwM2M operations processed in minutes
- **Edge-to-Cloud**: LwM2M bulk messaging at 1000+ msg/sec total
- **Edge Interop**: Sparkplug B path remains high-throughput
- **Redpanda Connect**: Now keeps up with device simulator

> **Note:** These results are from the latest "go for broke" test configuration. The platform is now proven to handle extremely high-throughput IoT workloads with both LwM2M and Sparkplug B.

## Key Features

- 🔄 **High-Throughput Dual-Path**: Both protocols optimized for 1000+ msg/sec
- 🚀 **Edge Interoperability**: Sparkplug B for device-to-device communication
- 📊 **Cloud Streaming**: LwM2M bulk messaging for cloud analytics
- 🔌 **HTTP Connector**: LwM2M events streaming via HTTP endpoint to Redpanda
- 📈 **Bulk Operations**: LwM2M bulk read/write/observe for high throughput
- 📊 **Comprehensive Monitoring**: Edge interop + Cloud streaming dashboards
- 🏭 **FDI Integration**: Standardized device configuration and management
- ☁️ **Pelion Cloud**: Real IoT platform integration with WebSocket connections
- ⚡ **Smart Breaker Simulator**: Realistic industrial IoT device simulation
- 🌐 **Web Demo Interface**: Interactive FDI workflow demonstration
- 🐳 **Fully Containerized**: No host dependencies, Docker-based deployment
- 🔄 **Live Code Updates**: Volume mounts enable development without rebuilds

## Use Cases & Components

### **Edge Interoperability (Sparkplug B):**
- **Real-time device coordination**: Temperature sensors triggering pressure adjustments
- **Local control loops**: Flow sensors controlling pump speeds
- **Edge analytics**: Device-to-device data correlation
- **Low-latency responses**: Sub-millisecond device communication

### **Cloud Streaming (LwM2M Bulk):**
- **Bulk telemetry upload**: Batch sensor data for cloud processing
- **Device management**: Bulk configuration and monitoring
- **Cloud analytics**: Historical data analysis and ML training
- **Enterprise integration**: Bulk data for business intelligence

### **Industrial IoT (FDI + Smart Breaker):**
- **Device configuration**: Standardized device setup and management
- **Industrial automation**: Circuit breaker monitoring and control
- **Device interoperability**: FDI-compliant device integration
- **Web-based management**: Interactive device configuration interface

### **Cloud Platform Integration (Pelion):**
- **Real IoT platforms**: Connect to production cloud services
- **Device registration**: Cloud-based device management
- **WebSocket streaming**: Real-time device notifications
- **Enterprise IoT**: Production-ready cloud integration

## 🚀 Quick Start

### **1. Basic Setup (Local Testing)**
```bash
# Start the environment
./scripts/start-environment.sh

# Deploy Redpanda connectors
./scripts/deploy-redpanda-connector.sh

# Monitor data flow
docker exec iot-redpanda rpk topic consume iot.telemetry.lwm2m --follow
```

### **2. FDI Web Demo**
```bash
# Start FDI web interface
python3 fdi_web_demo.py

# Open browser: http://localhost:8088
```

### **3. Smart Breaker Testing**
```bash
# Start smart breaker simulator
docker-compose -f docker-compose.smart-breaker-test.yml up -d

# Monitor smart breaker data
docker logs eaton-smart-breaker-test -f
```

### **4. Pelion Cloud Integration**
```bash
# Set your Pelion API key
./scripts/setup-pelion.sh

# Deploy cloud connector
./scripts/deploy-redpanda-connector.sh

# Monitor cloud data
docker exec iot-redpanda rpk topic consume iot.telemetry.pelion --follow
```

## 📁 Project Structure

```
IOT/
├── device-simulator/          # Multi-protocol device simulator
├── device-profiles/           # FDI device descriptions
├── fdi-device-driver/         # FDI client implementation
├── fdi_web_demo.py           # Interactive FDI web interface
├── smart_breaker_simulator.py # Eaton smart breaker simulation
├── redpanda-connect-config.yaml # Redpanda Connect configuration
├── pelion-connector-config.json # Pelion cloud connector
├── scripts/                   # Deployment and setup scripts
├── monitoring/                # Grafana dashboards and Prometheus
└── README files:              # Comprehensive documentation
    ├── README.md              # Main project overview
    ├── SMART_BREAKER_README.md # Smart breaker documentation
    ├── FDI_COMPLETE_README.md # FDI implementation details
    └── REDPANDA_CONNECTORS_README.md # Connector documentation
``` 