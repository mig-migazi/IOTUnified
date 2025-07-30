# FDI (Field Device Integration) Implementation

## Overview

This implementation provides a complete FDI (Field Device Integration) stack that enables standardized device integration, configuration, and management in industrial IoT environments. The solution demonstrates how FDI standards can be deployed on devices and gateways to provide infrastructure supporting the FDI standard.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              System Architecture                                │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              Development Environment                             │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                   │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐              │
│  │   Web UI        │    │   FDI Server    │    │   MQTT Broker   │              │
│  │   (Port 8080)   │◄──►│   (Port 4840)   │◄──►│   (Port 1883)   │              │
│  │                 │    │                 │    │                 │              │
│  │ • Device List   │    │ • OPC UA Server │    │ • Sparkplug B   │              │
│  │ • Parameters    │    │ • FDI Parser    │    │ • Topic Mgmt    │              │
│  │ • Configuration │    │ • MQTT Client   │    │ • Message Route │              │
│  │ • Commands      │    │ • Config Engine │    │                 │              │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘              │
│           │                       │                       │                      │
│           │                       │                       │                      │
│           ▼                       ▼                       ▼                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐  │
│  │                    Device Simulators                                      │  │
│  │                                                                           │  │
│  │  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐      │  │
│  │  │ Smart Breaker   │    │ Other Device    │    │ Legacy Device    │      │  │
│  │  │ Simulator       │    │ Simulator       │    │ Adapter         │      │  │
│  │  │                 │    │                 │    │                 │      │  │
│  │  │ • MQTT Client   │    │ • MQTT Client   │    │ • Protocol      │      │  │
│  │  │ • Telemetry     │    │ • Telemetry     │    │   Translation   │      │  │
│  │  │ • Commands      │    │ • Commands      │    │ • MQTT Bridge   │      │  │
│  │  │ • Config Store  │    │ • Config Store  │    │ • Legacy API    │      │  │
│  │  └─────────────────┘    └─────────────────┘    └─────────────────┘      │  │
│  └─────────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              Production Deployment                              │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              Device-Level FDI Support                           │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────────┐  │
│  │                    Physical Device                                        │  │
│  │                                                                           │  │
│  │  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐      │  │
│  │  │ FDI Server      │    │ MQTT Broker     │    │ Device App      │      │  │
│  │  │ (Port 4840)     │◄──►│ (Port 1883)     │◄──►│ (Internal)      │      │  │
│  │  │                 │    │                 │    │                 │      │  │
│  │  │ • OPC UA Server │    │ • Local Broker  │    │ • Hardware      │      │  │
│  │  │ • FDI Parser    │    │ • Sparkplug B   │    │   Interface     │      │  │
│  │  │ • MQTT Client   │    │ • Message Route │    │ • Telemetry     │      │  │
│  │  │ • Config Engine │    │                 │    │ • Commands      │      │  │
│  │  └─────────────────┘    └─────────────────┘    └─────────────────┘      │  │
│  └─────────────────────────────────────────────────────────────────────────────┘  │
│                                    │                                             │
│                                    ▼                                             │
│  ┌─────────────────────────────────────────────────────────────────────────────┐  │
│  │                    External Tools                                         │  │
│  │                                                                           │  │
│  │  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐      │  │
│  │  │ Siemens PDM     │    │ FieldCare       │    │ Custom OPC UA   │      │  │
│  │  │                 │    │                 │    │ Client           │      │  │
│  │  │ • Device Config │    │ • Device Config │    │ • Monitoring    │      │  │
│  │  │ • Diagnostics   │    │ • Diagnostics   │    │ • Control       │      │  │
│  │  │ • Maintenance   │    │ • Maintenance   │    │ • Integration   │      │  │
│  │  └─────────────────┘    └─────────────────┘    └─────────────────┘      │  │
│  └─────────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              Gateway Deployment                                 │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              Gateway with FDI Support                           │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────────┐  │
│  │                    Gateway Device                                         │  │
│  │                                                                           │  │
│  │  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐      │  │
│  │  │ FDI Server      │    │ MQTT Broker     │    │ Protocol        │      │  │
│  │  │ (Multi-device)  │◄──►│ (Centralized)   │◄──►│ Adapters        │      │  │
│  │  │                 │    │                 │    │                 │      │  │
│  │  │ • OPC UA Server │    │ • Multi-device  │    │ • Modbus        │      │  │
│  │  │ • FDI Parser    │    │ • Topic Mgmt    │    │ • Profinet      │      │  │
│  │  │ • MQTT Client   │    │ • Message Route │    │ • HART          │      │  │
│  │  │ • Config Engine │    │                 │    │ • Legacy        │      │  │
│  │  └─────────────────┘    └─────────────────┘    └─────────────────┘      │  │
│  └─────────────────────────────────────────────────────────────────────────────┘  │
│                                    │                                             │
│                                    ▼                                             │
│  ┌─────────────────────────────────────────────────────────────────────────────┐  │
│  │                    Connected Devices                                      │  │
│  │                                                                           │  │
│  │  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐      │  │
│  │  │ Device 1        │    │ Device 2        │    │ Device N        │      │  │
│  │  │ (Legacy)        │    │ (FDI-ready)     │    │ (Any Protocol)  │      │  │
│  │  │                 │    │                 │    │                 │      │  │
│  │  │ • Modbus        │    │ • MQTT Client   │    │ • Any Protocol  │      │  │
│  │  │ • HART          │    │ • Telemetry     │    │ • Adapter       │      │  │
│  │  │ • Profinet      │    │ • Commands      │    │ • Bridge        │      │  │
│  │  │ • Adapter       │    │ • Config Store  │    │ • Translation   │      │  │
│  │  └─────────────────┘    └─────────────────┘    └─────────────────┘      │  │
│  └─────────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────┘

