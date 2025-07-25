#!/usr/bin/env python3
"""
Smart Breaker Device Simulator
Implements FDI-compliant smart breaker with LwM2M + Sparkplug B dual-path communication

Features:
- Realistic electrical measurements and protection functions
- FDI-compliant device description and configuration
- High-throughput dual-path communication
- Advanced protection algorithms (overcurrent, ground fault, arc fault)
- Predictive maintenance and condition monitoring
"""

import asyncio
import json
import logging
import os
import ssl
import time
import threading
import uuid
import random
import math
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from queue import Queue
from typing import Dict, Any, Tuple, Optional
from datetime import datetime, timedelta
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
class BreakerConfig:
    """Smart breaker configuration parameters"""
    device_id: str
    rated_current: float = 100.0  # Amperes
    rated_voltage: float = 480.0  # Volts
    rated_frequency: float = 60.0  # Hz
    breaking_capacity: float = 25.0  # kA
    pole_count: int = 3
    mounting_type: str = "PanelMount"
    protection_class: str = "TypeB"
    
    # Protection settings
    overcurrent_pickup: float = 100.0  # A
    overcurrent_delay: float = 1000.0  # ms
    ground_fault_pickup: float = 5.0  # A
    ground_fault_delay: float = 500.0  # ms
    arc_fault_pickup: float = 50.0  # A
    arc_fault_delay: float = 100.0  # ms
    thermal_pickup: float = 120.0  # A
    thermal_delay: float = 300.0  # s
    
    # Communication settings
    mqtt_broker_host: str = "mosquitto"
    mqtt_broker_port: int = 8883
    mqtt_username: str = "device"
    mqtt_password: str = "testpass123"
    mqtt_use_tls: bool = True
    lwm2m_server_host: str = "lwm2m-server"
    lwm2m_server_port: int = 8080
    group_id: str = "IIoT"
    sparkplug_namespace: str = "spBv1.0"
    telemetry_interval: float = 0.001  # 1000 msg/sec
    lwm2m_interval: float = 0.005  # 200 msg/sec

class BreakerState:
    """Smart breaker operational state"""
    def __init__(self, config: BreakerConfig):
        self.config = config
        self.status = 1  # 0=Open, 1=Closed, 2=Tripped, 3=Fault
        self.position = 1  # 0=Disconnected, 1=Connected, 2=Test
        self.trip_count = 0
        self.last_trip_time = None
        self.trip_reason = ""
        self.trip_current = 0.0
        self.trip_delay = 0.0
        self.operating_hours = 0
        self.maintenance_due = False
        self.communication_status = 1  # 0=Offline, 1=Online, 2=Degraded, 3=Fault
        
        # Electrical measurements
        self.current_phase_a = 0.0
        self.current_phase_b = 0.0
        self.current_phase_c = 0.0
        self.voltage_phase_a = config.rated_voltage
        self.voltage_phase_b = config.rated_voltage
        self.voltage_phase_c = config.rated_voltage
        self.power_factor = 0.95
        self.frequency = config.rated_frequency
        self.temperature = 25.0
        
        # Calculated values
        self.active_power = 0.0
        self.reactive_power = 0.0
        self.apparent_power = 0.0
        self.load_percentage = 0.0
        self.harmonic_distortion = 2.5
        
        # Protection monitoring
        self.ground_fault_current = 0.0
        self.arc_fault_detected = False
        self.alarm_status = 0
        
        # Control settings
        self.remote_control_enabled = False
        self.auto_reclose_enabled = False
        self.auto_reclose_attempts = 0
        self.max_auto_reclose_attempts = 1
        
        # Timing
        self.start_time = time.time()
        self.last_protection_check = time.time()
        self.last_maintenance_check = time.time()

