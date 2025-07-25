#!/usr/bin/env python3
"""
Test FDI Device Driver
Simple test script to verify the FDI device driver works with the smart breaker
"""

import sys
import os
import time

# Add the fdi-device-driver to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'fdi-device-driver'))

from fdi_driver import create_fdi_driver

def test_fdi_driver():
    """Test the FDI device driver"""
    print("🧪 Testing FDI Device Driver")
    print("=" * 50)
    
    try:
        # Create FDI device driver
        print("📦 Creating FDI device driver...")
        driver = create_fdi_driver(
            fdi_package_path="device-profiles/smart-breaker.fdi",
            mqtt_broker_host="localhost",
            mqtt_broker_port=1883
        )
        
        print("✅ FDI device driver created successfully")
        
        # Wait a moment for MQTT connection
        print("⏳ Waiting for MQTT connection...")
        time.sleep(2)
        
        # Test device discovery
        print("🔍 Testing device discovery...")
        devices = driver.discover_devices()
        print(f"📱 Discovered devices: {devices}")
        
        if devices:
            device_id = devices[0]
            print(f"🎯 Using device: {device_id}")
            
            # Test getting device status
            print("📊 Testing device status...")
            status = driver.get_device_status(device_id)
            print(f"📈 Device status: {status}")
            
            # Test getting available templates
            print("📋 Testing template discovery...")
            templates = driver.get_available_templates()
            print(f"📄 Available templates: {templates}")
            
            if templates:
                template_name = templates[0]
                print(f"🎯 Using template: {template_name}")
                
                # Test applying configuration template
                print(f"⚙️ Testing template application: {template_name}")
                success = driver.apply_configuration_template(device_id, template_name)
                print(f"✅ Template application: {'Success' if success else 'Failed'}")
                
                # Test getting template parameters
                print("📝 Testing template parameters...")
                params = driver.get_template_parameters(template_name)
                print(f"📋 Template parameters: {params}")
            
            # Test sending commands
            print("📤 Testing command sending...")
            commands = ["trip", "close", "reset"]
            for command in commands:
                success = driver.send_command(device_id, command)
                print(f"📤 {command} command: {'Success' if success else 'Failed'}")
                time.sleep(1)  # Wait between commands
            
            # Test getting device parameters
            print("📊 Testing parameter retrieval...")
            params = driver.get_device_parameters(device_id)
            print(f"📋 Device parameters: {params}")
            
        else:
            print("⚠️ No devices discovered. Make sure the smart breaker is running.")
            print("💡 Start the smart breaker with: docker-compose up smart-breaker -d")
        
        # Close the driver
        print("🔌 Closing FDI device driver...")
        driver.close()
        print("✅ FDI device driver closed successfully")
        
        print("\n🎉 FDI Device Driver Test Completed!")
        
    except Exception as e:
        print(f"❌ Error testing FDI device driver: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = test_fdi_driver()
    sys.exit(0 if success else 1) 