```

## Architecture

### Core Components

#### 1. FDI Communication Server
- **Purpose**: Central hub that processes device data and exposes FDI capabilities via OPC UA
- **Protocols**: MQTT (device communication), OPC UA (client access)
- **Responsibilities**:
  - Device discovery and registration
  - Real-time data processing from MQTT devices
  - FDI package parsing and capability exposure
  - OPC UA method registration for FDI operations
  - Configuration management and validation

#### 2. Web UI (FDI Host Simulator)
- **Purpose**: Web-based interface for device management and configuration
- **Protocols**: OPC UA (server communication), HTTP (user interface)
- **Responsibilities**:
  - Device discovery and visualization
  - Real-time parameter monitoring
  - Dynamic configuration interface generation
  - Template application and command execution
  - FDI-driven UI generation

#### 3. Smart Breaker Simulator
- **Purpose**: Demonstrates FDI-compliant device behavior
- **Protocols**: MQTT (Sparkplug B), JSON commands
- **Responsibilities**:
  - FDI-compliant device simulation
  - Real-time telemetry generation
  - Configuration reception and application
  - Command processing and state management
  - Runtime parameter storage

### Separation of Concerns

#### Protocol Layer
- **MQTT Adapter**: Handles device communication using Sparkplug B protocol
- **OPC UA Server**: Exposes FDI capabilities to clients
- **HTTP Interface**: Provides web-based user access

#### Business Logic Layer
- **Device Management**: Handles device lifecycle and state
- **FDI Package Processing**: Parses and validates FDI definitions
- **Configuration Engine**: Manages device configuration and validation

#### Presentation Layer
- **Dynamic UI Generation**: Creates interfaces based on FDI definitions
- **Real-time Monitoring**: Displays live device data
- **Configuration Interface**: Provides FDI-driven configuration tools

## FDI Benefits

### Standardization
- **Unified Device Integration**: Consistent approach across different device types
- **Vendor Independence**: FDI packages define device capabilities independently
- **Interoperability**: Standard protocols enable multi-vendor environments

### Configuration Management
- **Dynamic Configuration**: UI adapts to device capabilities automatically
- **Template Support**: Predefined configurations for common scenarios
- **Validation**: FDI definitions ensure configuration validity
- **Runtime Updates**: Configuration changes applied without device restart

### Operational Efficiency
- **Zero-Coding Integration**: New devices integrated via FDI packages
- **Real-time Monitoring**: Live parameter tracking and visualization
- **Command Execution**: Direct device control through standardized interface
- **Predictive Maintenance**: Condition monitoring and alerting

## Implementation Details

### FDI Package Structure
```
smart-breaker.fdi
├── DeviceType: SmartCircuitBreaker
├── DeviceFunctions
│   ├── CircuitProtection (Safety)
│   ├── PowerMonitoring (Measurement)
│   ├── RemoteControl (Control)
│   └── PredictiveMaintenance (Analytics)
├── DeviceCommands
│   ├── TripBreaker
│   ├── CloseBreaker
│   └── ResetBreaker
└── ConfigurationTemplates
    ├── HighSensitivity
    ├── StandardOperation
    └── MaintenanceMode
