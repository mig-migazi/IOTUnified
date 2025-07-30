"""
FDI Communication Server - Protocol-Agnostic Bridge

This server acts as a bridge between FDI Host tools (via OPC UA) and various device protocols (MQTT, Modbus, etc.).
It implements the Communication Server Plugin pattern for FDI architecture.

Architecture:
- FDI Host (e.g., Siemens PDM) connects via OPC UA
- Devices connect via their native protocols (MQTT/SparkplugB, Modbus, etc.)
- This server bridges between them using protocol adapters
"""

import asyncio
import os
import time
import logging
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Any, Optional

# OPC UA for FDI Host communication
from asyncua import Server, ua

# MQTT for device communication
import paho.mqtt.client as mqtt

# Protobuf for Sparkplug B
try:
    import sys
    import os
    # Add the simulators directory to the Python path for protobuf import
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'simulators'))
    from proto import sparkplug_b_pb2
    PROTOBUF_AVAILABLE = True
except ImportError:
    PROTOBUF_AVAILABLE = False

# Structured logging
import structlog

# Configure structlog like the device simulator
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

@dataclass
class Device:
    """Generic device representation"""
    device_id: str
    device_type: str
    protocol: str  # e.g., "mqtt", "modbus", "opcua", "http"
    status: str = "offline"
    last_seen: float = 0
    metrics: Dict[str, Any] = None
    capabilities: Dict[str, Any] = None

class DeviceProtocolAdapter(ABC):
    """Abstract base class for device protocol adapters"""
    
    @abstractmethod
    async def start(self):
        """Start the adapter"""
        pass
    
    @abstractmethod
    async def stop(self):
        """Stop the adapter"""
        pass
    
    @abstractmethod
    async def discover_devices(self) -> List[Device]:
        """Discover devices on this protocol"""
        pass
    
    @abstractmethod
    async def get_device_data(self, device_id: str) -> Dict[str, Any]:
        """Get current data from a device"""
        pass
    
    @abstractmethod
    async def send_device_command(self, device_id: str, command: str, parameters: Dict[str, Any]):
        """Send command to a device"""
        pass

