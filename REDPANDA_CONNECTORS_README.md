# Redpanda Connect Connectors

This setup provides **dual-connector support** for both local testing and production cloud integration.

## 🔧 **Connector Types**

### **1. Local LwM2M Connector** (Testing)
- **Purpose**: Test with local smart breaker simulator
- **Source**: `http://lwm2m-server:8080/api/events`
- **Protocol**: HTTP polling
- **Topic**: `iot.telemetry.lwm2m`
- **Status**: ✅ Always active for local development

### **2. Pelion Cloud Connector** (Production)
- **Purpose**: Connect to Pelion Device Management cloud
- **Source**: `wss://api.us.east-1.mbedcloud.com/v2/notification/websocket`
- **Protocol**: WebSocket connection
- **Topic**: `iot.telemetry.pelion`
- **Status**: 🔒 Requires API key

## 🚀 **Setup Instructions**

### **Local Testing (Default)**
```bash
# Deploy local connector only
./scripts/deploy-redpanda-connector.sh
```

### **Pelion Cloud Integration**
```bash
# Set your Pelion API key
export PELION_API_KEY="your_pelion_api_key_here"

# Deploy both connectors
./scripts/deploy-redpanda-connector.sh
```

## 📊 **Monitoring**

### **Local Data**
```bash
# Monitor local LwM2M data
docker exec iot-redpanda rpk topic consume iot.telemetry.lwm2m --follow
```

### **Pelion Cloud Data**
```bash
# Monitor Pelion cloud data
docker exec iot-redpanda rpk topic consume iot.telemetry.pelion --follow
```

## 🔑 **Pelion API Key Setup**

1. **Get API Key**: Log into [Pelion Device Management](https://portal.mbedcloud.com/)
2. **Create API Key**: Navigate to Access Management → API Keys
3. **Set Environment**: `export PELION_API_KEY="your_key_here"`

## 📁 **Configuration Files**

- **`redpanda-connect-config.yaml`**: Main Redpanda Connect configuration
- **`pelion-connector-config.json`**: Pelion-specific connector settings
- **`scripts/deploy-redpanda-connector.sh`**: Deployment script

## 🔄 **Data Flow**

### **Local Testing**
```
Smart Breaker Simulator → LwM2M Server → HTTP Polling → Redpanda → iot.telemetry.lwm2m
```

### **Pelion Cloud**
```
Pelion Devices → Cloud WebSocket → Redpanda → iot.telemetry.pelion
```

## 🛠️ **Troubleshooting**

### **Local Connector Issues**
- Check LwM2M server: `curl http://localhost:8080/api/health`
- Verify topic exists: `docker exec iot-redpanda rpk topic list`

### **Pelion Connector Issues**
- Verify API key: `echo $PELION_API_KEY`
- Check WebSocket connection: `wscat -c "wss://api.us.east-1.mbedcloud.com/v2/notification/websocket"`

## 📈 **Benefits**

- **Dual Testing**: Test locally, deploy to cloud
- **Flexible**: Enable/disable connectors independently
- **Scalable**: Separate topics for different data sources
- **Production Ready**: Real cloud integration capabilities 