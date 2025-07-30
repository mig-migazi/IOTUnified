# Simulator FDI Configuration

This configuration provides an **isolated setup for testing FDI workflows** with device simulators. It's **FDI-focused** and **decoupled** from the full IoT stack (MQTT, Redpanda, LwM2M, etc.).

## 🏗️ **Architecture**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FDI Web Demo  │    │   FDI Server    │    │ Device Simulator│
│   (Port 8082)   │◄──►│   (Port 8081)   │◄──►│   (Port 8080)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  FDI Driver     │
                    │ (Plugin-based)  │
                    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │ Local API       │
                    │ Adapter         │
                    └─────────────────┘
```

**Key Points:**
- **Isolated**: No MQTT, No Redpanda, No LwM2M
- **FDI-Focused**: Pure device simulation with FDI support
- **Simple**: Just device + FDI server + web demo

## 📁 **Directory Structure**

```
configs/simulator-fdi/
├── README.md                    # This file
├── docker-compose.yml           # Main configuration
├── setup.sh                     # Setup script
├── test-fdi-workflow.sh         # Test script
└── devices/                     # Device configurations
    ├── smart-breaker/           # Smart Breaker configuration
    │   ├── docker-compose.yml   # Smart breaker specific config
    │   ├── config.env           # Environment variables
    │   └── README.md            # Smart breaker documentation
    ├── motor-drive/             # Motor Drive configuration (example)
    │   ├── docker-compose.yml   # Motor drive specific config
    │   ├── config.env           # Environment variables
    │   ├── motor_drive_simulator.py  # Motor drive simulator
    │   ├── motor-drive.fdi      # FDI device description
    │   └── README.md            # Motor drive documentation
    └── valve-controller/        # Valve Controller configuration (example)
        ├── docker-compose.yml   # Valve controller specific config
        │   ├── config.env       # Environment variables
        │   ├── valve_controller_simulator.py  # Valve simulator
        │   ├── valve-controller.fdi  # FDI device description
        │   └── README.md        # Valve controller documentation
```

## 🚀 **Quick Start**

### **1. Start Smart Breaker Simulator**
```bash
cd configs/simulator-fdi
docker-compose up -d
```

### **2. Access Services**
- **Device Simulator API**: http://localhost:8080
- **FDI Server API**: http://localhost:8081
- **FDI Web Demo**: http://localhost:8082

### **3. Test FDI Workflow**
```bash
./test-fdi-workflow.sh
```

## 🔧 **How to Add a New Device Configuration**

### **Step 1: Create Device Configuration Directory**
```bash
mkdir -p configs/simulator-fdi/devices/your-device-name
cd configs/simulator-fdi/devices/your-device-name
```

### **Step 2: Create Device Configuration Files**

#### **A. Device Simulator Python File**
```python
# your_device_simulator.py
class YourDeviceSimulator:
    def __init__(self):
        self.device_id = "your-device-001"
        self.config = {}
    
    def get_configuration(self):
        return self.config
    
    def configure(self, parameters):
        self.config.update(parameters)
        return True
    
    def execute_command(self, command, parameters=None):
        # Implement device-specific commands
        return True
    
    def get_status(self):
        return {
            "device_id": self.device_id,
            "status": "online",
            "configuration": self.config
        }
```

#### **B. FDI Device Description File**
```xml
<!-- your-device.fdi -->
<?xml version="1.0" encoding="UTF-8"?>
<FDI xmlns="http://opcfoundation.org/FDI/2011/Device">
    <DeviceIdentity>
        <DeviceType>YourDeviceType</DeviceType>
        <DeviceRevision>1.0</DeviceRevision>
        <DeviceRevisionDate>2024-01-01</DeviceRevisionDate>
        <DeviceManufacturer>YourCompany</DeviceManufacturer>
        <DeviceModel>YourDeviceModel</DeviceModel>
        <DeviceSerialNumber>YOUR-001</DeviceSerialNumber>
        <DeviceVersion>1.0.0</DeviceVersion>
        <DeviceDescription>Your Device Description</DeviceDescription>
    </DeviceIdentity>
    
    <DeviceCapabilities>
        <Parameters>
            <Parameter name="parameter1" type="float" units="unit1"/>
            <Parameter name="parameter2" type="int" units="unit2"/>
        </Parameters>
    </DeviceCapabilities>
    
    <Configuration>
        <Templates>
            <Template name="StandardConfig">
                <Description>Standard configuration</Description>
                <Settings>
                    <Setting name="parameter1" value="100.0"/>
                    <Setting name="parameter2" value="50"/>
                </Settings>
            </Template>
        </Templates>
    </Configuration>
</FDI>
```

#### **C. Docker Compose Configuration**
```yaml
# docker-compose.yml
version: '3.8'

