# Device Simulators

This directory contains device simulators for testing FDI workflows and IoT applications.

## 📁 **Structure**

```
device-simulators/
├── simulators/                  # Individual device simulators
│   ├── smart_breaker_simulator.py  # Smart breaker simulator
│   ├── motor_drive_simulator.py    # Motor drive simulator (future)
│   └── valve_controller_simulator.py # Valve controller simulator (future)
├── shared/                     # Shared infrastructure
│   ├── main.py                 # Generic high-performance simulator
│   ├── health_check.py         # Health check utilities
│   └── proto/                  # Protocol buffers
│       └── sparkplug_b.proto   # Sparkplug B protocol definition
├── Dockerfile                  # Container build instructions
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## 🚀 **Quick Start**

### **Run Smart Breaker Simulator**
```bash
cd device-simulators
docker build -t device-simulator .
docker run -p 8080:8080 device-simulator python simulators/smart_breaker_simulator.py
```

### **Run Generic Simulator**
```bash
cd device-simulators
docker build -t device-simulator .
docker run -p 8080:8080 device-simulator python shared/main.py
```

## 🔧 **Adding a New Device Simulator**

### **Step 1: Create Simulator File**
```python
# simulators/your_device_simulator.py
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

# Main execution
if __name__ == "__main__":
    simulator = YourDeviceSimulator()
    # Add your main loop here
```

### **Step 2: Create FDI Configuration**
```bash
mkdir -p configs/simulator-fdi/devices/your-device
cd configs/simulator-fdi/devices/your-device
```

Create the configuration files as documented in `configs/simulator-fdi/README.md`.

### **Step 3: Test Your Simulator**
```bash
# Test the simulator directly
python simulators/your_device_simulator.py

# Test with FDI
cd configs/simulator-fdi/devices/your-device
docker-compose up -d
```

## 📋 **Available Simulators**

### **Smart Breaker Simulator**
- **File**: `simulators/smart_breaker_simulator.py`
- **Purpose**: Simulates a smart circuit breaker with FDI support
- **Features**: Trip/Reset, configuration, monitoring
- **FDI Config**: `configs/simulator-fdi/devices/smart-breaker/`

### **Generic High-Performance Simulator**
- **File**: `shared/main.py`
- **Purpose**: Generic simulator with MQTT + LwM2M + Sparkplug B
- **Features**: High-throughput telemetry, dual-path communication
- **Use Case**: Full IoT stack testing

## 🔗 **Integration with FDI**

Each simulator can be integrated with the FDI workflow:

1. **Create FDI device description** (`.fdi` file)
2. **Configure FDI server** to use the simulator
3. **Test FDI workflow** via REST API or web demo

See `configs/simulator-fdi/README.md` for detailed FDI integration instructions.

## 🐳 **Docker Support**

### **Build Image**
```bash
docker build -t device-simulator .
```

### **Run with Custom Simulator**
```bash
docker run -p 8080:8080 device-simulator python simulators/your_device_simulator.py
```

### **Environment Variables**
```bash
docker run -e DEVICE_ID=my-device-001 -e DEVICE_TYPE=MyDevice device-simulator
```

## 📊 **Simulator Requirements**

All simulators should implement:

- **Configuration management** (get/set parameters)
- **Command execution** (device-specific commands)
- **Status reporting** (device state and health)
- **FDI compatibility** (if used with FDI workflow)

## 🔍 **Troubleshooting**

### **Common Issues**

1. **Import Errors**: Ensure `PYTHONPATH` includes the simulator directory
2. **Protocol Buffer Errors**: Run `protoc --python_out=shared shared/proto/sparkplug_b.proto`
3. **Docker Build Issues**: Check that all files are in the correct locations

### **Debug Mode**
```bash
# Run with debug logging
python -u simulators/smart_breaker_simulator.py --debug

# Run with Docker debug
docker run -it device-simulator python -u simulators/smart_breaker_simulator.py --debug
```

## 📚 **Examples**

See the `simulators/` directory for complete examples:
- `smart_breaker_simulator.py` - Complete smart breaker implementation
- `shared/main.py` - Generic high-performance simulator

## 🔗 **Related Documentation**

- `configs/simulator-fdi/README.md` - FDI workflow testing
- `fdi/README.md` - FDI implementation details
- `configs/pelion-only/README.md` - Pelion cloud integration 