```

### Device-to-FDI Mapping Architecture

The mapping between device capabilities and FDI requests happens through several layers:

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              Device-to-FDI Mapping                              │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              Physical Device                                    │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                   │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐              │
│  │ Hardware        │    │ Device          │    │ MQTT            │              │
│  │ Interface       │    │ Application     │    │ Communication   │              │
│  │                 │    │                 │    │                 │              │
│  │ • GPIO Pins     │    │ • Sensor Read   │    │ • Telemetry     │              │
│  │ • ADC Channels  │    │ • Actuator Ctrl │    │ • Commands      │              │
│  │ • I2C/SPI       │    │ • State Mgmt    │    │ • Config Store │              │
│  │ • UART          │    │ • Data Process  │    │ • Sparkplug B   │              │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘              │
│           │                       │                       │                      │
│           ▼                       ▼                       ▼                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐  │
│  │                    Device Data Model                                      │  │
│  │                                                                           │  │
│  │  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐      │  │
│  │  │ Raw Metrics     │    │ Processed Data  │    │ Device State    │      │  │
│  │  │                 │    │                 │    │                 │      │  │
│  │  │ • Current_A     │    │ • RMS Values    │    │ • Breaker Status│      │  │
│  │  │ • Voltage_B     │    │ • Calculated    │    │ • Trip Count    │      │  │
│  │  │ • Temperature   │    │   Parameters    │    │ • Alarm State   │      │  │
│  │  │ • Status Bits   │    │ • Filtered Data │    │ • Config Values │      │  │
│  │  └─────────────────┘    └─────────────────┘    └─────────────────┘      │  │
│  └─────────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              FDI Communication Server                            │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              Mapping Engine                                     │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                   │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐              │
│  │ MQTT Adapter    │    │ FDI Package     │    │ OPC UA Server   │              │
│  │                 │    │ Parser          │    │                 │              │
│  │ • Sparkplug B   │    │ • XML Parse     │    │ • Method        │              │
│  │ • Message Decode│    │ • Capability    │    │   Registration  │              │
│  │ • Topic Routing │    │   Extraction    │    │ • Data Model    │              │
│  │ • Device Data   │    │ • Validation    │    │ • Discovery     │              │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘              │
│           │                       │                       │                      │
│           ▼                       ▼                       ▼                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐  │
│  │                    Mapping Layer                                          │  │
│  │                                                                           │  │
│  │  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐      │  │
│  │  │ Device Data     │    │ FDI Definition  │    │ OPC UA          │      │  │
│  │  │ Translation     │    │ Mapping         │    │ Interface       │      │  │
│  │  │                 │    │                 │    │                 │      │  │
│  │  │ • Metric Names  │    │ • Function      │    │ • Methods       │      │  │
│  │  │ • Units Convert │    │   Mapping       │    │ • Properties    │      │  │
│  │  │ • Data Types    │    │ • Parameter     │    │ • Events        │      │  │
│  │  │ • Ranges        │    │   Validation    │    │ • Notifications │      │  │
│  │  └─────────────────┘    └─────────────────┘    └─────────────────┘      │  │
│  └─────────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              FDI Package (.fdi file)                            │
└─────────────────────────────────────────────────────────────────────────────────────┘

The FDI package serves as the **mapping contract** between device capabilities and FDI requests:

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              Mapping Examples                                   │
└─────────────────────────────────────────────────────────────────────────────────────┘

### 1. Device Metrics → FDI Parameters
```
Device Raw Data:          FDI Definition:           OPC UA Interface:
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│ Current_A: 15.2 │──────►│ Protection/      │──────►│ CurrentPhaseA   │
│ (ADC value)     │       │ OvercurrentPickup│       │ (Float, A)      │
│ Voltage_B: 230  │──────►│ Monitoring/      │──────►│ VoltagePhaseB   │
│ (raw voltage)   │       │ VoltagePhaseB    │       │ (Float, V)      │
│ Temp: 45        │──────►│ Monitoring/      │──────►│ Temperature     │
│ (raw temp)      │       │ Temperature      │       │ (Float, °C)     │
└─────────────────┘       └─────────────────┘       └─────────────────┘
```

### 2. Device Commands → FDI Commands
```
Device Actions:            FDI Definition:           OPC UA Methods:
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│ GPIO_Set(5,1)   │◄──────│ TripBreaker     │◄──────│ SendDeviceCommand│
│ (hardware)      │       │ (FDI command)   │       │ (OPC UA)        │
│ Relay_Control(1)│◄──────│ CloseBreaker    │◄──────│ SendDeviceCommand│
│ (actuator)      │       │ (FDI command)   │       │ (OPC UA)        │
└─────────────────┘       └─────────────────┘       └─────────────────┘
```

### 3. Configuration Templates → Device Settings
```
FDI Template:              Device Config:            Hardware Settings:
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│ HighSensitivity │──────►│ Protection/     │──────►│ ADC_Threshold   │
│ - Overcurrent:  │       │ OvercurrentPickup│       │ (hardware)      │
│   10A           │       │ - Value: 10A    │       │ Timer_Setting   │
│ - TripDelay:    │       │ - TripDelay:    │       │   0.1s          │
│   0.1s          │       │   0.1s          │       │ GPIO_Config     │
└─────────────────┘       └─────────────────┘       └─────────────────┘
```

### Mapping Process Flow

1. **Device Registration**:
   - Device sends birth certificate via MQTT (Sparkplug B)
   - FDI server receives and parses device data
   - FDI package validates device capabilities
   - OPC UA methods registered based on FDI definition

2. **Real-time Data Flow**:
   - Device sends telemetry via MQTT
   - FDI server maps raw data to FDI parameters
   - OPC UA clients receive standardized data
   - External tools see FDI-compliant interface

3. **Configuration Flow**:
   - External tool sends configuration via OPC UA
   - FDI server validates against FDI package
   - Configuration translated to device format
   - Device receives via MQTT commands

4. **Command Flow**:
   - External tool sends command via OPC UA
   - FDI server validates command against FDI definition
   - Command translated to device action
   - Device executes via MQTT command

### Key Benefits of This Mapping

- **Standardization**: All devices appear as FDI-compliant regardless of internal implementation
- **Validation**: FDI package ensures only valid operations are performed
- **Flexibility**: Device can change internal implementation without affecting external tools
- **Interoperability**: Multiple tools can work with the same device using standard FDI interface

## Multi-Protocol Support

The FDI Communication Server is designed to support multiple device protocols through the **DeviceProtocolAdapter** pattern. This allows devices using different communication protocols to be integrated into the same FDI framework.

### Protocol Adapter Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              Protocol Adapters                                   │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MQTT Adapter  │    │  Modbus Adapter │    │  OPC UA Adapter │    │   HTTP Adapter  │
│                 │    │                 │    │                 │    │                 │
│ • Sparkplug B   │    │ • RTU/TCP       │    │ • Client/Server │    │ • REST API      │
│ • Birth/Death   │    │ • Register Read │    │ • Method Calls  │    │ • JSON/XML      │
│ • Telemetry     │    │ • Write Commands│    │ • Data Access   │    │ • Web Services  │
│ • Commands      │    │ • Polling       │    │ • Events        │    │ • Polling       │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
           │                       │                       │                       │
           └───────────────────────┼───────────────────────┼───────────────────────┘
                                   ▼
                    ┌─────────────────────────────────────────────────────────────┐
                    │                    FDI Communication Server                │
                    │                                                           │
                    │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐  │
                    │  │ Protocol        │  │ FDI Package     │  │ OPC UA      │  │
                    │  │ Translation     │  │ Parser          │  │ Server      │  │
                    │  │                 │  │                 │  │             │  │
                    │  │ • Data Mapping  │  │ • XML Parse     │  │ • Methods   │  │
                    │  │ • Command       │  │ • Validation    │  │ • Properties│  │
                    │  │   Translation   │  │ • Capabilities  │  │ • Events    │  │
                    │  │ • Unit          │  │ • Templates     │  │ • Discovery │  │
                    │  │   Conversion    │  │                 │  │             │  │
                    │  └─────────────────┘  └─────────────────┘  └─────────────┘  │
                    └─────────────────────────────────────────────────────────────┘
```