services:
  your-device-simulator:
    build: 
      context: .
      dockerfile: Dockerfile
    container_name: your-device-simulator
    environment:
      - DEVICE_ID=your-device-001
      - DEVICE_TYPE=YourDeviceType
      - DEVICE_MANUFACTURER=YourCompany
    volumes:
      - ./your_device_simulator.py:/app/your_device_simulator.py
      - ../../fdi/device-profiles:/app/device-profiles:ro
    ports:
      - "8080:8080"
    networks:
      - simulator-network

  fdi-server:
    build:
      context: ../../fdi/fdi-device-driver
    environment:
      - FDI_PACKAGE_PATH=/app/device-profiles/your-device.fdi
      - FDI_ADAPTER=local_api
      - DEVICE_MODULE=your_device_simulator
    volumes:
      - ../../fdi/device-profiles:/app/device-profiles:ro
      - .:/app/device-simulator:ro
    ports:
      - "8081:8081"
    depends_on:
      - your-device-simulator

networks:
  simulator-network:
    external: true
```

#### **D. Environment Configuration**
```bash
# config.env
DEVICE_ID=your-device-001
DEVICE_TYPE=YourDeviceType
DEVICE_MANUFACTURER=YourCompany
DEVICE_MODEL=YourDeviceModel
DEVICE_SERIAL_NUMBER=YOUR-001
DEVICE_FIRMWARE_VERSION=1.0.0

# Device-specific parameters
PARAMETER1=100.0
PARAMETER2=50
```

#### **E. Dockerfile**
```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install flask structlog

# Copy device simulator
COPY your_device_simulator.py .

# Create simple HTTP API for the simulator
COPY device_api.py .

EXPOSE 8080

CMD ["python", "device_api.py"]
```

### **Step 3: Create Device API (Optional)**
```python
# device_api.py
from flask import Flask, jsonify, request
from your_device_simulator import YourDeviceSimulator

app = Flask(__name__)
device = YourDeviceSimulator()

@app.route('/api/configuration', methods=['GET'])
def get_configuration():
    return jsonify(device.get_configuration())

@app.route('/api/configuration', methods=['PUT'])
def set_configuration():
    data = request.get_json()
    success = device.configure(data)
    return jsonify({"success": success})

@app.route('/api/commands', methods=['POST'])
def execute_command():
    data = request.get_json()
    success = device.execute_command(data['command'], data.get('parameters'))
    return jsonify({"success": success})

@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify(device.get_status())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
```

### **Step 4: Update Main Configuration**
```bash
# Copy your device files to the main directories
cp your_device_simulator.py ../../device-simulators/simulators/
cp your-device.fdi ../../fdi/device-profiles/
```

### **Step 5: Test Your Device**
```bash
# Start your device configuration
cd configs/simulator-fdi/devices/your-device-name
docker-compose up -d

# Test FDI workflow
curl http://localhost:8081/api/devices
curl http://localhost:8081/api/devices/your-device-001/status
```

## 📋 **Required Files for New Device**

| File | Purpose | Required |
|------|---------|----------|
| `your_device_simulator.py` | Device simulation logic | ✅ |
| `your-device.fdi` | FDI device description | ✅ |
| `docker-compose.yml` | Container configuration | ✅ |
| `config.env` | Environment variables | ✅ |
| `Dockerfile` | Container build instructions | ✅ |
| `device_api.py` | HTTP API for device | Optional |
| `README.md` | Device documentation | Recommended |

## 🔄 **Switching Between Devices**

### **Method 1: Environment Variables**
```bash
# Set device-specific environment
export FDI_PACKAGE_PATH=device-profiles/your-device.fdi
export DEVICE_MODULE=your_device_simulator

# Start FDI server
docker-compose up fdi-server
```

### **Method 2: Different Configurations**
```bash
# Start smart breaker
cd devices/smart-breaker
docker-compose up -d

# Start motor drive
cd devices/motor-drive  
docker-compose up -d
```

## 🧪 **Testing FDI Workflow**

### **1. Discover Devices**
```bash
curl http://localhost:8081/api/devices
```

### **2. Get Device Status**
```bash
curl http://localhost:8081/api/devices/your-device-001/status
```

### **3. Apply Configuration Template**
```bash
curl -X POST http://localhost:8081/api/devices/your-device-001/templates/StandardConfig
```

### **4. Send Command**
```bash
curl -X POST http://localhost:8081/api/devices/your-device-001/commands \
  -H "Content-Type: application/json" \
  -d '{"command": "start", "parameters": {"speed": 100}}'
```

## 🎯 **Benefits of This Structure**

✅ **Modular**: Each device simulator is self-contained  
✅ **Reusable**: Same FDI server works with any device  
✅ **Testable**: Can test FDI workflow without full IoT stack  
✅ **Extensible**: Easy to add new device types  
✅ **Clear**: Obvious what files are needed for new devices  

## 📚 **Examples**

See the `devices/` directory for complete examples:
- `smart-breaker/` - Smart circuit breaker configuration
- `motor-drive/` - Motor drive configuration (example)
- `valve-controller/` - Valve controller configuration (example)

## 🔗 **Related Files**

- `../../../device-simulators/simulators/smart_breaker_simulator.py` - Device simulator
- `../../../fdi/device-profiles/smart-breaker.fdi` - FDI device description
- `../../../fdi/fdi-device-driver/fdi_server.py` - FDI server
- `../../../fdi/demos/fdi_web_demo.py` - Web demo interface 