#!/usr/bin/env python3
"""
Sparkplug B Host Application
Processes telemetry data from IoT devices using Protocol Buffers
"""

import json
import logging
import os
import ssl
import time
from datetime import datetime
from flask import Flask, jsonify
import paho.mqtt.client as mqtt
import structlog
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

# Import protobuf classes - simplified logic
try:
    from proto.sparkplug_b_pb2 import Payload
    print("✅ Protobuf bindings loaded successfully")
except ImportError:
    try:
        # Fallback: try direct import
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), 'proto'))
        from sparkplug_b_pb2 import Payload
        print("✅ Protobuf bindings loaded via fallback")
    except ImportError:
        print("❌ Protobuf bindings not found. Creating dummy class.")
        # Create a minimal Payload class for basic functionality
        class Payload:
            def __init__(self):
                self.metrics = []
                self.timestamp = 0
                self.seq = 0
            def ParseFromString(self, data):
                return True

# Optional imports (don't fail if missing)
try:
    from proto.sparkplug_b_pb2 import Metric, DataType
except ImportError:
    pass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = structlog.get_logger()

# Prometheus metrics
messages_received = Counter('sparkplug_messages_received_total', 'Total Sparkplug B messages received', ['message_type'])
devices_online = Gauge('sparkplug_devices_online', 'Number of online Sparkplug B devices')
message_processing_time = Histogram('sparkplug_message_processing_seconds', 'Time to process messages')
telemetry_metrics = Gauge('sparkplug_telemetry_value', 'Telemetry metric values', ['device_id', 'metric_name'])