class SmartBreakerSimulator:
    """High-performance smart breaker simulator with FDI compliance"""

    def __init__(self, config: BreakerConfig):
        self.config = config
        self.logger = logger.bind(device_id=config.device_id)
        self.fake = Faker()
        
        # Breaker state
        self.breaker_state = BreakerState(config)
        
        # Threading control
        self.running = True
        self.mqtt_connected = False
        
        # MQTT client optimized for high throughput
        import uuid
        self.mqtt_client = mqtt.Client(
            client_id=f"{config.device_id}-{uuid.uuid4().hex[:8]}",
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
        self.command_queue = Queue(maxsize=100)
        
        # Thread pool for message processing
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        self.setup_mqtt_client()
        self.pre_generate_payloads()
        self.start_worker_threads()

    def setup_mqtt_client(self):
        """Setup MQTT client with TLS and authentication"""
        # Authentication (only if username is provided)
        if self.config.mqtt_username and self.config.mqtt_username.strip():
            self.mqtt_client.username_pw_set(self.config.mqtt_username, self.config.mqtt_password)
        
        # TLS setup
        if self.config.mqtt_use_tls:
            context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            self.mqtt_client.tls_set_context(context)
        
        # Callbacks
        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_message = self._on_mqtt_message
        self.mqtt_client.on_disconnect = self._on_mqtt_disconnect
        
        # Connect to broker
        try:
            self.mqtt_client.connect(self.config.mqtt_broker_host, self.config.mqtt_broker_port, 60)
            self.mqtt_client.loop_start()
            self.logger.info("Connected to MQTT broker", host=self.config.mqtt_broker_host, port=self.config.mqtt_broker_port)
        except Exception as e:
            self.logger.error("Failed to connect to MQTT broker", error=str(e))

    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        if rc == 0:
            self.mqtt_connected = True
            self.logger.info("MQTT connected successfully")
            
            # Subscribe to topics
            topics = [
                f"lwm2m/{self.config.device_id}/cmd/#",
                f"spBv1.0/{self.config.group_id}/DCMD/{self.config.device_id}",
                f"spBv1.0/{self.config.group_id}/DDATA/+"
            ]
            
            for topic in topics:
                client.subscribe(topic)
                self.logger.info("Subscribed to topic", topic=topic)
            
            # Send birth certificate
            self._send_sparkplug_birth()
            
        else:
            self.logger.error("MQTT connection failed", rc=rc)

    def _on_mqtt_disconnect(self, client, userdata, rc):
        """MQTT disconnection callback"""
        self.mqtt_connected = False
        self.logger.warning("MQTT disconnected", rc=rc)

    def _on_mqtt_message(self, client, userdata, msg):
        """MQTT message callback"""
        # Process messages in background thread
        self.executor.submit(self._process_command_message, msg.topic, msg.payload)

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
                        "0": "Smart",
                        "1": f"XSeries-SmartBreaker-{self.config.protection_class}",
                        "2": self.config.device_id,
                        "3": "2.1.0"
                    }
                },
                "4": {
                    "0": {
                        "0": 1,
                        "1": 100,
                        "2": 100,
                        "4": "192.168.1.100"
                    }
                },
                "3200": {
                    "0": {
                        "0": self.breaker_state.status,
                        "1": self.breaker_state.current_phase_a,
                        "2": self.breaker_state.current_phase_b,
                        "3": self.breaker_state.current_phase_c,
                        "4": self.breaker_state.voltage_phase_a,
                        "5": self.breaker_state.voltage_phase_b,
                        "6": self.breaker_state.voltage_phase_c,
                        "7": self.breaker_state.power_factor,
                        "8": self.breaker_state.active_power,
                        "9": self.breaker_state.reactive_power,
                        "10": self.breaker_state.apparent_power,
                        "11": self.breaker_state.frequency,
                        "12": self.breaker_state.temperature,
                        "13": self.breaker_state.trip_count,
                        "14": self.breaker_state.last_trip_time or "",
                        "15": self.breaker_state.trip_reason,
                        "16": self.breaker_state.trip_current,
                        "17": self.breaker_state.trip_delay,
                        "18": self.breaker_state.ground_fault_current,
                        "19": self.breaker_state.arc_fault_detected,
                        "20": self.breaker_state.maintenance_due,
                        "21": self.breaker_state.operating_hours,
                        "22": self.breaker_state.load_percentage,
                        "23": self.breaker_state.harmonic_distortion,
                        "24": self.breaker_state.position,
                        "25": self.breaker_state.remote_control_enabled,
                        "26": self.breaker_state.auto_reclose_enabled,
                        "27": self.breaker_state.auto_reclose_attempts,
                        "29": self.breaker_state.alarm_status,
                        "30": self.breaker_state.communication_status
                    }
                },
                "3201": {
                    "0": {
                        "0": self.config.overcurrent_pickup,
                        "1": self.config.overcurrent_delay,
                        "2": self.config.ground_fault_pickup,
                        "3": self.config.ground_fault_delay,
                        "4": self.config.arc_fault_pickup,
                        "5": self.config.arc_fault_delay,
                        "6": self.config.thermal_pickup,
                        "7": self.config.thermal_delay,
                        "8": self.config.overcurrent_pickup * 8,  # Instantaneous pickup
                        "9": 5.0,  # Auto-reclose delay
                        "10": True  # Protection enabled
                    }
                }
            }
        }

    def start_worker_threads(self):
        """Start background worker threads"""
        # Telemetry thread
        threading.Thread(target=self._telemetry_worker, daemon=True).start()
        
        # LwM2M thread
        threading.Thread(target=self._lwm2m_worker, daemon=True).start()
        
        # Protection monitoring thread
        threading.Thread(target=self._protection_monitor, daemon=True).start()
        
        # Maintenance monitoring thread
        threading.Thread(target=self._maintenance_monitor, daemon=True).start()

    def _telemetry_worker(self):
        """High-throughput telemetry worker thread"""
        while self.running:
            try:
                # Generate realistic electrical measurements
                self._update_electrical_measurements()
                
                # Send Sparkplug B telemetry
                if self.mqtt_connected:
                    self._send_sparkplug_telemetry()
                
                time.sleep(self.config.telemetry_interval)
                
            except Exception as e:
                self.logger.error("Error in telemetry worker", error=str(e))
                time.sleep(1)

    def _lwm2m_worker(self):
        """LwM2M device management worker thread"""
        while self.running:
            try:
                if self.mqtt_connected:
                    if not self.lwm2m_registered:
                        self._send_lwm2m_registration()
                    else:
                        self._send_lwm2m_update()
                
                time.sleep(self.config.lwm2m_interval)
                
            except Exception as e:
                self.logger.error("Error in LwM2M worker", error=str(e))
                time.sleep(1)

    def _protection_monitor(self):
        """Protection algorithm monitoring thread"""
        while self.running:
            try:
                self._check_protection_functions()
                time.sleep(0.1)  # 10 Hz protection monitoring
                
            except Exception as e:
                self.logger.error("Error in protection monitor", error=str(e))
                time.sleep(1)

    def _maintenance_monitor(self):
        """Predictive maintenance monitoring thread"""
        while self.running:
            try:
                self._check_maintenance_conditions()
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                self.logger.error("Error in maintenance monitor", error=str(e))
                time.sleep(60)

    def _update_electrical_measurements(self):
        """Update realistic electrical measurements"""
        # Simulate load variations
        base_load = 60.0  # Base load percentage
        load_variation = random.uniform(-10, 10)
        self.breaker_state.load_percentage = max(0, min(100, base_load + load_variation))
        
        # Calculate currents based on load
        max_current = self.config.rated_current
        current_factor = self.breaker_state.load_percentage / 100.0
        
        # Add realistic phase imbalances
        imbalance_a = random.uniform(-0.05, 0.05)
        imbalance_b = random.uniform(-0.05, 0.05)
        imbalance_c = random.uniform(-0.05, 0.05)
        
        self.breaker_state.current_phase_a = max_current * current_factor * (1 + imbalance_a)
        self.breaker_state.current_phase_b = max_current * current_factor * (1 + imbalance_b)
        self.breaker_state.current_phase_c = max_current * current_factor * (1 + imbalance_c)
        
        # Voltage variations
        voltage_variation = random.uniform(-0.02, 0.02)  # ±2%
        self.breaker_state.voltage_phase_a = self.config.rated_voltage * (1 + voltage_variation)
        self.breaker_state.voltage_phase_b = self.config.rated_voltage * (1 + voltage_variation)
        self.breaker_state.voltage_phase_c = self.config.rated_voltage * (1 + voltage_variation)
        
        # Calculate power values
        voltage_avg = (self.breaker_state.voltage_phase_a + self.breaker_state.voltage_phase_b + self.breaker_state.voltage_phase_c) / 3
        current_avg = (self.breaker_state.current_phase_a + self.breaker_state.current_phase_b + self.breaker_state.current_phase_c) / 3
        
        self.breaker_state.apparent_power = voltage_avg * current_avg * math.sqrt(3) / 1000  # kVA
        self.breaker_state.active_power = self.breaker_state.apparent_power * self.breaker_state.power_factor
        self.breaker_state.reactive_power = self.breaker_state.apparent_power * math.sqrt(1 - self.breaker_state.power_factor**2)
        
        # Temperature variations
        temp_variation = random.uniform(-2, 2)
        self.breaker_state.temperature = 25 + temp_variation + (self.breaker_state.load_percentage * 0.3)
        
        # Frequency variations
        freq_variation = random.uniform(-0.1, 0.1)
        self.breaker_state.frequency = self.config.rated_frequency + freq_variation
        
        # Harmonic distortion
        self.breaker_state.harmonic_distortion = 2.5 + random.uniform(-0.5, 0.5)
        
        # Ground fault current (occasional)
        if random.random() < 0.001:  # 0.1% chance
            self.breaker_state.ground_fault_current = random.uniform(0.1, 2.0)
        else:
            self.breaker_state.ground_fault_current = 0.0
        
        # Arc fault detection (rare)
        if random.random() < 0.0001:  # 0.01% chance
            self.breaker_state.arc_fault_detected = True
        else:
            self.breaker_state.arc_fault_detected = False
        
        # Update operating hours
        elapsed_time = time.time() - self.breaker_state.start_time
        self.breaker_state.operating_hours = int(elapsed_time / 3600)

    def _check_protection_functions(self):
        """Check protection functions and trigger trips if needed"""
        current_time = time.time()
        
        # Overcurrent protection
        max_current = max(self.breaker_state.current_phase_a, self.breaker_state.current_phase_b, self.breaker_state.current_phase_c)
        if max_current > self.config.overcurrent_pickup:
            if current_time - self.breaker_state.last_protection_check > (self.config.overcurrent_delay / 1000):
                self._trip_breaker("Overcurrent", max_current, self.config.overcurrent_delay)
        
        # Ground fault protection
        if self.breaker_state.ground_fault_current > self.config.ground_fault_pickup:
            if current_time - self.breaker_state.last_protection_check > (self.config.ground_fault_delay / 1000):
                self._trip_breaker("GroundFault", self.breaker_state.ground_fault_current, self.config.ground_fault_delay)
        
        # Arc fault protection
        if self.breaker_state.arc_fault_detected:
            if current_time - self.breaker_state.last_protection_check > (self.config.arc_fault_delay / 1000):
                self._trip_breaker("ArcFault", max_current, self.config.arc_fault_delay)
        
        # Thermal protection
        if max_current > self.config.thermal_pickup:
            if current_time - self.breaker_state.last_protection_check > self.config.thermal_delay:
                self._trip_breaker("Thermal", max_current, self.config.thermal_delay * 1000)
        
        self.breaker_state.last_protection_check = current_time

    def _trip_breaker(self, reason: str, trip_current: float, trip_delay: float):
        """Trip the breaker due to protection function"""
        if self.breaker_state.status == 1:  # Only trip if currently closed
            self.breaker_state.status = 2  # Tripped
            self.breaker_state.trip_count += 1
            self.breaker_state.last_trip_time = datetime.now().isoformat()
            self.breaker_state.trip_reason = reason
            self.breaker_state.trip_current = trip_current
            self.breaker_state.trip_delay = trip_delay
            self.breaker_state.alarm_status |= 0x01  # Set alarm bit
            
            self.logger.warning("Breaker tripped", reason=reason, current=trip_current, delay=trip_delay)
            
            # Send immediate notification
            self._send_trip_notification(reason, trip_current)
            
            # Auto-reclose logic
            if self.breaker_state.auto_reclose_enabled and self.breaker_state.auto_reclose_attempts < self.breaker_state.max_auto_reclose_attempts:
                threading.Timer(5.0, self._auto_reclose).start()

    def _auto_reclose(self):
        """Auto-reclose the breaker"""
        if self.breaker_state.status == 2:  # Tripped
            self.breaker_state.status = 1  # Closed
            self.breaker_state.auto_reclose_attempts += 1
            self.logger.info("Breaker auto-reclosed", attempts=self.breaker_state.auto_reclose_attempts)

    def _check_maintenance_conditions(self):
        """Check maintenance conditions"""
        # Check operating hours
        if self.breaker_state.operating_hours > 5000:  # 5000 hours threshold
            self.breaker_state.maintenance_due = True
        
        # Check trip count
        if self.breaker_state.trip_count > 1000:  # 1000 trips threshold
            self.breaker_state.maintenance_due = True
        
        # Check temperature
        if self.breaker_state.temperature > 75:  # 75°C threshold
            self.breaker_state.maintenance_due = True

    def _send_sparkplug_birth(self):
        """Send Sparkplug B birth certificate"""
        if self.sparkplug_birth_payload:
            topic = f"spBv1.0/{self.config.group_id}/DBIRTH/{self.config.device_id}"
            self.mqtt_client.publish(topic, self.sparkplug_birth_payload.SerializeToString())
            self.logger.info("Sent Sparkplug B birth certificate")

    def _send_sparkplug_telemetry(self):
        """Send Sparkplug B telemetry data"""
        payload = Payload()
        payload.timestamp = int(time.time() * 1000)
        payload.seq = self.sparkplug_seq
        payload.uuid = str(uuid.uuid4())
        
        # Add breaker metrics
        metrics_data = [
            ("Breaker/Status", 10, self.breaker_state.status),  # INT32 = 10
            ("Breaker/CurrentPhaseA", 12, self.breaker_state.current_phase_a),  # FLOAT = 12
            ("Breaker/CurrentPhaseB", 12, self.breaker_state.current_phase_b),
            ("Breaker/CurrentPhaseC", 12, self.breaker_state.current_phase_c),
            ("Breaker/VoltagePhaseA", 12, self.breaker_state.voltage_phase_a),
            ("Breaker/VoltagePhaseB", 12, self.breaker_state.voltage_phase_b),
            ("Breaker/VoltagePhaseC", 12, self.breaker_state.voltage_phase_c),
            ("Breaker/PowerFactor", 12, self.breaker_state.power_factor),
            ("Breaker/ActivePower", 12, self.breaker_state.active_power),
            ("Breaker/ReactivePower", 12, self.breaker_state.reactive_power),
            ("Breaker/ApparentPower", 12, self.breaker_state.apparent_power),
            ("Breaker/Frequency", 12, self.breaker_state.frequency),
            ("Breaker/Temperature", 12, self.breaker_state.temperature),
            ("Breaker/TripCount", 10, self.breaker_state.trip_count),
            ("Breaker/LoadPercentage", 12, self.breaker_state.load_percentage),
            ("Breaker/HarmonicDistortion", 12, self.breaker_state.harmonic_distortion),
            ("Breaker/Position", 10, self.breaker_state.position),
            ("Breaker/RemoteControlEnabled", 11, self.breaker_state.remote_control_enabled),
            ("Breaker/AutoRecloseEnabled", 11, self.breaker_state.auto_reclose_enabled),
            ("Breaker/AutoRecloseAttempts", 10, self.breaker_state.auto_reclose_attempts),
            ("Breaker/AlarmStatus", 10, self.breaker_state.alarm_status),
            ("Breaker/CommunicationStatus", 10, self.breaker_state.communication_status),
            ("Protection/OvercurrentPickup", 12, self.config.overcurrent_pickup),
            ("Protection/GroundFaultPickup", 12, self.config.ground_fault_pickup),
            ("Protection/ArcFaultPickup", 12, self.config.arc_fault_pickup),
            ("Protection/Enabled", 11, True)
        ]
        
        for name, datatype, value in metrics_data:
            metric = payload.metrics.add()
            metric.name = name
            metric.datatype = datatype
            metric.timestamp = payload.timestamp
            
            if datatype == 10:  # INT32
                metric.int_value = int(value)
            elif datatype == 11:  # BOOLEAN
                metric.boolean_value = bool(value)
            elif datatype == 12:  # FLOAT
                metric.float_value = float(value)
        
        topic = f"spBv1.0/{self.config.group_id}/DDATA/{self.config.device_id}"
        self.mqtt_client.publish(topic, payload.SerializeToString())
        
        self.sparkplug_seq = (self.sparkplug_seq + 1) % 256

    def _send_lwm2m_registration(self):
        """Send LwM2M registration"""
        topic = f"lwm2m/{self.config.device_id}/reg"
        self.mqtt_client.publish(topic, json.dumps(self.lwm2m_registration_data))
        self.lwm2m_registered = True
        self.logger.info("Sent LwM2M registration")

    def _send_lwm2m_update(self):
        """Send LwM2M update"""
        # Update the registration data with current values
        self.lwm2m_registration_data["objects"]["3200"]["0"].update({
            "0": self.breaker_state.status,
            "1": self.breaker_state.current_phase_a,
            "2": self.breaker_state.current_phase_b,
            "3": self.breaker_state.current_phase_c,
            "4": self.breaker_state.voltage_phase_a,
            "5": self.breaker_state.voltage_phase_b,
            "6": self.breaker_state.voltage_phase_c,
            "7": self.breaker_state.power_factor,
            "8": self.breaker_state.active_power,
            "9": self.breaker_state.reactive_power,
            "10": self.breaker_state.apparent_power,
            "11": self.breaker_state.frequency,
            "12": self.breaker_state.temperature,
            "13": self.breaker_state.trip_count,
            "14": self.breaker_state.last_trip_time or "",
            "15": self.breaker_state.trip_reason,
            "16": self.breaker_state.trip_current,
            "17": self.breaker_state.trip_delay,
            "18": self.breaker_state.ground_fault_current,
            "19": self.breaker_state.arc_fault_detected,
            "20": self.breaker_state.maintenance_due,
            "21": self.breaker_state.operating_hours,
            "22": self.breaker_state.load_percentage,
            "23": self.breaker_state.harmonic_distortion,
            "24": self.breaker_state.position,
            "25": self.breaker_state.remote_control_enabled,
            "26": self.breaker_state.auto_reclose_enabled,
            "27": self.breaker_state.auto_reclose_attempts,
            "29": self.breaker_state.alarm_status,
            "30": self.breaker_state.communication_status
        })
        
        topic = f"lwm2m/{self.config.device_id}/update"
        self.mqtt_client.publish(topic, json.dumps(self.lwm2m_registration_data))

    def _send_trip_notification(self, reason: str, trip_current: float):
        """Send trip notification"""
        notification = {
            "device_id": self.config.device_id,
            "event_type": "breaker_trip",
            "reason": reason,
            "trip_current": trip_current,
            "timestamp": datetime.now().isoformat(),
            "breaker_status": self.breaker_state.status,
            "trip_count": self.breaker_state.trip_count
        }
        
        # Send via Sparkplug B
        topic = f"spBv1.0/{self.config.group_id}/DDATA/{self.config.device_id}"
        self.mqtt_client.publish(topic, json.dumps(notification))
        
        # Send via LwM2M
        topic = f"lwm2m/{self.config.device_id}/event"
        self.mqtt_client.publish(topic, json.dumps(notification))

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
        try:
            command_data = json.loads(payload)
            command = command_data.get("command", "")
            
            if command == "trip":
                self._trip_breaker("RemoteCommand", 0.0, 0.0)
            elif command == "close":
                if self.breaker_state.status == 2:  # Tripped
                    self.breaker_state.status = 1  # Closed
                    self.breaker_state.auto_reclose_attempts = 0
            elif command == "reset":
                self.breaker_state.alarm_status = 0
            elif command == "configure":
                # Handle FDI configuration
                self._handle_fdi_configuration(command_data)
            elif command == "get_configuration":
                # Send current configuration back
                self._send_current_configuration()
            
            self.logger.info("Executed LwM2M command", command=command)
            
        except Exception as e:
            self.logger.error("Error handling LwM2M command", error=str(e))
    
    def _handle_fdi_configuration(self, command_data: Dict[str, Any]):
        """Handle FDI configuration commands"""
        try:
            template = command_data.get("template")
            settings = command_data.get("settings", {})
            
            if template:
                self.logger.info("Applying FDI configuration template", template=template)
                
                # Apply template-specific settings
                if template == "StandardProtection":
                    self._apply_standard_protection_settings(settings)
                elif template == "HighSensitivity":
                    self._apply_high_sensitivity_settings(settings)
                elif template == "MotorProtection":
                    self._apply_motor_protection_settings(settings)
                else:
                    # Apply generic settings
                    self._apply_generic_settings(settings)
            else:
                # Apply direct settings
                self._apply_generic_settings(settings)
            
            # Update LwM2M registration data with new settings
            self._update_lwm2m_configuration()
            
            self.logger.info("FDI configuration applied", template=template)
            
        except Exception as e:
            self.logger.error("Error applying FDI configuration", error=str(e))
    
    def _apply_standard_protection_settings(self, settings: Dict[str, Any]):
        """Apply standard protection settings"""
        for setting_name, setting_data in settings.items():
            value = setting_data.get("value")
            if value is not None:
                if setting_name == "OvercurrentPickup":
                    self.config.overcurrent_pickup = float(value)
                elif setting_name == "OvercurrentDelay":
                    self.config.overcurrent_delay = float(value)
                elif setting_name == "GroundFaultPickup":
                    self.config.ground_fault_pickup = float(value)
                elif setting_name == "GroundFaultDelay":
                    self.config.ground_fault_delay = float(value)
                elif setting_name == "ArcFaultPickup":
                    self.config.arc_fault_pickup = float(value)
                elif setting_name == "ArcFaultDelay":
                    self.config.arc_fault_delay = float(value)
    
    def _apply_high_sensitivity_settings(self, settings: Dict[str, Any]):
        """Apply high sensitivity protection settings"""
        for setting_name, setting_data in settings.items():
            value = setting_data.get("value")
            if value is not None:
                if setting_name == "OvercurrentPickup":
                    self.config.overcurrent_pickup = float(value)
                elif setting_name == "OvercurrentDelay":
                    self.config.overcurrent_delay = float(value)
                elif setting_name == "GroundFaultPickup":
                    self.config.ground_fault_pickup = float(value)
                elif setting_name == "GroundFaultDelay":
                    self.config.ground_fault_delay = float(value)
                elif setting_name == "ArcFaultPickup":
                    self.config.arc_fault_pickup = float(value)
                elif setting_name == "ArcFaultDelay":
                    self.config.arc_fault_delay = float(value)
    
    def _apply_motor_protection_settings(self, settings: Dict[str, Any]):
        """Apply motor protection settings"""
        for setting_name, setting_data in settings.items():
            value = setting_data.get("value")
            if value is not None:
                if setting_name == "OvercurrentPickup":
                    self.config.overcurrent_pickup = float(value)
                elif setting_name == "OvercurrentDelay":
                    self.config.overcurrent_delay = float(value)
                elif setting_name == "ThermalPickup":
                    self.config.thermal_pickup = float(value)
                elif setting_name == "ThermalDelay":
                    self.config.thermal_delay = float(value)
                elif setting_name == "InstantaneousPickup":
                    # Instantaneous pickup is typically 8x overcurrent pickup
                    pass  # Handled by overcurrent pickup
    
    def _apply_generic_settings(self, settings: Dict[str, Any]):
        """Apply generic settings"""
        for setting_name, setting_data in settings.items():
            value = setting_data.get("value")
            if value is not None:
                if setting_name == "OvercurrentPickup":
                    self.config.overcurrent_pickup = float(value)
                elif setting_name == "OvercurrentDelay":
                    self.config.overcurrent_delay = float(value)
                elif setting_name == "GroundFaultPickup":
                    self.config.ground_fault_pickup = float(value)
                elif setting_name == "GroundFaultDelay":
                    self.config.ground_fault_delay = float(value)
                elif setting_name == "ArcFaultPickup":
                    self.config.arc_fault_pickup = float(value)
                elif setting_name == "ArcFaultDelay":
                    self.config.arc_fault_delay = float(value)
                elif setting_name == "ThermalPickup":
                    self.config.thermal_pickup = float(value)
                elif setting_name == "ThermalDelay":
                    self.config.thermal_delay = float(value)
    
    def _update_lwm2m_configuration(self):
        """Update LwM2M registration data with new configuration"""
        if self.lwm2m_registration_data and "objects" in self.lwm2m_registration_data:
            # Update protection settings object
            if "3201" in self.lwm2m_registration_data["objects"]:
                self.lwm2m_registration_data["objects"]["3201"]["0"].update({
                    "0": self.config.overcurrent_pickup,
                    "1": self.config.overcurrent_delay,
                    "2": self.config.ground_fault_pickup,
                    "3": self.config.ground_fault_delay,
                    "4": self.config.arc_fault_pickup,
                    "5": self.config.arc_fault_delay,
                    "6": self.config.thermal_pickup,
                    "7": self.config.thermal_delay,
                    "8": self.config.overcurrent_pickup * 8,  # Instantaneous pickup
                })
    
    def _send_current_configuration(self):
        """Send current configuration back to FDI host"""
        try:
            configuration = {
                "device_id": self.config.device_id,
                "configuration": {
                    "overcurrent_pickup": self.config.overcurrent_pickup,
                    "overcurrent_delay": self.config.overcurrent_delay,
                    "ground_fault_pickup": self.config.ground_fault_pickup,
                    "ground_fault_delay": self.config.ground_fault_delay,
                    "arc_fault_pickup": self.config.arc_fault_pickup,
                    "arc_fault_delay": self.config.arc_fault_delay,
                    "thermal_pickup": self.config.thermal_pickup,
                    "thermal_delay": self.config.thermal_delay,
                    "rated_current": self.config.rated_current,
                    "rated_voltage": self.config.rated_voltage,
                    "rated_frequency": self.config.rated_frequency,
                    "breaking_capacity": self.config.breaking_capacity,
                    "pole_count": self.config.pole_count,
                    "protection_class": self.config.protection_class
                },
                "timestamp": datetime.now().isoformat()
            }
            
            # Send via LwM2M
            topic = f"lwm2m/{self.config.device_id}/config"
            self.mqtt_client.publish(topic, json.dumps(configuration))
            
            self.logger.info("Sent current configuration")
            
        except Exception as e:
            self.logger.error("Error sending current configuration", error=str(e))

    def _handle_sparkplug_command(self, topic: str, payload: bytes):
        """Handle Sparkplug B command messages"""
        try:
            # Parse Sparkplug B command
            command_payload = Payload()
            command_payload.ParseFromString(payload)
            
            for metric in command_payload.metrics:
                if metric.name == "Command/Trip" and metric.boolean_value:
                    self._trip_breaker("SparkplugCommand", 0.0, 0.0)
                elif metric.name == "Command/Close" and metric.boolean_value:
                    if self.breaker_state.status == 2:  # Tripped
                        self.breaker_state.status = 1  # Closed
                        self.breaker_state.auto_reclose_attempts = 0
                elif metric.name == "Command/Reset" and metric.boolean_value:
                    self.breaker_state.alarm_status = 0
            
            self.logger.info("Executed Sparkplug B command")
            
        except Exception as e:
            self.logger.error("Error handling Sparkplug B command", error=str(e))

    def _create_sparkplug_birth_payload(self) -> Payload:
        """Create Sparkplug B birth certificate payload"""
        payload = Payload()
        payload.timestamp = int(time.time() * 1000)
        payload.seq = 0
        payload.uuid = str(uuid.uuid4())
        
        # Add device metrics
        metrics_data = [
            ("Device/Type", 12, "SmartBreaker"),  # STRING = 12
            ("Device/Manufacturer", 12, "Smart"),  # STRING = 12
            ("Device/Model", 12, f"XSeries-SmartBreaker-{self.config.protection_class}"),  # STRING = 12
            ("Device/SerialNumber", 12, self.config.device_id),  # STRING = 12
            ("Device/FirmwareVersion", 12, "2.1.0"),  # STRING = 12
            ("Device/Online", 11, True),  # BOOLEAN = 11
            ("Device/RatedCurrent", 12, self.config.rated_current),  # FLOAT = 12
            ("Device/RatedVoltage", 12, self.config.rated_voltage),  # FLOAT = 12
            ("Device/RatedFrequency", 12, self.config.rated_frequency),  # FLOAT = 12
            ("Device/BreakingCapacity", 12, self.config.breaking_capacity),  # FLOAT = 12
            ("Device/PoleCount", 10, self.config.pole_count),  # INT32 = 10
            ("Device/MountingType", 12, self.config.mounting_type),  # STRING = 12
            ("Device/ProtectionClass", 12, self.config.protection_class),  # STRING = 12
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
            elif datatype == 10:  # INT32
                metric.int_value = int(value)
        
        return payload

    def stop(self):
        """Stop the simulator"""
        self.running = False
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
        self.executor.shutdown(wait=True)
        self.logger.info("Smart breaker simulator stopped")

def create_breaker_config() -> BreakerConfig:
    """Create breaker configuration with environment variables"""
    device_count = int(os.getenv("DEVICE_COUNT", "1"))
    device_index = int(os.getenv("DEVICE_INDEX", "0"))
    
    return BreakerConfig(
        device_id=f"smart-breaker-{device_index:03d}",
        rated_current=float(os.getenv("RATED_CURRENT", "100.0")),
        rated_voltage=float(os.getenv("RATED_VOLTAGE", "480.0")),
        rated_frequency=float(os.getenv("RATED_FREQUENCY", "60.0")),
        breaking_capacity=float(os.getenv("BREAKING_CAPACITY", "25.0")),
        pole_count=int(os.getenv("POLE_COUNT", "3")),
        mounting_type=os.getenv("MOUNTING_TYPE", "PanelMount"),
        protection_class=os.getenv("PROTECTION_CLASS", "TypeB"),
        overcurrent_pickup=float(os.getenv("OVERCURRENT_PICKUP", "100.0")),
        overcurrent_delay=float(os.getenv("OVERCURRENT_DELAY", "1000.0")),
        ground_fault_pickup=float(os.getenv("GROUND_FAULT_PICKUP", "5.0")),
        ground_fault_delay=float(os.getenv("GROUND_FAULT_DELAY", "500.0")),
        arc_fault_pickup=float(os.getenv("ARC_FAULT_PICKUP", "50.0")),
        arc_fault_delay=float(os.getenv("ARC_FAULT_DELAY", "100.0")),
        thermal_pickup=float(os.getenv("THERMAL_PICKUP", "120.0")),
        thermal_delay=float(os.getenv("THERMAL_DELAY", "300.0")),
        mqtt_broker_host=os.getenv("MQTT_BROKER_HOST", "mosquitto"),
        mqtt_broker_port=int(os.getenv("MQTT_BROKER_PORT", "8883")),
        mqtt_username=os.getenv("MQTT_USERNAME", "device"),
        mqtt_password=os.getenv("MQTT_PASSWORD", "testpass123"),
        mqtt_use_tls=os.getenv("MQTT_USE_TLS", "true").lower() in ("true", "1", "yes"),
        lwm2m_server_host=os.getenv("LWM2M_SERVER_HOST", "lwm2m-server"),
        lwm2m_server_port=int(os.getenv("LWM2M_SERVER_PORT", "8080")),
        group_id=os.getenv("GROUP_ID", "IIoT"),
        sparkplug_namespace=os.getenv("SPARKPLUG_NAMESPACE", "spBv1.0"),
        telemetry_interval=0.001,  # 1000 msg/sec
        lwm2m_interval=0.005  # 200 msg/sec
    )

def main():
    """Main function"""
    try:
        config = create_breaker_config()
        simulator = SmartBreakerSimulator(config)
        
        logger.info("Smart breaker simulator started", 
                   device_id=config.device_id,
                   rated_current=config.rated_current,
                   rated_voltage=config.rated_voltage,
                   protection_class=config.protection_class)
        
        # Keep running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
        if 'simulator' in locals():
            simulator.stop()
    except Exception as e:
        logger.error("Fatal error", error=str(e))
        if 'simulator' in locals():
            simulator.stop()

if __name__ == "__main__":
    main() 