#!/usr/bin/env python3
"""
LwM2M Server Implementation with MQTT Transport and WebSocket Interface
Handles device registration, management, and firmware updates
"""

import json
import logging
import os
import ssl
import time
from datetime import datetime
from flask import Flask, jsonify, request, render_template_string
import paho.mqtt.client as mqtt
import structlog
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from functools import wraps

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = structlog.get_logger()

def track_http_request(endpoint_name):
    """Decorator to track HTTP request metrics"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = time.time()
            try:
                result = f(*args, **kwargs)
                duration = time.time() - start_time
                http_requests.labels(endpoint=endpoint_name, method=request.method).inc()
                http_request_duration.labels(endpoint=endpoint_name).observe(duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                http_requests.labels(endpoint=endpoint_name, method=request.method).inc()
                http_request_duration.labels(endpoint=endpoint_name).observe(duration)
                raise
        return decorated_function
    return decorator

# Prometheus metrics
device_registrations = Counter('lwm2m_device_registrations_total', 'Total device registrations')
device_updates = Counter('lwm2m_device_updates_total', 'Total device updates')
active_devices = Gauge('lwm2m_active_devices', 'Number of active devices')
command_latency = Histogram('lwm2m_command_latency_seconds', 'Command response latency')
websocket_events = Counter('lwm2m_websocket_events_total', 'Total WebSocket events sent')
http_requests = Counter('lwm2m_http_requests_total', 'Total HTTP requests', ['endpoint', 'method'])
http_request_duration = Histogram('lwm2m_http_request_duration_seconds', 'HTTP request duration', ['endpoint'])
events_endpoint_calls = Counter('lwm2m_events_endpoint_calls_total', 'Total calls to events endpoint')
events_data_size = Histogram('lwm2m_events_data_size_bytes', 'Size of events data returned', ['endpoint'])

class LwM2MServer:
    def __init__(self):
        self.devices = {}
        self.mqtt_client = None
        self.flask_app = Flask(__name__)
        # Store recent events for Redpanda Connect
        self.recent_events = []
        self.max_events = 1000  # Keep last 1000 events
        self.setup_flask_routes()
        self.setup_mqtt_client()



    def emit_device_event(self, event_type, data):
        """Store device event for Redpanda Connect"""
        try:
            event_data = {
                'event_type': event_type,
                'timestamp': datetime.now().isoformat(),
                'data': data
            }
            
            # Store event for Redpanda Connect
            self.recent_events.append(event_data)
            if len(self.recent_events) > self.max_events:
                self.recent_events.pop(0)  # Remove oldest event
            
            websocket_events.inc()
            logger.debug("Stored device event", event_type=event_type, device_id=data.get('device_id'))
        except Exception as e:
            logger.error("Error storing device event", error=str(e))

    def setup_mqtt_client(self):
        """Setup MQTT client for LwM2M transport"""
        self.mqtt_client = mqtt.Client(client_id="lwm2m-server")
        
        # Authentication
        username = os.getenv("MQTT_USERNAME", "lwm2m-server")
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
            # Subscribe to LwM2M topics
            client.subscribe("lwm2m/+/reg")      # Device registration
            client.subscribe("lwm2m/+/update")   # Device updates
            client.subscribe("lwm2m/+/resp/+")   # Command responses
            client.subscribe("lwm2m/+/dereg")    # Device deregistration
        else:
            logger.error("MQTT connection failed", result_code=rc)

    def _on_mqtt_message(self, client, userdata, msg):
        """Handle incoming MQTT messages"""
        try:
            topic_parts = msg.topic.split('/')
            if len(topic_parts) < 3:
                return
                
            device_id = topic_parts[1]
            message_type = topic_parts[2]
            
            payload = msg.payload.decode('utf-8')
            
            if message_type == "reg":
                self._handle_device_registration(device_id, payload)
            elif message_type == "update":
                self._handle_device_update(device_id, payload)
            elif message_type == "resp":
                if len(topic_parts) > 3:
                    command_type = topic_parts[3]
                    self._handle_command_response(device_id, command_type, payload)
            elif message_type == "dereg":
                self._handle_device_deregistration(device_id)
                
        except Exception as e:
            logger.error("Error handling MQTT message", error=str(e), topic=msg.topic)

    def _handle_device_registration(self, device_id, payload):
        """Handle device registration"""
        try:
            reg_data = json.loads(payload)
            
            device_info = {
                "device_id": device_id,
                "endpoint": reg_data.get("endpoint", device_id),
                "lifetime": reg_data.get("lifetime", 86400),
                "binding_mode": reg_data.get("bindingMode", "UQ"),
                "lwm2m_version": reg_data.get("version", "1.2"),
                "objects": reg_data.get("objects", {}),
                "registered_at": datetime.now().isoformat(),
                "last_update": datetime.now().isoformat(),
                "status": "registered"
            }
            
            self.devices[device_id] = device_info
            device_registrations.inc()
            active_devices.set(len(self.devices))
            
            logger.info("Device registered", device_id=device_id, endpoint=device_info["endpoint"])
            
            # Emit WebSocket event
            self.emit_device_event('device_registered', device_info)
            
            # Send registration response
            response = {
                "status": "registered",
                "location": f"/rd/{device_id}",
                "lifetime": device_info["lifetime"]
            }
            
            response_topic = f"lwm2m/{device_id}/resp/reg"
            self.mqtt_client.publish(response_topic, json.dumps(response))
            
        except Exception as e:
            logger.error("Error handling device registration", device_id=device_id, error=str(e))

    def _handle_device_update(self, device_id, payload):
        """Handle device update"""
        try:
            if device_id not in self.devices:
                logger.warning("Update from unregistered device", device_id=device_id)
                return
                
            update_data = json.loads(payload)
            device = self.devices[device_id]
            
            # Update device information
            if "objects" in update_data:
                device["objects"].update(update_data["objects"])
            
            device["last_update"] = datetime.now().isoformat()
            device["status"] = "active"
            
            device_updates.inc()
            
            logger.debug("Device updated", device_id=device_id)
            
            # Emit WebSocket event
            self.emit_device_event('device_updated', device)
            
            # Send update response
            response = {
                "status": "updated",
                "timestamp": device["last_update"]
            }
            
            response_topic = f"lwm2m/{device_id}/resp/update"
            self.mqtt_client.publish(response_topic, json.dumps(response))
            
        except Exception as e:
            logger.error("Error handling device update", device_id=device_id, error=str(e))

    def _handle_command_response(self, device_id, command_type, payload):
        """Handle command responses from devices"""
        try:
            response_data = json.loads(payload)
            logger.info("Command response received", 
                       device_id=device_id, 
                       command_type=command_type,
                       response=response_data)
            
            # Update device last seen
            if device_id in self.devices:
                self.devices[device_id]["last_update"] = datetime.now().isoformat()
                
            # Emit WebSocket event
            event_data = {
                "device_id": device_id,
                "command_type": command_type,
                "response": response_data
            }
            self.emit_device_event('command_response', event_data)
                
        except Exception as e:
            logger.error("Error handling command response", 
                        device_id=device_id, 
                        command_type=command_type, 
                        error=str(e))

    def _handle_device_deregistration(self, device_id):
        """Handle device deregistration"""
        if device_id in self.devices:
            device_info = self.devices[device_id]
            del self.devices[device_id]
            active_devices.set(len(self.devices))
            logger.info("Device deregistered", device_id=device_id)
            
            # Emit WebSocket event
            self.emit_device_event('device_deregistered', {"device_id": device_id, "device_info": device_info})

    def setup_flask_routes(self):
        """Setup Flask REST API routes"""
        
        @self.flask_app.route('/api/routes')
        def list_routes():
            routes = []
            for rule in self.flask_app.url_map.iter_rules():
                routes.append({
                    "endpoint": rule.endpoint,
                    "methods": list(rule.methods),
                    "rule": rule.rule
                })
            return jsonify(routes)

        @self.flask_app.route('/api/health')
        def health():
            return jsonify({
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "active_devices": len(self.devices),
                "events": self.recent_events
            })

        @self.flask_app.route('/api/devices')
        def list_devices():
            return jsonify(list(self.devices.values()))

        @self.flask_app.route('/api/devices/<device_id>')
        def get_device(device_id):
            if device_id in self.devices:
                return jsonify(self.devices[device_id])
            return jsonify({"error": "Device not found"}), 404

        @self.flask_app.route('/api/devices/<device_id>/read', methods=['POST'])
        def read_resource(device_id):
            if device_id not in self.devices:
                return jsonify({"error": "Device not found"}), 404
                
            data = request.get_json()
            command = {
                "objectId": data.get("objectId"),
                "instanceId": data.get("instanceId", 0),
                "resourceId": data.get("resourceId"),
                "timestamp": int(time.time() * 1000)
            }
            
            command_topic = f"lwm2m/{device_id}/cmd/read"
            self.mqtt_client.publish(command_topic, json.dumps(command))
            
            return jsonify({"status": "command_sent", "command": command})

        @self.flask_app.route('/api/devices/<device_id>/write', methods=['POST'])
        def write_resource(device_id):
            if device_id not in self.devices:
                return jsonify({"error": "Device not found"}), 404
                
            data = request.get_json()
            command = {
                "objectId": data.get("objectId"),
                "instanceId": data.get("instanceId", 0),
                "resourceId": data.get("resourceId"),
                "value": data.get("value"),
                "timestamp": int(time.time() * 1000)
            }
            
            command_topic = f"lwm2m/{device_id}/cmd/write"
            self.mqtt_client.publish(command_topic, json.dumps(command))
            
            return jsonify({"status": "command_sent", "command": command})

        @self.flask_app.route('/api/events')
        @track_http_request('events')
        def events():
            """REST endpoint for Redpanda Connect to consume events"""
            # Track events endpoint usage
            events_endpoint_calls.inc()
            
            # Return recent events in a format suitable for Redpanda Connect
            response_data = self.recent_events
            
            # Track data size
            data_size = len(json.dumps(response_data).encode('utf-8'))
            events_data_size.labels(endpoint='events').observe(data_size)
            
            logger.info("Events endpoint called", 
                       events_count=len(response_data), 
                       data_size_bytes=data_size,
                       client_ip=request.remote_addr)
            
            return jsonify(response_data)

        @self.flask_app.route('/api/devices/<device_id>/execute', methods=['POST'])
        def execute_resource(device_id):
            if device_id not in self.devices:
                return jsonify({"error": "Device not found"}), 404
                
            data = request.get_json()
            command = {
                "objectId": data.get("objectId"),
                "instanceId": data.get("instanceId", 0),
                "resourceId": data.get("resourceId"),
                "arguments": data.get("arguments", ""),
                "timestamp": int(time.time() * 1000)
            }
            
            command_topic = f"lwm2m/{device_id}/cmd/execute"
            self.mqtt_client.publish(command_topic, json.dumps(command))
            
            return jsonify({"status": "command_sent", "command": command})

        @self.flask_app.route('/metrics')
        def metrics():
            return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

        @self.flask_app.route('/api/simple')
        def simple():
            return jsonify({"message": "simple route works"})



        @self.flask_app.route('/')
        def dashboard():
            dashboard_html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>LwM2M Server Dashboard</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; }
                    .device { border: 1px solid #ccc; margin: 10px 0; padding: 15px; border-radius: 5px; }
                    .online { border-left: 5px solid green; }
                    .offline { border-left: 5px solid red; }
                    h1 { color: #333; }
                    .stats { background: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
                </style>
            </head>
            <body>
                <h1>LwM2M Server Dashboard</h1>
                <div class="stats">
                    <h3>Server Statistics</h3>
                    <p>Active Devices: <strong>{{ device_count }}</strong></p>
                    <p>Server Status: <strong>Running</strong></p>
                    <p>MQTT Transport: <strong>Enabled</strong></p>
                </div>
                <h2>Registered Devices</h2>
                {% for device in devices %}
                <div class="device online">
                    <h3>{{ device.device_id }}</h3>
                    <p><strong>Endpoint:</strong> {{ device.endpoint }}</p>
                    <p><strong>Version:</strong> {{ device.lwm2m_version }}</p>
                    <p><strong>Binding:</strong> {{ device.binding_mode }}</p>
                    <p><strong>Last Update:</strong> {{ device.last_update }}</p>
                    <p><strong>Objects:</strong> {{ device.objects.keys()|list|join(', ') }}</p>
                </div>
                {% endfor %}
                <script>
                    setTimeout(function(){ location.reload(); }, 30000);
                </script>
            </body>
            </html>
            """
            return render_template_string(dashboard_html, 
                                        devices=list(self.devices.values()),
                                        device_count=len(self.devices))

    def run(self):
        """Start the LwM2M server"""
        port = int(os.getenv("SERVER_PORT", "8080"))
        logger.info("Starting LwM2M Server", port=port)
        self.flask_app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == "__main__":
    server = LwM2MServer()
    server.run() 