class SparkplugBHost:
    def __init__(self):
        self.devices = {}
        self.metrics_cache = {}
        self.mqtt_client = None
        self.flask_app = Flask(__name__)
        self.group_id = os.getenv("GROUP_ID", "IIoT")
        self.namespace = os.getenv("SPARKPLUG_NAMESPACE", "spBv1.0")
        self.setup_flask_routes()
        self.setup_mqtt_client()

    def setup_mqtt_client(self):
        """Setup MQTT client for Sparkplug B messages"""
        self.mqtt_client = mqtt.Client(client_id="sparkplug-host")
        
        # Authentication
        username = os.getenv("MQTT_USERNAME", "sparkplug-host")
        password = os.getenv("MQTT_PASSWORD", "testpass123")
        self.mqtt_client.username_pw_set(username, password)
        
        # TLS setup
        if os.getenv("MQTT_USE_TLS", "true").lower() == "true":
            context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            self.mqtt_client.tls_set_context(context)
        
        # Callbacks
        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_message = self._on_mqtt_message
        
        # Connect to broker
        broker_host = os.getenv("MQTT_BROKER_HOST", "mosquitto")
        broker_port = int(os.getenv("MQTT_BROKER_PORT", "8883"))
        
        try:
            self.mqtt_client.connect(broker_host, broker_port, 60)
            self.mqtt_client.loop_start()
            logger.info("Connected to MQTT broker", host=broker_host, port=broker_port)
        except Exception as e:
            logger.error("Failed to connect to MQTT broker", error=str(e))

    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        if rc == 0:
            logger.info("MQTT connected")
            # Subscribe to all Sparkplug B topics
            topics = [
                f"{self.namespace}/{self.group_id}/NBIRTH/+",  # Node birth
                f"{self.namespace}/{self.group_id}/NDEATH/+",  # Node death
                f"{self.namespace}/{self.group_id}/DBIRTH/+",  # Device birth
                f"{self.namespace}/{self.group_id}/DDEATH/+",  # Device death
                f"{self.namespace}/{self.group_id}/NDATA/+",   # Node data
                f"{self.namespace}/{self.group_id}/DDATA/+",   # Device data
            ]
            
            for topic in topics:
                client.subscribe(topic)
                logger.info("Subscribed to topic", topic=topic)
        else:
            logger.error("MQTT connection failed", result_code=rc)

    def _on_mqtt_message(self, client, userdata, msg):
        """Handle incoming Sparkplug B messages"""
        try:
            topic_parts = msg.topic.split('/')
            if len(topic_parts) < 4:
                return
                
            namespace = topic_parts[0]
            group_id = topic_parts[1]
            message_type = topic_parts[2]
            device_id = topic_parts[3] if len(topic_parts) > 3 else None
            
            # Process message based on type
            if message_type in ["DBIRTH", "DDEATH", "DDATA"]:
                self._handle_device_message(device_id, message_type, msg.payload)
            elif message_type in ["NBIRTH", "NDEATH", "NDATA"]:
                self._handle_node_message(device_id, message_type, msg.payload)
                
            messages_received.labels(message_type=message_type).inc()
            
        except Exception as e:
            logger.error("Error handling MQTT message", error=str(e), topic=msg.topic)

    def _handle_device_message(self, device_id, message_type, payload):
        """Handle device-specific Sparkplug B messages"""
        try:
            with message_processing_time.time():
                if message_type == "DBIRTH":
                    self._handle_device_birth(device_id, payload)
                elif message_type == "DDEATH":
                    self._handle_device_death(device_id, payload)
                elif message_type == "DDATA":
                    self._handle_device_data(device_id, payload)
                    
        except Exception as e:
            logger.error("Error handling device message", 
                        device_id=device_id, 
                        message_type=message_type, 
                        error=str(e))

    def _handle_device_birth(self, device_id, payload):
        """Handle device birth certificate"""
        try:
            # For this demo, we'll process as JSON if protobuf parsing fails
            device_info = self._parse_sparkplug_payload(payload)
            
            self.devices[device_id] = {
                "device_id": device_id,
                "status": "online",
                "birth_time": datetime.now().isoformat(),
                "last_seen": datetime.now().isoformat(),
                "metrics": device_info.get("metrics", {})
            }
            
            devices_online.set(len([d for d in self.devices.values() if d["status"] == "online"]))
            
            logger.info("Device birth processed", device_id=device_id)
            
        except Exception as e:
            logger.error("Error handling device birth", device_id=device_id, error=str(e))

    def _handle_device_death(self, device_id, payload):
        """Handle device death certificate"""
        try:
            if device_id in self.devices:
                self.devices[device_id]["status"] = "offline"
                self.devices[device_id]["death_time"] = datetime.now().isoformat()
                
                devices_online.set(len([d for d in self.devices.values() if d["status"] == "online"]))
                
                logger.info("Device death processed", device_id=device_id)
                
        except Exception as e:
            logger.error("Error handling device death", device_id=device_id, error=str(e))

    def _handle_device_data(self, device_id, payload):
        """Handle device telemetry data"""
        try:
            # Parse telemetry data
            telemetry_data = self._parse_sparkplug_payload(payload)
            
            if device_id not in self.devices:
                # Auto-register device if not seen before
                self.devices[device_id] = {
                    "device_id": device_id,
                    "status": "online",
                    "birth_time": datetime.now().isoformat(),
                    "last_seen": datetime.now().isoformat(),
                    "metrics": {}
                }
            
            # Update device last seen
            self.devices[device_id]["last_seen"] = datetime.now().isoformat()
            
            # Process metrics
            metrics = telemetry_data.get("metrics", [])
            
            for metric in metrics:
                # Handle both dictionary and list formats
                if isinstance(metric, dict):
                    metric_name = metric.get("name", "unknown")
                    metric_value = metric.get("value", 0)
                    metric_timestamp = metric.get("timestamp", time.time() * 1000)
                    metric_datatype = metric.get("datatype", "unknown")
                elif isinstance(metric, list) and len(metric) >= 2:
                    # Handle list format [name, value, timestamp, datatype]
                    metric_name = str(metric[0]) if len(metric) > 0 else "unknown"
                    metric_value = metric[1] if len(metric) > 1 else 0
                    metric_timestamp = metric[2] if len(metric) > 2 else time.time() * 1000
                    metric_datatype = str(metric[3]) if len(metric) > 3 else "unknown"
                else:
                    logger.warning("Unknown metric format", device_id=device_id, metric_type=type(metric), metric_data=str(metric))
                    continue
                
                # Update device metrics
                self.devices[device_id]["metrics"][metric_name] = {
                    "value": metric_value,
                    "timestamp": metric_timestamp,
                    "datatype": metric_datatype
                }
                
                # Update Prometheus metrics
                if isinstance(metric_value, (int, float)):
                    telemetry_metrics.labels(device_id=device_id, metric_name=metric_name).set(metric_value)
                
                # Cache for quick access
                cache_key = f"{device_id}:{metric_name}"
                self.metrics_cache[cache_key] = metric_value
            
            logger.debug("Device telemetry processed", 
                        device_id=device_id, 
                        metrics_count=len(metrics))
            
        except Exception as e:
            logger.error("Error handling device data", device_id=device_id, error=str(e))

    def _handle_node_message(self, node_id, message_type, payload):
        """Handle node-level Sparkplug B messages"""
        try:
            logger.debug("Node message received", 
                        node_id=node_id, 
                        message_type=message_type)
            
        except Exception as e:
            logger.error("Error handling node message", 
                        node_id=node_id, 
                        message_type=message_type, 
                        error=str(e))

    def _parse_sparkplug_payload(self, payload):
        """Parse Sparkplug B payload using real protobuf parsing"""
        try:
            # Parse the protobuf payload
            sparkplug_payload = Payload()
            sparkplug_payload.ParseFromString(payload)
            
            # Extract metrics from the protobuf message
            metrics = []
            for metric in sparkplug_payload.metrics:
                # Determine the actual value based on datatype
                value = None
                datatype_name = "unknown"
                
                # Map integer datatype to value field and name
                if metric.datatype == 10:  # DOUBLE
                    value = metric.double_value
                    datatype_name = "double"
                elif metric.datatype == 8:  # UINT64
                    value = metric.long_value
                    datatype_name = "uint64"
                elif metric.datatype == 3:  # INT32
                    value = metric.int_value
                    datatype_name = "int32"
                elif metric.datatype == 9:  # FLOAT
                    value = metric.float_value
                    datatype_name = "float"
                elif metric.datatype == 12:  # STRING
                    value = metric.string_value
                    datatype_name = "string"
                elif metric.datatype == 11:  # BOOLEAN
                    value = metric.boolean_value
                    datatype_name = "boolean"
                else:
                    # Default to trying double_value for unknown types
                    value = metric.double_value if hasattr(metric, 'double_value') else 0
                    datatype_name = f"unknown_{metric.datatype}"
                
                metrics.append({
                    "name": metric.name,
                    "value": value,
                    "datatype": datatype_name,
                    "timestamp": metric.timestamp
                })
            
            return {
                "timestamp": sparkplug_payload.timestamp,
                "seq": sparkplug_payload.seq,
                "metrics": metrics
            }
            
        except Exception as e:
            logger.error("Error parsing Sparkplug protobuf payload", error=str(e))
            return {"metrics": []}

    def setup_flask_routes(self):
        """Setup Flask REST API routes"""
        
        @self.flask_app.route('/health')
        def health():
            return jsonify({
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "devices_online": len([d for d in self.devices.values() if d["status"] == "online"]),
                "total_devices": len(self.devices)
            })

        @self.flask_app.route('/api/devices')
        def list_devices():
            return jsonify(list(self.devices.values()))

        @self.flask_app.route('/api/devices/<device_id>')
        def get_device(device_id):
            if device_id in self.devices:
                return jsonify(self.devices[device_id])
            return jsonify({"error": "Device not found"}), 404

        @self.flask_app.route('/api/devices/<device_id>/metrics')
        def get_device_metrics(device_id):
            if device_id in self.devices:
                return jsonify(self.devices[device_id].get("metrics", {}))
            return jsonify({"error": "Device not found"}), 404

        @self.flask_app.route('/api/metrics/latest')
        def get_latest_metrics():
            return jsonify(self.metrics_cache)

        @self.flask_app.route('/metrics')
        def prometheus_metrics():
            return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

        @self.flask_app.route('/')
        def dashboard():
            return jsonify({
                "service": "Sparkplug B Host Application",
                "status": "running",
                "devices_online": len([d for d in self.devices.values() if d["status"] == "online"]),
                "total_devices": len(self.devices),
                "group_id": self.group_id,
                "namespace": self.namespace,
                "endpoints": {
                    "health": "/health",
                    "devices": "/api/devices",
                    "metrics": "/metrics",
                    "latest_metrics": "/api/metrics/latest"
                }
            })

    def run(self):
        """Start the Sparkplug B host application"""
        port = int(os.getenv("METRICS_PORT", "8081"))
        logger.info("Starting Sparkplug B Host Application", port=port)
        self.flask_app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == "__main__":
    host = SparkplugBHost()
    host.run() 