### Supported Protocols

#### 1. MQTT/Sparkplug B (Current Implementation)
```python
class MQTTAdapter(DeviceProtocolAdapter):
    """MQTT/Sparkplug B protocol adapter"""
    
    async def discover_devices(self) -> List[Device]:
        # Discover devices via MQTT birth certificates
        # Parse Sparkplug B messages
        # Extract device capabilities
        
    async def get_device_data(self, device_id: str) -> Dict[str, Any]:
        # Get real-time data from MQTT topics
        # Parse Sparkplug B telemetry
        # Map to FDI parameters
        
    async def send_device_command(self, device_id: str, command: str, parameters: Dict[str, Any]):
        # Send commands via MQTT NCMD messages
        # Format as Sparkplug B commands
        # Validate against FDI definitions
```

#### 2. Modbus RTU/TCP Adapter (Example)
```python
class ModbusAdapter(DeviceProtocolAdapter):
    """Modbus RTU/TCP protocol adapter"""
    
    def __init__(self, modbus_host: str, modbus_port: int):
        self.modbus_client = ModbusTcpClient(modbus_host, modbus_port)
        self.device_registers = {}  # Map of device_id -> register mappings
        
    async def discover_devices(self) -> List[Device]:
        # Scan Modbus network for devices
        # Read device identification registers
        # Map register addresses to FDI parameters
        
    async def get_device_data(self, device_id: str) -> Dict[str, Any]:
        # Read Modbus registers
        # Convert raw values to FDI format
        # Apply scaling and units conversion
        
    async def send_device_command(self, device_id: str, command: str, parameters: Dict[str, Any]):
        # Write to Modbus holding registers
        # Validate register addresses
        # Apply FDI parameter mapping
```

