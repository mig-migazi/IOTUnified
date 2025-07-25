#!/usr/bin/env python3
"""
FDI Device Driver for MQTT/LwM2M/Sparkplug B Devices
This driver can be loaded by FDI client applications to configure devices
that use modern IoT protocols instead of traditional fieldbus protocols.

The driver translates FDI commands to MQTT/LwM2M/Sparkplug B communication
so that FDI clients can configure devices like the Smart Breaker.

Usage:
1. Load this driver into an FDI client application
2. Point it to your .fdi device package file
3. The driver will handle communication with your devices
"""

import os
import json
import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import asyncio
import ssl
import structlog

# MQTT for device communication
import paho.mqtt.client as mqtt

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

@dataclass
class FDIDeviceParameter:
    """FDI Device Parameter definition"""
    name: str
    type: str
    units: Optional[str] = None
    range_min: Optional[float] = None
    range_max: Optional[float] = None
    default: Optional[Any] = None
    mandatory: bool = False
    value_map: Dict[str, str] = field(default_factory=dict)

@dataclass
class FDIConfigurationTemplate:
    """FDI Configuration Template definition"""
    name: str
    description: str
    settings: Dict[str, Any] = field(default_factory=dict)

@dataclass
class FDIDevicePackage:
    """FDI Device Package definition"""
    device_type: str
    device_revision: str
    device_manufacturer: str
    device_model: str
    device_serial_number: str
    device_version: str
    device_description: str
    parameters: Dict[str, FDIDeviceParameter] = field(default_factory=dict)
    configuration_templates: Dict[str, FDIConfigurationTemplate] = field(default_factory=dict)
    communication_protocol: str = "MQTT"
    mqtt_broker_host: str = "localhost"
    mqtt_broker_port: int = 1883
    mqtt_username: Optional[str] = None
    mqtt_password: Optional[str] = None
    mqtt_use_tls: bool = False

@dataclass
class FDIDevice:
    """FDI Device instance"""
    device_id: str
    device_package: FDIDevicePackage
    current_configuration: Dict[str, Any] = field(default_factory=dict)
    communication_status: str = "offline"
    last_seen: Optional[datetime] = None
    mqtt_client: Optional[mqtt.Client] = None

