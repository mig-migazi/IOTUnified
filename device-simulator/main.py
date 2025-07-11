#!/usr/bin/env python3
"""
High-Performance Unified Device Simulator
Supports LwM2M and Sparkplug B protocols over MQTT with high throughput
"""

import asyncio
import json
import logging
import os
import ssl
import time
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from queue import Queue
from typing import Dict, Any
import numpy as np

import paho.mqtt.client as mqtt
import structlog
from faker import Faker

# Import protobuf
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
    telemetry_interval: float
    lwm2m_interval: float

class HighPerformanceDeviceSimulator:
    """High-performance device simulator with multi-threading for scale"""

    def __init__(self, config: DeviceConfig):
        self.config = config
        self.logger = logger.bind(device_id=config.device_id)
        self.fake = Faker()
        
        # Threading control
        self.running = True
        self.mqtt_connected = False
        
        # MQTT client optimized for high throughput
        self.mqtt_client = mqtt.Client(
            client_id=f"{config.device_id}",
            protocol=mqtt.MQTTv311,
            clean_session=True
        )
        
        # Protocol state
        self.sparkplug_seq = 0
        self.lwm2m_registered = False
        self.start_time = time.time()
        
        # Performance optimization: pre-generated payload templates
        self.sparkplug_birth_payload = None
        self.lwm2m_registration_data = None
        
        # Message queues for high throughput
        self.telemetry_queue = Queue(maxsize=1000)
        self.management_queue = Queue(maxsize=100)
        
        # Thread pool for message processing
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        self.setup_mqtt_client()
        self.pre_generate_payloads()

    def setup_mqtt_client(self):
        """Configure MQTT client optimized for high throughput"""
        # Skip authentication if no username provided
        if self.config.mqtt_username and self.config.mqtt_username != "":
            self.mqtt_client.username_pw_set(
                self.config.mqtt_username, 
                self.config.mqtt_password
            )
        
        # Optimize MQTT settings for high throughput
        self.mqtt_client.max_inflight_messages_set(100)  # Allow more concurrent messages
        self.mqtt_client.max_queued_messages_set(1000)   # Larger message queue
        
        if self.config.mqtt_use_tls:
            context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            self.mqtt_client.tls_set_context(context)
        
        # Callbacks
        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_disconnect = self._on_mqtt_disconnect
        self.mqtt_client.on_message = self._on_mqtt_message
        self.mqtt_client.on_publish = self._on_mqtt_publish

    def pre_generate_payloads(self):
        """Pre-generate common payloads to avoid runtime serialization overhead"""
        # Pre-generate Sparkplug B birth certificate
        self.sparkplug_birth_payload = self._create_sparkplug_birth_payload()
        
        # Pre-generate LwM2M registration data
        self.lwm2m_registration_data = {
            "endpoint": self.config.device_id,
            "lifetime": 3600,
            "version": "1.2",
            "bindingMode": "UQ",
            "objects": {
                "3": {
                    "0": {
                        "0": "IoT Testing Corp",
                        "1": f"SimDevice-{self.config.device_type}",
                        "2": self.config.device_id,
                        "3": "1.0.0"
                    }
                },
                "4": {
                    "0": {
                        "0": 1,
                        "1": 100,
                        "2": 100,
                        "4": "192.168.1.100"
                    }
                }
            }
        }

    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        if rc == 0:
            self.mqtt_connected = True
            self.logger.info("MQTT connected", result_code=rc)
            
            # Subscribe to command topics
            lwm2m_cmd_topic = f"lwm2m/{self.config.device_id}/cmd/+"
            sparkplug_cmd_topic = f"{self.config.sparkplug_namespace}/{self.config.group_id}/DCMD/{self.config.device_id}"
            
            client.subscribe(lwm2m_cmd_topic)
            client.subscribe(sparkplug_cmd_topic)
            
            self.logger.info("Subscribed to command topics")
        else:
            self.logger.error("MQTT connection failed", result_code=rc)

    def _on_mqtt_disconnect(self, client, userdata, rc):
        """MQTT disconnection callback"""
        self.mqtt_connected = False
        self.logger.warning("MQTT disconnected", result_code=rc)

    def _on_mqtt_message(self, client, userdata, msg):
        """Handle incoming MQTT messages"""
        # Queue message processing to avoid blocking
        self.executor.submit(self._process_command_message, msg.topic, msg.payload)

    def _on_mqtt_publish(self, client, userdata, mid):
        """MQTT publish callback - used for flow control"""
        pass

    def _process_command_message(self, topic: str, payload: bytes):
        """Process command messages in background thread"""
        try:
            if "lwm2m" in topic:
                self._handle_lwm2m_command(topic, payload.decode('utf-8'))
            elif "DCMD" in topic:
                self._handle_sparkplug_command(topic, payload)
        except Exception as e:
            self.logger.error("Error processing command", error=str(e), topic=topic)

    def _handle_lwm2m_command(self, topic: str, payload: str):
        """Handle LwM2M management commands"""
        parts = topic.split('/')
        if len(parts) >= 4:
            command = parts[3]
            self.logger.info("Received LwM2M command", command=command)

    def _handle_sparkplug_command(self, topic: str, payload: bytes):
        """Handle Sparkplug B command messages"""
        self.logger.info("Received Sparkplug command", topic=topic)

    def _create_sparkplug_birth_payload(self) -> Payload:
        """Create Sparkplug B birth certificate payload"""
        payload = Payload()
        payload.timestamp = int(time.time() * 1000)
        payload.seq = 0
        payload.uuid = str(uuid.uuid4())
        
        # Add device metrics
        metrics_data = [
            ("Device/Type", 12, self.config.device_type),  # STRING = 12
            ("Device/Manufacturer", 12, "IoT Testing Corp"),  # STRING = 12
            ("Device/Model", 12, f"SimDevice-{self.config.device_type}"),  # STRING = 12
            ("Device/SerialNumber", 12, self.config.device_id),  # STRING = 12
            ("Device/FirmwareVersion", 12, "1.0.0"),  # STRING = 12
            ("Device/Online", 11, True),  # BOOLEAN = 11
        ]
        
        for name, datatype, value in metrics_data:
            metric = payload.metrics.add()
            metric.name = name
            metric.datatype = datatype
            metric.timestamp = payload.timestamp
            
            if datatype == 12:  # STRING
                metric.string_value = str(value)
            elif datatype == 11:  # BOOLEAN
                metric.boolean_value = bool(value)
        
        return payload

    def _create_high_frequency_telemetry_payload(self) -> bytes:
        """Create optimized telemetry payload for high-frequency transmission"""
        payload = Payload()
        payload.timestamp = int(time.time() * 1000)
        payload.seq = self.sparkplug_seq
        
        # Optimized sensor data generation
        if self.config.device_type == "temperature_sensor":
            temp = 20.0 + 5.0 * np.sin(time.time() / 60.0) + np.random.normal(0, 0.5)
            humidity = 50.0 + 20.0 * np.cos(time.time() / 90.0) + np.random.normal(0, 2.0)
            
            metrics_data = [
                ("Sensors/Temperature", 10, temp),  # DOUBLE = 10
                ("Sensors/Humidity", 10, humidity),  # DOUBLE = 10
                ("Battery/Level", 10, max(0, 100 - (time.time() % 86400) / 864)),  # DOUBLE = 10
                ("Device/Uptime", 8, int(time.time() - self.start_time)),  # UINT64 = 8
                ("Network/RSSI", 9, float(30 + 20 * np.random.random())),  # FLOAT = 9
            ]
        else:
            # Generic sensor data
            metrics_data = [
                ("Sensors/Value1", 10, 50.0 + 25.0 * np.sin(time.time() / 30.0)),  # DOUBLE = 10
                ("Sensors/Value2", 10, 25.0 + 10.0 * np.cos(time.time() / 45.0)),  # DOUBLE = 10
                ("Battery/Level", 10, max(0, 100 - (time.time() % 86400) / 864)),  # DOUBLE = 10
                ("Device/Uptime", 8, int(time.time() - self.start_time)),  # UINT64 = 8
                ("Network/RSSI", 9, float(30 + 20 * np.random.random())),  # FLOAT = 9
            ]
        
        for name, datatype, value in metrics_data:
            metric = payload.metrics.add()
            metric.name = name
            metric.datatype = datatype
            metric.timestamp = payload.timestamp
            
            if datatype == 10:  # DOUBLE
                metric.double_value = float(value)
            elif datatype == 8:  # UINT64
                metric.long_value = int(value)
            elif datatype == 3:  # INT32
                metric.int_value = int(value)
            elif datatype == 9:  # FLOAT
                metric.float_value = float(value)
        
        self.sparkplug_seq += 1
        return payload.SerializeToString()

    def high_frequency_telemetry_thread(self):
        """High-frequency telemetry thread - optimized for performance"""
        self.logger.info("Starting high-frequency telemetry thread", 
                        interval=self.config.telemetry_interval)
        
        # Wait for MQTT connection
        while not self.mqtt_connected and self.running:
            time.sleep(0.1)
        
        if not self.running:
            return
            
        # Send birth certificate
        birth_topic = f"{self.config.sparkplug_namespace}/{self.config.group_id}/DBIRTH/{self.config.device_id}"
        self.mqtt_client.publish(birth_topic, self.sparkplug_birth_payload.SerializeToString())
        self.logger.info("Sparkplug birth certificate sent")
        
        # High-frequency telemetry loop
        next_send_time = time.time()
        while self.running and self.mqtt_connected:
            try:
                # Generate and send telemetry
                telemetry_data = self._create_high_frequency_telemetry_payload()
                data_topic = f"{self.config.sparkplug_namespace}/{self.config.group_id}/DDATA/{self.config.device_id}"
                
                result = self.mqtt_client.publish(data_topic, telemetry_data, qos=0)
                
                if result.rc != mqtt.MQTT_ERR_SUCCESS:
                    self.logger.warning("Publish failed", error_code=result.rc)
                
                # Precise timing for high frequency
                next_send_time += self.config.telemetry_interval
                sleep_time = next_send_time - time.time()
                
                if sleep_time > 0:
                    time.sleep(sleep_time)
                else:
                    # We're behind schedule, log warning
                    if sleep_time < -0.1:  # More than 100ms behind
                        self.logger.warning("Telemetry thread falling behind", 
                                          behind_seconds=-sleep_time)
                    next_send_time = time.time()
                    
            except Exception as e:
                self.logger.error("Error in telemetry thread", error=str(e))
                time.sleep(1)  # Backoff on error

    def lwm2m_management_thread(self):
        """LwM2M device management thread"""
        self.logger.info("Starting LwM2M management thread", 
                        interval=self.config.lwm2m_interval)
        
        # Wait for MQTT connection
        while not self.mqtt_connected and self.running:
            time.sleep(0.1)
        
        if not self.running:
            return
            
        # Register device
        reg_topic = f"lwm2m/{self.config.device_id}/reg"
        self.mqtt_client.publish(reg_topic, json.dumps(self.lwm2m_registration_data))
        self.lwm2m_registered = True
        self.logger.info("LwM2M device registered")
        
        # Management update loop
        while self.running and self.mqtt_connected:
            try:
                # Send device update
                update_data = {
                    "endpoint": self.config.device_id,
                    "lifetime": 3600,
                    "objects": {
                        "4": {
                            "0": {
                                "2": int(30 + 20 * np.random.random()),  # Signal Strength
                                "4": f"192.168.1.{100 + int(100 * np.random.random())}"  # IP Address
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
                    self.logger.warning("LwM2M update failed", error_code=result.rc)
                
                time.sleep(self.config.lwm2m_interval)
                
            except Exception as e:
                self.logger.error("Error in LwM2M thread", error=str(e))
                time.sleep(5)

    def run(self):
        """Main device simulation with multi-threading for high performance"""
        self.start_time = time.time()
        self.logger.info("Starting high-performance device simulator")
        
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
                time.sleep(1)
                retry_count += 1
            
            if not self.mqtt_connected:
                raise Exception("Failed to connect to MQTT broker")
            
            self.logger.info("MQTT connected successfully")
            
            # Start high-performance threads
            telemetry_thread = threading.Thread(
                target=self.high_frequency_telemetry_thread,
                name=f"{self.config.device_id}-telemetry"
            )
            
            management_thread = threading.Thread(
                target=self.lwm2m_management_thread,
                name=f"{self.config.device_id}-management"
            )
            
            telemetry_thread.start()
            management_thread.start()
            
            self.logger.info("High-performance threads started", 
                           telemetry_rate=f"{1/self.config.telemetry_interval:.1f}/sec",
                           management_rate=f"{1/self.config.lwm2m_interval:.2f}/sec")
            
            # Keep main thread alive
            try:
                while self.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                self.logger.info("Shutdown requested")
                
            # Graceful shutdown
            self.running = False
            telemetry_thread.join(timeout=5)
            management_thread.join(timeout=5)
            
        except Exception as e:
            self.logger.error("Device simulation error", error=str(e))
        finally:
            self.running = False
            if self.mqtt_client:
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
            self.logger.info("Device simulator stopped")

def create_device_config() -> DeviceConfig:
    """Create device configuration with hardcoded values for 100 msg/sec"""
    device_count = int(os.getenv("DEVICE_COUNT", "1"))
    device_index = int(os.getenv("DEVICE_INDEX", "0"))
    
    device_types = ["temperature_sensor", "pressure_sensor", "flow_sensor", "level_sensor"]
    device_type = device_types[device_index % len(device_types)]
    
    # HARDCODED VALUES FOR 100 MSG/SEC - NO MORE ENV VARIABLE ISSUES!
    # Sparkplug B: 0.0105 seconds = 95.24 msg/sec
    # LwM2M: 0.2 seconds = 5 msg/sec
    # Total: 100.24 msg/sec
    
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
        telemetry_interval=0.0105,  # 95.24 msg/sec - HARDCODED FOR RELIABILITY
        lwm2m_interval=0.2         # 5 msg/sec - HARDCODED FOR RELIABILITY
    )

def main():
    """Main entry point"""
    config = create_device_config()
    
    # Create and run multiple devices if configured
    device_count = int(os.getenv("DEVICE_COUNT", "1"))
    
    if device_count == 1:
        # Single device mode
        simulator = HighPerformanceDeviceSimulator(config)
        simulator.run()
    else:
        # Multi-device mode with separate processes for better isolation
        import multiprocessing
        
        def run_device(device_index):
            device_config = create_device_config()
            device_config.device_id = f"device-{device_config.device_type}-{device_index:03d}"
            
            simulator = HighPerformanceDeviceSimulator(device_config)
            simulator.run()
        
        processes = []
        for i in range(device_count):
            p = multiprocessing.Process(target=run_device, args=(i,))
            p.start()
            processes.append(p)
        
        try:
            for p in processes:
                p.join()
        except KeyboardInterrupt:
            for p in processes:
                p.terminate()
                p.join()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Device simulator stopped by user")
    except Exception as e:
        print(f"Device simulator error: {e}")
        exit(1) 