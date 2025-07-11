# Unified LwM2M 1.2 + Sparkplug B over MQTT Testing Environment

This project demonstrates and validates the **innovative concept** of using a **single MQTT TLS connection** for both LwM2M 1.2 device management and Sparkplug B telemetry data. 

## 🎯 **Key Innovation: LwM2M over MQTT Transport**

Unlike standard LwM2M implementations that use CoAP over UDP, this project implements **LwM2M semantics over MQTT transport**, enabling true protocol unification over a single connection.

## Architecture Overview

```
┌─────────────────────────┐    ┌──────────────────┐    ┌─────────────────────────┐
│     IoT Devices         │    │   MQTT Broker    │    │   Management Layer      │
│  (Unified Protocol)     │    │  (Mosquitto)     │    │                         │
│                         │    │                  │    │ ┌─────────────────────┐ │
│ ┌─────────────────────┐ │    │                  │    │ │   LwM2M Server      │ │
│ │    LwM2M over      │◄┼────┼── MQTT Topics ───┼────┤ │ (MQTT Subscriber)   │ │
│ │    MQTT Transport  │ │    │  lwm2m/{id}/reg  │    │ │ Device Management   │ │
│ └─────────────────────┘ │    │  lwm2m/{id}/upd  │    │ └─────────────────────┘ │
│ ┌─────────────────────┐ │    │                  │    │ ┌─────────────────────┐ │
│ │   Sparkplug B      │◄┼────┼── MQTT Topics ───┼────┤ │  Sparkplug Host     │ │
│ │   Telemetry        │ │    │  spBv1.0/IIoT/*  │    │ │ Telemetry Processor │ │
│ └─────────────────────┘ │    │                  │    │ └─────────────────────┘ │
│                         │    │   Single TLS     │    │                         │
│      Same Device        │    │   Connection     │    │  ┌─────────────────────┐ │
│      Same Connection    │    │                  │    │  │ Prometheus/Grafana  │ │
│                         │    │                  │    │  │ Real-time Dashboard │ │
└─────────────────────────┘    └──────────────────┘    └──┴─────────────────────┴─┘
```

## ✅ **Proven Results**

### **Unified Device Performance:**
- **1 Device** using **BOTH protocols simultaneously**
- **Sparkplug B Telemetry**: 1 message/second (real-time sensor data)
- **LwM2M Device Management**: 1 message/3 seconds (lifecycle management)
- **Same MQTT Connection**: Single TLS session for both protocols

### **Dashboard Metrics:**
- ✅ **LwM2M Active Devices**: 1
- ✅ **Sparkplug B Online Devices**: 1  
- ✅ **Message Flow Rates**: Consistent, measurable activity
- ✅ **Protocol Coexistence**: No conflicts or interference

## Key Features

- 🔄 **Unified Connection**: Single MQTT TLS session for both protocols
- 🚀 **Custom LwM2M Transport**: LwM2M semantics over MQTT (not standard CoAP/UDP)
- 📊 **Protocol Buffers**: Sparkplug B uses protobuf for compact binary format
- 📈 **Scale Testing**: Proven stable operation, configurable device counts
- 📊 **Real-time Monitoring**: Live dashboard with Prometheus + Grafana
- 🐳 **Fully Containerized**: No host dependencies, Docker-based deployment

## Quick Start

```bash
# Start the entire unified environment
docker-compose up -d

# Access the live dashboard
open http://localhost:3000
# Login: admin/admin

# Scale to multiple devices (each uses both protocols)
docker-compose up -d --scale device-simulator=5

# View real-time logs
docker-compose logs -f device-simulator

# Monitor MQTT traffic
docker-compose logs -f mosquitto

# Stop everything
docker-compose down
```

## Components Deep Dive

### 1. **MQTT Broker (Mosquitto)**
- **Ports**: 8883 (TLS), 1883 (Plain), 9001 (WebSocket)
- **Role**: Unified transport layer for both protocols
- **Config**: Simplified for testing (`mosquitto/mosquitto.conf`)
- **Innovation**: Handles both LwM2M and Sparkplug B message flows

### 2. **Custom LwM2M Server** 
- **Port**: 8080 (REST API + Metrics)
- **Implementation**: Python-based MQTT subscriber
- **Innovation**: LwM2M semantics over MQTT transport (not CoAP/UDP)
- **Features**: Device registration, lifecycle management, command/response
- **Topics**: `lwm2m/{device_id}/reg`, `lwm2m/{device_id}/update`, `lwm2m/{device_id}/resp/*`

### 3. **Sparkplug B Host Application**
- **Port**: 8081 (Metrics endpoint)
- **Implementation**: Protobuf message processor
- **Features**: DBIRTH/DDATA message handling, device lifecycle tracking
- **Topics**: `spBv1.0/IIoT/DBIRTH/{device_id}`, `spBv1.0/IIoT/DDATA/{device_id}`

### 4. **Unified Device Simulators**
- **Language**: Python with asyncio
- **Innovation**: Single device implementing BOTH protocols
- **Features**: 
  - LwM2M registration and updates via MQTT
  - Sparkplug B birth certificates and telemetry
  - Realistic sensor data generation
  - Configurable message rates

### 5. **Monitoring & Observability**
- **Prometheus**: `http://localhost:9090` (metrics collection)
- **Grafana Dashboard**: `http://localhost:3000` (admin/admin)
- **Pre-configured Panels**:
  - Active Devices Overview (LwM2M + Sparkplug B)
  - Message Rate Tracking
  - Protocol-specific Activity
  - Service Health Monitoring

