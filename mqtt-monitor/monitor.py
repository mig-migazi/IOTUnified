#!/usr/bin/env python3
"""
MQTT Monitor - Real-time message inspection
"""

import json
import logging
import os
import ssl
from collections import deque
from datetime import datetime
from flask import Flask, jsonify, render_template_string
import paho.mqtt.client as mqtt
import structlog
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = structlog.get_logger()

# Metrics
messages_monitored = Counter('mqtt_messages_monitored_total', 'Total MQTT messages monitored', ['topic_type'])

class MQTTMonitor:
    def __init__(self):
        self.messages = deque(maxlen=1000)  # Keep last 1000 messages
        self.mqtt_client = None
        self.flask_app = Flask(__name__)
        self.setup_flask_routes()
        self.setup_mqtt_client()

    def setup_mqtt_client(self):
        """Setup MQTT client for monitoring"""
        self.mqtt_client = mqtt.Client(client_id="mqtt-monitor")
        
        # Authentication
        username = os.getenv("MQTT_USERNAME", "admin")
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
            # Subscribe to all topics
            client.subscribe("#")
        else:
            logger.error("MQTT connection failed", result_code=rc)

    def _on_mqtt_message(self, client, userdata, msg):
        """Handle incoming MQTT messages"""
        try:
            # Skip system messages for cleaner view
            if msg.topic.startswith("$SYS/"):
                return
                
            payload_str = msg.payload.decode('utf-8', errors='ignore')
            
            message_info = {
                "timestamp": datetime.now().isoformat(),
                "topic": msg.topic,
                "payload": payload_str[:500],  # Truncate long payloads
                "payload_size": len(msg.payload),
                "qos": msg.qos,
                "retain": msg.retain
            }
            
            # Categorize message type
            if "lwm2m" in msg.topic:
                message_info["type"] = "LwM2M"
                messages_monitored.labels(topic_type="lwm2m").inc()
            elif "spBv1.0" in msg.topic:
                message_info["type"] = "Sparkplug B"
                messages_monitored.labels(topic_type="sparkplug").inc()
            else:
                message_info["type"] = "Other"
                messages_monitored.labels(topic_type="other").inc()
            
            self.messages.appendleft(message_info)
            
            logger.debug("Message monitored", topic=msg.topic, type=message_info["type"])
            
        except Exception as e:
            logger.error("Error handling MQTT message", error=str(e))

    def setup_flask_routes(self):
        """Setup Flask routes"""
        
        @self.flask_app.route('/health')
        def health():
            return jsonify({
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "messages_monitored": len(self.messages)
            })

        @self.flask_app.route('/api/messages')
        def get_messages():
            return jsonify(list(self.messages))

        @self.flask_app.route('/api/messages/lwm2m')
        def get_lwm2m_messages():
            lwm2m_messages = [msg for msg in self.messages if msg.get("type") == "LwM2M"]
            return jsonify(lwm2m_messages)

        @self.flask_app.route('/api/messages/sparkplug')
        def get_sparkplug_messages():
            sparkplug_messages = [msg for msg in self.messages if msg.get("type") == "Sparkplug B"]
            return jsonify(sparkplug_messages)

        @self.flask_app.route('/metrics')
        def metrics():
            return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

        @self.flask_app.route('/')
        def dashboard():
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>MQTT Monitor Dashboard</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; }
                    .message { border: 1px solid #ccc; margin: 5px 0; padding: 10px; border-radius: 3px; }
                    .lwm2m { border-left: 4px solid blue; }
                    .sparkplug { border-left: 4px solid green; }
                    .other { border-left: 4px solid gray; }
                    .stats { background: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
                    .topic { font-weight: bold; color: #333; }
                    .timestamp { color: #666; font-size: 0.9em; }
                    .payload { background: #f9f9f9; padding: 5px; margin-top: 5px; font-family: monospace; }
                    h1 { color: #333; }
                </style>
                <script>
                    function refreshMessages() {
                        fetch('/api/messages')
                            .then(response => response.json())
                            .then(data => {
                                const container = document.getElementById('messages');
                                container.innerHTML = '';
                                data.slice(0, 50).forEach(msg => {
                                    const div = document.createElement('div');
                                    div.className = 'message ' + msg.type.toLowerCase().replace(' ', '');
                                    div.innerHTML = `
                                        <div class="topic">${msg.topic}</div>
                                        <div class="timestamp">${msg.timestamp} | Type: ${msg.type} | Size: ${msg.payload_size} bytes</div>
                                        <div class="payload">${msg.payload}</div>
                                    `;
                                    container.appendChild(div);
                                });
                            });
                    }
                    setInterval(refreshMessages, 2000);
                    window.onload = refreshMessages;
                </script>
            </head>
            <body>
                <h1>MQTT Monitor Dashboard</h1>
                <div class="stats">
                    <h3>Real-time MQTT Message Monitor</h3>
                    <p>Monitoring all MQTT traffic for LwM2M and Sparkplug B protocols</p>
                    <p>Messages are updated every 2 seconds</p>
                </div>
                <h2>Recent Messages (Last 50)</h2>
                <div id="messages"></div>
            </body>
            </html>
            """
            return html

    def run(self):
        """Start the MQTT monitor"""
        port = int(os.getenv("WEB_PORT", "8082"))
        logger.info("Starting MQTT Monitor", port=port)
        self.flask_app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == "__main__":
    monitor = MQTTMonitor()
    monitor.run() 