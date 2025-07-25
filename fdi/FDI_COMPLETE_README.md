# Complete FDI Implementation - Smart Breaker IoT

This implementation provides a **complete FDI (Field Device Integration) solution** for standardizing IoT device configuration, with a focus on Eaton Smart Breakers. It includes a **FDI device driver** that enables FDI client applications to configure devices using modern IoT protocols (MQTT, LwM2M, Sparkplug B).

## 🎯 **What Was Missing - Now Complete**

### **1. FDI Device Driver Implementation** ✅
- **FDI Device Package Parser**: Reads and validates `.fdi` files
- **Device Discovery**: Automatic device detection via MQTT
- **Device Registration**: FDI-compliant device registration
- **Configuration Management**: Template-based device configuration
- **Protocol Translation**: MQTT/LwM2M/Sparkplug B to FDI interface

### **2. Device Communication** ✅
- **FDI Configuration Commands**: Devices understand and apply FDI templates
- **Configuration Response**: Devices report current configuration back
- **Template Application**: Devices apply StandardProtection, HighSensitivity, MotorProtection templates
- **Real-time Updates**: Configuration changes applied immediately

### **3. Complete Workflow** ✅
- **Device Discovery** → **Registration** → **Configuration** → **Monitoring** → **Control**

## 🏗️ **Complete Architecture**

### **FDI Device Driver Architecture**
```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              FDI Client Applications                                │
│                                                                                     │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────────────────┐ │
│  │   Siemens       │    │   ABB 800xA     │    │   Emerson                       │
│  │   PCS 7         │    │                 │    │   DeltaV                        │
│  │                 │    │                 │    │                                 │ │
│  │ • Loads .fdi    │    │ • Loads .fdi    │    │ • Loads .fdi                    │ │
│  │ • Calls driver  │    │ • Calls driver  │    │ • Calls driver                  │ │
│  │ • Configures    │    │ • Configures    │    │ • Configures                    │ │
│  │   devices       │    │   devices       │    │   devices                       │ │
│  └─────────────────┘    └─────────────────┘    └─────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼ FDI Device Driver Interface
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              FDI Device Driver                                      │
│                                                                                     │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────────────────┐ │
│  │   FDI Parser    │    │   Protocol      │    │   Device                        │ │
│  │                 │    │   Translator    │    │   Manager                       │ │
│  │ • Parse .fdi    │    │                 │    │                                 │ │
│  │ • Extract       │    │ • FDI Commands  │    │ • Device Discovery             │ │
│  │   Templates     │    │   → MQTT        │    │ • Configuration                │ │
│  │ • Parameters    │    │ • MQTT Data     │    │ • Status Monitoring            │ │
│  │                 │    │   → FDI Status  │    │ • Command Execution            │ │
│  └─────────────────┘    └─────────────────┘    └─────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼ MQTT (port 1883/8883)
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              MQTT Broker (Mosquitto)                                │
│                                                                                     │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────────────────┐ │
│  │   Discovery     │    │   Commands      │    │   Telemetry                     │ │
│  │                 │    │                 │    │                                 │ │
│  │ • DBIRTH        │    │ • LwM2M CMD     │    │ • DDATA                         │ │
│  │ • Registration  │    │ • Configure     │    │ • Telemetry                     │ │
│  │ • Status        │    │ • Trip/Close    │    │ • Alarms                        │ │
│  └─────────────────┘    └─────────────────┘    └─────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              Eaton Smart Breaker                                    │
│                                                                                     │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────────────────┐ │
│  │   Protection    │    │   Monitoring    │    │   Communication                 │ │
│  │   Functions     │    │   Functions     │    │                                 │ │
│  │                 │    │                 │    │ • LwM2M Objects (3, 4, 3200)    │ │
│  │ • Overcurrent   │    │ • Electrical    │    │ • Sparkplug B Template          │ │
│  │ • Ground Fault  │    │   Measurements  │    │ • FDI Configuration Handler     │ │
│  │ • Arc Fault     │    │ • Power Quality │    │ • MQTT Client                   │ │
│  │ • Thermal       │    │ • Condition     │    │ • Dual-Path Protocol            │ │
│  └─────────────────┘    └─────────────────┘    └─────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### **FDI Communication Flow**
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   FDI       │    │   FDI       │    │   MQTT      │    │   Smart     │
│   Client    │    │   Driver    │    │   Broker    │    │   Breaker   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
       │                   │                   │                   │
       │ 1. Load .fdi      │                   │                   │
       │    Package        │                   │                   │
       │──────────────────▶│                   │                   │
       │                   │                   │                   │
       │ 2. Discover       │                   │                   │
       │    Devices        │                   │                   │
       │──────────────────▶│                   │                   │
       │                   │ 3. Request        │                   │
       │                   │    Discovery      │                   │
       │                   │──────────────────▶│                   │
       │                   │                   │ 4. Publish        │
       │                   │                   │    Birth Cert     │
       │                   │                   │◀──────────────────│
       │                   │ 5. Return Device  │                   │
       │                   │    List           │                   │
       │◀──────────────────│                   │                   │
       │                   │                   │                   │
       │ 6. Configure      │                   │                   │
       │    Device         │                   │                   │
       │──────────────────▶│                   │                   │
       │                   │ 7. Send Config    │                   │
       │                   │    via MQTT       │                   │
       │                   │──────────────────▶│                   │
       │                   │                   │ 8. Apply Config   │
       │                   │                   │◀──────────────────│
       │                   │                   │                   │
       │ 9. Send Command   │                   │                   │
       │    (Trip/Close)   │                   │                   │
       │──────────────────▶│                   │                   │
       │                   │ 10. Send Command  │                   │
       │                   │    via MQTT       │                   │
       │                   │──────────────────▶│                   │
       │                   │                   │ 11. Execute       │
       │                   │                   │    Command        │
       │                   │                   │◀──────────────────│
       │                   │                   │                   │
       │ 12. Get Status    │                   │                   │
       │──────────────────▶│                   │                   │
       │                   │ 13. Request       │                   │
       │                   │    Status         │                   │
       │                   │──────────────────▶│                   │
       │                   │                   │ 14. Send Status   │
       │                   │                   │◀──────────────────│
       │                   │ 15. Return Status │                   │
       │◀──────────────────│                   │                   │
       │                   │                   │                   │
```