## Configuration & Scaling

### **Message Rate Configuration**
```yaml
environment:
  - DEVICE_COUNT=1                    # Devices per container
  - TELEMETRY_INTERVAL=1              # Sparkplug B interval (seconds)
  - LWM2M_INTERVAL=3                  # LwM2M update interval (seconds)
```

### **Scaling Devices**
```bash
# Scale to 5 unified devices (each using both protocols)
docker-compose up -d --scale device-simulator=5

# Each device generates:
# - 1 Sparkplug B message/second (telemetry)
# - 1 LwM2M message/3 seconds (management)
```

### **Performance Testing**
```bash
# Test aggressive rates (be careful with resource usage)
# Edit docker-compose.yml:
# TELEMETRY_INTERVAL=0.1  # 10 messages/second
# LWM2M_INTERVAL=1        # 1 message/second

docker-compose restart device-simulator
```

## Innovation Highlights

### **1. LwM2M over MQTT Transport**
- **Standard LwM2M**: Uses CoAP over UDP
- **Our Innovation**: LwM2M semantics over MQTT topics
- **Benefits**: 
  - Unified connection management
  - Better NAT/firewall traversal
  - Leverages MQTT reliability and persistence
  - Enables true protocol convergence

### **2. Protocol Coexistence**
- **Single Device Connection**: One MQTT client per device
- **Dual Protocol Support**: Same device sends both LwM2M and Sparkplug B
- **No Interference**: Protocols operate independently on same connection
- **Resource Efficiency**: Shared TLS session, connection pooling

### **3. Real-world Validation**
- **Dashboard Metrics**: Live visualization of unified concept
- **Message Flow Tracking**: Independent verification of both protocols
- **Scalability Testing**: Proven stable operation under load

## Monitoring Dashboard

Access the Grafana dashboard at `http://localhost:3000` (admin/admin) to see:

- **📊 Active Devices Overview**: Real-time count of LwM2M + Sparkplug B devices
- **📈 Message Rate Panels**: Live telemetry and management message flows
- **🔧 LwM2M Device Activity**: Registration, updates, command responses
- **📡 Sparkplug B Telemetry**: Birth certificates, data messages, device lifecycle
- **⚡ Service Health**: Component status and performance metrics

## Protocol Message Examples

### **LwM2M Registration (MQTT)**
```json
Topic: lwm2m/device-temp-001/reg
{
  "endpoint": "device-temp-001",
  "lifetime": 3600,
  "version": "1.2",
  "bindingMode": "UQ",
  "objects": {
    "3": { "0": { "0": "IoT Testing Corp", "1": "SimDevice-temperature_sensor" }}
  }
}
```

### **Sparkplug B Telemetry (Protobuf)**
```
Topic: spBv1.0/IIoT/DDATA/device-temp-001
Binary protobuf payload containing:
- timestamp, seq, metrics[]
- Sensors/Temperature: 23.5°C
- Battery/Level: 85%
- Device/Uptime: 3600s
```

## Troubleshooting

### **Dashboard Shows No Data**
```bash
# Check device connection status
curl -s "http://localhost:9090/api/v1/query?query=sparkplug_devices_online"
curl -s "http://localhost:9090/api/v1/query?query=lwm2m_active_devices"

# Restart services to clear stale metrics
docker-compose restart sparkplug-host lwm2m-server device-simulator
```

### **Scaling Issues**
```bash
# Check container resource usage
docker stats

# Reduce message rates for higher device counts
# Edit docker-compose.yml: increase TELEMETRY_INTERVAL and LWM2M_INTERVAL
```

### **MQTT Connection Issues**
```bash
# Check MQTT broker logs
docker-compose logs mosquitto

# Test direct MQTT connectivity
docker exec -it lwm2m-mosquitto mosquitto_pub -h localhost -p 1883 -t "test" -m "hello"

# Monitor all MQTT traffic
docker exec -it lwm2m-mosquitto mosquitto_sub -h localhost -p 1883 -t "#" -v
```

## Development & Extension

### **Adding Custom LwM2M Objects**
1. Define object structure in `device-simulator/main.py`
2. Update registration payload in `register_lwm2m_device()`
3. Implement read/write/execute handlers

### **Custom Sparkplug B Metrics**
1. Modify `proto/sparkplug_b.proto` for new data types
2. Regenerate Python bindings: `protoc --python_out=. proto/sparkplug_b.proto`
3. Update telemetry payload in `_create_telemetry_payload()`

### **Scaling for Production**
1. Implement proper TLS certificates (currently using test certs)
2. Add authentication/authorization for MQTT
3. Configure resource limits and connection pooling
4. Implement proper device lifecycle management

## Concept Validation Status

✅ **Unified MQTT Transport**: Single connection for both protocols  
✅ **LwM2M over MQTT**: Custom transport implementation working  
✅ **Protocol Coexistence**: No conflicts or interference  
✅ **Real-time Monitoring**: Dashboard showing live metrics  
✅ **Scalable Architecture**: Containerized, configurable deployment  
✅ **Message Flow Validation**: Both protocols active and measurable  

**This project successfully demonstrates that LwM2M 1.2 device management and Sparkplug B telemetry can coexist over a unified MQTT TLS connection, providing a foundation for next-generation IoT communication architectures.**

## License

This project is for demonstration and testing purposes. Individual components may have their own licenses for production use. 