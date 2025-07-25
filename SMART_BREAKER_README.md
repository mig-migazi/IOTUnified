# Smart Breaker - FDI-Compliant IoT Device

This implementation demonstrates a **FDI-compliant Smart Breaker** that integrates seamlessly with the existing high-throughput dual-path IoT architecture (LwM2M + Sparkplug B).

## 🎯 **Key Features**

### **FDI Compliance**
- **Standardized Device Description**: Complete FDI device package with manufacturer, model, and capabilities
- **Unified Configuration**: Vendor-independent device configuration and parameter mapping
- **Automated Discovery**: FDI host integration for automatic device registration and configuration
- **Interoperability**: Works with any FDI-compliant host system

### **Advanced Protection Functions**
- **Overcurrent Protection**: Configurable pickup and delay settings
- **Ground Fault Protection**: Sensitive ground fault detection and isolation
- **Arc Fault Protection**: Advanced arc fault detection for enhanced safety
- **Thermal Protection**: Thermal overload protection with configurable curves
- **Auto-reclose**: Configurable auto-reclose functionality for temporary faults

### **Real-time Monitoring**
- **Electrical Measurements**: 3-phase current, voltage, power, power factor, frequency
- **Power Quality**: Harmonic distortion analysis and power quality monitoring
- **Condition Monitoring**: Temperature, operating hours, trip count tracking
- **Predictive Maintenance**: Maintenance alerts based on operating conditions

### **High-Performance Communication**
- **Dual-Path Architecture**: LwM2M (cloud) + Sparkplug B (edge) protocols
- **High-Throughput**: 1000+ messages/second per device
- **Real-time Control**: Remote breaker operation and protection configuration
- **Event Streaming**: Immediate trip notifications and alarm events

## 🏗️ **Architecture Overview**

```
┌─────────────────────────────────────────────────────────────────┐
│                    Smart Breaker                          │
│                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐ │
│  │   Protection    │    │   Monitoring    │    │   Control   │ │
│  │   Functions     │    │   & Analytics   │    │   Interface │ │
│  │                 │    │                 │    │             │ │
│  │ • Overcurrent   │    │ • Electrical    │    │ • Remote    │ │
│  │ • Ground Fault  │    │ • Power Quality │    │ • Auto-     │ │
│  │ • Arc Fault     │    │ • Condition     │    │   Reclose   │ │
│  │ • Thermal       │    │ • Predictive    │    │ • Settings  │ │
│  └─────────────────┘    └─────────────────┘    └─────────────┘ │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              FDI Device Description                         │ │
│  │  • Device Identity & Capabilities                           │ │
│  │  • Communication Protocols (LwM2M + Sparkplug B)           │ │
│  │  • Configuration Templates & Security                       │ │
│  │  • Diagnostic Tests & Alarm Definitions                     │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Communication Layer                          │
│                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐ │
│  │   LwM2M over    │    │   Sparkplug B   │    │   MQTT      │ │
│  │   MQTT          │    │   over MQTT     │    │   Broker    │ │
│  │                 │    │                 │    │             │ │
│  │ • Device Mgmt   │    │ • Edge Interop  │    │ • Message   │ │
│  │ • Cloud Stream  │    │ • Real-time     │    │   Routing   │ │
│  │ • Bulk Data     │    │ • High Through  │    │ • TLS       │ │
│  │ • Configuration │    │ • Event Driven  │    │ • Auth      │ │
│  └─────────────────┘    └─────────────────┘    └─────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Cloud & Edge Processing                      │
│                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐ │
│  │   LwM2M Server  │    │   Sparkplug     │    │   Redpanda  │ │
│  │                 │    │   Host          │    │   Connect   │ │
│  │ • Device Reg    │    │ • Edge Interop  │    │ • Data      │ │
│  │ • Management    │    │ • Command Proc  │    │   Streaming │ │
│  │ • Configuration │    │ • Event Routing │    │ • Analytics │ │
│  │ • Bulk Ops      │    │ • Monitoring    │    │ • Storage   │ │
│  └─────────────────┘    └─────────────────┘    └─────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## 📋 **FDI Device Description**

The smart breaker implements a comprehensive FDI device description (`device-profiles/smart-breaker.fdi`) that includes:

### **Device Identity**
- **Manufacturer**: Smart
- **Model**: XSeries-SmartBreaker
- **Type**: SmartCircuitBreaker
- **Category**: PowerDistribution/CircuitProtection
- **Version**: 2.1.0

### **Communication Protocols**

#### **LwM2M Objects**
- **Object 3**: Device Information
- **Object 4**: Connectivity Monitoring
- **Object 3200**: Smart Breaker (Custom)
- **Object 3201**: Protection Settings (Custom)

#### **Sparkplug B Template**
- **Device Metrics**: Identity, ratings, status
- **Breaker Metrics**: Electrical measurements, protection status
- **Protection Metrics**: Configuration settings, alarm status

### **Device Functions**
1. **Circuit Protection**: Overcurrent, ground fault, arc fault protection
2. **Power Monitoring**: Real-time electrical measurements and power quality
3. **Remote Control**: Remote breaker operation and control
4. **Predictive Maintenance**: Condition monitoring and maintenance alerts

### **Configuration Templates**
- **Standard Protection**: Typical industrial applications
- **High Sensitivity**: Critical applications requiring fast response
- **Motor Protection**: Motor-specific protection curves

## 🚀 **Quick Start**

### **1. Start the IoT Infrastructure**
```bash
# Start the base IoT environment
docker-compose up -d

