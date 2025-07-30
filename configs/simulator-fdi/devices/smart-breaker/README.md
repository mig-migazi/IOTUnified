# Smart Breaker Device Simulator

This directory contains the configuration for testing the FDI workflow with a Smart Breaker device simulator.

## 🚀 **Quick Start**

```bash
cd configs/simulator-fdi/device-simulators/smart-breaker
docker-compose up -d
```

## 📋 **Services**

| Service | Port | Description |
|---------|------|-------------|
| `smart-breaker-simulator` | 8080 | Smart breaker device simulator with HTTP API |
| `smart-breaker-fdi-server` | 8081 | FDI Server with Local API adapter |
| `smart-breaker-web-demo` | 8082 | FDI Web Demo interface |

## 🔧 **Configuration**

### **Device Parameters**
- **Trip Current**: 100.0A
- **Nominal Current**: 80.0A  
- **Temperature Threshold**: 85.0°C
- **Voltage Threshold**: 480.0V
- **Power Factor**: 0.95
- **Frequency**: 60.0Hz

### **Device States**
- **Circuit Status**: `closed` | `open` | `tripped`
- **Trip Status**: `normal` | `overcurrent` | `overtemperature` | `overvoltage`
- **Maintenance Mode**: `true` | `false`

## 🧪 **Testing FDI Workflow**

### **1. Check Device Status**
```bash
curl http://localhost:8080/api/status
```

### **2. Discover Devices via FDI**
```bash
curl http://localhost:8081/api/devices
```

### **3. Get Device Parameters**
```bash
curl http://localhost:8081/api/devices/smart-breaker-001/parameters
```

### **4. Apply Configuration Template**
```bash
curl -X POST http://localhost:8081/api/devices/smart-breaker-001/templates/StandardConfig
```

### **5. Send Commands**
```bash
# Trip the breaker
curl -X POST http://localhost:8081/api/devices/smart-breaker-001/commands \
  -H "Content-Type: application/json" \
  -d '{"command": "trip", "parameters": {"reason": "overcurrent"}}'

# Reset the breaker
curl -X POST http://localhost:8081/api/devices/smart-breaker-001/commands \
  -H "Content-Type: application/json" \
  -d '{"command": "reset"}'

# Set maintenance mode
curl -X POST http://localhost:8081/api/devices/smart-breaker-001/commands \
  -H "Content-Type: application/json" \
  -d '{"command": "set_maintenance_mode", "parameters": {"enabled": true}}'
```

## 🌐 **Web Interface**

Access the FDI Web Demo at: http://localhost:8082

Features:
- Load Smart Breaker FDI device description
- Discover and configure devices
- Apply configuration templates
- Send commands to devices
- Real-time device status monitoring

## 📊 **Device API Endpoints**

### **GET /api/status**
Get current device status and configuration.

### **GET /api/configuration**
Get current device configuration parameters.

### **PUT /api/configuration**
Update device configuration parameters.

### **POST /api/commands**
Execute device commands.

## 🔍 **Troubleshooting**

### **Check Service Logs**
```bash
# Smart breaker simulator
docker logs smart-breaker-simulator

# FDI server
docker logs smart-breaker-fdi-server

# Web demo
docker logs smart-breaker-web-demo
```

### **Check Service Health**
```bash
# Device simulator
curl http://localhost:8080/api/status

# FDI server
curl http://localhost:8081/health
```

### **Common Issues**

1. **Port Conflicts**: Ensure ports 8080-8082 are available
2. **File Permissions**: Check that FDI device profile is readable
3. **Network Issues**: Verify containers can communicate on `simulator-network`

## 📁 **Files**

- `docker-compose.yml` - Container orchestration
- `config.env` - Environment variables
- `README.md` - This documentation

## 🔗 **Related Files**

- `../../../device-simulator/smart_breaker_simulator.py` - Device simulator
- `../../../fdi/device-profiles/smart-breaker.fdi` - FDI device description
- `../../../fdi/fdi-device-driver/fdi_server.py` - FDI server
- `../../../fdi/demos/fdi_web_demo.py` - Web demo interface 