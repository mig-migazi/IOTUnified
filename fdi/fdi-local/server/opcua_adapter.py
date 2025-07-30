#!/usr/bin/env python3
"""
OPC UA Adapter for FDI Communication Server
Implements DeviceProtocolAdapter pattern for OPC UA protocol
"""

import asyncio
import json
import logging
from typing import Dict, Any, List
from dataclasses import dataclass
from abc import ABC, abstractmethod

from asyncua import Server, ua

logger = logging.getLogger(__name__)

@dataclass
class Device:
    """Generic device representation"""
    device_id: str
    device_type: str
    protocol: str = "opcua"
    status: str = "offline"
    last_seen: float = 0
    metrics: Dict[str, Any] = None
    capabilities: Dict[str, Any] = None

class DeviceProtocolAdapter(ABC):
    """Abstract base class for device protocol adapters"""
    
    @abstractmethod
    async def start(self):
        """Start the adapter"""
        pass
    
    @abstractmethod
    async def stop(self):
        """Stop the adapter"""
        pass
    
    @abstractmethod
    async def discover_devices(self) -> List[Device]:
        """Discover devices via this protocol"""
        pass
    
    @abstractmethod
    async def get_device_data(self, device_id: str) -> Dict[str, Any]:
        """Get device data"""
        pass
    
    @abstractmethod
    async def send_device_command(self, device_id: str, command: str, parameters: Dict[str, Any]):
        """Send command to device"""
        pass