class FDIDeviceDriver:
    """
    FDI Device Driver for MQTT/LwM2M/Sparkplug B devices
    
    This driver implements the FDI device driver interface that can be loaded
    by FDI client applications to configure devices using modern IoT protocols.
    """
    
    def __init__(self, fdi_package_path: str, mqtt_broker_host: str = "localhost", 
                 mqtt_broker_port: int = 1883):
        self.logger = logger.bind(component="fdi_device_driver")
        self.fdi_package_path = fdi_package_path
        self.mqtt_broker_host = mqtt_broker_host
        self.mqtt_broker_port = mqtt_broker_port
        self.device_package: Optional[FDIDevicePackage] = None
        self.devices: Dict[str, FDIDevice] = {}
        self.mqtt_client: Optional[mqtt.Client] = None
        
        # Load FDI device package
        self._load_fdi_package()
        
        # Setup MQTT communication
        self._setup_mqtt_client()
    
    def _load_fdi_package(self):
        """Load FDI device package from .fdi file"""
        try:
            tree = ET.parse(self.fdi_package_path)
            root = tree.getroot()
            
            # Define namespace
            namespace = {'fdi': 'http://www.opcfoundation.org/FDI/2011/Device'}
            
            # Extract device identity
            device_identity = root.find("fdi:DeviceIdentity", namespace)
            if device_identity is None:
                # Try without namespace as fallback
                device_identity = root.find("DeviceIdentity")
            
            if device_identity is None:
                raise ValueError("DeviceIdentity element not found in FDI file")
            
            self.device_package = FDIDevicePackage(
                device_type=self._get_text(device_identity, "DeviceType", namespace),
                device_revision=self._get_text(device_identity, "DeviceRevision", namespace),
                device_manufacturer=self._get_text(device_identity, "DeviceManufacturer", namespace),
                device_model=self._get_text(device_identity, "DeviceModel", namespace),
                device_serial_number=self._get_text(device_identity, "DeviceSerialNumber", namespace),
                device_version=self._get_text(device_identity, "DeviceVersion", namespace),
                device_description=self._get_text(device_identity, "DeviceDescription", namespace),
                mqtt_broker_host=self.mqtt_broker_host,
                mqtt_broker_port=self.mqtt_broker_port
            )
            
            # Parse device parameters
            capabilities = root.find("fdi:DeviceCapabilities", namespace)
            if capabilities is None:
                capabilities = root.find("DeviceCapabilities")
            if capabilities is not None:
                self._parse_device_parameters(capabilities, namespace)
            
            # Parse configuration templates
            configuration = root.find("fdi:DeviceConfiguration", namespace)
            if configuration is None:
                configuration = root.find("DeviceConfiguration")
            if configuration is not None:
                self._parse_configuration_templates(configuration, namespace)
            
            self.logger.info("Loaded FDI device package", 
                           device_type=self.device_package.device_type,
                           manufacturer=self.device_package.device_manufacturer,
                           model=self.device_package.device_model)
            
        except Exception as e:
            self.logger.error("Failed to load FDI device package", error=str(e))
            raise
    
    def _get_text(self, element: ET.Element, tag: str, namespace: Dict[str, str] = None) -> str:
        """Get text content of XML element"""
        if namespace:
            child = element.find(f"fdi:{tag}", namespace)
            if child is None:
                child = element.find(tag)  # Fallback without namespace
        else:
            child = element.find(tag)
        return child.text if child is not None else ""
    
    def _parse_device_parameters(self, capabilities: ET.Element, namespace: Dict[str, str] = None):
        """Parse device parameters from FDI file"""
        parameters_elem = capabilities.find("DeviceParameters")
        if parameters_elem is None:
            return
        
        for param_elem in parameters_elem.findall("Parameter"):
            param_name = param_elem.get("name", "")
            param_type = param_elem.get("type", "")
            param_units = param_elem.get("units")
            param_default = param_elem.get("default")
            param_mandatory = param_elem.get("mandatory", "false").lower() == "true"
            
            # Parse range
            range_min = None
            range_max = None
            range_attr = param_elem.get("range")
            if range_attr:
                try:
                    range_parts = range_attr.split("-")
                    if len(range_parts) == 2:
                        range_min = float(range_parts[0])
                        range_max = float(range_parts[1])
                except ValueError:
                    pass
            
            # Parse value map
            value_map = {}
            value_map_elem = param_elem.find("ValueMap")
            if value_map_elem is not None:
                for value_elem in value_map_elem.findall("Value"):
                    value_name = value_elem.get("name", "")
                    value_map[value_name] = value_name
            
            device_parameter = FDIDeviceParameter(
                name=param_name,
                type=param_type,
                units=param_units,
                range_min=range_min,
                range_max=range_max,
                default=param_default,
                mandatory=param_mandatory,
                value_map=value_map
            )
            
            self.device_package.parameters[param_name] = device_parameter
    
    def _parse_configuration_templates(self, configuration: ET.Element, namespace: Dict[str, str] = None):
        """Parse configuration templates from FDI file"""
        templates_elem = configuration.find("ConfigurationTemplates")
        if templates_elem is None:
            return
        
        for template_elem in templates_elem.findall("Template"):
            template_name = template_elem.get("name", "")
            template_description = self._get_text(template_elem, "Description")
            
            template = FDIConfigurationTemplate(
                name=template_name,
                description=template_description
            )
            
            # Parse settings
            settings_elem = template_elem.find("Settings")
            if settings_elem is not None:
                for setting_elem in settings_elem.findall("Setting"):
                    setting_name = setting_elem.get("name", "")
                    setting_value = setting_elem.get("value", "")
                    setting_units = setting_elem.get("units")
                    
                    template.settings[setting_name] = {
                        "value": setting_value,
                        "units": setting_units
                    }
            
            self.device_package.configuration_templates[template_name] = template
    
    def _setup_mqtt_client(self):
        """Setup MQTT client for device communication"""
        try:
            self.mqtt_client = mqtt.Client(client_id=f"fdi-driver-{os.getpid()}")
            
            # Set credentials if provided
            if self.device_package.mqtt_username:
                self.mqtt_client.username_pw_set(
                    self.device_package.mqtt_username,
                    self.device_package.mqtt_password
                )
            
            # Set TLS if required
            if self.device_package.mqtt_use_tls:
                self.mqtt_client.tls_set(cert_reqs=ssl.CERT_NONE)
                self.mqtt_client.tls_insecure_set(True)
            
            # Set callbacks
            self.mqtt_client.on_connect = self._on_mqtt_connect
            self.mqtt_client.on_message = self._on_mqtt_message
            self.mqtt_client.on_disconnect = self._on_mqtt_disconnect
            
            # Connect to broker
            self.mqtt_client.connect(
                self.device_package.mqtt_broker_host,
                self.device_package.mqtt_broker_port,
                60
            )
            
            # Start the loop
            self.mqtt_client.loop_start()
            
            self.logger.info("MQTT client setup completed", 
                           broker=f"{self.device_package.mqtt_broker_host}:{self.device_package.mqtt_broker_port}")
            
        except Exception as e:
            self.logger.error("Failed to setup MQTT client", error=str(e))
            raise
    
    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        if rc == 0:
            self.logger.info("MQTT connected successfully")
            
            # Subscribe to device topics
            topics = [
                "spBv1.0/+/DBIRTH/+",  # Sparkplug B birth certificates
                "lwm2m/+/reg",         # LwM2M registrations
                "lwm2m/+/config",      # Device configuration responses
                "lwm2m/+/status"       # Device status updates
            ]
            
            for topic in topics:
                client.subscribe(topic)
                self.logger.info("Subscribed to topic", topic=topic)
        else:
            self.logger.error("MQTT connection failed", rc=rc)
    
    def _on_mqtt_message(self, client, userdata, msg):
        """MQTT message callback"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            
            self.logger.debug("Received MQTT message", topic=topic, payload=payload)
            
            # Handle different message types
            if "DBIRTH" in topic:
                self._handle_sparkplug_birth(topic, payload)
            elif "lwm2m" in topic and "reg" in topic:
                self._handle_lwm2m_registration(topic, payload)
            elif "lwm2m" in topic and "config" in topic:
                self._handle_configuration_response(topic, payload)
            elif "lwm2m" in topic and "status" in topic:
                self._handle_status_update(topic, payload)
                
        except Exception as e:
            self.logger.error("Error handling MQTT message", error=str(e))
    
    def _on_mqtt_disconnect(self, client, userdata, rc):
        """MQTT disconnection callback"""
        self.logger.warning("MQTT disconnected", rc=rc)
    
    def _handle_sparkplug_birth(self, topic: str, payload: str):
        """Handle Sparkplug B birth certificate"""
        try:
            # Extract device ID from topic
            # Topic format: spBv1.0/{group_id}/DBIRTH/{device_id}
            topic_parts = topic.split("/")
            if len(topic_parts) >= 4:
                device_id = topic_parts[3]
                
                # Parse birth certificate
                birth_data = json.loads(payload)
                
                # Create or update device
                if device_id not in self.devices:
                    device = FDIDevice(
                        device_id=device_id,
                        device_package=self.device_package
                    )
                    self.devices[device_id] = device
                
                device = self.devices[device_id]
                device.communication_status = "online"
                device.last_seen = datetime.now()
                
                self.logger.info("Device discovered via Sparkplug B", device_id=device_id)
                
        except Exception as e:
            self.logger.error("Error handling Sparkplug B birth", error=str(e))
    
    def _handle_lwm2m_registration(self, topic: str, payload: str):
        """Handle LwM2M registration"""
        try:
            # Extract device ID from topic
            # Topic format: lwm2m/{device_id}/reg
            topic_parts = topic.split("/")
            if len(topic_parts) >= 2:
                device_id = topic_parts[1]
                
                # Parse registration data
                reg_data = json.loads(payload)
                
                # Create or update device
                if device_id not in self.devices:
                    device = FDIDevice(
                        device_id=device_id,
                        device_package=self.device_package
                    )
                    self.devices[device_id] = device
                
                device = self.devices[device_id]
                device.communication_status = "online"
                device.last_seen = datetime.now()
                
                self.logger.info("Device registered via LwM2M", device_id=device_id)
                
        except Exception as e:
            self.logger.error("Error handling LwM2M registration", error=str(e))
    
    def _handle_configuration_response(self, topic: str, payload: str):
        """Handle configuration response from device"""
        try:
            # Extract device ID from topic
            topic_parts = topic.split("/")
            if len(topic_parts) >= 2:
                device_id = topic_parts[1]
                
                if device_id in self.devices:
                    device = self.devices[device_id]
                    config_data = json.loads(payload)
                    device.current_configuration = config_data.get("configuration", {})
                    
                    self.logger.info("Received configuration from device", 
                                   device_id=device_id, 
                                   configuration=device.current_configuration)
                
        except Exception as e:
            self.logger.error("Error handling configuration response", error=str(e))
    
    def _handle_status_update(self, topic: str, payload: str):
        """Handle status update from device"""
        try:
            # Extract device ID from topic
            topic_parts = topic.split("/")
            if len(topic_parts) >= 2:
                device_id = topic_parts[1]
                
                if device_id in self.devices:
                    device = self.devices[device_id]
                    status_data = json.loads(payload)
                    
                    device.communication_status = status_data.get("status", "online")
                    device.last_seen = datetime.now()
                    
                    self.logger.info("Received status update from device", 
                                   device_id=device_id, 
                                   status=device.communication_status)
                
        except Exception as e:
            self.logger.error("Error handling status update", error=str(e))
    
    # FDI Device Driver Interface Methods
    
    def discover_devices(self) -> List[str]:
        """Discover devices - FDI interface method"""
        try:
            # Request device discovery
            discovery_topic = "fdi/discovery/request"
            discovery_message = {
                "command": "discover",
                "timestamp": datetime.now().isoformat()
            }
            
            self.mqtt_client.publish(discovery_topic, json.dumps(discovery_message))
            
            # Return currently known devices
            device_ids = list(self.devices.keys())
            self.logger.info("Device discovery completed", device_count=len(device_ids))
            
            return device_ids
            
        except Exception as e:
            self.logger.error("Error discovering devices", error=str(e))
            return []
    
    def get_device_parameters(self, device_id: str) -> Dict[str, Any]:
        """Get device parameters - FDI interface method"""
        try:
            if device_id not in self.devices:
                raise ValueError(f"Device {device_id} not found")
            
            device = self.devices[device_id]
            
            # Request current configuration from device
            config_topic = f"lwm2m/{device_id}/command"
            config_message = {
                "command": "get_configuration",
                "timestamp": datetime.now().isoformat()
            }
            
            self.mqtt_client.publish(config_topic, json.dumps(config_message))
            
            # Return current configuration
            return device.current_configuration
            
        except Exception as e:
            self.logger.error("Error getting device parameters", error=str(e))
            return {}
    
    def set_device_parameters(self, device_id: str, parameters: Dict[str, Any]) -> bool:
        """Set device parameters - FDI interface method"""
        try:
            if device_id not in self.devices:
                raise ValueError(f"Device {device_id} not found")
            
            # Send configuration to device
            config_topic = f"lwm2m/{device_id}/command"
            config_message = {
                "command": "configure",
                "settings": parameters,
                "timestamp": datetime.now().isoformat()
            }
            
            self.mqtt_client.publish(config_topic, json.dumps(config_message))
            
            self.logger.info("Configuration sent to device", 
                           device_id=device_id, 
                           parameters=parameters)
            
            return True
            
        except Exception as e:
            self.logger.error("Error setting device parameters", error=str(e))
            return False
    
    def apply_configuration_template(self, device_id: str, template_name: str) -> bool:
        """Apply configuration template - FDI interface method"""
        try:
            if device_id not in self.devices:
                raise ValueError(f"Device {device_id} not found")
            
            if template_name not in self.device_package.configuration_templates:
                raise ValueError(f"Template {template_name} not found")
            
            template = self.device_package.configuration_templates[template_name]
            
            # Send template configuration to device
            config_topic = f"lwm2m/{device_id}/command"
            config_message = {
                "command": "configure",
                "template": template_name,
                "settings": template.settings,
                "timestamp": datetime.now().isoformat()
            }
            
            self.mqtt_client.publish(config_topic, json.dumps(config_message))
            
            self.logger.info("Template configuration applied", 
                           device_id=device_id, 
                           template=template_name)
            
            return True
            
        except Exception as e:
            self.logger.error("Error applying configuration template", error=str(e))
            return False
    
    def send_command(self, device_id: str, command: str, parameters: Dict[str, Any] = None) -> bool:
        """Send command to device - FDI interface method"""
        try:
            if device_id not in self.devices:
                raise ValueError(f"Device {device_id} not found")
            
            # Send command to device
            command_topic = f"lwm2m/{device_id}/command"
            command_message = {
                "command": command,
                "parameters": parameters or {},
                "timestamp": datetime.now().isoformat()
            }
            
            self.mqtt_client.publish(command_topic, json.dumps(command_message))
            
            self.logger.info("Command sent to device", 
                           device_id=device_id, 
                           command=command, 
                           parameters=parameters)
            
            return True
            
        except Exception as e:
            self.logger.error("Error sending command", error=str(e))
            return False
    
    def get_device_status(self, device_id: str) -> Dict[str, Any]:
        """Get device status - FDI interface method"""
        try:
            if device_id not in self.devices:
                raise ValueError(f"Device {device_id} not found")
            
            device = self.devices[device_id]
            
            status = {
                "device_id": device.device_id,
                "device_type": device.device_package.device_type,
                "manufacturer": device.device_package.device_manufacturer,
                "model": device.device_package.device_model,
                "communication_status": device.communication_status,
                "last_seen": device.last_seen.isoformat() if device.last_seen else None,
                "current_configuration": device.current_configuration
            }
            
            return status
            
        except Exception as e:
            self.logger.error("Error getting device status", error=str(e))
            return {}
    
    def get_available_templates(self) -> List[str]:
        """Get available configuration templates - FDI interface method"""
        return list(self.device_package.configuration_templates.keys())
    
    def get_template_parameters(self, template_name: str) -> Dict[str, Any]:
        """Get template parameters - FDI interface method"""
        try:
            if template_name not in self.device_package.configuration_templates:
                raise ValueError(f"Template {template_name} not found")
            
            template = self.device_package.configuration_templates[template_name]
            return template.settings
            
        except Exception as e:
            self.logger.error("Error getting template parameters", error=str(e))
            return {}
    
    def close(self):
        """Close the FDI device driver"""
        try:
            if self.mqtt_client:
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
            
            self.logger.info("FDI device driver closed")
            
        except Exception as e:
            self.logger.error("Error closing FDI device driver", error=str(e))

# Example usage for FDI client integration
def create_fdi_driver(fdi_package_path: str, mqtt_broker_host: str = "localhost", 
                     mqtt_broker_port: int = 1883) -> FDIDeviceDriver:
    """
    Factory function to create FDI device driver
    
    This function can be called by FDI client applications to create
    a device driver for MQTT/LwM2M/Sparkplug B devices.
    """
    return FDIDeviceDriver(fdi_package_path, mqtt_broker_host, mqtt_broker_port)

# Example of how FDI clients would use this driver
def example_fdi_client_usage():
    """Example of how an FDI client would use this driver"""
    
    # Create FDI device driver
    driver = create_fdi_driver(
        fdi_package_path="device-profiles/smart-breaker.fdi",
        mqtt_broker_host="localhost",
        mqtt_broker_port=1883
    )
    
    try:
        # Discover devices
        devices = driver.discover_devices()
        print(f"Discovered devices: {devices}")
        
        if devices:
            device_id = devices[0]
            
            # Get device status
            status = driver.get_device_status(device_id)
            print(f"Device status: {status}")
            
            # Apply configuration template
            templates = driver.get_available_templates()
            if templates:
                success = driver.apply_configuration_template(device_id, templates[0])
                print(f"Template applied: {success}")
            
            # Send command
            success = driver.send_command(device_id, "trip")
            print(f"Command sent: {success}")
    
    finally:
        # Close driver
        driver.close()

if __name__ == "__main__":
    # Run example
    example_fdi_client_usage() 