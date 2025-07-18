#!/usr/bin/env python3
"""
MQTT to Redpanda Bridge
Simple bridge connecting MQTT IoT telemetry to Redpanda event streaming
"""

import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, Any, Optional
from flask import Flask, jsonify
import paho.mqtt.client as mqtt
from kafka import KafkaProducer
from kafka.errors import KafkaError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MQTTRedpandaBridge:
    def __init__(self):
        self.mqtt_client = None
        self.kafka_producer = None
        self.flask_app = Flask(__name__)
        
        # Configuration
        self.mqtt_broker_host = os.getenv("MQTT_BROKER_HOST", "mosquitto")
        self.mqtt_broker_port = int(os.getenv("MQTT_BROKER_PORT", "1883"))
        self.mqtt_use_tls = os.getenv("MQTT_USE_TLS", "false").lower() == "true"
        self.redpanda_brokers = os.getenv("REDPANDA_BROKERS", "redpanda:29092")
        
        # Topic mappings
        self.topic_mappings = {
            "spBv1.0/IIoT/DBIRTH/+": "iot.telemetry.sparkplug.birth",
            "spBv1.0/IIoT/DDATA/+": "iot.telemetry.sparkplug.data",
            "spBv1.0/IIoT/DDEATH/+": "iot.telemetry.sparkplug.death",
            "lwm2m/+/reg": "iot.telemetry.lwm2m.registration",
            "lwm2m/+/update": "iot.telemetry.lwm2m.update",
        }
        
        # Metrics
        self.messages_bridged = 0
        self.bridge_errors = 0
        
        self.setup_flask_routes()
        self.setup_kafka_producer()
        self.setup_mqtt_client()

    def setup_kafka_producer(self):
        """Setup Kafka producer for Redpanda"""
        try:
            self.kafka_producer = KafkaProducer(
                bootstrap_servers=self.redpanda_brokers.split(','),
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',
                retries=3
            )
            logger.info(f"Kafka producer connected to {self.redpanda_brokers}")
        except Exception as e:
            logger.error(f"Failed to create Kafka producer: {e}")
            raise

    def setup_mqtt_client(self):
        """Setup MQTT client"""
        self.mqtt_client = mqtt.Client(client_id="mqtt-redpanda-bridge")
        
        # Callbacks
        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_message = self._on_mqtt_message
        self.mqtt_client.on_disconnect = self._on_mqtt_disconnect
        
        # Connect to broker
        try:
            self.mqtt_client.connect(self.mqtt_broker_host, self.mqtt_broker_port, 60)
            self.mqtt_client.loop_start()
            logger.info(f"Connected to MQTT broker {self.mqtt_broker_host}:{self.mqtt_broker_port}")
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            raise

    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        if rc == 0:
            logger.info("MQTT connected successfully")
            
            # Subscribe to all mapped topics
            for mqtt_topic in self.topic_mappings.keys():
                client.subscribe(mqtt_topic)
                logger.info(f"Subscribed to MQTT topic: {mqtt_topic}")
        else:
            logger.error(f"MQTT connection failed with code: {rc}")
            self.bridge_errors += 1

    def _on_mqtt_disconnect(self, client, userdata, rc):
        """MQTT disconnection callback"""
        logger.warning(f"MQTT disconnected with code: {rc}")
        if rc != 0:
            self.bridge_errors += 1

    def _on_mqtt_message(self, client, userdata, msg):
        """Handle incoming MQTT messages"""
        try:
            # Find matching Redpanda topic
            redpanda_topic = self._map_mqtt_to_redpanda_topic(msg.topic)
            if not redpanda_topic:
                logger.debug(f"No mapping found for MQTT topic: {msg.topic}")
                return
            
            # Parse message
            message_data = self._parse_mqtt_message(msg.topic, msg.payload)
            if not message_data:
                self.bridge_errors += 1
                return
            
            # Extract device ID for key
            device_id = self._extract_device_id(msg.topic, message_data)
            
            # Send to Redpanda
            future = self.kafka_producer.send(
                topic=redpanda_topic,
                key=device_id,
                value=message_data
            )
            
            # Wait for send confirmation
            try:
                record_metadata = future.get(timeout=10)
                self.messages_bridged += 1
                
                logger.debug(f"Message bridged: {msg.topic} -> {redpanda_topic} (device: {device_id})")
                
            except KafkaError as e:
                logger.error(f"Failed to send message to Redpanda: {e}")
                self.bridge_errors += 1
                
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")
            self.bridge_errors += 1

    def _map_mqtt_to_redpanda_topic(self, mqtt_topic: str) -> Optional[str]:
        """Map MQTT topic to Redpanda topic"""
        for mqtt_pattern, redpanda_topic in self.topic_mappings.items():
            if self._topic_matches_pattern(mqtt_topic, mqtt_pattern):
                return redpanda_topic
        return None

    def _topic_matches_pattern(self, topic: str, pattern: str) -> bool:
        """Check if MQTT topic matches pattern with wildcards"""
        topic_parts = topic.split('/')
        pattern_parts = pattern.split('/')
        
        if len(topic_parts) != len(pattern_parts):
            return False
        
        for topic_part, pattern_part in zip(topic_parts, pattern_parts):
            if pattern_part != '+' and topic_part != pattern_part:
                return False
        
        return True

    def _parse_mqtt_message(self, topic: str, payload: bytes) -> Optional[Dict[str, Any]]:
        """Parse MQTT message payload"""
        try:
            # Try JSON first
            if payload.startswith(b'{'):
                data = json.loads(payload.decode('utf-8'))
            else:
                # Handle binary payload (Sparkplug B)
                data = {"raw_payload": payload.hex()}
            
            # Add metadata
            message = {
                "device_id": self._extract_device_id(topic, data),
                "topic": topic,
                "timestamp": datetime.now().isoformat(),
                "payload_size": len(payload),
                "data": data
            }
            
            return message
            
        except Exception as e:
            logger.error(f"Failed to parse MQTT message: {e}")
            return None

    def _extract_device_id(self, topic: str, message_data: Dict[str, Any]) -> str:
        """Extract device ID from topic or message data"""
        # Try to get from message data first
        if isinstance(message_data, dict) and "device_id" in message_data:
            return message_data["device_id"]
        
        # Extract from topic
        topic_parts = topic.split('/')
        if 'spBv1.0' in topic and len(topic_parts) > 3:
            return topic_parts[3]
        elif 'lwm2m' in topic and len(topic_parts) > 1:
            return topic_parts[1]
        
        return "unknown"

    def setup_flask_routes(self):
        """Setup Flask routes for monitoring"""
        @self.flask_app.route('/health')
        def health():
            return jsonify({
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "mqtt_connected": self.mqtt_client.is_connected() if self.mqtt_client else False,
                "kafka_connected": self.kafka_producer is not None,
                "messages_bridged": self.messages_bridged,
                "bridge_errors": self.bridge_errors
            })
        
        @self.flask_app.route('/metrics')
        def metrics():
            return f"""# HELP mqtt_redpanda_messages_bridged_total Total messages bridged to Redpanda
# TYPE mqtt_redpanda_messages_bridged_total counter
mqtt_redpanda_messages_bridged_total {self.messages_bridged}

# HELP mqtt_redpanda_bridge_errors_total Total bridge errors
# TYPE mqtt_redpanda_bridge_errors_total counter
mqtt_redpanda_bridge_errors_total {self.bridge_errors}

# HELP mqtt_redpanda_mqtt_connected MQTT connection status
# TYPE mqtt_redpanda_mqtt_connected gauge
mqtt_redpanda_mqtt_connected {1 if self.mqtt_client and self.mqtt_client.is_connected() else 0}

# HELP mqtt_redpanda_kafka_connected Kafka connection status
# TYPE mqtt_redpanda_kafka_connected gauge
mqtt_redpanda_kafka_connected {1 if self.kafka_producer else 0}
""", 200, {'Content-Type': 'text/plain'}
        
        @self.flask_app.route('/topics')
        def topics():
            return jsonify({
                "topic_mappings": self.topic_mappings
            })

    def run(self):
        """Run the bridge"""
        port = int(os.getenv("BRIDGE_PORT", "8083"))
        self.flask_app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == "__main__":
    bridge = MQTTRedpandaBridge()
    bridge.run() 