# Verify services are running
docker-compose ps
```

### **2. Deploy Smart Breaker**
```bash
# Deploy single smart breaker
docker-compose -f docker-compose.smart-breaker.yml up smart-breaker -d

# Deploy smart breaker fleet (3 instances)
docker-compose -f docker-compose.smart-breaker.yml up smart-breaker-fleet -d
```

### **3. Monitor Device**
```bash
# View smart breaker logs
docker logs smart-breaker -f

# Access LwM2M server UI
open http://localhost:8080

# Access Redpanda Console
open http://localhost:8086
```

## ⚙️ **Configuration**

### **Environment Variables**

#### **Device Identity**
```bash
DEVICE_ID=smart-breaker-001
DEVICE_TYPE=SmartBreaker
DEVICE_MANUFACTURER=Smart
DEVICE_MODEL=XSeries-SmartBreaker-TypeB
```

#### **Electrical Ratings**
```bash
RATED_CURRENT=100.0          # Amperes
RATED_VOLTAGE=480.0          # Volts
RATED_FREQUENCY=60.0         # Hz
BREAKING_CAPACITY=25.0       # kA
POLE_COUNT=3                 # 1, 2, 3, or 4
PROTECTION_CLASS=TypeB       # TypeA, TypeB, TypeC, TypeD
```

#### **Protection Settings**
```bash
OVERCURRENT_PICKUP=100.0     # A
OVERCURRENT_DELAY=1000.0     # ms
GROUND_FAULT_PICKUP=5.0      # A
GROUND_FAULT_DELAY=500.0     # ms
ARC_FAULT_PICKUP=50.0        # A
ARC_FAULT_DELAY=100.0        # ms
THERMAL_PICKUP=120.0         # A
THERMAL_DELAY=300.0          # s
```

#### **Performance Settings**
```bash
TELEMETRY_INTERVAL=0.001     # 1000 msg/sec
LWM2M_INTERVAL=0.005         # 200 msg/sec
PROTECTION_MONITORING_INTERVAL=0.1  # 10 Hz
```

### **Configuration Files**

#### **Smart Breaker Config**
```bash
# Copy template
cp config.env.smart-breaker config.env

# Edit configuration
nano config.env
```

#### **FDI Device Profile**
The FDI device description is located at:
```
device-profiles/smart-breaker.fdi
```

## 📊 **Monitoring & Analytics**

### **Grafana Dashboards**
Access pre-configured dashboards at `http://localhost:3000`:

- **Smart Breaker Overview**: Real-time electrical measurements
- **Protection Status**: Protection function status and trip history
- **Power Quality**: Harmonic distortion and power factor analysis
- **Predictive Maintenance**: Operating hours, temperature, maintenance alerts

### **MQTT Topics**

#### **Sparkplug B Topics**
```
spBv1.0/IIoT/DBIRTH/smart-breaker-001    # Birth certificate
spBv1.0/IIoT/DDATA/smart-breaker-001     # Telemetry data
spBv1.0/IIoT/DCMD/smart-breaker-001      # Commands
spBv1.0/IIoT/DDEATH/smart-breaker-001    # Death certificate
```

#### **LwM2M Topics**
```
lwm2m/smart-breaker-001/reg              # Registration
lwm2m/smart-breaker-001/update           # Updates
lwm2m/smart-breaker-001/cmd/trip         # Trip command
lwm2m/smart-breaker-001/cmd/close        # Close command
lwm2m/smart-breaker-001/cmd/configure    # Configuration
```

### **Key Metrics**

#### **Electrical Measurements**
- **Current**: Phase A, B, C currents (A)
- **Voltage**: Phase A, B, C voltages (V)
- **Power**: Active, reactive, apparent power (kW, kVAR, kVA)
- **Power Factor**: Real-time power factor
- **Frequency**: System frequency (Hz)
- **Harmonic Distortion**: Total harmonic distortion (%)

#### **Protection Status**
- **Breaker Status**: Open, Closed, Tripped, Fault
- **Trip Count**: Total number of trips
- **Trip Reason**: Last trip reason (Overcurrent, GroundFault, ArcFault, Thermal)
- **Trip Current**: Current at trip (A)
- **Trip Delay**: Trip delay time (ms)

#### **Condition Monitoring**
- **Temperature**: Breaker temperature (°C)
- **Operating Hours**: Total operating hours
- **Load Percentage**: Current load as percentage of rated
- **Maintenance Due**: Maintenance alert flag
- **Communication Status**: Online, Offline, Degraded, Fault

## 🔧 **Advanced Features**

### **Protection Functions**

#### **Overcurrent Protection**
```python
# Example: Configure overcurrent protection
if max_current > overcurrent_pickup:
    if time_since_check > overcurrent_delay:
        trip_breaker("Overcurrent", max_current, delay)
```

#### **Ground Fault Protection**
```python
# Example: Ground fault detection
if ground_fault_current > ground_fault_pickup:
    if time_since_check > ground_fault_delay:
        trip_breaker("GroundFault", ground_fault_current, delay)
```

#### **Arc Fault Protection**
```python
# Example: Arc fault detection
if arc_fault_detected:
    if time_since_check > arc_fault_delay:
        trip_breaker("ArcFault", current, delay)
```

### **Auto-Reclose Function**
```python
# Example: Auto-reclose logic
if auto_reclose_enabled and attempts < max_attempts:
    timer = threading.Timer(auto_reclose_delay, auto_reclose)
    timer.start()
```

### **Predictive Maintenance**
```python
# Example: Maintenance condition checking
if (operating_hours > maintenance_hours or 
    trip_count > maintenance_trips or 
    temperature > maintenance_temp):
    maintenance_due = True
```

## 🛡️ **Security**

### **Security Levels**
- **Standard**: TLS, authentication, authorization, encryption
- **Enhanced**: Standard + certificate validation, access control
- **Critical**: Enhanced + audit logging, tamper detection

### **Access Control**
- **Administrator**: Full access to all functions
- **Operator**: Read, write, control access
- **Maintenance**: Read, write access
- **Viewer**: Read-only access

## 🔍 **Troubleshooting**

### **Common Issues**

#### **Connection Problems**
```bash
# Check MQTT connectivity
docker logs smart-breaker | grep "MQTT"

# Verify network connectivity
docker exec smart-breaker ping mosquitto
```