#### 3. OPC UA Client Adapter (Example)
```python
class OPCUAAdapter(DeviceProtocolAdapter):
    """OPC UA client protocol adapter"""
    
    def __init__(self, opcua_url: str):
        self.opcua_client = Client(opcua_url)
        self.device_nodes = {}  # Map of device_id -> node mappings
        
    async def discover_devices(self) -> List[Device]:
        # Browse OPC UA server for devices
        # Read device information nodes
        # Map OPC UA nodes to FDI parameters
        
    async def get_device_data(self, device_id: str) -> Dict[str, Any]:
        # Read OPC UA variables
        # Convert data types to FDI format
        # Apply FDI parameter mapping
        
    async def send_device_command(self, device_id: str, command: str, parameters: Dict[str, Any]):
        # Call OPC UA methods
        # Validate method parameters
        # Apply FDI command mapping
```

#### 4. HTTP/REST Adapter (Example)
```python
class HTTPAdapter(DeviceProtocolAdapter):
    """HTTP/REST protocol adapter"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = aiohttp.ClientSession()
        
    async def discover_devices(self) -> List[Device]:
        # GET /devices endpoint
        # Parse JSON device list
        # Map REST resources to FDI parameters
        
    async def get_device_data(self, device_id: str) -> Dict[str, Any]:
        # GET /devices/{id}/data
        # Parse JSON response
        # Map to FDI parameter format
        
    async def send_device_command(self, device_id: str, command: str, parameters: Dict[str, Any]):
        # POST /devices/{id}/commands
        # Validate JSON payload
        # Apply FDI command mapping
```

### Protocol Translation Process

For any protocol, the translation follows this pattern:

```
Device Protocol Data → Protocol Adapter → FDI Mapping → OPC UA Interface
        ↓                    ↓                ↓                ↓
Modbus Registers    →   Raw Values    →   FDI Params   →   OPC UA Methods
OPC UA Variables   →   Node Values   →   FDI Params   →   OPC UA Methods
HTTP JSON Data     →   REST Response →   FDI Params   →   OPC UA Methods
```

### Adding New Protocol Support

To add support for a new protocol:

1. **Create Protocol Adapter**:
   ```python
   class NewProtocolAdapter(DeviceProtocolAdapter):
       async def discover_devices(self) -> List[Device]:
           # Implement device discovery for new protocol
           
       async def get_device_data(self, device_id: str) -> Dict[str, Any]:
           # Implement data retrieval for new protocol
           
       async def send_device_command(self, device_id: str, command: str, parameters: Dict[str, Any]):
           # Implement command sending for new protocol
   ```

