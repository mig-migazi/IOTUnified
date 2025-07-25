#!/usr/bin/env python3
"""
Simple MQTT Test
Test MQTT connection with the same settings as the smart breaker
"""

import paho.mqtt.client as mqtt
import time
import os

def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    if rc == 0:
        print("✅ MQTT connection successful!")
        # Subscribe to a test topic
        client.subscribe("test/topic")
        # Publish a test message
        client.publish("test/topic", "Hello from test client")
    else:
        print(f"❌ MQTT connection failed with code {rc}")

def on_message(client, userdata, msg):
    print(f"Received message: {msg.topic} {msg.payload.decode()}")

def on_disconnect(client, userdata, rc):
    print(f"Disconnected with result code {rc}")

def test_mqtt_connection():
    """Test MQTT connection with smart breaker settings"""
    print("🔌 Testing MQTT Connection")
    print("=" * 40)
    
    # Use the same settings as the smart breaker
    mqtt_broker_host = os.getenv("MQTT_BROKER_HOST", "lwm2m-mosquitto")
    mqtt_broker_port = int(os.getenv("MQTT_BROKER_PORT", "1883"))
    mqtt_username = os.getenv("MQTT_USERNAME", "")
    mqtt_password = os.getenv("MQTT_PASSWORD", "")
    mqtt_use_tls = os.getenv("MQTT_USE_TLS", "false").lower() in ("true", "1", "yes")
    
    print(f"   Broker: {mqtt_broker_host}:{mqtt_broker_port}")
    print(f"   TLS: {mqtt_use_tls}")
    print(f"   Username: '{mqtt_username}'")
    print(f"   Password: '{mqtt_password}'")
    
    # Create MQTT client
    client = mqtt.Client()
    
    # Set callbacks
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    
    # Set authentication (only if username is provided)
    if mqtt_username and mqtt_username.strip():
        print(f"   Setting authentication: {mqtt_username}")
        client.username_pw_set(mqtt_username, mqtt_password)
    else:
        print("   No authentication (anonymous)")
    
    # Set TLS (only if enabled)
    if mqtt_use_tls:
        print("   Setting up TLS...")
        import ssl
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        client.tls_set_context(context)
    
    try:
        print(f"   Connecting to {mqtt_broker_host}:{mqtt_broker_port}...")
        client.connect(mqtt_broker_host, mqtt_broker_port, 60)
        client.loop_start()
        
        # Wait for connection
        time.sleep(3)
        
        # Check if connected
        if client.is_connected():
            print("✅ MQTT connection test successful!")
            return True
        else:
            print("❌ MQTT connection test failed!")
            return False
            
    except Exception as e:
        print(f"❌ MQTT connection error: {e}")
        return False
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    success = test_mqtt_connection()
    exit(0 if success else 1) 