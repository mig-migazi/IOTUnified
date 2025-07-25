#!/usr/bin/env python3
"""
Test FDI XML Parsing
Debug the FDI file parsing to see what's happening
"""

import xml.etree.ElementTree as ET

def test_fdi_parsing():
    """Test parsing the FDI file"""
    print("🔍 Testing FDI XML Parsing")
    print("=" * 40)
    
    # Parse the FDI XML file
    tree = ET.parse("device-profiles/eaton-smart-breaker.fdi")
    root = tree.getroot()
    
    # Define namespace
    namespace = {'fdi': 'http://www.opcfoundation.org/FDI/2011/Device'}
    
    print("📋 Looking for Configuration Templates...")
    
    # Try different ways to find configuration templates
    configuration = root.find("fdi:DeviceConfiguration", namespace)
    print(f"   Found DeviceConfiguration with namespace: {configuration is not None}")
    
    if configuration is None:
        configuration = root.find("DeviceConfiguration")
        print(f"   Found DeviceConfiguration without namespace: {configuration is not None}")
    
    if configuration is not None:
        templates_elem = configuration.find("fdi:ConfigurationTemplates", namespace)
        print(f"   Found ConfigurationTemplates with namespace: {templates_elem is not None}")
        
        if templates_elem is None:
            templates_elem = configuration.find("ConfigurationTemplates")
            print(f"   Found ConfigurationTemplates without namespace: {templates_elem is not None}")
        
        if templates_elem is not None:
            templates = templates_elem.findall("Template")
            print(f"   Found {len(templates)} Template elements")
            
            # Also try with namespace
            templates_with_ns = templates_elem.findall("fdi:Template", namespace)
            print(f"   Found {len(templates_with_ns)} Template elements with namespace")
            
            # Try direct findall on root
            all_templates = root.findall(".//Template")
            print(f"   Found {len(all_templates)} Template elements in entire document")
            
            # Try with namespace on root
            all_templates_ns = root.findall(".//fdi:Template", namespace)
            print(f"   Found {len(all_templates_ns)} Template elements with namespace in entire document")
            
            for i, template in enumerate(templates):
                name = template.get("name", "")
                print(f"     Template {i+1}: {name}")
                
                desc = template.find("Description")
                if desc is not None:
                    print(f"       Description: {desc.text}")
                
                settings = template.find("Settings")
                if settings is not None:
                    setting_elems = settings.findall("Setting")
                    print(f"       Settings: {len(setting_elems)}")
                    for setting in setting_elems:
                        setting_name = setting.get("name", "")
                        setting_value = setting.get("value", "")
                        setting_units = setting.get("units", "")
                        print(f"         {setting_name}: {setting_value} {setting_units}")
    
    print("\n📤 Looking for Device Commands...")
    
    capabilities = root.find("fdi:DeviceCapabilities", namespace)
    print(f"   Found DeviceCapabilities with namespace: {capabilities is not None}")
    
    if capabilities is None:
        capabilities = root.find("DeviceCapabilities")
        print(f"   Found DeviceCapabilities without namespace: {capabilities is not None}")
    
    if capabilities is not None:
        commands_elem = capabilities.find("fdi:DeviceCommands", namespace)
        print(f"   Found DeviceCommands with namespace: {commands_elem is not None}")
        
        if commands_elem is None:
            commands_elem = capabilities.find("DeviceCommands")
            print(f"   Found DeviceCommands without namespace: {commands_elem is not None}")
        
        if commands_elem is not None:
            commands = commands_elem.findall("Command")
            print(f"   Found {len(commands)} Command elements")
            
            for i, command in enumerate(commands):
                name = command.get("name", "")
                desc = command.get("description", "")
                print(f"     Command {i+1}: {name} - {desc}")
    
    print("\n🔍 Looking for Device Functions...")
    
    if capabilities is not None:
        functions_elem = capabilities.find("fdi:DeviceFunctions", namespace)
        print(f"   Found DeviceFunctions with namespace: {functions_elem is not None}")
        
        if functions_elem is None:
            functions_elem = capabilities.find("DeviceFunctions")
            print(f"   Found DeviceFunctions without namespace: {functions_elem is not None}")
        
        if functions_elem is not None:
            functions = functions_elem.findall("Function")
            print(f"   Found {len(functions)} Function elements")
            
            for i, function in enumerate(functions):
                name = function.get("name", "")
                desc_elem = function.find("Description")
                desc = desc_elem.text if desc_elem is not None else ""
                print(f"     Function {i+1}: {name} - {desc}")

if __name__ == "__main__":
    test_fdi_parsing() 