2. **Register with FDI Server**:
   ```python
   server = FDICommunicationServer()
   server.register_adapter("new_protocol", NewProtocolAdapter())
   ```

3. **Define FDI Package**: Create `.fdi` file that maps the protocol's data model to FDI parameters

4. **Configure Device**: Update device to use the new protocol adapter

### Benefits of Multi-Protocol Support

- **Legacy Integration**: Connect existing Modbus, OPC UA, or HTTP devices
- **Protocol Flexibility**: Choose the best protocol for each device type
- **Gradual Migration**: Migrate devices to FDI without changing all at once
- **Vendor Independence**: Support devices from different vendors using different protocols
- **Scalability**: Add new protocols without changing the core FDI framework

## Smart Breaker Simulator

### Device Profile
- **Type**: SmartCircuitBreaker
- **Protocol**: MQTT (Sparkplug B)
- **Capabilities**: Protection, monitoring, control, maintenance

### Real-time Features
- **Live Telemetry**: Current, voltage, temperature, status updates every 30 seconds
- **State Management**: Breaker position, trip count, alarm status
- **Configuration Storage**: Runtime parameter storage with validation
- **Command Processing**: Trip, close, reset, configuration commands

### FDI Integration
- **Birth Certificate**: Announces device capabilities and current state
- **Parameter Mapping**: FDI parameters mapped to device metrics
- **Command Reception**: Processes MQTT commands for configuration and control
- **State Synchronization**: Maintains consistency between device state and FDI definitions

### Configuration Flow
1. **Discovery**: Device sends birth certificate with capabilities
2. **Monitoring**: Real-time telemetry provides current parameter values
3. **Configuration**: UI presents FDI-defined writable parameters
4. **Validation**: Configuration validated against FDI definitions
5. **Application**: Commands sent via MQTT, device state updated
6. **Verification**: Updated parameters reflected in next telemetry cycle

## Deployment Architecture

### Device-Level Deployment
- **FDI Communication Server**: Runs on device or edge gateway
- **MQTT Broker**: Local or cloud-based message broker
- **FDI Packages**: Device-specific capability definitions
- **Web UI**: Local or remote management interface

### Gateway Deployment
- **Protocol Translation**: Converts device protocols to FDI standard
- **Data Aggregation**: Collects data from multiple devices
- **Configuration Management**: Centralized device configuration
- **Monitoring**: Unified view of all connected devices

### Cloud Integration
- **Data Pipeline**: Real-time data streaming to cloud platforms
- **Analytics**: Advanced analytics and machine learning
- **Remote Management**: Cloud-based device management
- **Scalability**: Horizontal scaling for large device fleets

## Technology Stack

### Backend
- **Python**: Core implementation language
- **asyncua**: OPC UA server implementation
- **paho-mqtt**: MQTT client for device communication
- **FastAPI**: Web framework for REST APIs
- **structlog**: Structured logging

### Frontend
- **HTML/JavaScript**: Dynamic web interface
- **OPC UA Client**: Real-time data access
- **Chart.js**: Real-time data visualization

### Infrastructure
- **Mosquitto**: MQTT broker
- **Virtual Environment**: Python dependency management
- **Process Management**: Background service management

## Configuration Management

### FDI-Driven Configuration
- **Dynamic UI Generation**: Interface adapts to device capabilities
- **Parameter Validation**: FDI definitions ensure valid configurations
- **Template Support**: Predefined configurations for common scenarios
- **Real-time Updates**: Configuration changes applied immediately

### Configuration Flow
1. **FDI Package Parsing**: Device capabilities extracted from FDI files
2. **UI Generation**: Dynamic forms created based on writable parameters
3. **Current State Retrieval**: Real-time parameter values displayed
4. **Configuration Validation**: Changes validated against FDI definitions
5. **Command Execution**: Validated configurations sent to devices
6. **State Verification**: Updated parameters confirmed in telemetry

## Benefits for Industrial IoT

### Operational Excellence
- **Reduced Integration Time**: New devices integrated in hours, not weeks
- **Standardized Operations**: Consistent approach across device types
- **Real-time Visibility**: Live monitoring of all device parameters
- **Predictive Maintenance**: Condition monitoring and alerting

### Cost Optimization
- **Vendor Independence**: Avoid vendor lock-in through standardization
- **Reduced Training**: Consistent interfaces across device types
- **Faster Troubleshooting**: Standardized diagnostic capabilities
- **Scalable Operations**: Same tools work across device fleets