### **Device Configuration Templates**
```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              FDI Configuration Templates                            │
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐ │
│  │                        StandardProtection Template                              │ │
│  │                                                                                 │ │
│  │  • OvercurrentPickup: 100.0A                                                   │ │
│  │  • OvercurrentDelay: 1000.0ms                                                  │ │
│  │  • GroundFaultPickup: 5.0A                                                     │ │
│  │  • GroundFaultDelay: 500.0ms                                                   │ │
│  │  • ArcFaultPickup: 50.0A                                                       │ │
│  │  • ArcFaultDelay: 100.0ms                                                      │ │
│  │  • Use Case: Typical industrial applications                                   │ │
│  └─────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐ │
│  │                        HighSensitivity Template                                 │ │
│  │                                                                                 │ │
│  │  • OvercurrentPickup: 80.0A                                                    │ │
│  │  • OvercurrentDelay: 500.0ms                                                   │ │
│  │  • GroundFaultPickup: 2.0A                                                     │ │
│  │  • GroundFaultDelay: 200.0ms                                                   │ │
│  │  • ArcFaultPickup: 30.0A                                                       │ │
│  │  • ArcFaultDelay: 50.0ms                                                       │ │
│  │  • Use Case: Critical applications requiring fast response                     │ │
│  └─────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐ │
│  │                        MotorProtection Template                                 │ │
│  │                                                                                 │ │
│  │  • OvercurrentPickup: 120.0A                                                   │ │
│  │  • OvercurrentDelay: 2000.0ms                                                  │ │
│  │  • ThermalPickup: 120.0A                                                       │ │
│  │  • ThermalDelay: 300.0ms                                                       │ │
│  │  • InstantaneousPickup: 960.0A (8x overcurrent)                                │ │
│  │  • Use Case: Motor protection with thermal overload                            │ │
│  └─────────────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

## 🚀 **Quick Start - Complete Workflow**

### **1. Start the IoT Infrastructure**
```bash
# Start the base IoT environment
docker-compose up -d
```

### **2. Verify Services**
```bash
# Check all services are running
docker-compose ps

