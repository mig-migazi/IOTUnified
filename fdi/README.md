# FDI (Field Device Integration) Components

This directory contains all FDI-related components for industrial IoT device integration and management.

## 📁 Directory Structure

```
fdi/
├── README.md                    # This file
├── fdi_web_demo.py             # Interactive web demo for FDI workflow
├── fdi_client_demo.py          # FDI client demonstration
├── demo_fdi_configuration.py   # FDI configuration demo
├── test_fdi_*.py               # FDI testing scripts
├── FDI_*.md                    # FDI documentation
├── templates/                  # Web demo templates
├── fdi-device-driver/          # FDI device driver implementation
├── fdi-test-env/              # Python virtual environment for FDI testing
└── device-profiles/           # FDI device description files (.fdi)
```

## 🎯 Components Overview

### **Web Demo** (`fdi_web_demo.py`)
Interactive web interface for demonstrating FDI workflow:
- Load FDI device descriptions
- Execute device commands
- Real-time device monitoring
- Configuration management

**Usage:**
```bash
cd fdi
python3 fdi_web_demo.py
# Open http://localhost:8088
```

### **FDI Client** (`fdi_client_demo.py`)
Demonstrates how to load and parse FDI device descriptions:
- Parse `.fdi` files
- Extract device information
- List available commands
- Validate device descriptions

**Usage:**
```bash
cd fdi
python3 fdi_client_demo.py
```

### **Device Driver** (`fdi-device-driver/`)
Implementation of FDI device driver:
- FDI protocol implementation
- Device communication
- Command execution
- Status monitoring

### **Device Profiles** (`device-profiles/`)
FDI device description files:
- `smart-breaker.fdi` - Smart breaker device description
- Additional device profiles can be added here

### **Testing** (`test_fdi_*.py`)
Comprehensive test suite for FDI components:
- `test_fdi_parsing.py` - Test FDI file parsing
- `test_fdi_driver.py` - Test device driver functionality
- `test_fdi_driver_simple.py` - Simple driver tests

## 🚀 Quick Start

### 1. Setup Environment
```bash
cd fdi
python3 -m venv fdi-test-env
source fdi-test-env/bin/activate  # On Windows: fdi-test-env\Scripts\activate
pip install -r fdi-device-driver/requirements.txt
pip install flask flask-socketio structlog
```

### 2. Test FDI Parsing
```bash
python3 test_fdi_parsing.py
```

### 3. Run Web Demo
```bash
python3 fdi_web_demo.py
# Open browser: http://localhost:8088
```

### 4. Test Device Driver
```bash
python3 test_fdi_driver.py
```

## 📚 Documentation

- **FDI Complete Guide**: See `FDI_COMPLETE_README.md`
- **Demo Summary**: See `FDI_DEMO_SUMMARY.md`
- **Test Results**: See `FDI_TEST_RESULTS.md`

## 🔧 Development

### Adding New Device Profiles
1. Create a new `.fdi` file in `device-profiles/`
2. Follow the FDI standard format
3. Test with `test_fdi_parsing.py`
4. Update the web demo if needed

### Extending the Device Driver
1. Modify `fdi-device-driver/fdi_driver.py`
2. Add new commands and functionality
3. Update tests in `test_fdi_driver.py`
4. Test with the web demo

### Customizing the Web Demo
1. Modify `fdi_web_demo.py` for new features
2. Update templates in `templates/`
3. Add new device types and commands
4. Test the complete workflow

## 🎮 Interactive Features

### Web Demo Features
- **Device Loading**: Upload or select FDI files
- **Command Execution**: Trip, close, reset, configure devices
- **Real-time Monitoring**: Live device status updates
- **Configuration Display**: View and modify device settings

### Device Simulation
- **Realistic Behavior**: Simulates actual industrial devices
- **FDI Compliance**: Standardized device interface
- **Multi-Protocol Support**: Works with LwM2M and other protocols
- **Web Management**: Browser-based device control

## 🔍 Troubleshooting

### Common Issues
1. **Python Dependencies**: Ensure all required packages are installed
2. **FDI File Format**: Verify `.fdi` files follow the standard format
3. **Port Conflicts**: Check if port 8088 is available for the web demo
4. **Device Communication**: Ensure device simulators are running

### Testing
```bash
# Run all FDI tests
python3 test_fdi_parsing.py
python3 test_fdi_driver.py
python3 test_fdi_driver_simple.py

# Test web demo
python3 fdi_web_demo.py
curl http://localhost:8088/api/load-fdi
``` 