#!/usr/bin/env python3
"""
Simple FDI Client Demo
Demonstrates how a real FDI client would load .fdi files and configure devices
"""

import sys
import os
import time
import json
import xml.etree.ElementTree as ET
from datetime import datetime

# Add the fdi-device-driver to the path for MQTT communication
sys.path.append(os.path.join(os.path.dirname(__file__), 'fdi-device-driver'))
from fdi_driver import create_fdi_driver

class SimpleFDIClient:
    """Simple FDI Client that demonstrates the standard FDI workflow"""
    
    def __init__(self):
        self.fdi_file_path = "device-profiles/eaton-smart-breaker.fdi"
        self.device_driver = None
        self.device_info = None
        self.configuration_templates = []
        self.device_commands = []
        
    def load_fdi_file(self):
        """Load and parse the FDI file - this is what real FDI clients do"""
        print("📁 Loading FDI File...")
        print(f"   File: {self.fdi_file_path}")
        
        try:
            # Parse the FDI XML file
            tree = ET.parse(self.fdi_file_path)
            root = tree.getroot()
            
            # Define namespace
            namespace = {'fdi': 'http://www.opcfoundation.org/FDI/2011/Device'}
            
            # Extract device identity
            device_identity = root.find("fdi:DeviceIdentity", namespace)
            if device_identity is None:
                device_identity = root.find("DeviceIdentity")
            
            if device_identity is None:
                raise ValueError("DeviceIdentity not found in FDI file")
            
            # Extract device information
            self.device_info = {
                'type': self._get_text(device_identity, "DeviceType", namespace),
                'manufacturer': self._get_text(device_identity, "DeviceManufacturer", namespace),
                'model': self._get_text(device_identity, "DeviceModel", namespace),
                'serial_number': self._get_text(device_identity, "DeviceSerialNumber", namespace),
                'version': self._get_text(device_identity, "DeviceVersion", namespace),
                'description': self._get_text(device_identity, "DeviceDescription", namespace)
            }
            
            print("✅ Device Information:")
            for key, value in self.device_info.items():
                print(f"   {key.replace('_', ' ').title()}: {value}")
            
            # Extract configuration templates
            self._load_configuration_templates(root, namespace)
            
            # Extract device commands
            self._load_device_commands(root, namespace)
            
            print("✅ FDI file loaded successfully")
            return True
            
        except Exception as e:
            print(f"❌ Failed to load FDI file: {e}")
            return False
    
    def _get_text(self, element, tag, namespace=None):
        """Get text content of XML element"""
        if namespace:
            child = element.find(f"fdi:{tag}", namespace)
            if child is None:
                child = element.find(tag)
        else:
            child = element.find(tag)
        return child.text if child is not None else ""
    
    def _load_configuration_templates(self, root, namespace):
        """Load configuration templates from FDI file"""
        print("\n📋 Loading Configuration Templates...")
        
        configuration = root.find("fdi:DeviceConfiguration", namespace)
        if configuration is None:
            configuration = root.find("DeviceConfiguration")
        
        if configuration is not None:
            templates_elem = configuration.find("fdi:ConfigurationTemplates", namespace)
            if templates_elem is None:
                templates_elem = configuration.find("ConfigurationTemplates")
            
            if templates_elem is not None:
                for template_elem in templates_elem.findall("fdi:Template", namespace):
                    template_name = template_elem.get("name", "")
                    
                    # Get description from Description element
                    desc_elem = template_elem.find("fdi:Description", namespace)
                    if desc_elem is None:
                        desc_elem = template_elem.find("Description")
                    template_description = desc_elem.text if desc_elem is not None else ""
                    
                    # Extract settings
                    parameters = {}
                    settings_elem = template_elem.find("fdi:Settings", namespace)
                    if settings_elem is None:
                        settings_elem = template_elem.find("Settings")
                    if settings_elem is not None:
                        for setting_elem in settings_elem.findall("fdi:Setting", namespace):
                            param_name = setting_elem.get("name", "")
                            param_value = setting_elem.get("value", "")
                            param_unit = setting_elem.get("units", "")
                            parameters[param_name] = {
                                'value': param_value,
                                'unit': param_unit
                            }
                    
                    self.configuration_templates.append({
                        'name': template_name,
                        'description': template_description,
                        'parameters': parameters
                    })
        
        print(f"✅ Found {len(self.configuration_templates)} configuration templates:")
        for template in self.configuration_templates:
            print(f"   • {template['name']}: {template['description']}")
    
    def _load_device_commands(self, root, namespace):
        """Load device commands from FDI file"""
        print("\n📤 Loading Device Commands...")
        
        capabilities = root.find("fdi:DeviceCapabilities", namespace)
        if capabilities is None:
            capabilities = root.find("DeviceCapabilities")
        
        if capabilities is not None:
            functions_elem = capabilities.find("fdi:DeviceFunctions", namespace)
            if functions_elem is None:
                functions_elem = capabilities.find("DeviceFunctions")
            
            if functions_elem is not None:
                for func_elem in functions_elem.findall("fdi:Function", namespace):
                    function_name = func_elem.get("name", "")
                    
                    # Get description from Description element
                    desc_elem = func_elem.find("fdi:Description", namespace)
                    if desc_elem is None:
                        desc_elem = func_elem.find("Description")
                    function_description = desc_elem.text if desc_elem is not None else ""
                    
                    # Extract parameters
                    parameters = []
                    params_elem = func_elem.find("fdi:Parameters", namespace)
                    if params_elem is None:
                        params_elem = func_elem.find("Parameters")
                    if params_elem is not None:
                        for param_elem in params_elem.findall("fdi:Parameter", namespace):
                            param_name = param_elem.get("name", "")
                            param_type = param_elem.get("type", "")
                            param_default = param_elem.get("default", "")
                            param_units = param_elem.get("units", "")
                            parameters.append({
                                'name': param_name,
                                'type': param_type,
                                'default': param_default,
                                'units': param_units
                            })
                    
                    self.device_commands.append({
                        'name': function_name,
                        'description': function_description,
                        'parameters': parameters
                    })
        
        print(f"✅ Found {len(self.device_commands)} device functions:")
        for command in self.device_commands:
            print(f"   • {command['name']}: {command['description']}")
        
        # Also load device commands
        commands_elem = capabilities.find("fdi:DeviceCommands", namespace)
        if commands_elem is None:
            commands_elem = capabilities.find("DeviceCommands")
        
        if commands_elem is not None:
            for cmd_elem in commands_elem.findall("fdi:Command", namespace):
                command_name = cmd_elem.get("name", "")
                command_description = cmd_elem.get("description", "")
                
                # Extract parameters
                parameters = []
                params_elem = cmd_elem.find("fdi:Parameters", namespace)
                if params_elem is None:
                    params_elem = cmd_elem.find("Parameters")
                if params_elem is not None:
                    for param_elem in params_elem.findall("fdi:Parameter", namespace):
                        param_name = param_elem.get("name", "")
                        param_type = param_elem.get("type", "")
                        param_required = param_elem.get("required", "false").lower() == "true"
                        param_default = param_elem.get("default", "")
                        parameters.append({
                            'name': param_name,
                            'type': param_type,
                            'required': param_required,
                            'default': param_default
                        })
                
                self.device_commands.append({
                    'name': command_name,
                    'description': command_description,
                    'parameters': parameters
                })
        
        print(f"✅ Found {len(self.device_commands)} total commands/functions:")
        for command in self.device_commands:
            print(f"   • {command['name']}: {command['description']}")
    
    def discover_devices(self):
        """Discover devices that match this FDI description"""
        print("\n🔍 Discovering Devices...")
        
        try:
            # Create device driver for communication
            self.device_driver = create_fdi_driver(
                fdi_package_path=self.fdi_file_path,
                mqtt_broker_host="localhost",
                mqtt_broker_port=1883
            )
            
            # Discover devices
            devices = self.device_driver.discover_devices()
            
            if devices:
                print(f"✅ Found {len(devices)} device(s):")
                for device_id in devices:
                    print(f"   • {device_id}")
                return devices
            else:
                print("⚠️ No devices found")
                return []
                
        except Exception as e:
            print(f"❌ Device discovery failed: {e}")
            return []
    
    def configure_device(self, device_id, template_name):
        """Configure device using FDI template"""
        print(f"\n⚙️ Configuring Device {device_id}")
        print(f"   Template: {template_name}")
        
        # Find the template
        template = None
        for t in self.configuration_templates:
            if t['name'] == template_name:
                template = t
                break
        
        if not template:
            print(f"❌ Template '{template_name}' not found")
            return False
        
        print(f"   Description: {template['description']}")
        print("   Parameters:")
        for param_name, param_info in template['parameters'].items():
            print(f"     • {param_name}: {param_info['value']} {param_info['unit']}")
        
        try:
            # Apply configuration using the FDI driver
            success = self.device_driver.apply_configuration_template(device_id, template_name)
            
            if success:
                print("✅ Configuration applied successfully")
                return True
            else:
                print("⚠️ Configuration application failed")
                return False
                
        except Exception as e:
            print(f"❌ Configuration failed: {e}")
            return False
    
    def send_command(self, device_id, command_name, parameters=None):
        """Send command to device using FDI definition"""
        print(f"\n📤 Sending Command to {device_id}")
        print(f"   Command: {command_name}")
        
        # Find the command
        command = None
        for cmd in self.device_commands:
            if cmd['name'] == command_name:
                command = cmd
                break
        
        if not command:
            print(f"❌ Command '{command_name}' not found in FDI file")
            return False
        
        print(f"   Description: {command['description']}")
        if parameters:
            print(f"   Parameters: {parameters}")
        
        try:
            # Send command using the FDI driver
            success = self.device_driver.send_command(device_id, command_name, parameters)
            
            if success:
                print("✅ Command sent successfully")
                return True
            else:
                print("⚠️ Command failed")
                return False
                
        except Exception as e:
            print(f"❌ Command failed: {e}")
            return False
    
    def get_device_status(self, device_id):
        """Get device status"""
        print(f"\n📊 Getting Status for {device_id}...")
        
        try:
            status = self.device_driver.get_device_status(device_id)
            if status:
                print("✅ Device Status Retrieved:")
                print(json.dumps(status, indent=2))
                return status
            else:
                print("⚠️ No status received")
                return None
                
        except Exception as e:
            print(f"❌ Failed to get device status: {e}")
            return None
    
    def run_demo(self):
        """Run the complete FDI client demo"""
        print("🎬 FDI Client Demo - Standard FDI Workflow")
        print("=" * 60)
        print("This demonstrates how a real FDI client would work:")
        print("1. Load .fdi file")
        print("2. Discover devices")
        print("3. Configure devices using templates")
        print("4. Send commands")
        print("=" * 60)
        
        # Step 1: Load FDI file
        if not self.load_fdi_file():
            return False
        
        # Step 2: Discover devices
        devices = self.discover_devices()
        if not devices:
            print("\n⚠️ No devices found. Starting smart breaker...")
            os.system("docker-compose -f docker-compose.smart-breaker-test.yml up smart-breaker -d")
            time.sleep(5)
            devices = self.discover_devices()
            if not devices:
                print("❌ Still no devices found")
                return False
        
        device_id = devices[0]
        print(f"\n🎯 Using device: {device_id}")
        
        # Step 3: Get initial status
        initial_status = self.get_device_status(device_id)
        
        # Step 4: Apply configuration template
        if self.configuration_templates:
            template_name = self.configuration_templates[0]['name']
            self.configure_device(device_id, template_name)
        
        # Step 5: Send commands
        if self.device_commands:
            # Try to send a get_configuration command
            for command in self.device_commands:
                if 'config' in command['name'].lower():
                    self.send_command(device_id, command['name'])
                    break
        
        # Step 6: Get final status
        final_status = self.get_device_status(device_id)
        
        print("\n🎉 FDI Client Demo Complete!")
        print("\n📋 What was demonstrated:")
        print("   • Loading .fdi file and parsing device information")
        print("   • Discovering devices automatically")
        print("   • Applying configuration templates from FDI file")
        print("   • Sending commands defined in FDI file")
        print("   • Getting device status")
        
        return True
    
    def cleanup(self):
        """Cleanup resources"""
        if self.device_driver:
            self.device_driver.close()

def main():
    """Main demo function"""
    client = SimpleFDIClient()
    
    try:
        success = client.run_demo()
        if success:
            print("\n✅ FDI Client Demo completed successfully!")
        else:
            print("\n❌ FDI Client Demo failed")
    except KeyboardInterrupt:
        print("\n⏹️ Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo error: {e}")
    finally:
        client.cleanup()

if __name__ == "__main__":
    main() 