# Check MQTT broker is running
netstat -an | grep 1883
```

### **3. Test the FDI Device Driver**
```bash
# Run the FDI device driver example
cd fdi-device-driver
python fdi_driver.py
```

## 🔧 **Testing Options - No External Downloads Required**

### **Option 1: Use the Included Driver (Recommended)**
The implementation includes a complete FDI device driver that demonstrates all functionality:

```bash
cd fdi-device-driver
python fdi_driver.py
```

**What it does:**
- Loads the FDI device package (.fdi file)
- Discovers devices via MQTT
- Applies configuration templates
- Sends control commands
- Retrieves device status

### **Option 2: Use Real FDI Clients**
If you want to use real FDI client applications, here are some options:

#### **Commercial FDI Clients:**
1. **Siemens PCS 7** with FDI support
   - Load the FDI device driver
   - Point to your `.fdi` file
   - Configure devices through the PCS 7 interface

2. **ABB 800xA** with FDI support
   - Add the FDI device driver to the system
   - Import your `.fdi` device package
   - Use the 800xA FDI interface

3. **Emerson DeltaV** with FDI support
   - Install the FDI device driver
   - Load your device package
   - Configure through DeltaV FDI tools

#### **Using Siemens PCS 7 (Example):**
1. Install PCS 7 with FDI support
2. Add the FDI device driver to the system
3. Load your `.fdi` file: `device-profiles/eaton-smart-breaker.fdi`
4. Configure MQTT broker settings
5. Discover and configure devices through PCS 7

### **Option 3: Use Python FDI Driver Integration**
```python
# Install FDI driver
pip install -r fdi-device-driver/requirements.txt

# Use the FDI driver
from fdi_driver import create_fdi_driver

def test_fdi():
    driver = create_fdi_driver(
        fdi_package_path="device-profiles/eaton-smart-breaker.fdi",
        mqtt_broker_host="localhost",
        mqtt_broker_port=1883
    )
    
    # Discover devices
    devices = driver.discover_devices()
    print(f"Discovered devices: {devices}")
    
    # Apply configuration template
    if devices:
        success = driver.apply_configuration_template(devices[0], "StandardProtection")
        print(f"Configuration applied: {success}")
    
    driver.close()

test_fdi()
```

## 📋 **FDI Host Features**

### **FDI Parser** (`fdi_opcua_host.py`)
- **XML Parsing**: Reads OPC Foundation FDI device packages
- **Device Identity**: Extracts manufacturer, model, version information
- **Protocol Support**: Parses LwM2M objects and Sparkplug B templates
- **Configuration Templates**: Extracts StandardProtection, HighSensitivity, MotorProtection
- **Security Levels**: Parses Standard, Enhanced, Critical security configurations

### **OPC UA Server** (`fdi_opcua_host.py`)
- **FDI Address Space**: Compliant with FDI specification
- **Device Management Methods**: DiscoverDevices, RegisterDevice, ConfigureDevice, SendCommand, GetDeviceStatus
- **Device Packages**: Automatic loading and registration of .fdi files
- **Device Registration**: Dynamic device registration and management
- **Configuration Templates**: Template-based device configuration

### **Device Manager** (`fdi_opcua_host.py`)
- **MQTT Discovery**: Listens for device birth certificates and registrations
- **Automatic Registration**: Registers discovered devices with FDI host
- **Configuration Requests**: Requests current configuration from devices
- **Template Matching**: Matches devices to appropriate FDI device packages

## 🔧 **Device Communication**

### **FDI Configuration Handler** (`smart_breaker_simulator.py`)
The smart breaker now includes a complete FDI configuration handler:

```python
def _handle_fdi_configuration(self, command_data: Dict[str, Any]):
    """Handle FDI configuration commands"""
    template = command_data.get("template")
    settings = command_data.get("settings", {})
    
    if template == "StandardProtection":
        self._apply_standard_protection_settings(settings)
    elif template == "HighSensitivity":
        self._apply_high_sensitivity_settings(settings)
    elif template == "MotorProtection":
        self._apply_motor_protection_settings(settings)
    
    # Update LwM2M registration data
    self._update_lwm2m_configuration()
```

### **Configuration Templates**
The device applies different protection settings based on FDI templates:

- **StandardProtection**: Typical industrial applications
- **HighSensitivity**: Critical applications requiring fast response
- **MotorProtection**: Motor-specific protection curves

### **Configuration Response**
Devices report their current configuration back to the FDI host:

```python
def _send_current_configuration(self):
    """Send current configuration back to FDI host"""
    configuration = {
        "device_id": self.config.device_id,
        "configuration": {
            "overcurrent_pickup": self.config.overcurrent_pickup,
            "ground_fault_pickup": self.config.ground_fault_pickup,
            # ... all current settings
        }
    }
    self.mqtt_client.publish(f"lwm2m/{self.config.device_id}/config", 
                           json.dumps(configuration))
