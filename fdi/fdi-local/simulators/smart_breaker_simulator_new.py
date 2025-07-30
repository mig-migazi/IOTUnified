#!/usr/bin/env python3
"""
Smart Breaker Simulator - NEW CLEAN VERSION
Starting with minimal MQTT connection only
"""

import paho.mqtt.client as mqtt
import time
import sys
import os
import random
import json

# Add the simulators directory to the Python path for protobuf import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import Sparkplug B protobuf
try:
    from proto.sparkplug_b_pb2 import Payload, Metric, DataType
    PROTOBUF_AVAILABLE = True
except ImportError:
    print("ERROR: Protobuf not available. Install: pip install protobuf")
    PROTOBUF_AVAILABLE = False

class BreakerConfig:
    """Minimal breaker configuration"""
    def __init__(self):
        self.device_id = "smart-breaker-000"
        self.mqtt_broker_host = "localhost"
        self.mqtt_broker_port = 1883

class SmartBreakerSimulator:
    """Minimal smart breaker simulator - MQTT connection only"""

    def __init__(self):
        """Initialize the smart breaker simulator"""
        print("DEBUG: SmartBreakerSimulator constructor called")
        
        # Create minimal breaker configuration
        self.config = self._create_minimal_breaker_config()
        
        # Initialize device state
        self.breaker_status = "closed"
        self.trip_count = 0
        self.last_trip_time = "2024-01-15T14:30:00Z"
        self.trip_reason = "Overcurrent"
        self.alarm_status = 0
        
        # Initialize MQTT client
        self.mqtt_client = None
        self.mqtt_connected = False
        
        # Setup MQTT client
        self.setup_mqtt_client()
        
        print("DEBUG: Constructor completed")
    
    def _create_minimal_breaker_config(self):
        """Create minimal breaker configuration"""
        return {
            "device_id": "smart-breaker-000",
            "protection": {
                "overcurrent_pickup": 100.0,
                "overcurrent_delay": 1000.0,
                "ground_fault_pickup": 5.0,
                "ground_fault_delay": 500.0,
                "arc_fault_pickup": 50.0,
                "arc_fault_delay": 100.0,
                "thermal_pickup": 120.0,
                "thermal_delay": 300.0,
                "instantaneous_pickup": 800.0,
                "auto_reclose_delay": 5.0,
                "enabled": True
            },
            "control": {
                "remote_control_enabled": False,
                "auto_reclose_enabled": False,
                "auto_reclose_attempts": 1
            },
            "monitoring": {
                "measurement_interval": 1000,
                "harmonic_analysis": True,
                "power_quality_monitoring": True
            },
            "maintenance": {
                "maintenance_interval": 5000,
                "temperature_threshold": 75.0,
                "trip_count_threshold": 1000
            }
        }

    def get_current_configuration(self):
        """Get current configuration as a dictionary"""
        return {
            "protection": self.config["protection"].copy(),
            "control": self.config["control"].copy(),
            "monitoring": self.config["monitoring"].copy(),
            "maintenance": self.config["maintenance"].copy()
        }

    def setup_mqtt_client(self):
        """Setup MQTT client - MINIMAL VERSION"""
        # Initialize MQTT client
        self.mqtt_client = mqtt.Client()
        
        # Callbacks
        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_message = self._on_mqtt_message
        self.mqtt_client.on_disconnect = self._on_mqtt_disconnect
        
        # Connect to broker
        try:
            time.sleep(0.1)  # Small delay to ensure client is ready
            self.mqtt_client.connect("localhost", 1883, 60)
            self.mqtt_client.loop_start()
            print(f"Connected to MQTT broker at localhost:1883")
        except Exception as e:
            print(f"Failed to connect to MQTT broker: {e}")

    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        print(f"Connected to MQTT broker with result code: {rc}")
        if rc == 0:
            print("MQTT connection successful")
            self.mqtt_connected = True
            
            # Subscribe to Sparkplug B topics
            client.subscribe("spBv1.0/+/+/NBIRTH/#")
            client.subscribe("spBv1.0/+/DBIRTH/+")
            client.subscribe("spBv1.0/+/DDATA/+")
            client.subscribe("spBv1.0/+/+/NDEATH/#")
            client.subscribe("spBv1.0/+/+/DDEATH/#")
            
            # Subscribe to command topics
            client.subscribe("spBv1.0/IIoT/NCMD/#")
            
            print("Subscribed to MQTT topics")
            
            # Send birth certificate
            self._send_birth_certificate()
        else:
            print(f"Failed to connect to MQTT broker, return code: {rc}")

    def _on_mqtt_disconnect(self, client, userdata, rc):
        """MQTT disconnection callback - MINIMAL VERSION"""
        self.mqtt_connected = False
        print(f"MQTT disconnected with rc={rc}")

    def _on_mqtt_message(self, client, userdata, msg):
        """MQTT message callback"""
        print(f"Received message on topic: {msg.topic}")
        
        # Parse topic to determine message type
        topic_parts = msg.topic.split('/')
        
        if len(topic_parts) >= 4:
            message_type = topic_parts[2]
            
            if message_type == "NCMD":
                # Handle command messages
                self._handle_command_message(msg.payload)
            else:
                # Handle other Sparkplug B messages (birth, data, death)
                print(f"Received {message_type} message")
    
    def _handle_command_message(self, payload):
        """Handle MQTT command messages"""
        try:
            # Parse JSON command message
            command_data = json.loads(payload.decode('utf-8'))
            print(f"Received command: {command_data}")
            
            command = command_data.get('command', '')
            parameters = command_data.get('parameters', {})
            
            if command == "set_configuration":
                self._apply_configuration(parameters)
            elif command == "trip":
                self._trip_breaker(parameters.get('reason', 'Manual'))
            elif command == "close":
                self._close_breaker(parameters.get('reason', 'Manual'))
            elif command == "reset":
                self._reset_breaker(parameters.get('reset_type', 'Full'))
            else:
                print(f"Unknown command: {command}")
                
        except Exception as e:
            print(f"Error handling command message: {e}")
    
    def _apply_configuration(self, parameters):
        """Apply configuration parameters to the device"""
        print(f"Applying configuration: {parameters}")
        
        # Store old configuration for comparison
        old_config = self.get_current_configuration()
        
        # Apply new parameters
        for param_name, param_value in parameters.items():
            # Map FDI parameter names to simulator parameters
            if param_name == "OvercurrentPickup":
                self.config["protection"]["overcurrent_pickup"] = float(param_value)
            elif param_name == "OvercurrentDelay":
                self.config["protection"]["overcurrent_delay"] = float(param_value)
            elif param_name == "GroundFaultPickup":
                self.config["protection"]["ground_fault_pickup"] = float(param_value)
            elif param_name == "GroundFaultDelay":
                self.config["protection"]["ground_fault_delay"] = float(param_value)
            elif param_name == "ArcFaultPickup":
                self.config["protection"]["arc_fault_pickup"] = float(param_value)
            elif param_name == "ArcFaultDelay":
                self.config["protection"]["arc_fault_delay"] = float(param_value)
            elif param_name == "ThermalPickup":
                self.config["protection"]["thermal_pickup"] = float(param_value)
            elif param_name == "ThermalDelay":
                self.config["protection"]["thermal_delay"] = float(param_value)
            elif param_name == "InstantaneousPickup":
                self.config["protection"]["instantaneous_pickup"] = float(param_value)
            elif param_name == "AutoRecloseDelay":
                self.config["protection"]["auto_reclose_delay"] = float(param_value)
            elif param_name == "RemoteControlEnabled":
                self.config["control"]["remote_control_enabled"] = bool(param_value)
            elif param_name == "AutoRecloseEnabled":
                self.config["control"]["auto_reclose_enabled"] = bool(param_value)
            elif param_name == "AutoRecloseAttempts":
                self.config["control"]["auto_reclose_attempts"] = int(param_value)
            elif param_name == "MeasurementInterval":
                self.config["monitoring"]["measurement_interval"] = int(param_value)
            elif param_name == "HarmonicAnalysis":
                self.config["monitoring"]["harmonic_analysis"] = bool(param_value)
            elif param_name == "PowerQualityMonitoring":
                self.config["monitoring"]["power_quality_monitoring"] = bool(param_value)
            elif param_name == "MaintenanceInterval":
                self.config["maintenance"]["maintenance_interval"] = int(param_value)
            elif param_name == "TemperatureThreshold":
                self.config["maintenance"]["temperature_threshold"] = float(param_value)
            elif param_name == "TripCountThreshold":
                self.config["maintenance"]["trip_count_threshold"] = int(param_value)
            else:
                print(f"Unknown parameter: {param_name}")
        
        # Get new configuration for comparison
        new_config = self.get_current_configuration()
        
        # Print configuration changes
        print("Configuration changes:")
        for section in ["protection", "control", "monitoring", "maintenance"]:
            for param, new_value in new_config[section].items():
                old_value = old_config[section].get(param)
                if old_value != new_value:
                    print(f"  {section}.{param}: {old_value} -> {new_value}")
        
        print("Configuration applied successfully")
    
    def _trip_breaker(self, reason):
        """Trip the circuit breaker"""
        print(f"Tripping breaker - reason: {reason}")
        self.breaker_status = "open"
        self.trip_count += 1
        self.last_trip_time = time.strftime("%Y-%m-%dT%H:%M:%SZ")
        self.trip_reason = reason
    
    def _close_breaker(self, reason):
        """Close the circuit breaker"""
        print(f"Closing breaker - reason: {reason}")
        self.breaker_status = "closed"
    
    def _reset_breaker(self, reset_type):
        """Reset the circuit breaker"""
        print(f"Resetting breaker - type: {reset_type}")
        if reset_type == "Full":
            self.trip_count = 0
            self.alarm_status = 0
        elif reset_type == "Alarms":
            self.alarm_status = 0
        elif reset_type == "Counters":
            self.trip_count = 0

    def _send_birth_certificate(self):
        """Send birth certificate for device discovery"""
        if not PROTOBUF_AVAILABLE:
            print("ERROR: Cannot send birth certificate - protobuf not available")
            return
            
        try:
            # Create Sparkplug B birth certificate
            payload = Payload()
            payload.timestamp = int(time.time() * 1000)
            payload.seq = 0
            
            # Add device metrics (matching FDI profile)
            metrics_data = [
                ("Device/Type", DataType.STRING, "SmartCircuitBreaker"),
                ("Device/Manufacturer", DataType.STRING, "Smart"),
                ("Device/Model", DataType.STRING, "XSeries-SmartBreaker"),
                ("Device/SerialNumber", DataType.STRING, "ETN-XSB-001"),
                ("Device/FirmwareVersion", DataType.STRING, "2.1.0"),
                ("Device/Online", DataType.BOOLEAN, True),
            ]
            
            # Add protection settings (default values from FDI profile)
            protection_metrics = [
                ("Protection/OvercurrentPickup", DataType.FLOAT, 100.0),
                ("Protection/OvercurrentDelay", DataType.FLOAT, 1000.0),
                ("Protection/GroundFaultPickup", DataType.FLOAT, 5.0),
                ("Protection/GroundFaultDelay", DataType.FLOAT, 500.0),
                ("Protection/ArcFaultPickup", DataType.FLOAT, 50.0),
                ("Protection/ArcFaultDelay", DataType.FLOAT, 100.0),
                ("Protection/ThermalPickup", DataType.FLOAT, 120.0),
                ("Protection/ThermalDelay", DataType.FLOAT, 300.0),
                ("Protection/InstantaneousPickup", DataType.FLOAT, 800.0),
                ("Protection/AutoRecloseDelay", DataType.FLOAT, 5.0),
                ("Protection/Enabled", DataType.BOOLEAN, True),
            ]
            
            # Combine device and protection metrics
            metrics_data.extend(protection_metrics)
            
            # Add additional device capabilities (default values)
            capability_metrics = [
                ("Breaker/ActivePower", DataType.FLOAT, 1829.6),
                ("Breaker/Frequency", DataType.FLOAT, 60.0),
                ("Breaker/OperatingHours", DataType.INT32, 8760),
                ("Breaker/LoadPercentage", DataType.FLOAT, 75.5),
                ("Breaker/RemoteControlEnabled", DataType.BOOLEAN, True),
                ("Breaker/AutoRecloseEnabled", DataType.BOOLEAN, False),
            ]
            
            # Combine all metrics
            metrics_data.extend(capability_metrics)
            
            for name, datatype, value in metrics_data:
                metric = payload.metrics.add()
                metric.name = name
                metric.datatype = datatype
                metric.timestamp = payload.timestamp
                
                if datatype == DataType.STRING:
                    metric.string_value = str(value)
                elif datatype == DataType.BOOLEAN:
                    metric.boolean_value = bool(value)
                elif datatype == DataType.FLOAT:
                    metric.float_value = float(value)
                elif datatype == DataType.INT32:
                    metric.int_value = int(value)
            
            # Send protobuf birth certificate
            topic = f"spBv1.0/IIoT/DBIRTH/smart-breaker-000"
            self.mqtt_client.publish(topic, payload.SerializeToString())
            print(f"Sent protobuf birth certificate: {topic}")
            
        except Exception as e:
            print(f"Error sending birth certificate: {e}")

    def _send_telemetry(self):
        """Send basic telemetry data"""
        if not PROTOBUF_AVAILABLE:
            print("ERROR: Cannot send telemetry - protobuf not available")
            return
            
        try:
            # Create Sparkplug B telemetry payload
            payload = Payload()
            payload.timestamp = int(time.time() * 1000)
            payload.seq = 0
            
            # Generate random but realistic telemetry values
            current_a = random.uniform(40.0, 50.0)  # 40-50A
            current_b = random.uniform(40.0, 50.0)  # 40-50A
            current_c = random.uniform(40.0, 50.0)  # 40-50A
            voltage_a = random.uniform(475.0, 485.0)  # 475-485V
            voltage_b = random.uniform(475.0, 485.0)  # 475-485V
            voltage_c = random.uniform(475.0, 485.0)  # 475-485V
            temperature = random.uniform(20.0, 35.0)  # 20-35°C
            status = random.choice(["closed", "open"])  # Random status
            trip_count = random.randint(0, 5)  # 0-5 trips
            
            # Add telemetry metrics
            metrics_data = [
                ("Breaker/CurrentPhaseA", DataType.FLOAT, current_a),
                ("Breaker/CurrentPhaseB", DataType.FLOAT, current_b),
                ("Breaker/CurrentPhaseC", DataType.FLOAT, current_c),
                ("Breaker/VoltagePhaseA", DataType.FLOAT, voltage_a),
                ("Breaker/VoltagePhaseB", DataType.FLOAT, voltage_b),
                ("Breaker/VoltagePhaseC", DataType.FLOAT, voltage_c),
                ("Breaker/Temperature", DataType.FLOAT, temperature),
                ("Breaker/Status", DataType.STRING, status),
                ("Breaker/TripCount", DataType.INT32, trip_count),
            ]
            
            # Add missing Breaker metrics (from FDI definition)
            breaker_metrics = [
                ("Breaker/PowerFactor", DataType.FLOAT, random.uniform(0.85, 0.95)),  # Power factor
                ("Breaker/ReactivePower", DataType.FLOAT, random.uniform(200.0, 400.0)),  # Reactive power
                ("Breaker/ApparentPower", DataType.FLOAT, random.uniform(1800.0, 2200.0)),  # Apparent power
                ("Breaker/LastTripTime", DataType.STRING, self.last_trip_time),  # Last trip time
                ("Breaker/TripReason", DataType.STRING, self.trip_reason),  # Trip reason
                ("Breaker/TripCurrent", DataType.FLOAT, random.uniform(80.0, 120.0)),  # Trip current
                ("Breaker/TripDelay", DataType.FLOAT, random.uniform(50.0, 150.0)),  # Trip delay
                ("Breaker/GroundFaultCurrent", DataType.FLOAT, random.uniform(0.0, 2.0)),  # Ground fault current
                ("Breaker/ArcFaultDetected", DataType.BOOLEAN, random.choice([True, False])),  # Arc fault detected
                ("Breaker/MaintenanceDue", DataType.BOOLEAN, random.choice([True, False])),  # Maintenance due
                ("Breaker/HarmonicDistortion", DataType.FLOAT, random.uniform(2.0, 8.0)),  # Harmonic distortion
                ("Breaker/Position", DataType.INT32, random.randint(0, 2)),  # Position (0=Disconnected, 1=Connected, 2=Test)
                ("Breaker/AutoRecloseAttempts", DataType.INT32, self.config["control"]["auto_reclose_attempts"]),  # Auto reclose attempts
                ("Breaker/AlarmStatus", DataType.INT32, self.alarm_status),  # Alarm status
                ("Breaker/CommunicationStatus", DataType.INT32, random.randint(0, 3)),  # Communication status (0=Offline, 1=Online, 2=Degraded, 3=Fault)
                ("Breaker/RemoteControlEnabled", DataType.BOOLEAN, self.config["control"]["remote_control_enabled"]),  # Remote control enabled
                ("Breaker/AutoRecloseEnabled", DataType.BOOLEAN, self.config["control"]["auto_reclose_enabled"]),  # Auto reclose enabled
            ]
            
            # Add missing Device metrics
            device_metrics = [
                ("Device/Online", DataType.BOOLEAN, True),  # Device online status
            ]
            
            # Combine all metrics
            metrics_data.extend(breaker_metrics)
            metrics_data.extend(device_metrics)
            
            # Add Protection parameters (from FDI definition with realistic values)
            protection_metrics = [
                ("Protection/OvercurrentPickup", DataType.FLOAT, self.config["protection"]["overcurrent_pickup"]),
                ("Protection/OvercurrentDelay", DataType.FLOAT, self.config["protection"]["overcurrent_delay"]),
                ("Protection/GroundFaultPickup", DataType.FLOAT, self.config["protection"]["ground_fault_pickup"]),
                ("Protection/GroundFaultDelay", DataType.FLOAT, self.config["protection"]["ground_fault_delay"]),
                ("Protection/ArcFaultPickup", DataType.FLOAT, self.config["protection"]["arc_fault_pickup"]),
                ("Protection/ArcFaultDelay", DataType.FLOAT, self.config["protection"]["arc_fault_delay"]),
                ("Protection/ThermalPickup", DataType.FLOAT, self.config["protection"]["thermal_pickup"]),
                ("Protection/ThermalDelay", DataType.FLOAT, self.config["protection"]["thermal_delay"]),
                ("Protection/InstantaneousPickup", DataType.FLOAT, self.config["protection"]["instantaneous_pickup"]),
                ("Protection/AutoRecloseDelay", DataType.FLOAT, self.config["protection"]["auto_reclose_delay"]),
                ("Protection/Enabled", DataType.BOOLEAN, self.config["protection"]["enabled"]),
            ]
            
            # Combine telemetry and protection metrics
            metrics_data.extend(protection_metrics)
            
            for name, datatype, value in metrics_data:
                metric = payload.metrics.add()
                metric.name = name
                metric.datatype = datatype
                metric.timestamp = payload.timestamp
                
                if datatype == DataType.FLOAT:
                    metric.float_value = float(value)
                elif datatype == DataType.STRING:
                    metric.string_value = str(value)
                elif datatype == DataType.INT32:
                    metric.int_value = int(value)
                elif datatype == DataType.BOOLEAN:
                    metric.boolean_value = bool(value)
            
            # Send protobuf telemetry
            topic = f"spBv1.0/IIoT/DDATA/smart-breaker-000"
            self.mqtt_client.publish(topic, payload.SerializeToString())
            print(f"Sent protobuf telemetry: {topic}")
            
        except Exception as e:
            print(f"Error sending telemetry: {e}")

def create_breaker_config() -> BreakerConfig:
    """Create minimal breaker configuration"""
    return BreakerConfig()

def main():
    """Main function - MINIMAL VERSION"""
    print("Starting minimal smart breaker simulator...")
    
    # Create config
    config = create_breaker_config()
    
    # Create simulator
    simulator = SmartBreakerSimulator()
    
    # Wait for connection
    time.sleep(5)
    
    if simulator.mqtt_connected:
        print("Success! MQTT is connected.")
        
        # Send periodic telemetry
        print("Starting telemetry loop...")
        try:
            while True:
                simulator._send_telemetry()
                time.sleep(30)  # Send telemetry every 30 seconds
        except KeyboardInterrupt:
            print("Stopping telemetry...")
    else:
        print("Failed to connect to MQTT")
    
    # Cleanup
    simulator.mqtt_client.loop_stop()
    simulator.mqtt_client.disconnect()
    print("Test completed")

if __name__ == "__main__":
    main() 