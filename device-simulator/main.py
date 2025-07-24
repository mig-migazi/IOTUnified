#!/usr/bin/env python3
"""
High-Performance Dual-Path Device Simulator
Supports LwM2M (cloud) + Sparkplug B (edge) protocols over MQTT

Dual-Path Architecture:
- LwM2M over MQTT: Low-throughput device management for cloud streaming
- Sparkplug B over MQTT: High-throughput telemetry for edge device interoperability
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
from typing import Dict, Any, Tuple
import numpy as np
import math

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
    """High-performance dual-path device simulator with edge interoperability"""

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
        
        # Edge interoperability: track other devices
        self.edge_devices = {}  # Store other devices' telemetry
        self.edge_commands = Queue(maxsize=100)  # Commands from other devices
        
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
            
            # Edge interoperability: subscribe to other devices' telemetry
            # Subscribe to all DDATA topics in the group (except our own)
            edge_telemetry_topic = f"{self.config.sparkplug_namespace}/{self.config.group_id}/DDATA/+"
            client.subscribe(edge_telemetry_topic)
            
            self.logger.info("Subscribed to command and edge telemetry topics")
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
            elif "DDATA" in topic and topic != f"spBv1.0/{self.config.group_id}/DDATA/{self.config.device_id}":
                # Edge interoperability: process other devices' telemetry
                self._handle_edge_telemetry(topic, payload)
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

    def _handle_edge_telemetry(self, topic: str, payload: bytes):
        """Handle telemetry from other edge devices for interoperability"""
        try:
            # Parse Sparkplug B payload from other devices
            sparkplug_payload = Payload()
            sparkplug_payload.ParseFromString(payload)
            
            # Extract device ID from topic
            parts = topic.split('/')
            if len(parts) >= 4:
                source_device = parts[3]
                
                # Store telemetry data for edge interoperability
                self.edge_devices[source_device] = {
                    'timestamp': sparkplug_payload.timestamp,
                    'metrics': {},
                    'last_seen': time.time()
                }
                
                # Extract metrics for edge processing
                for metric in sparkplug_payload.metrics:
                    self.edge_devices[source_device]['metrics'][metric.name] = {
                        'value': self._extract_metric_value(metric),
                        'datatype': metric.datatype,
                        'timestamp': metric.timestamp
                    }
                
                # Edge interoperability: respond to other devices' data
                self._process_edge_interoperability(source_device, self.edge_devices[source_device])
                
                self.logger.debug("Processed edge telemetry", 
                                source_device=source_device, 
                                metrics_count=len(sparkplug_payload.metrics))
                
        except Exception as e:
            self.logger.error("Error processing edge telemetry", error=str(e), topic=topic)

    def _extract_metric_value(self, metric):
        """Extract value from Sparkplug B metric based on datatype"""
        if metric.HasField('int_value'):
            return metric.int_value
        elif metric.HasField('long_value'):
            return metric.long_value
        elif metric.HasField('float_value'):
            return metric.float_value
        elif metric.HasField('double_value'):
            return metric.double_value
        elif metric.HasField('boolean_value'):
            return metric.boolean_value
        elif metric.HasField('string_value'):
            return metric.string_value
        else:
            return None

    def _process_edge_interoperability(self, source_device: str, device_data: dict):
        """Process edge interoperability logic based on other devices' data"""
        try:
            # Example: Temperature sensor triggers pressure sensor adjustment
            if 'temperature_sensor' in source_device and self.config.device_type == 'pressure_sensor':
                temp_metric = device_data['metrics'].get('Temperature/Value')
                if temp_metric and temp_metric['value'] > 30:
                    # High temperature detected - adjust pressure setpoint
                    self.logger.info("Edge interop: High temp detected, adjusting pressure", 
                                   source_device=source_device, 
                                   temperature=temp_metric['value'])
                    # Could send command back to source device or adjust local parameters
            
            # Example: Flow sensor triggers pump control
            elif 'flow_sensor' in source_device and self.config.device_type == 'pump_monitor':
                flow_metric = device_data['metrics'].get('Flow/Rate')
                if flow_metric and flow_metric['value'] < 10:
                    # Low flow detected - could trigger pump speed increase
                    self.logger.info("Edge interop: Low flow detected, considering pump adjustment", 
                                   source_device=source_device, 
                                   flow_rate=flow_metric['value'])
            
            # Example: Level sensor triggers valve control
            elif 'level_sensor' in source_device and self.config.device_type in ['valve_controller', 'pump_monitor']:
                level_metric = device_data['metrics'].get('Level/Percentage')
                if level_metric and level_metric['value'] > 80:
                    # High level detected - could trigger valve opening or pump shutdown
                    self.logger.info("Edge interop: High level detected, considering valve/pump action", 
                                   source_device=source_device, 
                                   level=level_metric['value'])
                    
        except Exception as e:
            self.logger.error("Error in edge interoperability processing", error=str(e))

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

    def _get_realistic_temperature_data(self) -> Tuple[float, float]:
        """Generate realistic temperature and humidity with daily cycles and correlations"""
        current_time = time.time()
        
        # Daily temperature cycle (peak at 2 PM, low at 6 AM)
        daily_cycle = 12 * math.sin((current_time % 86400) / 86400 * 2 * math.pi - math.pi/2)
        
        # Seasonal variation (simplified)
        seasonal_cycle = 8 * math.sin((current_time % (365 * 86400)) / (365 * 86400) * 2 * math.pi)
        
        # Base temperature with realistic variation
        base_temp = 22.0 + daily_cycle + seasonal_cycle + np.random.normal(0, 0.8)
        
        # Humidity inversely correlated with temperature
        humidity = max(20, min(95, 75 - (base_temp - 22) * 1.5 + np.random.normal(0, 3)))
        
        return base_temp, humidity

    def _get_realistic_pressure_data(self) -> Tuple[float, float]:
        """Generate realistic pressure data with process cycles and system variations"""
        current_time = time.time()
        
        # Process cycle (pump operation every 30 minutes)
        process_cycle = 15 * math.sin((current_time % 1800) / 1800 * 2 * math.pi)
        
        # System pressure baseline with slow drift
        system_drift = 5 * math.sin(current_time / 3600 * 2 * math.pi)
        
        # Main pressure reading (bar)
        pressure = 4.5 + process_cycle + system_drift + np.random.normal(0, 0.3)
        
        # Differential pressure across filter/valve
        differential = 0.8 + 0.4 * abs(process_cycle) / 15 + np.random.normal(0, 0.05)
        
        return pressure, differential

    def _get_realistic_flow_data(self) -> Tuple[float, float]:
        """Generate realistic flow data with demand patterns and pump cycles"""
        current_time = time.time()
        
        # Demand pattern (higher flow during business hours)
        hour_of_day = (current_time % 86400) / 3600
        demand_factor = 1.0
        if 6 <= hour_of_day <= 18:  # Business hours
            demand_factor = 1.5 + 0.3 * math.sin((hour_of_day - 6) / 12 * math.pi)
        else:
            demand_factor = 0.4 + 0.2 * np.random.random()
        
        # Pump operation cycle (30-second cycles)
        pump_cycle = max(0, math.sin((current_time % 30) / 30 * 2 * math.pi))
        
        # Flow rate (L/min)
        flow_rate = 25 * demand_factor * pump_cycle + np.random.normal(0, 1.5)
        flow_rate = max(0, flow_rate)
        
        # Totalizer (cumulative flow)
        totalizer = (current_time - self.start_time) * 12.5 * demand_factor  # Approximate
        
        return flow_rate, totalizer

    def _get_realistic_level_data(self) -> Tuple[float, float]:
        """Generate realistic level data with tank filling/draining cycles"""
        current_time = time.time()
        
        # Tank cycle (fill/drain every 45 minutes)
        tank_cycle = (current_time % 2700) / 2700  # 0 to 1
        
        # Realistic tank behavior with non-linear fill/drain
        if tank_cycle < 0.7:  # Filling phase
            level = 20 + 60 * (tank_cycle / 0.7) ** 0.8
        else:  # Draining phase
            drain_progress = (tank_cycle - 0.7) / 0.3
            level = 80 - 60 * drain_progress ** 1.5
        
        level = max(5, min(95, level + np.random.normal(0, 2)))
        
        # Secondary level sensor (slightly offset for redundancy)
        level_2 = level + np.random.normal(0, 0.8)
        
        return level, level_2

    def _get_vibration_data(self) -> Tuple[float, float, float]:
        """Generate realistic vibration data with equipment health degradation"""
        current_time = time.time()
        
        # Equipment aging factor (gradually increases over time)
        aging_factor = 1.0 + (current_time - self.start_time) / (365 * 86400) * 0.3
        
        # Base vibration with harmonics (simulating mechanical issues)
        base_vibration = 2.5 * aging_factor
        harmonic_1 = 0.8 * math.sin(current_time * 50 * 2 * math.pi)  # 50 Hz
        harmonic_2 = 0.4 * math.sin(current_time * 100 * 2 * math.pi)  # 100 Hz
        
        x_axis = base_vibration + harmonic_1 + np.random.normal(0, 0.3)
        y_axis = base_vibration + harmonic_2 + np.random.normal(0, 0.3)
        z_axis = base_vibration * 0.7 + np.random.normal(0, 0.2)
        
        return x_axis, y_axis, z_axis

    def _get_realistic_battery_data(self) -> Tuple[float, float]:
        """Generate realistic battery discharge with temperature effects"""
        current_time = time.time()
        runtime = current_time - self.start_time
        
        # Temperature effect on battery (get from temperature sensor if available)
        temp_effect = 1.0
        if hasattr(self, '_last_temperature'):
            temp_effect = 1.0 + (self._last_temperature - 22) * 0.02
        
        # Realistic battery discharge curve (non-linear)
        if runtime < 3600:  # First hour - stable
            battery_level = 100 - runtime / 3600 * 5
        elif runtime < 36000:  # Next 9 hours - linear
            battery_level = 95 - (runtime - 3600) / 32400 * 80
        else:  # Final hour - rapid decline
            battery_level = 15 - (runtime - 36000) / 3600 * 15
        
        # Temperature effect
        battery_level *= temp_effect
        battery_level = max(0, min(100, battery_level + np.random.normal(0, 1)))
        
        # Battery voltage correlation
        voltage = 3.0 + (battery_level / 100) * 1.2 + np.random.normal(0, 0.05)
        
        return battery_level, voltage

    def _get_realistic_network_data(self) -> Tuple[float, int]:
        """Generate realistic network data with environmental factors"""
        current_time = time.time()
        
        # Time-based network quality (worse during peak hours)
        hour_of_day = (current_time % 86400) / 3600
        network_load = 1.0
        if 8 <= hour_of_day <= 20:  # Peak hours
            network_load = 1.5 + 0.3 * math.sin((hour_of_day - 8) / 12 * math.pi)
        
        # RSSI with realistic fading
        base_rssi = -65  # Good signal
        fading = 15 * math.sin(current_time / 10) * network_load
        rssi = base_rssi + fading + np.random.normal(0, 3)
        rssi = max(-100, min(-30, rssi))
        
        # Packet loss correlation with RSSI
        if rssi > -70:
            packet_loss = np.random.poisson(0.1)
        elif rssi > -80:
            packet_loss = np.random.poisson(0.5)
        else:
            packet_loss = np.random.poisson(2.0)
        
        return rssi, packet_loss

    def _create_high_frequency_telemetry_payload(self) -> bytes:
        """Create optimized telemetry payload with realistic industrial IoT patterns"""
        payload = Payload()
        payload.timestamp = int(time.time() * 1000)
        payload.seq = self.sparkplug_seq
        
        # Generate realistic sensor data based on device type
        if self.config.device_type == "temperature_sensor":
            temp, humidity = self._get_realistic_temperature_data()
            self._last_temperature = temp  # Store for battery calculations
            battery_level, battery_voltage = self._get_realistic_battery_data()
            rssi, packet_loss = self._get_realistic_network_data()
            
            metrics_data = [
                ("Sensors/Temperature", 10, temp),
                ("Sensors/Humidity", 10, humidity),
                ("Battery/Level", 10, battery_level),
                ("Battery/Voltage", 10, battery_voltage),
                ("Device/Uptime", 8, int(time.time() - self.start_time)),
                ("Network/RSSI", 9, rssi),
                ("Network/PacketLoss", 3, packet_loss),
                ("Status/DeviceHealth", 12, "NORMAL" if battery_level > 20 else "LOW_BATTERY"),
            ]
            
        elif self.config.device_type == "pressure_sensor":
            pressure, differential = self._get_realistic_pressure_data()
            battery_level, battery_voltage = self._get_realistic_battery_data()
            rssi, packet_loss = self._get_realistic_network_data()
            
            metrics_data = [
                ("Sensors/Pressure", 10, pressure),
                ("Sensors/DifferentialPressure", 10, differential),
                ("Battery/Level", 10, battery_level),
                ("Battery/Voltage", 10, battery_voltage),
                ("Device/Uptime", 8, int(time.time() - self.start_time)),
                ("Network/RSSI", 9, rssi),
                ("Network/PacketLoss", 3, packet_loss),
                ("Status/DeviceHealth", 12, "NORMAL" if pressure > 1.0 else "LOW_PRESSURE"),
            ]
            
        elif self.config.device_type == "flow_sensor":
            flow_rate, totalizer = self._get_realistic_flow_data()
            battery_level, battery_voltage = self._get_realistic_battery_data()
            rssi, packet_loss = self._get_realistic_network_data()
            
            metrics_data = [
                ("Sensors/FlowRate", 10, flow_rate),
                ("Sensors/Totalizer", 10, totalizer),
                ("Battery/Level", 10, battery_level),
                ("Battery/Voltage", 10, battery_voltage),
                ("Device/Uptime", 8, int(time.time() - self.start_time)),
                ("Network/RSSI", 9, rssi),
                ("Network/PacketLoss", 3, packet_loss),
                ("Status/DeviceHealth", 12, "NORMAL" if flow_rate > 0 else "NO_FLOW"),
            ]
            
        elif self.config.device_type == "level_sensor":
            level, level_2 = self._get_realistic_level_data()
            battery_level, battery_voltage = self._get_realistic_battery_data()
            rssi, packet_loss = self._get_realistic_network_data()
            
            metrics_data = [
                ("Sensors/Level", 10, level),
                ("Sensors/LevelSecondary", 10, level_2),
                ("Battery/Level", 10, battery_level),
                ("Battery/Voltage", 10, battery_voltage),
                ("Device/Uptime", 8, int(time.time() - self.start_time)),
                ("Network/RSSI", 9, rssi),
                ("Network/PacketLoss", 3, packet_loss),
                ("Status/DeviceHealth", 12, "NORMAL" if 10 < level < 90 else "LEVEL_ALARM"),
            ]
            
        # Industrial IoT device types
        elif self.config.device_type == "pump_monitor":
            # Pump monitoring with vibration and performance metrics
            vib_x, vib_y, vib_z = self._get_vibration_data()
            pressure, differential = self._get_realistic_pressure_data()
            temp, _ = self._get_realistic_temperature_data()
            
            # Pump-specific metrics
            pump_speed = 1750 + 100 * math.sin(time.time() / 30) + np.random.normal(0, 25)
            power_consumption = 15.5 + pressure * 0.8 + np.random.normal(0, 0.5)
            efficiency = max(65, min(95, 85 - (time.time() - self.start_time) / 86400 * 0.1))
            
            metrics_data = [
                ("Pump/Speed", 10, pump_speed),
                ("Pump/PowerConsumption", 10, power_consumption),
                ("Pump/Efficiency", 10, efficiency),
                ("Pump/DischargePresssure", 10, pressure),
                ("Pump/Temperature", 10, temp),
                ("Vibration/X", 10, vib_x),
                ("Vibration/Y", 10, vib_y),
                ("Vibration/Z", 10, vib_z),
                ("Device/Uptime", 8, int(time.time() - self.start_time)),
                ("Status/DeviceHealth", 12, "NORMAL" if efficiency > 70 else "MAINTENANCE_REQUIRED"),
            ]
            
        elif self.config.device_type == "compressor_monitor":
            # Compressor monitoring with advanced analytics
            vib_x, vib_y, vib_z = self._get_vibration_data()
            pressure, differential = self._get_realistic_pressure_data()
            temp, _ = self._get_realistic_temperature_data()
            
            # Compressor-specific metrics
            discharge_pressure = pressure * 4 + np.random.normal(0, 0.2)
            compression_ratio = discharge_pressure / pressure
            oil_temperature = temp + 25 + np.random.normal(0, 2)
            load_factor = 45 + 35 * math.sin(time.time() / 120) + np.random.normal(0, 5)
            
            metrics_data = [
                ("Compressor/DischargePressure", 10, discharge_pressure),
                ("Compressor/CompressionRatio", 10, compression_ratio),
                ("Compressor/OilTemperature", 10, oil_temperature),
                ("Compressor/LoadFactor", 10, load_factor),
                ("Vibration/X", 10, vib_x),
                ("Vibration/Y", 10, vib_y),
                ("Vibration/Z", 10, vib_z),
                ("Device/Uptime", 8, int(time.time() - self.start_time)),
                ("Status/DeviceHealth", 12, "NORMAL" if oil_temperature < 85 else "HIGH_TEMPERATURE"),
            ]
            
        elif self.config.device_type == "motor_monitor":
            # Motor monitoring with electrical and mechanical parameters
            vib_x, vib_y, vib_z = self._get_vibration_data()
            temp, _ = self._get_realistic_temperature_data()
            
            # Motor-specific metrics
            motor_current = 8.2 + 2.1 * math.sin(time.time() / 45) + np.random.normal(0, 0.3)
            voltage = 380 + 15 * math.sin(time.time() / 60) + np.random.normal(0, 2)
            power_factor = 0.85 + 0.1 * math.sin(time.time() / 90) + np.random.normal(0, 0.02)
            bearing_temp = temp + 15 + np.random.normal(0, 1.5)
            
            metrics_data = [
                ("Motor/Current", 10, motor_current),
                ("Motor/Voltage", 10, voltage),
                ("Motor/PowerFactor", 10, power_factor),
                ("Motor/BearingTemperature", 10, bearing_temp),
                ("Vibration/X", 10, vib_x),
                ("Vibration/Y", 10, vib_y),
                ("Vibration/Z", 10, vib_z),
                ("Device/Uptime", 8, int(time.time() - self.start_time)),
                ("Status/DeviceHealth", 12, "NORMAL" if bearing_temp < 75 else "BEARING_OVERHEATING"),
            ]
            
        else:
            # Default industrial sensor with basic patterns
            temp, humidity = self._get_realistic_temperature_data()
            battery_level, battery_voltage = self._get_realistic_battery_data()
            rssi, packet_loss = self._get_realistic_network_data()
            
            metrics_data = [
                ("Sensors/PrimaryValue", 10, 50.0 + 25.0 * math.sin(time.time() / 30.0)),
                ("Sensors/SecondaryValue", 10, 25.0 + 10.0 * math.cos(time.time() / 45.0)),
                ("Battery/Level", 10, battery_level),
                ("Device/Uptime", 8, int(time.time() - self.start_time)),
                ("Network/RSSI", 9, rssi),
                ("Status/DeviceHealth", 12, "NORMAL"),
            ]
        
        # Build protobuf payload
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
            elif datatype == 12:  # STRING
                metric.string_value = str(value)
            elif datatype == 11:  # BOOLEAN
                metric.boolean_value = bool(value)
        
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
        """LwM2M device management thread with bulk messaging for high throughput"""
        self.logger.info("Starting LwM2M bulk management thread", 
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
        
        # Bulk management update loop
        bulk_operations = []
        last_bulk_send = time.time()
        
        while self.running and self.mqtt_connected:
            try:
                current_time = time.time()
                
                # Create individual operation
                operation = {
                    "operation": "update",
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
                    "timestamp": int(current_time * 1000)
                }
                
                # Add to bulk operations
                bulk_operations.append(operation)
                
                # Send bulk message when we have enough operations or time has passed
                bulk_size = 10  # Send 10 operations at once
                bulk_interval = 0.05  # Or every 50ms
                
                if (len(bulk_operations) >= bulk_size or 
                    (current_time - last_bulk_send) >= bulk_interval):
                    
                    # Create bulk message
                    bulk_data = {
                        "bulk_operations": bulk_operations,
                        "device_id": self.config.device_id,
                        "bulk_size": len(bulk_operations),
                        "timestamp": int(current_time * 1000)
                    }
                    
                    # Send bulk message
                    bulk_topic = f"lwm2m/{self.config.device_id}/bulk"
                    result = self.mqtt_client.publish(bulk_topic, json.dumps(bulk_data))
                    
                    if result.rc == mqtt.MQTT_ERR_SUCCESS:
                        self.logger.debug("LwM2M bulk update sent", 
                                        bulk_size=len(bulk_operations),
                                        operations_per_sec=len(bulk_operations) / (current_time - last_bulk_send))
                    else:
                        self.logger.warning("LwM2M bulk update failed", error_code=result.rc)
                    
                    # Reset for next bulk send
                    bulk_operations = []
                    last_bulk_send = current_time
                
                time.sleep(self.config.lwm2m_interval)
                
            except Exception as e:
                self.logger.error("Error in LwM2M bulk thread", error=str(e))
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
    
    # Enhanced device types with realistic sensor patterns and industrial IoT scenarios
    device_types = [
        "temperature_sensor",    # Environmental monitoring with daily cycles
        "pressure_sensor",       # Process control with system variations 
        "flow_sensor",          # Demand-based flow patterns
        "level_sensor",         # Tank fill/drain cycles
        "pump_monitor",         # Industrial pump monitoring
        "compressor_monitor",   # Compressor performance analytics
        "motor_monitor",        # Motor electrical and mechanical monitoring
    ]
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
        telemetry_interval=0.001,   # 1000 msg/sec - CRANKED UP!
        lwm2m_interval=0.005       # 200 msg/sec - GOING FOR BROKE!
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
            # Set the device index environment variable for this process
            os.environ['DEVICE_INDEX'] = str(device_index)
            device_config = create_device_config()
            
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