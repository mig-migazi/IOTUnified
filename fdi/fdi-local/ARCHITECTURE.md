# FDI Architecture - OPC UA Primary Interface

## Overview
**OPC UA is the default and primary interface for configurators/operators.** MQTT adapters handle device communication via Sparkplug B protocol.

## Architecture Flow

```
┌─────────────────┐    OPC UA    ┌──────────────────┐    MQTT/Sparkplug B    ┌─────────────────┐
│   Configurator  │ ────────────► │   FDI Server     │ ─────────────────────► │   Smart Device  │
│   / Operator    │               │   (OPC UA)       │                        │   (Simulator)   │
└─────────────────┘               └──────────────────┘                        └─────────────────┘
         │                                  │                                          │
         │                                  │                                          │
         │                                  ▼                                          │
         │                        ┌──────────────────┐                                │
         │                        │   MQTT Adapter   │                                │
         │                        │   (Sparkplug B)  │                                │
         │                        └──────────────────┘                                │
         │                                  │                                          │
         └──────────────────────────────────┴──────────────────────────────────────────┘
```

## Protocol Roles

### OPC UA (Primary Interface)
- **Purpose**: Configuration and control interface for operators/configurators
- **Port**: 4840
- **Methods**: 
  - `DiscoverDevices()` - Find available devices
  - `GetDeviceParameters()` - Read device data
  - `SetDeviceParameters()` - Configure devices
  - `SendDeviceCommand()` - Send commands
  - `ParseFDIWritableParameters()` - Get configuration options

### MQTT/Sparkplug B (Device Communication)
- **Purpose**: Device discovery and data collection
- **Port**: 1883
- **Topics**: 
  - `spBv1.0/+/+/NBIRTH/#` - Node birth certificates
  - `spBv1.0/+/DBIRTH/+` - Device birth certificates
  - `spBv1.0/+/DDATA/+` - Device data
  - `spBv1.0/+/NCMD/+` - Commands to devices

## Configuration Priority

1. **OPC UA**: Always enabled (primary interface)
2. **MQTT Adapters**: Configurable based on device types
   - `default`: Smart breakers (Sparkplug B)
   - `industrial`: Factory devices
   - `building`: Building automation
   - `test`: Development/testing

## Usage Examples

### For Configurators/Operators:
```bash
# Connect to OPC UA server
opc.tcp://localhost:4840

# Discover devices
DiscoverDevices() → Returns list of available devices

# Get device parameters
GetDeviceParameters("smart-breaker-000") → Returns device data

# Configure device
SetDeviceParameters("smart-breaker-000", {"OvercurrentPickup": 150})
```

### For Device Communication:
```bash
# MQTT topics for device discovery
mosquitto_sub -t "spBv1.0/+/+/NBIRTH/#" -v

# Send command to device
mosquitto_pub -t "spBv1.0/IIoT/NCMD/smart-breaker-000" -m '{"command": "trip"}'
```

## Key Points

✅ **OPC UA is the primary interface** for configurators/operators  
✅ **MQTT handles device communication** via Sparkplug B  
✅ **Pluggable architecture** allows multiple MQTT adapters  
✅ **Configuration-driven** switching between adapter types  
✅ **Real-world protocols** used throughout  

## Testing the Architecture

1. **Start the system**: `./start.sh`
2. **Access OPC UA**: Connect to `opc.tcp://localhost:4840`
3. **Use Web UI**: `http://localhost:8080` (uses OPC UA client)
4. **Monitor MQTT**: `mosquitto_sub -t "spBv1.0/+/+/NBIRTH/#" -v`
5. **Switch adapters**: Edit `config/adapter_config.json` 