class MQTTAdapter(DeviceProtocolAdapter):
    """MQTT/Sparkplug B protocol adapter"""
    
    def __init__(self, mqtt_host: str = None, mqtt_port: int = None):
        # Use environment variables with same defaults as shared/main.py
        self.mqtt_host = mqtt_host or os.getenv("MQTT_BROKER_HOST", "localhost")
        self.mqtt_port = mqtt_port or int(os.getenv("MQTT_BROKER_PORT", "1883"))
        self.mqtt_client = None
        self.devices: Dict[str, Device] = {}
        self.mqtt_connected = False
        
        # Sparkplug B protobuf
        if PROTOBUF_AVAILABLE:
            self.sparkplug_b_pb2 = sparkplug_b_pb2
        else:
            logger.warning("Protobuf not available. Install: pip install protobuf")
            self.sparkplug_b_pb2 = None
    
    def debug_callback(self, client, userdata, msg):
        print("DEBUG: Callback called with topic:", msg.topic)
        logger.info("DEBUG: Callback called with topic")
        try:
            print("DEBUG: About to parse topic:", msg.topic)
            # Parse Sparkplug B topic
            topic_parts = msg.topic.split('/')
            print("DEBUG: Topic parts:", topic_parts)
            print("DEBUG: Checking if len(topic_parts) >= 4:", len(topic_parts) >= 4)
            if len(topic_parts) >= 4:
                print("DEBUG: Inside the if block")
                message_type = topic_parts[2]  # NBIRTH, DBIRTH, DDATA, etc.
                print("DEBUG: message_type =", message_type)
                node_id = topic_parts[3]
                print("DEBUG: node_id =", node_id)
                
                print("DEBUG: Checking if message_type == 'DDATA' and len(topic_parts) >= 4:", message_type == "DDATA" and len(topic_parts) >= 4)
                print("DEBUG: About to enter DDATA condition")
                print("DEBUG: message_type == 'DDATA':", message_type == "DDATA")
                print("DEBUG: len(topic_parts) >= 4:", len(topic_parts) >= 4)
                if message_type == "DDATA":
                    print("DEBUG: Inside DDATA condition block")
                    device_id = topic_parts[3]
                    print("DEBUG: device_id =", device_id)
                    print("DEBUG: Processing DDATA for device", device_id, "devices_count =", len(self.devices))
                    # Create device if it doesn't exist (in case we missed DBIRTH)
                    if device_id not in self.devices:
                        self.devices[device_id] = Device(
                            device_id=device_id,
                            device_type="smart_breaker",
                            protocol="mqtt",
                            status="online",
                            last_seen=time.time()
                        )
                        logger.info("Created device from DDATA", device_id=device_id, total_devices=len(self.devices))
                    else:
                        logger.info("Device already exists", device_id=device_id)
                        # Update timestamp
                        self.devices[device_id].last_seen = time.time()
        except Exception as e:
            logger.error("Error in debug callback", error=str(e))
    
    def start(self):
        """Start MQTT client - using same pattern as device simulator"""
        try:
            client_id = f"fdi-comm-server-{int(time.time())}-{id(self)}"
            logger.info("Creating MQTT client", client_id=client_id)
            self.mqtt_client = mqtt.Client(client_id=client_id)
            
            # Set up callbacks exactly like device simulator
            self.mqtt_client.on_connect = self._on_mqtt_connect
            self.mqtt_client.on_disconnect = self._on_mqtt_disconnect
            self.mqtt_client.on_message = self._on_mqtt_message
            
            # Connect to MQTT broker
            logger.info("Attempting to connect to MQTT broker", host=self.mqtt_host, port=self.mqtt_port)
            result = self.mqtt_client.connect(self.mqtt_host, self.mqtt_port, 60)
            if result != 0:
                raise Exception(f"MQTT connection failed with result {result}")
            
            # Start the loop exactly like device simulator
            self.mqtt_client.loop_start()
            logger.info("MQTT connect result", result=result)
            logger.info("MQTT loop started")
            
            # Wait for connection
            while not self.mqtt_connected:
                time.sleep(0.1)
            
            logger.info("MQTT adapter started")
            
        except Exception as e:
            logger.error("Failed to start MQTT adapter", error=str(e))
            raise
    
    def stop(self):
        """Stop MQTT client"""
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            logger.info("MQTT adapter stopped")
    
    async def discover_devices(self) -> List[Device]:
        """Return discovered devices"""
        print(f"MQTT ADAPTER: discover_devices() called, devices count: {len(self.devices)}")
        print(f"MQTT ADAPTER: devices keys: {list(self.devices.keys())}")
        devices_list = list(self.devices.values())
        print(f"MQTT ADAPTER: returning {len(devices_list)} devices")
        return devices_list
    
    async def get_device_data(self, device_id: str) -> Dict[str, Any]:
        """Get device data"""
        if device_id in self.devices:
            device = self.devices[device_id]
            return {
                "device_id": device.device_id,
                "device_type": device.device_type,
                "protocol": device.protocol,
                "status": device.status,
                "last_seen": device.last_seen,
                "metrics": device.metrics or {},
                "capabilities": device.capabilities or {}
            }
        return {}
    
    async def send_device_command(self, device_id: str, command: str, parameters: Dict[str, Any]):
        """Send command to device via MQTT"""
        if self.mqtt_client and device_id in self.devices:
            # Publish command to device
            topic = f"spBv1.0/IIoT/NCMD/{device_id}"
            
            # Create command message structure
            command_message = {
                "command": command,
                "parameters": parameters,
                "timestamp": int(time.time() * 1000)  # Current timestamp in milliseconds
            }
            
            # Send as JSON
            payload = json.dumps(command_message)
            self.mqtt_client.publish(topic, payload)
            
            logger.info("Command sent to device", device_id=device_id, command=command, parameters=parameters, topic=topic)
        else:
            logger.error("Cannot send command - MQTT client not available or device not found", 
                        device_id=device_id, mqtt_connected=self.mqtt_connected, device_exists=device_id in self.devices)
    
    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """MQTT connection callback - exactly like device simulator"""
        logger.info("MQTT connected", rc=rc)
        if rc == 0:
            self.mqtt_connected = True
            logger.info("MQTT connection flag set to True")
            
            # Subscribe to Sparkplug B topics
            logger.info("Subscribing to MQTT topics")
            client.subscribe("spBv1.0/+/+/NBIRTH/#")
            client.subscribe("spBv1.0/+/DBIRTH/+")
            client.subscribe("spBv1.0/+/DDATA/+")
            client.subscribe("spBv1.0/+/+/NDEATH/#")
            client.subscribe("spBv1.0/+/+/DDEATH/#")
            logger.info("MQTT subscriptions completed")
        else:
            logger.error("MQTT connection failed", result_code=rc)
    
    def _on_mqtt_disconnect(self, client, userdata, rc):
        """MQTT disconnection callback"""
        self.mqtt_connected = False
        logger.info("MQTT disconnected", rc=rc)
    
    def _on_mqtt_message(self, client, userdata, msg):
        """MQTT message callback"""
        print("MQTT MESSAGE CALLBACK CALLED")  # Simple print for debugging
        print(f"Topic: {msg.topic}")  # Simple print for debugging
        logger.info("MQTT message received", topic=msg.topic, payload_length=len(msg.payload))
        logger.info("Message callback called successfully")
        try:
            print("STARTING MESSAGE PROCESSING")  # Simple print for debugging
            print("ABOUT TO PARSE TOPIC")  # NEW: Check if we reach this
            logger.info("Starting message processing")
            logger.info("About to split topic")
            # Parse Sparkplug B topic
            topic_parts = msg.topic.split('/')
            print(f"TOPIC PARTS: {topic_parts}")  # NEW: See the actual parts
            logger.info("Topic parts", parts=topic_parts)
            if len(topic_parts) >= 4:
                print(f"INSIDE LENGTH CHECK: {len(topic_parts)} >= 4")  # NEW
                message_type = topic_parts[2]  # NBIRTH, DBIRTH, DDATA, etc.
                node_id = topic_parts[3]
                print(f"MESSAGE TYPE: {message_type}, NODE ID: {node_id}")  # NEW
                logger.info("Processing message", message_type=message_type, node_id=node_id)
                
                if message_type == "NBIRTH":
                    self._handle_node_birth(node_id, msg.payload)
                elif message_type == "DBIRTH" and len(topic_parts) >= 5:
                    device_id = topic_parts[4]
                    self._handle_device_birth(node_id, msg.payload, device_id)
                elif message_type == "DDATA" and len(topic_parts) >= 4:
                    print("INSIDE DDATA CONDITION!")  # NEW
                    device_id = topic_parts[3]
                    print(f"DEVICE ID: {device_id}")  # NEW
                    # Create device if it doesn't exist (in case we missed DBIRTH)
                    print(f"CHECKING IF DEVICE EXISTS: {device_id} in {list(self.devices.keys())}")  # NEW
                    if device_id not in self.devices:
                        print("CREATING NEW DEVICE!")  # NEW
                        # Create device with basic info - capabilities will come from FDI package
                        self.devices[device_id] = Device(
                            device_id=device_id,
                            device_type="smart_breaker",
                            protocol="mqtt",
                            status="online",
                            last_seen=time.time(),
                            metrics={
                                "Breaker/Status": 1,  # Closed
                                "Breaker/CurrentPhaseA": 15.2,
                                "Breaker/VoltagePhaseA": 120.5,
                                "Breaker/ActivePower": 1829.6,
                                "Breaker/Temperature": 45.3,
                                "Breaker/Frequency": 60.0,
                                "Breaker/TripCount": 0,
                                "Breaker/OperatingHours": 8760,
                                "Breaker/LoadPercentage": 75.5,
                                "Breaker/RemoteControlEnabled": True,
                                "Breaker/AutoRecloseEnabled": False,
                                "Device/Type": "SmartCircuitBreaker",
                                "Device/Manufacturer": "Smart",
                                "Device/Model": "XSeries-SmartBreaker",
                                "Device/SerialNumber": "ETN-XSB-001",
                                "Device/FirmwareVersion": "2.1.0"
                            },
                            capabilities={}  # Will be populated from FDI package
                        )
                        print(f"DEVICE CREATED! Total devices: {len(self.devices)}")  # NEW
                        logger.info("Created device from DDATA", device_id=device_id, total_devices=len(self.devices))
                    else:
                        print("DEVICE ALREADY EXISTS!")  # NEW
                        # Update timestamp for existing device
                        self.devices[device_id].last_seen = time.time()
                        logger.info("Updated device timestamp", device_id=device_id)
                    # Only try to parse protobuf if available
                    if PROTOBUF_AVAILABLE:
                        self._handle_device_data(node_id, msg.payload, device_id)
                    else:
                        # Just update the device timestamp
                        if device_id in self.devices:
                            self.devices[device_id].last_seen = time.time()
                            logger.info("Updated device timestamp", device_id=device_id)
                elif message_type == "NDEATH":
                    self._handle_node_death(node_id, msg.payload)
                elif message_type == "DDEATH" and len(topic_parts) >= 5:
                    device_id = topic_parts[4]
                    self._handle_device_death(node_id, msg.payload, device_id)
                    
        except Exception as e:
            logger.error("Error processing MQTT message", error=str(e))
    
    def _handle_node_birth(self, node_id: str, payload: bytes):
        """Handle node birth message"""
        try:
            logger.info("Node birth received", node_id=node_id)
            
            # Create or update device
            if node_id not in self.devices:
                self.devices[node_id] = Device(
                    device_id=node_id,
                    device_type="mqtt_device",
                    protocol="mqtt",
                    status="online",
                    last_seen=time.time()
                )
            else:
                self.devices[node_id].status = "online"
                self.devices[node_id].last_seen = time.time()
                
        except Exception as e:
            logger.error("Error handling node birth", node_id=node_id, error=str(e))
    
    def _handle_device_birth(self, node_id: str, payload: bytes, device_id: str):
        """Handle device birth message"""
        try:
            logger.info("Device birth received", node_id=node_id, device_id=device_id)
            
            # Create or update device
            if device_id not in self.devices:
                self.devices[device_id] = Device(
                    device_id=device_id,
                    device_type="mqtt_device",
                    protocol="mqtt",
                    status="online",
                    last_seen=time.time()
                )
            else:
                self.devices[device_id].status = "online"
                self.devices[device_id].last_seen = time.time()
                
        except Exception as e:
            logger.error("Error handling device birth", node_id=node_id, device_id=device_id, error=str(e))
    
    def _handle_device_data(self, node_id: str, payload: bytes, device_id: str):
        """Handle device data message"""
        print(f"DEBUG: _handle_device_data called for device {device_id}")
        try:
            if not PROTOBUF_AVAILABLE:
                print("DEBUG: Protobuf not available")
                logger.warning("Protobuf not available, cannot parse device data")
                return
            
            print("DEBUG: About to parse protobuf payload")
            # Parse Sparkplug B payload
            sparkplug_payload = self.sparkplug_b_pb2.Payload()
            sparkplug_payload.ParseFromString(payload)
            
            print(f"DEBUG: Parsed payload with {len(sparkplug_payload.metrics)} metrics")
            # Extract all metrics
            metrics = {}
            for metric in sparkplug_payload.metrics:
                value = self._extract_metric_value(metric)
                metrics[metric.name] = value
                print(f"DEBUG: Extracted metric {metric.name} = {value}")
                logger.info("Extracted metric", name=metric.name, value=value, datatype=metric.datatype)
            
            # Update device with all metrics (merge instead of replace)
            if device_id in self.devices:
                # Merge new metrics with existing ones instead of replacing
                if self.devices[device_id].metrics is None:
                    self.devices[device_id].metrics = {}
                self.devices[device_id].metrics.update(metrics)
                self.devices[device_id].last_seen = time.time()
                print(f"DEBUG: Updated device {device_id} with {len(metrics)} metrics (total: {len(self.devices[device_id].metrics)})")
                logger.info("Updated device with metrics", device_id=device_id, metrics_count=len(metrics), total_metrics=len(self.devices[device_id].metrics))
            else:
                print(f"DEBUG: Device {device_id} not found for data update")
                logger.warning("Device not found for data update", device_id=device_id)
                
        except Exception as e:
            print(f"DEBUG: Error in _handle_device_data: {str(e)}")
            logger.error("Error handling device data", device_id=device_id, error=str(e))
    
    def _handle_node_death(self, node_id: str, payload: bytes):
        """Handle node death message"""
        try:
            logger.info("Node death received", node_id=node_id)
            
            # Update device status
            if node_id in self.devices:
                self.devices[node_id].status = "offline"
                
        except Exception as e:
            logger.error("Error handling node death", node_id=node_id, error=str(e))
    
    def _handle_device_death(self, node_id: str, payload: bytes, device_id: str):
        """Handle device death message"""
        try:
            logger.info("Device death received", node_id=node_id, device_id=device_id)
            
            # Update device status
            if device_id in self.devices:
                self.devices[device_id].status = "offline"
                
        except Exception as e:
            logger.error("Error handling device death", node_id=node_id, device_id=device_id, error=str(e))
    
    def _extract_metric_value(self, metric) -> Any:
        """Extract value from Sparkplug B metric"""
        try:
            # Check which value field is set based on datatype
            datatype = metric.datatype

            # Map datatype to field names using correct Sparkplug B datatype values
            if datatype == 3:  # INT32
                return metric.int_value
            elif datatype == 4:  # INT64
                return metric.long_value
            elif datatype == 9:  # FLOAT
                return metric.float_value
            elif datatype == 10:  # DOUBLE
                return metric.double_value
            elif datatype == 11:  # BOOLEAN
                return metric.boolean_value
            elif datatype == 12:  # STRING
                return metric.string_value
            elif datatype == 17:  # BYTES
                return metric.bytes_value
            else:
                # Try to get any available value
                if hasattr(metric, 'int_value') and metric.int_value != 0:
                    return metric.int_value
                elif hasattr(metric, 'float_value') and metric.float_value != 0.0:
                    return metric.float_value
                elif hasattr(metric, 'boolean_value'):
                    return metric.boolean_value
                elif hasattr(metric, 'string_value') and metric.string_value:
                    return metric.string_value
                else:
                    return None
        except Exception as e:
            logger.error("Error extracting metric value", error=str(e))
            return None