class OPCUAAdapter(DeviceProtocolAdapter):
    """OPC UA Adapter implementing DeviceProtocolAdapter pattern"""
    
    def __init__(self, 
                 opcua_host: str = "0.0.0.0", 
                 opcua_port: int = 4840,
                 fdi_server=None):
        """
        Initialize OPC UA Adapter
        
        Args:
            opcua_host: OPC UA server host
            opcua_port: OPC UA server port
            fdi_server: Reference to FDI Communication Server for method calls
        """
        self.opcua_host = opcua_host
        self.opcua_port = opcua_port
        self.fdi_server = fdi_server
        self.opcua_server = None
        self.idx = None
        self.devices_folder = None
        
        # Store discovered devices
        self.devices: Dict[str, Device] = {}
        
        logger.info("OPCUAAdapter initialized", host=opcua_host, port=opcua_port)
    
    async def start(self):
        """Start the OPC UA server"""
        print("=== STARTING OPC UA SERVER (Adapter) ===")
        try:
            # Create OPC UA server
            print("Creating OPC UA server...")
            self.opcua_server = Server()
            print("Initializing OPC UA server...")
            await self.opcua_server.init()
            print("OPC UA server initialized")
            
            # Set endpoint
            print("Setting endpoint...")
            self.opcua_server.set_endpoint(f"opc.tcp://{self.opcua_host}:{self.opcua_port}")
            print("Setting server name...")
            self.opcua_server.set_server_name("FDI_Communication_Server")
            
            # Create namespace
            print("Creating namespace...")
            uri = "http://fdi.communication.server"
            self.idx = await self.opcua_server.register_namespace(uri)
            print(f"Namespace registered with index: {self.idx}")
            
            # Get root node
            root = self.opcua_server.nodes.objects
            
            # Create simple address space
            print("Creating FDI object...")
            fdi_obj = await root.add_object(self.idx, "FDI")
            print(f"FDI object created: {fdi_obj}")
            
            # Create Devices folder
            self.devices_folder = await fdi_obj.add_object(self.idx, "Devices")
            print(f"Devices folder created: {self.devices_folder}")
            
            # Create Methods folder
            methods_folder = await fdi_obj.add_object(self.idx, "Methods")
            print(f"Methods folder created: {methods_folder}")
            
            # Create methods directly on the FDI object
            discover_method = await fdi_obj.add_method(
                self.idx, "DiscoverDevices",
                self._discover_devices_method,
                [],  # input arguments
                [ua.VariantType.String]  # output arguments
            )
            print(f"DiscoverDevices method created: {discover_method}")
            
            # Create GetDeviceParameters method
            get_params_method = await fdi_obj.add_method(
                self.idx, "GetDeviceParameters",
                self._get_device_parameters_method,
                [ua.VariantType.String],  # input arguments (device_id)
                [ua.VariantType.String]  # output arguments
            )
            print(f"GetDeviceParameters method created: {get_params_method}")
            
            # Create SetDeviceParameters method
            set_params_method = await fdi_obj.add_method(
                self.idx, "SetDeviceParameters",
                self._set_device_parameters_method,
                [ua.VariantType.String, ua.VariantType.String],  # input arguments (device_id, parameters)
                [ua.VariantType.String]  # output arguments
            )
            print(f"SetDeviceParameters method created: {set_params_method}")
            
            # Create SendDeviceCommand method
            send_command_method = await fdi_obj.add_method(
                self.idx, "SendDeviceCommand",
                self._send_device_command_method,
                [ua.VariantType.String, ua.VariantType.String, ua.VariantType.String],  # input arguments (device_id, command, parameters)
                [ua.VariantType.String]  # output arguments
            )
            print(f"SendDeviceCommand method created: {send_command_method}")
            
            # Create ParseFDIWritableParameters method
            parse_writable_method = await fdi_obj.add_method(
                self.idx, "ParseFDIWritableParameters",
                self._parse_fdi_writable_parameters_method,
                [ua.VariantType.String],  # input arguments (device_type)
                [ua.VariantType.String]  # output arguments
            )
            print(f"ParseFDIWritableParameters method created: {parse_writable_method}")

            # Create GetDeviceConfiguration method
            print("DEBUG: About to register GetDeviceConfiguration method...")
            
            # Create a bound method to ensure it's called on the correct instance
            async def bound_get_device_configuration_method(parent, device_id):
                return await self._get_device_configuration_method(parent, device_id)
            
            get_config_method = await fdi_obj.add_method(
                self.idx, "GetDeviceConfiguration",
                bound_get_device_configuration_method,
                [ua.VariantType.String],  # input arguments (device_id)
                [ua.VariantType.String]  # output arguments
            )
            print(f"DEBUG: GetDeviceConfiguration method created: {get_config_method}")
            
            print("OPC UA server initialized successfully")
            logger.info("OPC UA server initialized successfully")
            
            # Start the OPC UA server
            print("Starting OPC UA server...")
            await self.opcua_server.start()
            print(f"OPC UA server started at opc.tcp://{self.opcua_host}:{self.opcua_port}")
            logger.info(f"OPC UA server started at opc.tcp://{self.opcua_host}:{self.opcua_port}")
            
        except Exception as e:
            logger.error("Error starting OPC UA server", error=str(e))
            raise
    
    async def stop(self):
        """Stop the OPC UA server"""
        if self.opcua_server:
            await self.opcua_server.stop()
            logger.info("OPC UA server stopped")
    
    async def discover_devices(self) -> List[Device]:
        """Discover devices via OPC UA - OPC UA adapter doesn't discover devices directly"""
        # OPC UA adapter doesn't discover devices - it only provides OPC UA interface
        # Devices are discovered by other adapters (MQTT, etc.) and exposed via OPC UA
        return []
    
    async def get_device_data(self, device_id: str) -> Dict[str, Any]:
        """Get device data via OPC UA - delegates to FDI server"""
        if self.fdi_server:
            return await self.fdi_server.get_device_data(device_id)
        return {}
    
    async def send_device_command(self, device_id: str, command: str, parameters: Dict[str, Any]):
        """Send command to device via OPC UA - delegates to FDI server"""
        if self.fdi_server:
            return await self.fdi_server.send_device_command(device_id, command, parameters)
    
    # OPC UA Method Handlers (delegate to FDI server)
    
    async def _discover_devices_method(self, parent):
        """OPC UA method handler for device discovery"""
        try:
            # Get devices from FDI server's device storage
            if self.fdi_server:
                # Get devices from all adapters except OPC UA
                all_devices = []
                for protocol, adapter in self.fdi_server.adapters.items():
                    if protocol != "opcua":  # Don't include OPC UA adapter to avoid recursion
                        try:
                            devices = await adapter.discover_devices()
                            all_devices.extend(devices)
                        except Exception as e:
                            logger.error("Error discovering devices from adapter", protocol=protocol, error=str(e))
                
                result = json.dumps([{
                    "device_id": device.device_id,
                    "device_type": device.device_type,
                    "protocol": device.protocol,
                    "status": device.status,
                    "last_seen": device.last_seen
                } for device in all_devices])
                
                logger.info("Devices discovered via OPC UA", device_count=len(all_devices))
                return [ua.Variant(result, ua.VariantType.String)]
            else:
                return [ua.Variant(json.dumps([]), ua.VariantType.String)]
            
        except Exception as e:
            logger.error("Error in discover devices method", error=str(e))
            return [ua.Variant(json.dumps([]), ua.VariantType.String)]
    
    async def _get_device_parameters_method(self, parent, device_id):
        """OPC UA method handler for getting device parameters"""
        try:
            # Extract string value if device_id is a Variant
            if hasattr(device_id, 'Value'):
                device_id = device_id.Value
                print(f"DEBUG: Extracted device_id from Variant: {device_id}")
            
            device_data = await self.get_device_data(device_id)
            
            if device_data:
                logger.info("Retrieved device parameters", device_id=device_id)
                return [ua.Variant(json.dumps(device_data), ua.VariantType.String)]
            else:
                logger.warning("No device data found", device_id=device_id)
                return [ua.Variant(json.dumps({"device_id": device_id, "metrics": {}, "capabilities": {}}), ua.VariantType.String)]
                
        except Exception as e:
            logger.error("Error in get device parameters method", device_id=device_id, error=str(e))
            return [ua.Variant(json.dumps({"error": str(e)}), ua.VariantType.String)]
    
    async def _get_device_configuration_method(self, parent, device_id):
        """OPC UA method handler for getting device configuration"""
        try:
            # Extract string value if device_id is a Variant
            if hasattr(device_id, 'Value'):
                device_id = device_id.Value
                print(f"DEBUG: Extracted device_id from Variant: {device_id}")
            
            # Get current configuration from FDI server
            if self.fdi_server and device_id in self.fdi_server.devices:
                device = self.fdi_server.devices[device_id]
                config_data = {
                    "device_id": device_id,
                    "metrics": device.metrics or {},
                    "capabilities": device.capabilities or {}
                }
                logger.info("Retrieved device configuration", device_id=device_id)
                return [ua.Variant(json.dumps(config_data), ua.VariantType.String)]
            else:
                logger.warning("Device not found for configuration", device_id=device_id)
                return [ua.Variant(json.dumps({"device_id": device_id, "metrics": {}, "capabilities": {}}), ua.VariantType.String)]
                
        except Exception as e:
            logger.error("Error in get device configuration method", device_id=device_id, error=str(e))
            return [ua.Variant(json.dumps({"error": str(e)}), ua.VariantType.String)]
    
    async def _set_device_parameters_method(self, parent, device_id, parameters_json):
        """OPC UA method handler for setting device parameters"""
        try:
            # Extract string value if device_id is a Variant
            if hasattr(device_id, 'Value'):
                device_id = device_id.Value
                print(f"DEBUG: Extracted device_id from Variant: {device_id}")
            
            parameters = json.loads(parameters_json)
            
            # Delegate to FDI server for parameter validation and setting
            if self.fdi_server:
                # Get writable parameters from FDI definition
                writable_params = self.fdi_server.parse_fdi_writable_parameters("SmartCircuitBreaker")
                
                # Validate parameters against FDI definition
                validated_params = {}
                for param_name, param_value in parameters.items():
                    # Check if parameter is writable (in functions or commands)
                    is_writable = False
                    param_info = None
                    
                    # Check in functions
                    for func_name, func_data in writable_params.get('functions', {}).items():
                        if param_name in func_data.get('parameters', {}):
                            is_writable = True
                            param_info = func_data['parameters'][param_name]
                            break
                    
                    # Check in commands
                    for cmd_name, cmd_data in writable_params.get('commands', {}).items():
                        if param_name in cmd_data.get('parameters', {}):
                            is_writable = True
                            param_info = cmd_data['parameters'][param_name]
                            break
                    
                    if is_writable:
                        validated_params[param_name] = param_value
                        logger.info("Parameter validated as writable", device_id=device_id, param_name=param_name, param_value=param_value)
                    else:
                        logger.warning("Parameter not writable according to FDI definition", device_id=device_id, param_name=param_name)
                
                if validated_params:
                    # Send configuration command to device
                    await self.fdi_server.send_device_command(device_id, "set_configuration", validated_params)
                    logger.info("Configuration sent to device", device_id=device_id, parameters=validated_params)
                    return [ua.Variant(json.dumps({"status": "success", "message": "Configuration applied"}), ua.VariantType.String)]
                else:
                    logger.warning("No valid writable parameters found", device_id=device_id, parameters=parameters)
                    return [ua.Variant(json.dumps({"status": "error", "message": "No valid writable parameters"}), ua.VariantType.String)]
            else:
                return [ua.Variant(json.dumps({"status": "error", "message": "FDI server not available"}), ua.VariantType.String)]
                
        except Exception as e:
            logger.error("Error in set device parameters method", device_id=device_id, error=str(e))
            return [ua.Variant(json.dumps({"status": "error", "message": str(e)}), ua.VariantType.String)]
    
    async def _send_device_command_method(self, parent, device_id, command, parameters_json):
        """OPC UA method handler for sending device commands"""
        try:
            parameters = json.loads(parameters_json)
            
            await self.send_device_command(device_id, command, parameters)
            
            return [ua.Variant(json.dumps({"status": "success"}), ua.VariantType.String)]
        except Exception as e:
            logger.error("Error in send device command method", device_id=device_id, error=str(e))
            return [ua.Variant(json.dumps({"status": "error", "message": str(e)}), ua.VariantType.String)]
    
    async def _parse_fdi_writable_parameters_method(self, parent, device_type):
        """OPC UA method handler for parsing FDI writable parameters"""
        try:
            # Extract string value if device_type is a Variant
            if hasattr(device_type, 'Value'):
                device_type = device_type.Value
                print(f"DEBUG: Extracted device_type from Variant: {device_type}")
            
            # Parse writable parameters from FDI definition
            if self.fdi_server:
                writable_params = self.fdi_server.parse_fdi_writable_parameters(device_type)
                
                # Return as JSON string
                result = json.dumps(writable_params)
                print(f"DEBUG: Returning writable parameters: {result}")
                
                return [ua.Variant(result, ua.VariantType.String)]
            else:
                return [ua.Variant(json.dumps({}), ua.VariantType.String)]
            
        except Exception as e:
            logger.error("Error in parse FDI writable parameters method", device_type=device_type, error=str(e))
            return [ua.Variant(json.dumps({}), ua.VariantType.String)] 