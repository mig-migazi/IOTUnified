# FDI Device Driver for MQTT/LwM2M/Sparkplug B Devices

This FDI device driver enables **FDI client applications** (like Siemens PCS 7, ABB 800xA, Emerson DeltaV) to configure devices that use modern IoT protocols (MQTT, LwM2M, Sparkplug B) instead of traditional fieldbus protocols (HART, Foundation Fieldbus, Profibus).

## 🎯 **What This Solves**

**Problem**: FDI clients can only configure devices using traditional fieldbus protocols, but your devices use modern IoT protocols.

**Solution**: This driver acts as a **bridge** that:
1. **Loads your `.fdi` device package file**
2. **Translates FDI commands to MQTT/LwM2M/Sparkplug B**
3. **Communicates with your devices using their native protocols**

## 🏗️ **How It Works**

### **Traditional FDI Architecture**
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FDI Client    │    │   FDI Engine    │    │   Field Device  │
│   (PCS 7)       │    │                 │    │   (HART/FF)     │
│                 │    │ • Loads .fdi    │    │                 │
│ • Device Config │───▶│ • Generates     │───▶│ • HART          │
│ • Parameters    │    │   driver        │    │ • Foundation    │
│ • Templates     │    │ • Commands      │    │   Fieldbus      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### **Our FDI Architecture**
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FDI Client    │    │   Our FDI       │    │   Your Device   │
│   (PCS 7)       │    │   Driver        │    │   (MQTT/LwM2M)  │
│                 │    │                 │    │                 │
│ • Device Config │───▶│ • Loads .fdi    │───▶│ • MQTT          │
│ • Parameters    │    │ • Translates    │    │ • LwM2M         │
│ • Templates     │    │   commands      │    │ • Sparkplug B   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 **Quick Start**

### **1. Install the Driver**
```bash
cd fdi-device-driver
pip install -r requirements.txt
```

### **2. Test the Driver**
```bash
# Run the example
python fdi_driver.py
```

### **3. Integrate with FDI Client**
```python
from fdi_driver import create_fdi_driver

# Create driver instance
driver = create_fdi_driver(
    fdi_package_path="device-profiles/smart-breaker.fdi",
    mqtt_broker_host="localhost",
    mqtt_broker_port=1883
)

# Use FDI interface methods
devices = driver.discover_devices()
driver.apply_configuration_template(devices[0], "StandardProtection")
driver.send_command(devices[0], "trip")
```

## 📋 **FDI Interface Methods**

The driver implements the standard FDI device driver interface:

### **Device Discovery**
```python
# Discover available devices
devices = driver.discover_devices()
# Returns: ["smart-breaker-001", "smart-breaker-002"]
```

### **Parameter Management**
```python
# Get device parameters
params = driver.get_device_parameters("smart-breaker-001")
# Returns: {"overcurrent_pickup": 100.0, "ground_fault_pickup": 5.0, ...}

# Set device parameters
success = driver.set_device_parameters("smart-breaker-001", {
    "overcurrent_pickup": 120.0,
    "ground_fault_pickup": 3.0
})
```

### **Configuration Templates**
```python
# Get available templates
templates = driver.get_available_templates()
# Returns: ["StandardProtection", "HighSensitivity", "MotorProtection"]

# Apply template
success = driver.apply_configuration_template("smart-breaker-001", "StandardProtection")
```

### **Device Control**
```python
# Send commands
success = driver.send_command("smart-breaker-001", "trip")
success = driver.send_command("smart-breaker-001", "close")
success = driver.send_command("smart-breaker-001", "reset")
```

### **Status Monitoring**
```python
# Get device status
status = driver.get_device_status("smart-breaker-001")
# Returns: {"device_id": "...", "communication_status": "online", ...}
```

## 🔧 **Integration with FDI Clients**

### **Siemens PCS 7 Integration**
```python
# In PCS 7 FDI configuration
fdi_driver_path = "/path/to/fdi_driver.py"
fdi_package_path = "/path/to/smart-breaker.fdi"
mqtt_broker = "192.168.1.100:1883"

# PCS 7 will load the driver and use it to configure devices
```

### **ABB 800xA Integration**
```python
# In 800xA FDI configuration
driver_config = {
    "driver_path": "/path/to/fdi_driver.py",
    "fdi_package": "/path/to/smart-breaker.fdi",
    "mqtt_broker": "192.168.1.100:1883",
    "mqtt_username": "device",
    "mqtt_password": "password"
}
```

### **Emerson DeltaV Integration**
```python
# In DeltaV FDI configuration
fdi_driver = {
    "type": "mqtt_lwm2m_sparkplug",
    "package_file": "/path/to/smart-breaker.fdi",
    "broker_host": "192.168.1.100",
    "broker_port": 1883,
    "security": "tls"
}
```