class FDICommunicationServer:
    """Main FDI Communication Server that coordinates protocol adapters"""
    
    def __init__(self, 
                 opcua_host: str = "0.0.0.0", 
                 opcua_port: int = 4840):
        self.opcua_host = opcua_host
        self.opcua_port = opcua_port
        self.adapters: Dict[str, DeviceProtocolAdapter] = {}
        self.opcua_server = None
        self.idx = None
        
        # FDI package registry
        self.fdi_packages = {}
    
    def register_adapter(self, protocol: str, adapter: DeviceProtocolAdapter):
        """Register a protocol adapter"""
        self.adapters[protocol] = adapter
        logger.info("Registered protocol adapter", protocol=protocol)
    
    async def start(self):
        """Start the FDI Communication Server"""
        logger.info("Starting FDI Communication Server")
        
        # Start all protocol adapters
        for protocol, adapter in self.adapters.items():
            adapter.start()  # Remove await since MQTTAdapter.start() is not async
            logger.info("Started protocol adapter", protocol=protocol)
        
        # Start OPC UA server
        await self._start_opcua_server()
        
        # Start the OPC UA server
        logger.info("About to start OPC UA server...")
        try:
            await self.opcua_server.start()
            logger.info(f"OPC UA server started at opc.tcp://{self.opcua_host}:{self.opcua_port}")
        except Exception as e:
            logger.error(f"Failed to start OPC UA server: {e}")
            raise

        # Keep server running
        logger.info("FDI Communication Server running...")
        while True:
            await asyncio.sleep(1)
                
    async def _start_opcua_server(self):
        """Start the OPC UA server - simple working example"""
        print("=== STARTING OPC UA SERVER ===")
        try:
            # Create OPC UA server
            print("Creating OPC UA server...")
            self.opcua_server = Server()
            print("Initializing OPC UA server...")
            await self.opcua_server.init()
            print("OPC UA server initialized")
            
            # Set endpoint
            print("Setting endpoint...")
            self.opcua_server.set_endpoint(f"opc.tcp://{self.opcua_host}:{self.opcua_port}")
            print("Setting server name...")
            self.opcua_server.set_server_name("FDI_Communication_Server")
            
            # Create namespace
            print("Creating namespace...")
            uri = "http://fdi.communication.server"
            self.idx = await self.opcua_server.register_namespace(uri)
            print(f"Namespace registered with index: {self.idx}")
            
            # Get root node
            root = self.opcua_server.nodes.objects
            
            # Create simple address space
            print("Creating FDI object...")
            fdi_obj = await root.add_object(self.idx, "FDI")
            print(f"FDI object created: {fdi_obj}")
            
            # Create Devices folder
            self.devices_folder = await fdi_obj.add_object(self.idx, "Devices")
            print(f"Devices folder created: {self.devices_folder}")
            
            # Create Methods folder
            methods_folder = await fdi_obj.add_object(self.idx, "Methods")
            print(f"Methods folder created: {methods_folder}")
            
            # Create methods directly on the FDI object (like working example)
            discover_method = await fdi_obj.add_method(
                self.idx, "DiscoverDevices",
                self._discover_devices_method,
                [],  # input arguments
                [ua.VariantType.String]  # output arguments
            )
            print(f"DiscoverDevices method created: {discover_method}")
            
            # Create GetDeviceParameters method - using correct ua.VariantType
            get_params_method = await fdi_obj.add_method(
                self.idx, "GetDeviceParameters",
                self._get_device_parameters_method,
                [ua.VariantType.String],  # input arguments (device_id)
                [ua.VariantType.String]  # output arguments
            )
            print(f"GetDeviceParameters method created: {get_params_method}")
            
            # Create SetDeviceParameters method - using correct ua.VariantType
            set_params_method = await fdi_obj.add_method(
                self.idx, "SetDeviceParameters",
                self._set_device_parameters_method,
                [ua.VariantType.String, ua.VariantType.String],  # input arguments (device_id, parameters)
                [ua.VariantType.String]  # output arguments
            )
            print(f"SetDeviceParameters method created: {set_params_method}")
            
            # Create SendDeviceCommand method - using correct ua.VariantType
            send_command_method = await fdi_obj.add_method(
                self.idx, "SendDeviceCommand",
                self._send_device_command_method,
                [ua.VariantType.String, ua.VariantType.String, ua.VariantType.String],  # input arguments (device_id, command, parameters)
                [ua.VariantType.String]  # output arguments
            )
            print(f"SendDeviceCommand method created: {send_command_method}")
            
            # Create ParseFDIWritableParameters method
            parse_writable_method = await fdi_obj.add_method(
                self.idx, "ParseFDIWritableParameters",
                self._parse_fdi_writable_parameters_method,
                [ua.VariantType.String],  # input arguments (device_type)
                [ua.VariantType.String]  # output arguments
            )
            print(f"ParseFDIWritableParameters method created: {parse_writable_method}")

            # Create GetDeviceConfiguration method
            print("DEBUG: About to register GetDeviceConfiguration method...")
            
            # Create a bound method to ensure it's called on the correct instance
            async def bound_get_device_configuration_method(parent, device_id):
                return await self._get_device_configuration_method(parent, device_id)
            
            get_config_method = await fdi_obj.add_method(
                self.idx, "GetDeviceConfiguration",
                bound_get_device_configuration_method,
                [ua.VariantType.String],  # input arguments (device_id)
                [ua.VariantType.String]  # output arguments
            )
            print(f"DEBUG: GetDeviceConfiguration method created: {get_config_method}")
            
            # Start the server using async context manager
            print("Starting OPC UA server...")
            # Note: We'll use the async context manager in the main loop
            print("OPC UA server initialized successfully")
            
            logger.info("OPC UA server initialized successfully")
            
        except Exception as e:
            print(f"Error starting OPC UA server: {e}")
            logger.error("Failed to start OPC UA server", error=str(e))
            import traceback
            logger.error("OPC UA server traceback", traceback=traceback.format_exc())
            raise
    
    async def _discover_devices_method(self, parent):
        """OPC UA method handler for device discovery"""
        try:
            devices = await self.discover_devices()
            devices_json = json.dumps([{
                'device_id': device.device_id,
                'device_type': device.device_type,
                'protocol': device.protocol,
                'status': device.status,
                'last_seen': device.last_seen
            } for device in devices])
            return [ua.Variant(devices_json, ua.VariantType.String)]
        except Exception as e:
            logger.error("Error in discover devices method", error=str(e))
            return [ua.Variant(json.dumps([]), ua.VariantType.String)]
    
    async def _get_device_parameters_method(self, parent, device_id):
        """OPC UA method handler for getting device parameters"""
        print("=== METHOD HANDLER CALLED ===")  # NEW: Simple print to see if method is called
        print(f"DEBUG: _get_device_parameters_method called with device_id: {device_id}")
        try:
            print(f"DEBUG: Getting device data for: {device_id}")
            data = await self.get_device_data(device_id)
            print(f"DEBUG: Device data: {data}")
            result = [ua.Variant(json.dumps(data), ua.VariantType.String)]
            print(f"DEBUG: Returning result: {result}")
            return result
        except Exception as e:
            print(f"DEBUG: Error in _get_device_parameters_method: {str(e)}")
            logger.error("Error in get device parameters method", device_id=device_id, error=str(e))
            return [ua.Variant(json.dumps({}), ua.VariantType.String)]
    
    async def _get_device_configuration_method(self, parent, device_id):
        """Get current device configuration"""
        print("DEBUG: METHOD CALLED!")
        try:
            print(f"DEBUG: _get_device_configuration_method called with device_id: {device_id}")
            print(f"DEBUG: self.devices exists: {hasattr(self, 'devices')}")
            if hasattr(self, 'devices'):
                print(f"DEBUG: self.devices keys: {list(self.devices.keys())}")
            else:
                print("DEBUG: self.devices does not exist!")
                print(f"DEBUG: self attributes: {dir(self)}")
            
            # Extract device_id from Variant if needed
            if hasattr(device_id, 'Value'):
                device_id = device_id.Value
            
            device_id = str(device_id)
            logger.info(f"Getting configuration for device: {device_id}")
            
            # Get current configuration from device data
            if device_id in self.devices:
                device_data = self.devices[device_id]
                # Return current configuration as JSON string
                config_data = {
                    "protection": {
                        "overcurrent_pickup": device_data.metrics.get("Protection/OvercurrentPickup", 100.0),
                        "overcurrent_delay": device_data.metrics.get("Protection/OvercurrentDelay", 1000.0),
                        "ground_fault_pickup": device_data.metrics.get("Protection/GroundFaultPickup", 5.0),
                        "ground_fault_delay": device_data.metrics.get("Protection/GroundFaultDelay", 500.0),
                        "arc_fault_pickup": device_data.metrics.get("Protection/ArcFaultPickup", 50.0),
                        "arc_fault_delay": device_data.metrics.get("Protection/ArcFaultDelay", 100.0),
                        "thermal_pickup": device_data.metrics.get("Protection/ThermalPickup", 120.0),
                        "thermal_delay": device_data.metrics.get("Protection/ThermalDelay", 300.0),
                        "instantaneous_pickup": device_data.metrics.get("Protection/InstantaneousPickup", 800.0),
                        "auto_reclose_delay": device_data.metrics.get("Protection/AutoRecloseDelay", 5.0),
                        "enabled": device_data.metrics.get("Protection/Enabled", True)
                    },
                    "control": {
                        "remote_control_enabled": device_data.metrics.get("Breaker/RemoteControlEnabled", False),
                        "auto_reclose_enabled": device_data.metrics.get("Breaker/AutoRecloseEnabled", False),
                        "auto_reclose_attempts": device_data.metrics.get("Breaker/AutoRecloseAttempts", 1)
                    },
                    "monitoring": {
                        "measurement_interval": 1000,  # Default value
                        "harmonic_analysis": True,  # Default value
                        "power_quality_monitoring": True  # Default value
                    },
                    "maintenance": {
                        "maintenance_interval": 5000,  # Default value
                        "temperature_threshold": 75.0,  # Default value
                        "trip_count_threshold": 1000  # Default value
                    }
                }
                return [ua.Variant(json.dumps(config_data), ua.VariantType.String)]
            else:
                logger.warning(f"Device {device_id} not found")
                return [ua.Variant(json.dumps({}), ua.VariantType.String)]
        except Exception as e:
            logger.error(f"Error getting device configuration: {e}")
            return [ua.Variant(json.dumps({}), ua.VariantType.String)]
    
    def parse_fdi_writable_parameters(self, device_type: str) -> Dict[str, Any]:
        """Parse FDI package to extract writable parameters from DeviceFunctions and DeviceCommands"""
        print(f"DEBUG: Parsing FDI writable parameters for device type: {device_type}")
        if device_type not in self.fdi_packages:
            print(f"DEBUG: FDI package not found for device type: {device_type}")
            logger.warning("FDI package not found for device type", device_type=device_type)
            return {}
        
        fdi_file_path = self.fdi_packages[device_type]
        print(f"DEBUG: FDI file path: {fdi_file_path}")
        
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(fdi_file_path)
            root = tree.getroot()
            
            # Define namespace
            ns = {'fdi': 'http://www.opcfoundation.org/FDI/2011/Device'}
            
            writable_params = {
                'functions': {},
                'commands': {},
                'templates': {}
            }
            
            # Parse DeviceFunctions
            device_functions = root.findall('.//fdi:DeviceFunctions/fdi:Function', ns)
            for function in device_functions:
                func_name = function.get('name')
                func_category = function.get('category')
                func_desc = function.find('fdi:Description', ns)
                func_desc_text = func_desc.text if func_desc is not None else ""
                
                writable_params['functions'][func_name] = {
                    'category': func_category,
                    'description': func_desc_text,
                    'parameters': {}
                }
                
                # Parse function parameters
                parameters = function.findall('.//fdi:Parameter', ns)
                for param in parameters:
                    param_name = param.get('name')
                    param_type = param.get('type')
                    param_units = param.get('units', '')
                    param_range = param.get('range', '')
                    param_default = param.get('default', '')
                    
                    writable_params['functions'][func_name]['parameters'][param_name] = {
                        'type': param_type,
                        'units': param_units,
                        'range': param_range,
                        'default': param_default
                    }
            
            # Parse DeviceCommands
            device_commands = root.findall('.//fdi:DeviceCommands/fdi:Command', ns)
            for command in device_commands:
                cmd_name = command.get('name')
                cmd_desc = command.get('description', '')
                
                writable_params['commands'][cmd_name] = {
                    'description': cmd_desc,
                    'parameters': {}
                }
                
                # Parse command parameters
                parameters = command.findall('.//fdi:Parameter', ns)
                for param in parameters:
                    param_name = param.get('name')
                    param_type = param.get('type')
                    param_required = param.get('required', 'false').lower() == 'true'
                    param_default = param.get('default', '')
                    
                    writable_params['commands'][cmd_name]['parameters'][param_name] = {
                        'type': param_type,
                        'required': param_required,
                        'default': param_default
                    }
            
            # Parse ConfigurationTemplates
            templates = root.findall('.//fdi:ConfigurationTemplates/fdi:Template', ns)
            for template in templates:
                template_name = template.get('name')
                template_desc = template.find('fdi:Description', ns)
                template_desc_text = template_desc.text if template_desc is not None else ""
                
                writable_params['templates'][template_name] = {
                    'description': template_desc_text,
                    'settings': {}
                }
                
                # Parse template settings
                settings = template.findall('.//fdi:Setting', ns)
                for setting in settings:
                    setting_name = setting.get('name')
                    setting_value = setting.get('value')
                    setting_units = setting.get('units', '')
                    
                    # Convert value to appropriate type
                    try:
                        if setting_value.lower() == 'true':
                            setting_value = True
                        elif setting_value.lower() == 'false':
                            setting_value = False
                        elif '.' in setting_value:
                            setting_value = float(setting_value)
                        else:
                            setting_value = int(setting_value)
                    except (ValueError, AttributeError):
                        # Keep as string if conversion fails
                        pass
                    
                    # Store just the value directly (not as an object)
                    writable_params['templates'][template_name]['settings'][setting_name] = setting_value
            
            print(f"DEBUG: Parsed writable parameters: {writable_params}")
            return writable_params
            
        except Exception as e:
            print(f"DEBUG: Error parsing FDI writable parameters: {str(e)}")
            logger.error("Error parsing FDI writable parameters", device_type=device_type, error=str(e))
            return {}

    async def _set_device_parameters_method(self, parent, device_id, parameters_json):
        """OPC UA method handler for setting device parameters"""
        try:
            # Extract string value if device_id is a Variant
            if hasattr(device_id, 'Value'):
                device_id = device_id.Value
                print(f"DEBUG: Extracted device_id from Variant: {device_id}")
            
            parameters = json.loads(parameters_json)
            
            # Get writable parameters from FDI definition
            writable_params = self.parse_fdi_writable_parameters("SmartCircuitBreaker")
            
            # Validate parameters against FDI definition
            validated_params = {}
            for param_name, param_value in parameters.items():
                # Check if parameter is writable (in functions or commands)
                is_writable = False
                param_info = None
                
                # Check in functions
                for func_name, func_data in writable_params.get('functions', {}).items():
                    if param_name in func_data.get('parameters', {}):
                        is_writable = True
                        param_info = func_data['parameters'][param_name]
                        break
                
                # Check in commands
                for cmd_name, cmd_data in writable_params.get('commands', {}).items():
                    if param_name in cmd_data.get('parameters', {}):
                        is_writable = True
                        param_info = cmd_data['parameters'][param_name]
                        break
                
                if is_writable:
                    validated_params[param_name] = param_value
                    logger.info("Parameter validated as writable", device_id=device_id, param_name=param_name, param_value=param_value)
                else:
                    logger.warning("Parameter not writable according to FDI definition", device_id=device_id, param_name=param_name)
            
            if validated_params:
                # Send configuration command to device
                await self.send_device_command(device_id, "set_configuration", validated_params)
                logger.info("Configuration sent to device", device_id=device_id, parameters=validated_params)
                return [ua.Variant(json.dumps({"status": "success", "message": "Configuration applied"}), ua.VariantType.String)]
            else:
                logger.warning("No valid writable parameters found", device_id=device_id, parameters=parameters)
                return [ua.Variant(json.dumps({"status": "error", "message": "No valid writable parameters"}), ua.VariantType.String)]
                
        except Exception as e:
            logger.error("Error in set device parameters method", device_id=device_id, error=str(e))
            return [ua.Variant(json.dumps({"status": "error", "message": str(e)}), ua.VariantType.String)]
    
    async def _send_device_command_method(self, parent, device_id, command, parameters_json):
        """OPC UA method handler for sending device commands"""
        try:
            parameters = json.loads(parameters_json)
            
            await self.send_device_command(device_id, command, parameters)
            
            return [ua.Variant(json.dumps({"status": "success"}), ua.VariantType.String)]
        except Exception as e:
            logger.error("Error in send device command method", device_id=device_id, error=str(e))
            return [ua.Variant(json.dumps({"status": "error", "message": str(e)}), ua.VariantType.String)]
    
    async def _parse_fdi_writable_parameters_method(self, parent, device_type):
        """OPC UA method handler for parsing FDI writable parameters"""
        try:
            # Extract string value if device_type is a Variant
            if hasattr(device_type, 'Value'):
                device_type = device_type.Value
                print(f"DEBUG: Extracted device_type from Variant: {device_type}")
            
            # Parse writable parameters from FDI definition
            writable_params = self.parse_fdi_writable_parameters(device_type)
            
            # Return as JSON string
            result = json.dumps(writable_params)
            print(f"DEBUG: Returning writable parameters: {result}")
            
            return [ua.Variant(result, ua.VariantType.String)]
            
        except Exception as e:
            logger.error("Error in parse FDI writable parameters method", device_type=device_type, error=str(e))
            return [ua.Variant(json.dumps({}), ua.VariantType.String)]
    
    async def discover_devices(self) -> List[Device]:
        """Discover devices from all adapters"""
        print(f"FDI SERVER: discover_devices() called, adapters: {list(self.adapters.keys())}")
        all_devices = []
        for protocol, adapter in self.adapters.items():
            try:
                print(f"FDI SERVER: calling adapter.discover_devices() for protocol: {protocol}")
                devices = await adapter.discover_devices()
                print(f"FDI SERVER: adapter returned {len(devices)} devices")
                all_devices.extend(devices)
            except Exception as e:
                logger.error("Error discovering devices", protocol=protocol, error=str(e))
        print(f"FDI SERVER: total devices found: {len(all_devices)}")
        return all_devices
    
    async def get_device_data(self, device_id: str) -> Dict[str, Any]:
        """Get device data from appropriate adapter"""
        # Extract string value if device_id is a Variant
        if hasattr(device_id, 'Value'):
            device_id = device_id.Value
            print(f"DEBUG: Extracted device_id from Variant: {device_id}")
        
        print(f"DEBUG: get_device_data called for device_id: {device_id}")
        print(f"DEBUG: Available adapters: {list(self.adapters.keys())}")
        
        # Find which adapter has this device
        for protocol, adapter in self.adapters.items():
            try:
                print(f"DEBUG: Calling adapter.get_device_data for protocol: {protocol}")
                data = await adapter.get_device_data(device_id)
                print(f"DEBUG: Adapter returned data: {data}")
                
                if data:
                    # Add FDI capabilities to the device data
                    device_type = data.get("device_type", "smart_breaker")
                    print(f"DEBUG: Device type: {device_type}")
                    fdi_capabilities = self.parse_fdi_capabilities("SmartCircuitBreaker")
                    print(f"DEBUG: FDI capabilities: {fdi_capabilities}")
                    data["capabilities"] = fdi_capabilities
                    print(f"DEBUG: Final data to return: {data}")
                    return data
                else:
                    print(f"DEBUG: No data returned from adapter for protocol: {protocol}")
            except Exception as e:
                print(f"DEBUG: Error getting device data: {str(e)}")
                logger.error("Error getting device data", device_id=device_id, protocol=protocol, error=str(e))
        
        print(f"DEBUG: No data found for device_id: {device_id}")
        return {}
    
    async def send_device_command(self, device_id: str, command: str, parameters: Dict[str, Any]):
        """Send command to device via appropriate adapter"""
        # Find which adapter has this device
        for protocol, adapter in self.adapters.items():
            try:
                await adapter.send_device_command(device_id, command, parameters)
                return
            except Exception as e:
                logger.error("Error sending device command", device_id=device_id, protocol=protocol, error=str(e))
    
    def register_fdi_package(self, device_type: str, fdi_file_path: str):
        """Register FDI package for device type"""
        self.fdi_packages[device_type] = fdi_file_path
        logger.info("FDI package registered", device_type=device_type, fdi_file=fdi_file_path)
    
    def parse_fdi_capabilities(self, device_type: str) -> Dict[str, Any]:
        """Parse FDI package to extract device capabilities"""
        print(f"DEBUG: Parsing FDI capabilities for device type: {device_type}")
        if device_type not in self.fdi_packages:
            print(f"DEBUG: FDI package not found for device type: {device_type}")
            logger.warning("FDI package not found for device type", device_type=device_type)
            return {}
        
        fdi_file_path = self.fdi_packages[device_type]
        print(f"DEBUG: FDI file path: {fdi_file_path}")
        if not os.path.exists(fdi_file_path):
            print(f"DEBUG: FDI file not found: {fdi_file_path}")
            logger.warning("FDI file not found", file_path=fdi_file_path)
            return {}
        
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(fdi_file_path)
            root = tree.getroot()
            
            # Define namespace
            ns = {'fdi': 'http://www.opcfoundation.org/FDI/2011/Device'}
            
            capabilities = {}
            
            # Extract SparkplugB template metrics
            sparkplug_section = root.find('.//fdi:Protocol[@name="SparkplugB"]', ns)
            if sparkplug_section is not None:
                template = sparkplug_section.find('.//fdi:Template', ns)
                if template is not None:
                    for metric in template.findall('.//fdi:Metric', ns):
                        name = metric.get('name')
                        datatype = metric.get('datatype')
                        alias = metric.get('alias')
                        
                        if name and datatype:
                            # Convert SparkplugB datatypes to our format
                            if datatype == 'Float':
                                type_info = {'type': 'Float', 'units': self._get_units_from_name(name)}
                            elif datatype == 'Int32':
                                type_info = {'type': 'Integer', 'units': self._get_units_from_name(name)}
                            elif datatype == 'Boolean':
                                type_info = {'type': 'Boolean'}
                            elif datatype == 'String':
                                type_info = {'type': 'String'}
                            else:
                                type_info = {'type': datatype}
                            
                            capabilities[name] = type_info
            
            print(f"DEBUG: Parsed {len(capabilities)} capabilities from FDI package")
            logger.info("FDI capabilities parsed", device_type=device_type, capabilities_count=len(capabilities))
            return capabilities
            
        except Exception as e:
            print(f"DEBUG: Error parsing FDI package: {str(e)}")
            logger.error("Error parsing FDI package", device_type=device_type, error=str(e))
            return {}
    
    def _get_units_from_name(self, metric_name: str) -> str:
        """Extract units from metric name"""
        if 'Current' in metric_name:
            return 'A'
        elif 'Voltage' in metric_name:
            return 'V'
        elif 'Power' in metric_name:
            return 'W'
        elif 'Temperature' in metric_name:
            return '°C'
        elif 'Frequency' in metric_name:
            return 'Hz'
        elif 'Percentage' in metric_name or 'LoadPercentage' in metric_name:
            return '%'
        elif 'Time' in metric_name:
            return 's'
        elif 'Delay' in metric_name:
            return 'ms'
        elif 'Hours' in metric_name:
            return 'hours'
        return ''
    
    async def stop(self):
        """Stop the FDI Communication Server"""
        try:
            # Stop all adapters
            for protocol, adapter in self.adapters.items():
                adapter.stop()  # Remove await since MQTTAdapter.stop() is not async
            
            # Stop OPC UA server
            if self.opcua_server:
                await self.opcua_server.stop()
            
            logger.info("FDI Communication Server stopped")
            
        except Exception as e:
            logger.error("Error stopping FDI Communication Server", error=str(e))

async def main():
    """Main function to start the FDI Communication Server"""
    server = None
    try:
        # Create FDI Communication Server
        server = FDICommunicationServer()
        
        # Register MQTT adapter with environment variable configuration
        mqtt_adapter = MQTTAdapter()  # Uses environment variables automatically
        server.register_adapter("mqtt", mqtt_adapter)
        
        # Register FDI package
        server.register_fdi_package("SmartCircuitBreaker", "config/device-profiles/smart-breaker.fdi")
        
        # Start server (this will initialize and start the OPC UA server)
        await server.start()
                
    except Exception as e:
        logger.error("Error in main", error=str(e))
    finally:
        if server:
            await server.stop()

if __name__ == "__main__":
    asyncio.run(main()) 