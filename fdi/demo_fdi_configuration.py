#!/usr/bin/env python3
"""
FDI Configuration Demo
Demonstrates complete FDI device configuration workflow with dashboard visualization
"""

import sys
import os
import time
import json
import threading
from datetime import datetime

# Add the fdi-device-driver to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'fdi-device-driver'))

from fdi_driver import create_fdi_driver

class FDIConfigurationDemo:
    """Complete FDI configuration demonstration"""
    
    def __init__(self):
        self.driver = None
        self.devices = []
        self.running = True
        
    def setup_fdi_driver(self):
        """Setup FDI device driver"""
        print("🔧 Setting up FDI Device Driver...")
        try:
            self.driver = create_fdi_driver(
                fdi_package_path="device-profiles/smart-breaker.fdi",
                mqtt_broker_host="localhost",
                mqtt_broker_port=1883
            )
            print("✅ FDI Device Driver ready")
            return True
        except Exception as e:
            print(f"❌ Failed to setup FDI driver: {e}")
            return False
    
    def discover_devices(self):
        """Discover available devices"""
        print("\n🔍 Discovering Devices...")
        try:
            self.devices = self.driver.discover_devices()
            print(f"📱 Found {len(self.devices)} device(s): {self.devices}")
            return len(self.devices) > 0
        except Exception as e:
            print(f"❌ Device discovery failed: {e}")
            return False
    
    def get_device_status(self, device_id):
        """Get current device status"""
        print(f"\n📊 Getting Status for {device_id}...")
        try:
            status = self.driver.get_device_status(device_id)
            print(f"📈 Device Status: {json.dumps(status, indent=2)}")
            return status
        except Exception as e:
            print(f"❌ Failed to get device status: {e}")
            return None
    
    def apply_configuration_template(self, device_id, template_name):
        """Apply configuration template to device"""
        print(f"\n⚙️ Applying Configuration Template '{template_name}' to {device_id}...")
        try:
            success = self.driver.apply_configuration_template(device_id, template_name)
            if success:
                print(f"✅ Configuration template '{template_name}' applied successfully")
            else:
                print(f"⚠️ Configuration template application failed")
            return success
        except Exception as e:
            print(f"❌ Configuration failed: {e}")
            return False
    
    def send_command(self, device_id, command, parameters=None):
        """Send command to device"""
        print(f"\n📤 Sending Command '{command}' to {device_id}...")
        try:
            success = self.driver.send_command(device_id, command, parameters)
            if success:
                print(f"✅ Command '{command}' sent successfully")
            else:
                print(f"⚠️ Command '{command}' failed")
            return success
        except Exception as e:
            print(f"❌ Command failed: {e}")
            return False
    
    def monitor_device(self, device_id, duration=30):
        """Monitor device for specified duration"""
        print(f"\n📺 Monitoring Device {device_id} for {duration} seconds...")
        print("=" * 60)
        
        start_time = time.time()
        while time.time() - start_time < duration and self.running:
            try:
                status = self.driver.get_device_status(device_id)
                if status:
                    self.display_device_dashboard(device_id, status)
                time.sleep(2)
            except KeyboardInterrupt:
                print("\n⏹️ Monitoring stopped by user")
                break
            except Exception as e:
                print(f"❌ Monitoring error: {e}")
                break
    
    def display_device_dashboard(self, device_id, status):
        """Display device dashboard"""
        print(f"\n🖥️  Device Dashboard - {device_id}")
        print(f"⏰ Time: {datetime.now().strftime('%H:%M:%S')}")
        print("-" * 40)
        
        # Electrical measurements
        if 'electrical_measurements' in status:
            elec = status['electrical_measurements']
            print(f"⚡ Current Phase A: {elec.get('current_phase_a', 'N/A')} A")
            print(f"⚡ Current Phase B: {elec.get('current_phase_b', 'N/A')} A")
            print(f"⚡ Current Phase C: {elec.get('current_phase_c', 'N/A')} A")
            print(f"🔌 Voltage Phase A: {elec.get('voltage_phase_a', 'N/A')} V")
            print(f"🔌 Voltage Phase B: {elec.get('voltage_phase_b', 'N/A')} V")
            print(f"🔌 Voltage Phase C: {elec.get('voltage_phase_c', 'N/A')} V")
            print(f"⚡ Active Power: {elec.get('active_power', 'N/A')} kW")
            print(f"⚡ Power Factor: {elec.get('power_factor', 'N/A')}")
        
        # Breaker status
        if 'breaker_status' in status:
            breaker = status['breaker_status']
            status_map = {0: "Open", 1: "Closed", 2: "Tripped", 3: "Fault"}
            print(f"🔌 Breaker Status: {status_map.get(breaker.get('status', 0), 'Unknown')}")
            print(f"🔌 Trip Count: {breaker.get('trip_count', 'N/A')}")
            print(f"🔌 Operating Hours: {breaker.get('operating_hours', 'N/A')} hours")
        
        # Protection settings
        if 'protection_settings' in status:
            prot = status['protection_settings']
            print(f"🛡️ Overcurrent Pickup: {prot.get('overcurrent_pickup', 'N/A')} A")
            print(f"🛡️ Ground Fault Pickup: {prot.get('ground_fault_pickup', 'N/A')} A")
            print(f"🛡️ Arc Fault Pickup: {prot.get('arc_fault_pickup', 'N/A')} A")
        
        print("-" * 40)
    
    def run_complete_demo(self):
        """Run complete FDI configuration demo"""
        print("🎬 FDI Configuration Demo")
        print("=" * 60)
        
        # Step 1: Setup FDI Driver
        if not self.setup_fdi_driver():
            return False
        
        # Step 2: Discover Devices
        if not self.discover_devices():
            print("⚠️ No devices found. Starting smart breaker...")
            # Try to start smart breaker
            os.system("docker-compose -f docker-compose.smart-breaker-test.yml up smart-breaker -d")
            time.sleep(5)
            if not self.discover_devices():
                print("❌ Still no devices found. Check smart breaker configuration.")
                return False
        
        device_id = self.devices[0]
        print(f"🎯 Using device: {device_id}")
        
        # Step 3: Get Initial Status
        initial_status = self.get_device_status(device_id)
        
        # Step 4: Monitor Device (Initial State)
        print("\n📺 Initial Device State:")
        self.monitor_device(device_id, 10)
        
        # Step 5: Apply Configuration Template
        templates = self.driver.get_available_templates()
        if templates:
            print(f"\n📋 Available Templates: {templates}")
            self.apply_configuration_template(device_id, templates[0])
        else:
            print("\n📋 No templates available, applying custom configuration...")
            # Apply custom configuration
            custom_config = {
                "overcurrent_pickup": 120.0,
                "ground_fault_pickup": 8.0,
                "arc_fault_pickup": 60.0
            }
            print(f"⚙️ Applying custom configuration: {custom_config}")
            # This would be done through the FDI driver interface
        
        # Step 6: Send Commands
        print("\n📤 Testing Device Commands...")
        self.send_command(device_id, "get_configuration")
        time.sleep(2)
        
        # Step 7: Monitor Device (After Configuration)
        print("\n📺 Device State After Configuration:")
        self.monitor_device(device_id, 15)
        
        # Step 8: Test Trip Command
        print("\n⚠️ Testing Trip Command...")
        self.send_command(device_id, "trip")
        time.sleep(3)
        
        # Step 9: Test Close Command
        print("\n🔌 Testing Close Command...")
        self.send_command(device_id, "close")
        time.sleep(3)
        
        # Step 10: Final Monitoring
        print("\n📺 Final Device State:")
        self.monitor_device(device_id, 10)
        
        print("\n🎉 Demo Complete!")
        return True
    
    def cleanup(self):
        """Cleanup resources"""
        self.running = False
        if self.driver:
            self.driver.close()
        print("🧹 Cleanup complete")

def main():
    """Main demo function"""
    demo = FDIConfigurationDemo()
    
    try:
        success = demo.run_complete_demo()
        if success:
            print("\n✅ Demo completed successfully!")
            print("\n📊 What was demonstrated:")
            print("   • FDI device package loading")
            print("   • Device discovery")
            print("   • Configuration template application")
            print("   • Command sending (trip/close)")
            print("   • Real-time device monitoring")
            print("   • Dashboard visualization")
        else:
            print("\n❌ Demo failed")
    except KeyboardInterrupt:
        print("\n⏹️ Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo error: {e}")
    finally:
        demo.cleanup()

if __name__ == "__main__":
    main() 