## 📊 **Device Communication**

### **MQTT Topics**
The driver communicates with devices using these MQTT topics:

```
# Device Discovery
fdi/discovery/request          # Request device discovery

# LwM2M Communication
lwm2m/{device_id}/reg         # Device registration
lwm2m/{device_id}/command     # Commands to device
lwm2m/{device_id}/config      # Configuration responses
lwm2m/{device_id}/status      # Status updates

# Sparkplug B Communication
spBv1.0/{group_id}/DBIRTH/{device_id}  # Device birth certificate
spBv1.0/{group_id}/DDATA/{device_id}   # Device data
spBv1.0/{group_id}/DCMD/{device_id}    # Device commands
```

### **Message Formats**
```json
// Configuration Command
{
    "command": "configure",
    "template": "StandardProtection",
    "settings": {
        "OvercurrentPickup": {"value": "100.0", "units": "A"},
        "GroundFaultPickup": {"value": "5.0", "units": "A"}
    },
    "timestamp": "2024-01-01T12:00:00Z"
}

// Device Response
{
    "device_id": "smart-breaker-001",
    "configuration": {
        "overcurrent_pickup": 100.0,
        "ground_fault_pickup": 5.0,
        "arc_fault_pickup": 50.0
    },
    "timestamp": "2024-01-01T12:00:01Z"
}
```

## 🛡️ **Security**

### **MQTT Security**
```python
# TLS/SSL Support
driver = create_fdi_driver(
    fdi_package_path="device-profiles/smart-breaker.fdi",
    mqtt_broker_host="localhost",
    mqtt_broker_port=8883,  # TLS port
    mqtt_username="device",
    mqtt_password="password",
    mqtt_use_tls=True
)
```

### **Authentication**
```python
# Username/Password Authentication
driver = create_fdi_driver(
    fdi_package_path="device-profiles/smart-breaker.fdi",
    mqtt_broker_host="localhost",
    mqtt_broker_port=1883,
    mqtt_username="fdi_client",
    mqtt_password="secure_password"
)
```

## 🔍 **Troubleshooting**

### **Common Issues**

#### **1. Device Not Discovered**
```bash
# Check MQTT connection
mosquitto_pub -h localhost -t "test/topic" -m "test message"

# Check device is publishing
mosquitto_sub -h localhost -t "spBv1.0/+/DBIRTH/+" -v
```

#### **2. Configuration Not Applied**
```bash
# Check device is receiving commands
mosquitto_sub -h localhost -t "lwm2m/+/command" -v

# Check device responses
mosquitto_sub -h localhost -t "lwm2m/+/config" -v
```

#### **3. Driver Connection Issues**
```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Test driver connection
driver = create_fdi_driver(...)
devices = driver.discover_devices()
print(f"Discovered devices: {devices}")
```

## 📚 **Standards Compliance**

### **FDI Compliance**
- **Device Package Format**: Compliant with FDI 1.0 specification
- **Parameter Interface**: Standard FDI parameter access methods
- **Template Support**: FDI configuration template application
- **Command Interface**: Standard FDI device command methods

### **Protocol Support**
- **MQTT**: Message Queuing Telemetry Transport
- **LwM2M**: Lightweight M2M device management
- **Sparkplug B**: Industrial IoT protocol over MQTT
- **TLS/SSL**: Secure communication support

## 🚀 **Deployment**

### **Development**
```bash
# Run locally
python fdi_driver.py
```

### **Production**
```bash
# Install as package
pip install -e .

# Use in FDI client
from fdi_device_driver import create_fdi_driver
driver = create_fdi_driver(...)
```

### **Docker**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY fdi_driver.py .
CMD ["python", "fdi_driver.py"]
```

## 🤝 **Contributing**

To contribute to this FDI device driver:

1. **Fork the repository**
2. **Create a feature branch**
3. **Add your improvements**
4. **Submit a pull request**

### **Areas for Enhancement**
- **Additional Protocols**: Support for CoAP, HTTP, WebSocket
- **Advanced Security**: Certificate-based authentication
- **Performance**: High-throughput device management
- **Monitoring**: Advanced device monitoring and diagnostics

---

## 📞 **Support**

For questions or issues:
1. Check the troubleshooting section above
2. Review the MQTT logs: `mosquitto_sub -h localhost -t "#" -v`
3. Test the driver: `python fdi_driver.py`
4. Check device communication: Monitor MQTT topics

This FDI device driver enables **true FDI compliance** for devices using modern IoT protocols! 