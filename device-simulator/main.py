#!/usr/bin/env python3
"""
Unified IoT Device Simulator
Demonstrates LwM2M 1.2 + Sparkplug B over single MQTT TLS connection
"""

import asyncio
import json
import logging
import os
import ssl
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Dict, List, Optional

import paho.mqtt.client as mqtt
from faker import Faker
import numpy as np
import structlog

# Import generated protobuf classes
try:
    from proto.sparkplug_b_pb2 import Payload, Metric, DataType
except ImportError:
    print("Protobuf bindings not found. Run: protoc --python_out=. proto/sparkplug_b.proto")
    exit(1)

# Configure structured logging
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
class DeviceConfig:
    """Device configuration parameters"""
    device_id: str
    device_type: str
    mqtt_broker_host: str
    mqtt_broker_port: int
    mqtt_username: str
    mqtt_password: str
    mqtt_use_tls: bool
    lwm2m_server_host: str
    lwm2m_server_port: int
    group_id: str
    sparkplug_namespace: str
    telemetry_interval: int
    lwm2m_interval: int

class DeviceSimulator:
    """Unified device simulator supporting LwM2M and Sparkplug B"""

    def __init__(self, config: DeviceConfig):
        self.config = config
        self.logger = logger.bind(device_id=config.device_id)
        self.fake = Faker()
        
        # MQTT client setup
        self.mqtt_client = mqtt.Client(client_id=f"{config.device_id}")
        self.mqtt_connected = False
        
        # Protocol state
        self.sparkplug_seq = 0
        self.lwm2m_registered = False
        self.device_metrics = {}
        
        # Async event loop
        self.loop = None
        self.executor = ThreadPoolExecutor(max_workers=2)

    def setup_mqtt_client(self):
        """Configure MQTT client with TLS and authentication"""
        # Only set credentials if username is provided (for testing anonymous connections)
        if self.config.mqtt_username and self.config.mqtt_username != "":
            self.mqtt_client.username_pw_set(
                self.config.mqtt_username, 
                self.config.mqtt_password
            )
        
        if self.config.mqtt_use_tls:
            context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE  # For self-signed certs in testing
            self.mqtt_client.tls_set_context(context)
        
        # MQTT callbacks
        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_disconnect = self._on_mqtt_disconnect
        self.mqtt_client.on_message = self._on_mqtt_message
        self.mqtt_client.on_log = self._on_mqtt_log

    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        if rc == 0:
            self.mqtt_connected = True
            self.logger.info("MQTT connected", result_code=rc)
            
            # Subscribe to LwM2M command topics
            lwm2m_cmd_topic = f"lwm2m/{self.config.device_id}/cmd/+"
            client.subscribe(lwm2m_cmd_topic)
            
            # Subscribe to Sparkplug B command topics
            sparkplug_cmd_topic = f"{self.config.sparkplug_namespace}/{self.config.group_id}/DCMD/{self.config.device_id}"
            client.subscribe(sparkplug_cmd_topic)
            
            self.logger.info("Subscribed to command topics", 
                           lwm2m_topic=lwm2m_cmd_topic,
                           sparkplug_topic=sparkplug_cmd_topic)
        else:
            self.logger.error("MQTT connection failed", result_code=rc)

    def _on_mqtt_disconnect(self, client, userdata, rc):
        """MQTT disconnection callback"""
        self.mqtt_connected = False
        self.logger.warning("MQTT disconnected", result_code=rc)

    def _on_mqtt_message(self, client, userdata, msg):
        """Handle incoming MQTT messages"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            
            if "lwm2m" in topic:
                self._handle_lwm2m_command(topic, payload)
            elif "DCMD" in topic:
                self._handle_sparkplug_command(topic, msg.payload)
                
        except Exception as e:
            self.logger.error("Error handling MQTT message", error=str(e), topic=msg.topic)

    def _on_mqtt_log(self, client, userdata, level, buf):
        """MQTT client logging"""
        if level <= mqtt.MQTT_LOG_WARNING:
            self.logger.debug("MQTT log", level=level, message=buf)

    def _handle_lwm2m_command(self, topic: str, payload: str):
        """Handle LwM2M management commands"""
        try:
            parts = topic.split('/')
            if len(parts) >= 4:
                command = parts[3]
                self.logger.info("Received LwM2M command", command=command, payload=payload)
                
                if command == "read":
                    self._handle_lwm2m_read(payload)
                elif command == "write":
                    self._handle_lwm2m_write(payload)
                elif command == "execute":
                    self._handle_lwm2m_execute(payload)
                    
        except Exception as e:
            self.logger.error("Error handling LwM2M command", error=str(e))

    def _handle_lwm2m_read(self, payload: str):
        """Handle LwM2M read operations"""
        try:
            request = json.loads(payload)
            object_id = request.get("objectId")
            instance_id = request.get("instanceId", 0)
            resource_id = request.get("resourceId")
            
            # Simulate reading device resources
            if object_id == 3:  # Device object
                if resource_id == 0:  # Manufacturer
                    value = "IoT Testing Corp"
                elif resource_id == 1:  # Model Number
                    value = f"SimDevice-{self.config.device_type}"
                elif resource_id == 2:  # Serial Number
                    value = self.config.device_id
                else:
                    value = "Unknown"
            else:
                value = self.fake.random_int(0, 100)
            
            response = {
                "objectId": object_id,
                "instanceId": instance_id,
                "resourceId": resource_id,
                "value": value,
                "timestamp": int(time.time() * 1000)
            }
            
            response_topic = f"lwm2m/{self.config.device_id}/resp/read"
            self.mqtt_client.publish(response_topic, json.dumps(response))
            
            self.logger.info("LwM2M read response sent", response=response)
            
        except Exception as e:
            self.logger.error("Error handling LwM2M read", error=str(e))

    def _handle_lwm2m_write(self, payload: str):
        """Handle LwM2M write operations"""
        try:
            request = json.loads(payload)
            self.logger.info("LwM2M write operation", request=request)
            
            # Acknowledge write operation
            response = {
                "objectId": request.get("objectId"),
                "instanceId": request.get("instanceId", 0),
                "resourceId": request.get("resourceId"),
                "status": "success",
                "timestamp": int(time.time() * 1000)
            }
            
            response_topic = f"lwm2m/{self.config.device_id}/resp/write"
            self.mqtt_client.publish(response_topic, json.dumps(response))
            
        except Exception as e:
            self.logger.error("Error handling LwM2M write", error=str(e))

    def _handle_lwm2m_execute(self, payload: str):
        """Handle LwM2M execute operations"""
        try:
            request = json.loads(payload)
            self.logger.info("LwM2M execute operation", request=request)
            
            # Simulate command execution
            response = {
                "objectId": request.get("objectId"),
                "instanceId": request.get("instanceId", 0),
                "resourceId": request.get("resourceId"),
                "status": "executed",
                "timestamp": int(time.time() * 1000)
            }
            
            response_topic = f"lwm2m/{self.config.device_id}/resp/execute"
            self.mqtt_client.publish(response_topic, json.dumps(response))
            
        except Exception as e:
            self.logger.error("Error handling LwM2M execute", error=str(e))

    def _handle_sparkplug_command(self, topic: str, payload: bytes):
        """Handle Sparkplug B device commands"""
        try:
            # Deserialize protobuf payload
            command_payload = Payload()
            command_payload.ParseFromString(payload)
            
            self.logger.info("Received Sparkplug B command", 
                           seq=command_payload.seq,
                           metrics_count=len(command_payload.metrics))
            
            # Process command metrics
            for metric in command_payload.metrics:
                self.logger.info("Processing command metric", 
                               name=metric.name, 
                               datatype=metric.datatype)
                
                # Simulate command processing
                if metric.name == "reboot":
                    self._simulate_device_reboot()
                elif metric.name == "config_update":
                    self._simulate_config_update(metric)
                    
        except Exception as e:
            self.logger.error("Error handling Sparkplug command", error=str(e))

    def _simulate_device_reboot(self):
        """Simulate device reboot sequence"""
        self.logger.info("Simulating device reboot")
        
        # Send death certificate
        death_payload = self._create_sparkplug_death_payload()
        death_topic = f"{self.config.sparkplug_namespace}/{self.config.group_id}/DDEATH/{self.config.device_id}"
        self.mqtt_client.publish(death_topic, death_payload.SerializeToString())
        
        # Reset sequence number
        self.sparkplug_seq = 0

    def _simulate_config_update(self, metric: Metric):
        """Simulate configuration update"""
        self.logger.info("Simulating configuration update", metric_name=metric.name)

    async def register_lwm2m_device(self):
        """Register device with LwM2M server via MQTT"""
        if self.lwm2m_registered:
            return
            
        try:
            registration_data = {
                "endpoint": self.config.device_id,
                "lifetime": 3600,
                "version": "1.2",
                "bindingMode": "UQ",  # UDP + Queue mode
                "objects": {
                    "3": {  # Device object
                        "0": {
                            "0": "IoT Testing Corp",      # Manufacturer
                            "1": f"SimDevice-{self.config.device_type}",  # Model
                            "2": self.config.device_id,   # Serial Number
                            "3": "1.0.0"                  # Firmware Version
                        }
                    },
                    "4": {  # Connectivity Monitoring
                        "0": {
                            "0": 1,    # Network Bearer
                            "1": 100,  # Available Network Bearer
                            "2": 100,  # Radio Signal Strength
                            "4": "192.168.1.100"  # IP Address
                        }
                    }
                }
            }
            
            reg_topic = f"lwm2m/{self.config.device_id}/reg"
            self.mqtt_client.publish(reg_topic, json.dumps(registration_data))
            
            self.lwm2m_registered = True
            self.logger.info("LwM2M device registered")
            
        except Exception as e:
            self.logger.error("Error registering LwM2M device", error=str(e))

    def send_sparkplug_birth_certificate(self):
        """Send Sparkplug B device birth certificate"""
        try:
            birth_payload = self._create_sparkplug_birth_payload()
            birth_topic = f"{self.config.sparkplug_namespace}/{self.config.group_id}/DBIRTH/{self.config.device_id}"
            
            result = self.mqtt_client.publish(birth_topic, birth_payload.SerializeToString())
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.logger.info("Sparkplug B birth certificate sent", seq=self.sparkplug_seq)
            else:
                self.logger.error("Failed to send birth certificate", error_code=result.rc)
                
        except Exception as e:
            self.logger.error("Error sending birth certificate", error=str(e))

    def _create_sparkplug_birth_payload(self) -> Payload:
        """Create Sparkplug B birth certificate payload"""
        payload = Payload()
        payload.timestamp = int(time.time() * 1000)
        payload.seq = self.sparkplug_seq
        payload.uuid = str(uuid.uuid4())
        
        # Add device metrics to birth certificate
        metrics = [
            ("Device/Type", DataType.STRING, self.config.device_type),
            ("Device/Manufacturer", DataType.STRING, "IoT Testing Corp"),
            ("Device/Model", DataType.STRING, f"SimDevice-{self.config.device_type}"),
            ("Device/SerialNumber", DataType.STRING, self.config.device_id),
            ("Device/FirmwareVersion", DataType.STRING, "1.0.0"),
            ("Device/Online", DataType.BOOLEAN, True),
        ]
        
        for name, datatype, value in metrics:
            metric = payload.metrics.add()
            metric.name = name
            metric.datatype = datatype
            metric.timestamp = payload.timestamp
            
            if datatype == DataType.STRING:
                metric.string_value = str(value)
            elif datatype == DataType.BOOLEAN:
                metric.boolean_value = bool(value)
            elif datatype == DataType.DOUBLE:
                metric.double_value = float(value)
        
        self.sparkplug_seq += 1
        return payload

    def _create_sparkplug_death_payload(self) -> Payload:
        """Create Sparkplug B death certificate payload"""
        payload = Payload()
        payload.timestamp = int(time.time() * 1000)
        
        return payload

    async def send_sparkplug_telemetry(self):
        """Send Sparkplug B telemetry data"""
        while self.mqtt_connected:
            try:
                telemetry_payload = self._create_telemetry_payload()
                data_topic = f"{self.config.sparkplug_namespace}/{self.config.group_id}/DDATA/{self.config.device_id}"
                
                result = self.mqtt_client.publish(data_topic, telemetry_payload.SerializeToString())
                
                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    self.logger.debug("Sparkplug telemetry sent", 
                                    seq=self.sparkplug_seq,
                                    metrics_count=len(telemetry_payload.metrics))
                else:
                    self.logger.error("Failed to send telemetry", error_code=result.rc)
                
                await asyncio.sleep(self.config.telemetry_interval)
                
            except Exception as e:
                self.logger.error("Error sending telemetry", error=str(e))
                await asyncio.sleep(5)

    def _create_telemetry_payload(self) -> Payload:
        """Create Sparkplug B telemetry payload with sensor data"""
        payload = Payload()
        payload.timestamp = int(time.time() * 1000)
        payload.seq = self.sparkplug_seq
        
        # Generate realistic sensor data based on device type
        if self.config.device_type == "temperature_sensor":
            metrics_data = [
                ("Sensors/Temperature", DataType.DOUBLE, self.fake.random_int(18, 35) + self.fake.random.random()),
                ("Sensors/Humidity", DataType.DOUBLE, self.fake.random_int(30, 80) + self.fake.random.random()),
                ("Battery/Level", DataType.DOUBLE, max(0, 100 - (time.time() % 86400) / 864)),  # Simulate battery drain
            ]
        elif self.config.device_type == "pressure_sensor":
            metrics_data = [
                ("Sensors/Pressure", DataType.DOUBLE, 1013.25 + np.random.normal(0, 5)),
                ("Sensors/Temperature", DataType.DOUBLE, self.fake.random_int(15, 30) + self.fake.random.random()),
                ("Battery/Level", DataType.DOUBLE, max(0, 100 - (time.time() % 86400) / 864)),
            ]
        else:  # Default sensor type
            metrics_data = [
                ("Sensors/Value1", DataType.DOUBLE, self.fake.random.random() * 100),
                ("Sensors/Value2", DataType.DOUBLE, self.fake.random.random() * 50),
                ("Battery/Level", DataType.DOUBLE, self.fake.random_int(0, 100)),
            ]
        
        # Add common metrics
        metrics_data.extend([
            ("Device/Uptime", DataType.UINT64, int(time.time() - self.start_time)),
            ("Network/RSSI", DataType.INT32, self.fake.random_int(30, 80)),
            ("Device/MemoryUsage", DataType.DOUBLE, self.fake.random_int(20, 80)),
        ])
        
        for name, datatype, value in metrics_data:
            metric = payload.metrics.add()
            metric.name = name
            metric.datatype = datatype
            metric.timestamp = payload.timestamp
            
            if datatype == DataType.STRING:
                metric.string_value = str(value)
            elif datatype == DataType.BOOLEAN:
                metric.boolean_value = bool(value)
            elif datatype == DataType.DOUBLE:
                metric.double_value = float(value)
            elif datatype == DataType.UINT64:
                metric.long_value = int(value)
            elif datatype == DataType.INT32:
                metric.int_value = int(value)
        
        self.sparkplug_seq += 1
        return payload

    async def send_single_sparkplug_telemetry(self):
        """Send a single Sparkplug B telemetry message"""
        try:
            telemetry_payload = self._create_telemetry_payload()
            data_topic = f"{self.config.sparkplug_namespace}/{self.config.group_id}/DDATA/{self.config.device_id}"
            
            result = self.mqtt_client.publish(data_topic, telemetry_payload.SerializeToString())
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.logger.debug("Sparkplug telemetry sent", 
                                seq=self.sparkplug_seq,
                                metrics_count=len(telemetry_payload.metrics))
            else:
                self.logger.error("Failed to send telemetry", error_code=result.rc)
                
        except Exception as e:
            self.logger.error("Error sending telemetry", error=str(e))

    async def send_single_lwm2m_update(self):
        """Send a single LwM2M update"""
        try:
            update_data = {
                "endpoint": self.config.device_id,
                "lifetime": 3600,
                "objects": {
                    "4": {  # Connectivity Monitoring
                        "0": {
                            "2": self.fake.random_int(-80, -30),  # Signal Strength
                            "4": f"192.168.1.{self.fake.random_int(100, 200)}"  # IP Address
                        }
                    }
                },
                "timestamp": int(time.time() * 1000)
            }
            
            update_topic = f"lwm2m/{self.config.device_id}/update"
            result = self.mqtt_client.publish(update_topic, json.dumps(update_data))
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.logger.debug("LwM2M update sent")
            else:
                self.logger.error("Failed to send LwM2M update", error_code=result.rc)
                
        except Exception as e:
            self.logger.error("Error sending LwM2M update", error=str(e))

    async def send_lwm2m_updates(self):
        """Send periodic LwM2M updates"""
        while self.mqtt_connected and self.lwm2m_registered:
            try:
                update_data = {
                    "endpoint": self.config.device_id,
                    "lifetime": 3600,
                    "objects": {
                        "4": {  # Connectivity Monitoring
                            "0": {
                                "2": self.fake.random_int(-100, -30),  # Signal Strength
                                "4": f"192.168.1.{self.fake.random_int(100, 200)}"  # IP Address
                            }
                        }
                    },
                    "timestamp": int(time.time() * 1000)
                }
                
                update_topic = f"lwm2m/{self.config.device_id}/update"
                result = self.mqtt_client.publish(update_topic, json.dumps(update_data))
                
                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    self.logger.debug("LwM2M update sent")
                else:
                    self.logger.error("Failed to send LwM2M update", error_code=result.rc)
                
                await asyncio.sleep(self.config.lwm2m_interval)
                
            except Exception as e:
                self.logger.error("Error sending LwM2M update", error=str(e))
                await asyncio.sleep(30)

    async def run(self):
        """Main device simulation loop"""
        self.start_time = time.time()
        self.logger.info("Starting device simulator")
        
        # Setup MQTT connection
        self.setup_mqtt_client()
        
        try:
            # Connect to MQTT broker
            self.logger.info("Connecting to MQTT broker", 
                           host=self.config.mqtt_broker_host, 
                           port=self.config.mqtt_broker_port)
            
            self.mqtt_client.connect(
                self.config.mqtt_broker_host, 
                self.config.mqtt_broker_port, 
                60
            )
            
            # Start MQTT loop in background
            self.mqtt_client.loop_start()
            
            # Wait for MQTT connection
            retry_count = 0
            while not self.mqtt_connected and retry_count < 30:
                await asyncio.sleep(1)
                retry_count += 1
            
            if not self.mqtt_connected:
                raise Exception("Failed to connect to MQTT broker")
            
            self.logger.info("MQTT connected successfully")
            
            # Register LwM2M device
            await self.register_lwm2m_device()
            
            # Send Sparkplug B birth certificate
            self.send_sparkplug_birth_certificate()
            
            # Start telemetry and update loops with better error handling
            while self.mqtt_connected:
                try:
                    # Send Sparkplug B telemetry
                    await self.send_single_sparkplug_telemetry()
                    
                    # Send LwM2M update (less frequent)
                    if int(time.time()) % self.config.lwm2m_interval == 0:
                        await self.send_single_lwm2m_update()
                    
                    await asyncio.sleep(self.config.telemetry_interval)
                    
                except Exception as e:
                    self.logger.error("Error in telemetry loop", error=str(e))
                    await asyncio.sleep(5)  # Wait before retrying
            
        except Exception as e:
            self.logger.error("Device simulation error", error=str(e))
        finally:
            if self.mqtt_client:
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
            self.logger.info("Device simulator stopped")

def create_device_config() -> DeviceConfig:
    """Create device configuration from environment variables"""
    device_count = int(os.getenv("DEVICE_COUNT", "1"))
    device_index = int(os.getenv("DEVICE_INDEX", "0"))
    
    device_types = ["temperature_sensor", "pressure_sensor", "flow_sensor", "level_sensor"]
    device_type = device_types[device_index % len(device_types)]
    
    return DeviceConfig(
        device_id=f"device-{device_type}-{device_index:03d}",
        device_type=device_type,
        mqtt_broker_host=os.getenv("MQTT_BROKER_HOST", "mosquitto"),
        mqtt_broker_port=int(os.getenv("MQTT_BROKER_PORT", "8883")),
        mqtt_username=os.getenv("MQTT_USERNAME", "device"),
        mqtt_password=os.getenv("MQTT_PASSWORD", "testpass123"),
        mqtt_use_tls=os.getenv("MQTT_USE_TLS", "true").lower() == "true",
        lwm2m_server_host=os.getenv("LWM2M_SERVER_HOST", "lwm2m-server"),
        lwm2m_server_port=int(os.getenv("LWM2M_SERVER_PORT", "8080")),
        group_id=os.getenv("GROUP_ID", "IIoT"),
        sparkplug_namespace=os.getenv("SPARKPLUG_NAMESPACE", "spBv1.0"),
        telemetry_interval=int(os.getenv("TELEMETRY_INTERVAL", "5")),
        lwm2m_interval=int(os.getenv("LWM2M_INTERVAL", "30"))
    )

async def main():
    """Main entry point"""
    config = create_device_config()
    
    # Create and run multiple devices if configured
    device_count = int(os.getenv("DEVICE_COUNT", "1"))
    
    if device_count == 1:
        # Single device mode
        simulator = DeviceSimulator(config)
        await simulator.run()
    else:
        # Multi-device mode
        tasks = []
        for i in range(device_count):
            # Create config for each device
            device_config = create_device_config()
            device_config.device_id = f"device-{device_config.device_type}-{i:03d}"
            
            simulator = DeviceSimulator(device_config)
            tasks.append(simulator.run())
        
        # Run all devices concurrently
        await asyncio.gather(*tasks, return_exceptions=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Device simulator stopped by user")
    except Exception as e:
        print(f"Device simulator error: {e}")
        exit(1) 