### Future-Proofing
- **Technology Evolution**: New capabilities added via FDI packages
- **Protocol Flexibility**: Support for emerging IoT protocols
- **Analytics Integration**: Standard data format enables advanced analytics
- **Cloud Integration**: Seamless cloud platform integration

## Conclusion

This FDI implementation demonstrates how standardized device integration can transform industrial IoT deployments. By providing a complete stack that supports FDI standards, organizations can achieve faster device integration, improved operational efficiency, and future-proof their IoT infrastructure.

The smart breaker simulator showcases how real devices can leverage this stack to provide FDI-compliant behavior, enabling seamless integration into larger industrial systems while maintaining vendor independence and operational flexibility.

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              Deployment Scenarios                                │
└─────────────────────────────────────────────────────────────────────────────────────┘

### 1. Device-Level FDI Support (Minimal Deployment)
**What a device needs to support FDI:**

```
┌─────────────────────────────────────────────────────────────────┐
│                    Device with FDI Support                    │
├─────────────────────────────────────────────────────────────────┤
│ • FDI Communication Server (Core)                             │
│   - OPC UA Server (port 4840)                                │
│   - MQTT Client (for device communication)                   │
│   - FDI Package Parser                                       │
│   - Configuration Engine                                     │
│                                                               │
│ • MQTT Broker (Mosquitto)                                    │
│   - Local broker (port 1883)                                 │
│   - Sparkplug B message handling                             │
│                                                               │
│ • Device Application                                         │
│   - MQTT client for telemetry                                │
│   - Command processing                                       │
│   - Configuration storage                                    │
└─────────────────────────────────────────────────────────────────┘
```

**External Tools (Optional):**
- Siemens PDM, FieldCare, or similar FDI host tools
- Custom OPC UA clients
- Web-based management interfaces

### 2. Gateway-Level Deployment
**For aggregating multiple devices:**

```
┌─────────────────────────────────────────────────────────────────┐
│                    Gateway with FDI Support                   │
├─────────────────────────────────────────────────────────────────┤
│ • FDI Communication Server (Multi-device)                    │
│   - Multiple device management                               │
│   - Protocol translation (Modbus, Profinet, etc.)            │
│   - Data aggregation                                         │
│                                                               │
│ • MQTT Broker (Centralized)                                  │
│   - Multi-device message routing                             │
│   - Topic management                                         │
│                                                               │
│ • Device Simulators/Connectors                               │
│   - Protocol adapters                                        │
│   - Legacy device integration                                │
└─────────────────────────────────────────────────────────────────┘
```

### 3. Development/Demo Environment
**Complete stack for testing and development:**

```
┌─────────────────────────────────────────────────────────────────┐
│                    Development Environment                     │
├─────────────────────────────────────────────────────────────────┤
│ • FDI Communication Server                                   │
│ • MQTT Broker (Mosquitto)                                    │
│ • Web UI (FDI Host Simulator)                               │
│   - Simulates Siemens PDM/FieldCare tools                    │
│   - Device discovery and management                          │
│   - Configuration interface                                  │
│ • Device Simulators                                          │
│   - Smart breaker simulator                                  │
│   - Other device types                                       │
└─────────────────────────────────────────────────────────────────┘
```

### Deployment Requirements

#### Minimal Device Requirements
**To make any device FDI-compliant, you need:**

1. **FDI Communication Server** (Core component)
   - Python 3.8+
   - `asyncua` (OPC UA server)
   - `paho-mqtt` (MQTT client)
   - `protobuf` (Sparkplug B messages)
   - FDI package file (.fdi)

2. **MQTT Broker** (Local or remote)
   - Mosquitto or any MQTT broker
   - Sparkplug B topic support
   - Port 1883 (default)

3. **Device Application**
   - MQTT client for telemetry
   - Command processing logic
   - Configuration storage

#### Optional Components
- **Web UI**: Only needed for development/testing
- **Cloud Integration**: Not applicable at this stage
- **External Tools**: Siemens PDM, FieldCare, etc.

#### Network Requirements
- **OPC UA**: Port 4840 (for external tools)
- **MQTT**: Port 1883 (device communication)
- **HTTP**: Port 8080 (Web UI, optional)
