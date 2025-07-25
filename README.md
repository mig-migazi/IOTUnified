# IoT Data Pipeline Configurations

This repository contains multiple IoT data pipeline configurations for different use cases, from simple cloud integrations to full-stack IoT environments.

## 🏗️ Available Configurations

### 1. **Pelion-Only** (`configs/pelion-only/`)
**Minimal cloud integration** - Connect to Pelion Device Management cloud and stream data to Redpanda.

- **Use Case**: Cloud-only IoT data streaming
- **Components**: Redpanda + Redpanda Connect + Pelion WebSocket
- **External Dependencies**: Pelion Device Management cloud
- **Ports**: 9093, 8087-8089, 4196

```bash
cd configs/pelion-only
./setup.sh
```

### 2. **Smart Breaker** (`configs/smart-breaker/`)
**FDI-compliant smart breaker simulation** with LwM2M and Sparkplug B communication.

- **Use Case**: Industrial IoT device simulation and testing
- **Components**: Smart Breaker Simulator + LwM2M Server + MQTT + Redpanda
- **Features**: FDI device integration, real-time monitoring, web demo
- **Ports**: 1883, 5684, 8080, 8088, 9092, 8084-8086

```bash
cd configs/smart-breaker
docker-compose up -d
```

### 3. **Full Stack** (`configs/full-stack/`)
**Complete IoT environment** with multiple protocols, monitoring, and device simulators.

- **Use Case**: Comprehensive IoT development and testing
- **Components**: All services (LwM2M, MQTT, Sparkplug B, Redpanda, monitoring)
- **Features**: Multi-protocol support, device simulation, monitoring dashboards
- **Ports**: 1883, 5684, 8080, 8088, 9092, 8084-8086, 4195

```bash
cd configs/full-stack
docker-compose up -d
```

### 4. **FDI Components** (`fdi/`)
**Industrial IoT device integration** - Complete FDI (Field Device Integration) implementation with web interface.

- **Use Case**: Industrial device management and testing
- **Components**: FDI Web Demo + Device Driver + Device Profiles + Testing Suite
- **Features**: Interactive web interface, device simulation, command execution
- **Ports**: 8088 (Web Demo)

```bash
cd fdi
python3 fdi_web_demo.py
# Open http://localhost:8088
```

## 🚀 Quick Start

### Choose Your Configuration

1. **For Pelion cloud integration**:
   ```bash
   cd configs/pelion-only
   cp config.env.example config.env
   # Edit config.env with your PELION_API_KEY
   ./setup.sh
   ```

2. **For smart breaker testing**:
   ```bash
   cd configs/smart-breaker
   docker-compose up -d
   # Access web demo at http://localhost:8088
   ```

3. **For full IoT development**:
   ```bash
   cd configs/full-stack
   docker-compose up -d
   # Access all services and monitoring
   ```

4. **For FDI device management**:
   ```bash
   cd fdi
   python3 fdi_web_demo.py
   # Open http://localhost:8088 for interactive device management
   ```

## 📊 Monitoring

Each configuration provides monitoring capabilities:

- **Redpanda Console**: Web UI for topic monitoring (`http://localhost:8086`)
- **Topic Consumption**: Real-time data streaming
- **Service Logs**: Docker container logs for debugging

## 🔧 Configuration Management

### Environment Variables

Each configuration has its own `config.env` file:

- **Pelion-Only**: `PELION_API_KEY`, Redpanda settings
- **Smart Breaker**: Device simulation, MQTT, LwM2M settings
- **Full Stack**: Complete environment configuration

### Port Management

Each configuration uses different port ranges to avoid conflicts:

- **Pelion-Only**: 9092, 8084-8086, 4195
- **Smart Breaker**: 1883, 5684, 8080, 8088, 9092, 8084-8086
- **Full Stack**: All ports (can be customized)

## 📁 Project Structure

```
├── configs/
│   ├── pelion-only/          # Minimal cloud integration
│   │   ├── docker-compose.yml
│   │   ├── redpanda-connect-config.yaml
│   │   ├── config.env.example
│   │   ├── setup.sh
│   │   └── README.md
│   ├── smart-breaker/        # FDI smart breaker simulation
│   │   ├── docker-compose.yml
│   │   ├── config.env
│   │   └── README.md
│   └── full-stack/           # Complete IoT environment
│       ├── docker-compose.yml
│       ├── redpanda-connect-config.yaml
│       ├── config.env
│       └── README.md
├── device-simulator/         # Smart breaker simulator
├── fdi/                     # FDI components and web demo
│   ├── fdi_web_demo.py      # Interactive web interface
│   ├── device-profiles/     # FDI device definitions
│   ├── fdi-device-driver/   # FDI driver implementation
│   └── templates/           # Web demo templates
├── lwm2m-server/            # LwM2M server implementation
├── scripts/                 # Utility scripts
└── README.md               # This file
```

## 🛠️ Development

### Adding New Configurations

1. Create a new directory in `configs/`
2. Add `docker-compose.yml` and configuration files
3. Create `README.md` with usage instructions
4. Update this main README

### Customizing Existing Configurations

Each configuration is self-contained and can be customized:

- Modify `docker-compose.yml` for service changes
- Update `config.env` for environment variables
- Customize connector configurations for different data sources

## 📚 Documentation

- **Pelion-Only**: See `configs/pelion-only/README.md`
- **Smart Breaker**: See `configs/smart-breaker/README.md` and `SMART_BREAKER_README.md`
- **Full Stack**: See `configs/full-stack/README.md`
- **FDI Integration**: See `fdi/README.md` and `fdi/FDI_COMPLETE_README.md`
- **Redpanda Connectors**: See `REDPANDA_CONNECTORS_README.md`

## 🤝 Contributing

1. Choose the appropriate configuration for your use case
2. Follow the setup instructions in each configuration's README
3. Customize as needed for your specific requirements
4. Share improvements and new configurations

## 📄 License

This project is open source and available under the MIT License. 