```

## 📊 **Complete API Reference**

### **OPC UA Methods**
```python
# Discover devices
result = await device_mgmt.call_method("DiscoverDevices", "all")

# Register device
success = await device_mgmt.call_method("RegisterDevice", 
                                       "Eaton_SmartCircuitBreaker", 
                                       "eaton-breaker-001")

# Configure device
success = await device_mgmt.call_method("ConfigureDevice", 
                                       "eaton-breaker-001", 
                                       "StandardProtection")

# Send command
success = await device_mgmt.call_method("SendCommand", 
                                       "eaton-breaker-001", 
                                       "trip", 
                                       "{}")

# Get device status
status = await device_mgmt.call_method("GetDeviceStatus", 
                                      "eaton-breaker-001")
```

### **OPC UA Address Space**
```
Root
└── FDI (Namespace: http://opcfoundation.org/FDI/2011/Device)
    └── DeviceManagement
        ├── DevicePackages
        │   └── Eaton_SmartCircuitBreaker
        │       ├── DeviceType
        │       ├── Manufacturer
        │       ├── Model
        │       ├── Version
        │       ├── Description
        │       └── ConfigurationTemplates
        │           ├── StandardProtection
        │           ├── HighSensitivity
        │           └── MotorProtection
        ├── Devices
        │   └── eaton-breaker-001
        │       ├── DeviceType
        │       ├── Manufacturer
        │       ├── Model
        │       ├── Version
        │       └── Status
        ├── Configuration
        ├── Discovery
        ├── DiscoverDevices (Method)
        ├── RegisterDevice (Method)
        ├── ConfigureDevice (Method)
        ├── SendCommand (Method)
        └── GetDeviceStatus (Method)
```

## 📚 **Standards Compliance**

### **OPC Foundation FDI**
- **Device Package Format**: Compliant with FDI 1.0 specification
- **XML Schema**: Validates against FDI device description schema
- **Protocol Support**: LwM2M and Sparkplug B protocol definitions
- **Configuration Templates**: Standardized configuration templates
- **OPC UA Communication**: Industry-standard OPC UA protocol

### **Industrial Standards**
- **IEC 61850**: Device communication standards
- **Modbus**: Legacy protocol support
- **DNP3**: Distributed Network Protocol support
- **MQTT**: Message Queuing Telemetry Transport
- **OPC UA**: Unified Architecture for industrial communication

## 🚀 **Deployment Options**

### **Single Host Deployment**
```bash
# Deploy single FDI host with smart breaker
docker-compose -f docker-compose.fdi.yml up -d
```

### **Fleet Deployment**
```bash
# Deploy multiple smart breakers
docker-compose -f docker-compose.fdi.yml up smart-breaker-fleet -d
```

### **Production Deployment**
```bash
# Deploy with production settings
docker-compose -f docker-compose.fdi.yml -f docker-compose.prod.yml up -d
```

## 🔍 **Troubleshooting**

### **Common Issues**

#### **1. FDI Host Not Starting**
```bash
# Check logs
docker-compose -f docker-compose.fdi.yml logs fdi-host

# Check port availability
netstat -an | grep 4840
```

#### **2. OPC UA Connection Issues**
```bash
# Test OPC UA connection
python -c "
import socket
s = socket.socket()
s.connect(('localhost', 4840))
print('OPC UA port is accessible')
s.close()
"
```

#### **3. Device Not Discovered**
```bash
# Check MQTT connection
docker-compose -f docker-compose.fdi.yml logs smart-breaker

# Check device registration
docker exec -it fdi-host python fdi_client_example.py
```

### **Debug Mode**
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
docker-compose -f docker-compose.fdi.yml up -d
```

## 🤝 **Contributing**

This implementation provides a complete FDI solution. To contribute:

1. **Fork the repository**
2. **Create a feature branch**
3. **Add your improvements**
4. **Submit a pull request**

### **Areas for Enhancement**
- **Additional Device Types**: Support for other industrial devices
- **Advanced Templates**: More sophisticated configuration templates
- **Cloud Integration**: AWS IoT, Azure IoT Hub integration
- **Edge Computing**: Local FDI host deployment
- **Security**: Enhanced OPC UA security policies
- **Performance**: High-throughput device management

---

## 📞 **Support**

For questions or issues:
1. Check the troubleshooting section above
2. Review the logs: `docker-compose -f docker-compose.fdi.yml logs`
3. Test with the included client: `python fdi_client_example.py`
4. Use external OPC UA clients for advanced testing

**No external downloads required** - everything you need is included in this implementation! 