#### **Protection Issues**
```bash
# Check protection settings
docker exec smart-breaker env | grep PICKUP

# View protection logs
docker logs smart-breaker | grep "trip"
```

#### **Performance Issues**
```bash
# Monitor resource usage
docker stats smart-breaker

# Check message rates
docker logs smart-breaker | grep "msg/sec"
```

### **Diagnostic Tests**
The FDI device description includes diagnostic tests:
- **SelfTest**: Comprehensive hardware and software test
- **ProtectionTest**: Protection function validation
- **CommunicationTest**: Communication interface verification

## 📈 **Performance Metrics**

### **High-Throughput Results**
- **Sparkplug B**: 1000+ messages/second per device
- **LwM2M**: 200+ messages/second per device
- **Total Throughput**: 1200+ messages/second per device
- **Latency**: <10ms end-to-end

### **Scalability**
- **Single Device**: 1200+ msg/sec
- **Fleet (3 devices)**: 3600+ msg/sec
- **Large Deployment**: 10,000+ msg/sec across fleet

## 🔗 **Integration Examples**

### **FDI Host Integration**
```python
# Example: FDI host integration
from fdi_host import FDIHost

host = FDIHost()
device_package = host.load_device_package("smart-breaker.fdi")
device = host.register_device(device_package)

# Automatic configuration
host.configure_device(device, "StandardProtection")
```

### **LwM2M Management**
```python
# Example: LwM2M device management
import requests

# Get device information
response = requests.get("http://lwm2m-server:8080/api/devices/smart-breaker-001")
device_info = response.json()

# Send trip command
trip_command = {"command": "trip"}
requests.post("http://lwm2m-server:8080/api/devices/smart-breaker-001/command", 
              json=trip_command)
```

### **Sparkplug B Edge Interoperability**
```python
# Example: Edge device interaction
import paho.mqtt.client as mqtt

def on_message(client, userdata, msg):
    if "smart-breaker-001" in msg.topic:
        # Process breaker telemetry
        process_breaker_data(msg.payload)

client = mqtt.Client()
client.on_message = on_message
client.subscribe("spBv1.0/IIoT/DDATA/smart-breaker-001")
```

## 📚 **References**

### **Standards & Specifications**
- **FDI**: Field Device Integration standard (OPC Foundation)
- **LwM2M**: Lightweight M2M (OMA SpecWorks)
- **Sparkplug B**: MQTT-based industrial IoT protocol (Eclipse Tahu)
- **MQTT**: Message Queuing Telemetry Transport (OASIS)

### **Smart Breaker Documentation**
- **XSeries Smart Breaker**: Smart's intelligent circuit breaker series
- **Protection Functions**: Overcurrent, ground fault, arc fault protection
- **Communication Protocols**: Modbus, DNP3, IEC 61850, MQTT

### **Related Documentation**
- [FDI Device Integration Guide](https://opcfoundation.org/fdi/)
- [LwM2M Specification](https://omaspecworks.org/what-is-oma-specworks/iot/lightweight-m2m-lwm2m/)
- [Sparkplug B Specification](https://www.eclipse.org/tahu/spec/Sparkplug%20Topic%20Namespace%20and%20State%20ManagementV2.2-with%20appendix%20B%20format%20-%20Eclipse.pdf)

## 🤝 **Contributing**

This implementation demonstrates FDI compliance for smart breakers. To contribute:

1. **Fork the repository**
2. **Create a feature branch**
3. **Add your improvements**
4. **Submit a pull request**

### **Areas for Enhancement**
- **Additional Protection Functions**: Distance protection, differential protection
- **Advanced Analytics**: Machine learning for predictive maintenance
- **Edge Computing**: Local processing and decision making
- **Cloud Integration**: AWS IoT, Azure IoT Hub, Google Cloud IoT

---

**Note**: This implementation provides a comprehensive FDI-compliant smart breaker model that can be extended and customized for specific Smart breaker models and applications. 