#!/usr/bin/env python3
"""
FDI Web Demo - Interactive Web Interface
Demonstrates the complete FDI workflow with a modern web UI
"""

import os
import sys
import json
import xml.etree.ElementTree as ET
from datetime import datetime
import threading
import time

# Add the fdi-device-driver to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'fdi-device-driver'))
from fdi_driver import create_fdi_driver

from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'fdi-demo-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

class FDIWebDemo:
    def __init__(self):
        self.fdi_file_path = "device-profiles/eaton-smart-breaker.fdi"
        self.device_driver = None
        self.device_info = None
        self.configuration_templates = []
        self.device_commands = []
        self.discovered_devices = []
        self.current_step = "start"
        self.demo_log = []
        
    def load_fdi_file(self):
        """Load and parse the FDI file"""
        try:
            tree = ET.parse(self.fdi_file_path)
            root = tree.getroot()
            
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
            
            # Extract configuration templates
            self._load_configuration_templates(root, namespace)
            
            # Extract device commands
            self._load_device_commands(root, namespace)
            
            return True
            
        except Exception as e:
            self.log_event(f"Failed to load FDI file: {e}", "error")
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
                    template_desc = template_elem.get("description", "")
                    self.configuration_templates.append({
                        'name': template_name,
                        'description': template_desc
                    })
    
    def _load_device_commands(self, root, namespace):
        """Load device commands from FDI file"""
        commands = root.find("fdi:DeviceCommands", namespace)
        if commands is None:
            commands = root.find("DeviceCommands")
        
        if commands is not None:
            # Try with namespace first
            for command_elem in commands.findall("fdi:Command", namespace):
                command_name = command_elem.get("name", "")
                command_desc = command_elem.get("description", "")
                self.device_commands.append({
                    'name': command_name,
                    'description': command_desc
                })
            
            # If no commands found with namespace, try without namespace
            if not self.device_commands:
                for command_elem in commands.findall("Command"):
                    command_name = command_elem.get("name", "")
                    command_desc = command_elem.get("description", "")
                    self.device_commands.append({
                        'name': command_name,
                        'description': command_desc
                    })
            
            # Debug: log what we found
            self.log_event(f"Found {len(self.device_commands)} commands", "info")
            for cmd in self.device_commands:
                self.log_event(f"Command: {cmd['name']} - {cmd['description']}", "info")
        else:
            self.log_event("No DeviceCommands section found in FDI file", "warning")
        
        # If still no commands, add default ones for demo
        if not self.device_commands:
            self.device_commands = [
                {'name': 'get_configuration', 'description': 'Get current device configuration'},
                {'name': 'set_configuration', 'description': 'Set device configuration'},
                {'name': 'trip', 'description': 'Trip the circuit breaker'},
                {'name': 'close', 'description': 'Close the circuit breaker'},
                {'name': 'reset', 'description': 'Reset the circuit breaker'},
                {'name': 'run_diagnostic', 'description': 'Run diagnostic test'}
            ]
            self.log_event("Added default commands for demo", "info")
    
    def discover_devices(self):
        """Simulate device discovery"""
        # Simulate discovering the smart breaker
        self.discovered_devices = [{
            'id': 'eaton-breaker-001',
            'name': 'Eaton Smart Breaker',
            'type': 'SmartCircuitBreaker',
            'status': 'online',
            'ip': '192.168.1.100',
            'last_seen': datetime.now().isoformat()
        }]
        return len(self.discovered_devices) > 0
    
    def configure_device(self, device_id, template_name):
        """Simulate device configuration"""
        self.log_event(f"Applying {template_name} configuration to {device_id}", "info")
        time.sleep(2)  # Simulate configuration time
        self.log_event(f"Configuration {template_name} applied successfully to {device_id}", "success")
        return True
    
    def send_command(self, device_id, command_name):
        """Simulate sending command to device"""
        self.log_event(f"Sending {command_name} command to {device_id}", "info")
        time.sleep(1)  # Simulate command execution time
        
        # Generate realistic response based on command
        if command_name == "get_configuration":
            config_data = {
                "device_id": device_id,
                "configuration": {
                    "overcurrent_pickup": 100.0,
                    "overcurrent_delay": 1000.0,
                    "ground_fault_pickup": 5.0,
                    "ground_fault_delay": 500.0,
                    "arc_fault_pickup": 50.0,
                    "arc_fault_delay": 100.0,
                    "thermal_pickup": 120.0,
                    "thermal_delay": 300.0,
                    "rated_current": 100.0,
                    "rated_voltage": 480.0,
                    "rated_frequency": 60.0,
                    "breaking_capacity": 25.0,
                    "pole_count": 3,
                    "protection_class": "TypeB"
                },
                "timestamp": datetime.now().isoformat()
            }
            self.log_event(f"Configuration retrieved successfully", "success")
            self.log_event(f"Current settings: Overcurrent={config_data['configuration']['overcurrent_pickup']}A, Ground Fault={config_data['configuration']['ground_fault_pickup']}A", "info")
            return True
            
        elif command_name == "trip":
            self.log_event(f"Breaker tripped successfully", "success")
            self.log_event(f"Trip reason: Manual command", "info")
            return True
            
        elif command_name == "close":
            self.log_event(f"Breaker closed successfully", "success")
            self.log_event(f"Close reason: Manual command", "info")
            return True
            
        elif command_name == "reset":
            self.log_event(f"Breaker reset successfully", "success")
            self.log_event(f"Reset type: Full system reset", "info")
            return True
            
        elif command_name == "run_diagnostic":
            diagnostic_results = {
                "self_test": "PASS",
                "protection_test": "PASS", 
                "communication_test": "PASS",
                "overall_status": "HEALTHY"
            }
            self.log_event(f"Diagnostic completed successfully", "success")
            self.log_event(f"Results: {diagnostic_results['overall_status']} - All tests passed", "info")
            return True
            
        else:
            self.log_event(f"Command {command_name} executed successfully on {device_id}", "success")
            return True
    
    def log_event(self, message, level="info"):
        """Log an event for the web interface"""
        event = {
            'timestamp': datetime.now().isoformat(),
            'message': message,
            'level': level
        }
        self.demo_log.append(event)
        socketio.emit('log_event', event)

# Global FDI demo instance
fdi_demo = FDIWebDemo()

@app.route('/')
def index():
    return render_template('fdi_demo.html')

@app.route('/api/load-fdi', methods=['POST'])
def load_fdi():
    """Load FDI file"""
    fdi_demo.current_step = "loading"
    fdi_demo.log_event("Starting FDI file loading process...", "info")
    
    if fdi_demo.load_fdi_file():
        fdi_demo.current_step = "loaded"
        fdi_demo.log_event("FDI file loaded successfully!", "success")
        return jsonify({
            'success': True,
            'device_info': fdi_demo.device_info,
            'templates': fdi_demo.configuration_templates,
            'commands': [
                {'name': 'get_configuration', 'description': 'Get current device configuration'},
                {'name': 'set_configuration', 'description': 'Set device configuration'},
                {'name': 'trip', 'description': 'Trip the circuit breaker'},
                {'name': 'close', 'description': 'Close the circuit breaker'},
                {'name': 'reset', 'description': 'Reset the circuit breaker'},
                {'name': 'run_diagnostic', 'description': 'Run diagnostic test'}
            ]
        })
    else:
        fdi_demo.current_step = "error"
        return jsonify({'success': False, 'error': 'Failed to load FDI file'})

@app.route('/api/discover-devices', methods=['POST'])
def discover_devices():
    """Discover devices"""
    fdi_demo.current_step = "discovering"
    fdi_demo.log_event("Starting device discovery...", "info")
    
    if fdi_demo.discover_devices():
        fdi_demo.current_step = "discovered"
        fdi_demo.log_event(f"Discovered {len(fdi_demo.discovered_devices)} device(s)", "success")
        return jsonify({
            'success': True,
            'devices': fdi_demo.discovered_devices
        })
    else:
        fdi_demo.current_step = "error"
        return jsonify({'success': False, 'error': 'No devices found'})

@app.route('/api/configure-device', methods=['POST'])
def configure_device():
    """Configure device with template"""
    data = request.json
    device_id = data.get('device_id')
    template_name = data.get('template_name')
    
    fdi_demo.current_step = "configuring"
    fdi_demo.log_event(f"Starting device configuration...", "info")
    
    if fdi_demo.configure_device(device_id, template_name):
        fdi_demo.current_step = "configured"
        return jsonify({'success': True})
    else:
        fdi_demo.current_step = "error"
        return jsonify({'success': False, 'error': 'Configuration failed'})

@app.route('/api/send-command', methods=['POST'])
def send_command():
    """Send command to device"""
    data = request.json
    device_id = data.get('device_id')
    command_name = data.get('command_name')
    
    fdi_demo.current_step = "commanding"
    fdi_demo.log_event(f"Executing device command...", "info")
    
    if fdi_demo.send_command(device_id, command_name):
        fdi_demo.current_step = "completed"
        return jsonify({'success': True})
    else:
        fdi_demo.current_step = "error"
        return jsonify({'success': False, 'error': 'Command failed'})

@app.route('/api/status')
def get_status():
    """Get current demo status"""
    return jsonify({
        'current_step': fdi_demo.current_step,
        'device_info': fdi_demo.device_info,
        'templates': fdi_demo.configuration_templates,
        'commands': fdi_demo.device_commands,
        'devices': fdi_demo.discovered_devices,
        'log': fdi_demo.demo_log[-10:]  # Last 10 log entries
    })

def create_html_template():
    """Create the HTML template for the FDI demo"""
    html_content = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FDI Smart Breaker Demo</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .header p {
            font-size: 1.2em;
            opacity: 0.9;
        }
        
        .workflow {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .step {
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }
        
        .step.active {
            transform: translateY(-5px);
            box-shadow: 0 15px 40px rgba(0,0,0,0.2);
            border-left: 5px solid #4CAF50;
        }
        
        .step.completed {
            border-left: 5px solid #2196F3;
        }
        
        .step.error {
            border-left: 5px solid #f44336;
        }
        
        .step-number {
            position: absolute;
            top: 15px;
            right: 15px;
            width: 30px;
            height: 30px;
            background: #667eea;
            color: white;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
        }
        
        .step h3 {
            color: #333;
            margin-bottom: 15px;
            font-size: 1.3em;
        }
        
        .step-content {
            margin-bottom: 20px;
        }
        
        .btn {
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 25px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            transition: all 0.3s ease;
            margin: 5px;
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }
        
        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        
        .btn-success {
            background: linear-gradient(45deg, #4CAF50, #45a049);
        }
        
        .btn-warning {
            background: linear-gradient(45deg, #ff9800, #f57c00);
        }
        
        .btn-danger {
            background: linear-gradient(45deg, #f44336, #d32f2f);
        }
        
        .device-info {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 15px;
            margin: 10px 0;
        }
        
        .device-info h4 {
            color: #667eea;
            margin-bottom: 10px;
        }
        
        .device-info p {
            margin: 5px 0;
            font-size: 14px;
        }
        
        .template-list, .command-list {
            list-style: none;
            margin: 10px 0;
        }
        
        .template-list li, .command-list li {
            background: #e3f2fd;
            margin: 5px 0;
            padding: 10px;
            border-radius: 8px;
            border-left: 4px solid #2196F3;
        }
        
        .log-container {
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            margin-top: 20px;
        }
        
        .log-container h3 {
            color: #333;
            margin-bottom: 15px;
        }
        
        .log-entries {
            background: #1e1e1e;
            color: #00ff00;
            padding: 15px;
            border-radius: 10px;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            max-height: 300px;
            overflow-y: auto;
        }
        
        .log-entry {
            margin: 5px 0;
            padding: 5px;
            border-radius: 5px;
        }
        
        .log-entry.info {
            background: rgba(33, 150, 243, 0.1);
        }
        
        .log-entry.success {
            background: rgba(76, 175, 80, 0.1);
        }
        
        .log-entry.warning {
            background: rgba(255, 152, 0, 0.1);
        }
        
        .log-entry.error {
            background: rgba(244, 67, 54, 0.1);
        }
        
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }
        
        .status-online {
            background: #4CAF50;
        }
        
        .status-offline {
            background: #f44336;
        }
        
        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .progress-bar {
            width: 100%;
            height: 6px;
            background: #e0e0e0;
            border-radius: 3px;
            overflow: hidden;
            margin: 10px 0;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(45deg, #4CAF50, #45a049);
            width: 0%;
            transition: width 0.3s ease;
        }
        
        .config-container {
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            margin-top: 20px;
        }
        
        .config-container h3 {
            color: #333;
            margin-bottom: 15px;
        }
        
        .config-details {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            font-family: 'Courier New', monospace;
            font-size: 14px;
        }
        
        .config-section {
            margin: 15px 0;
            padding: 15px;
            background: white;
            border-radius: 8px;
            border-left: 4px solid #2196F3;
        }
        
        .config-section h4 {
            color: #2196F3;
            margin-bottom: 10px;
        }
        
        .config-item {
            display: flex;
            justify-content: space-between;
            margin: 8px 0;
            padding: 5px 0;
            border-bottom: 1px solid #eee;
        }
        
        .config-label {
            font-weight: bold;
            color: #555;
        }
        
        .config-value {
            color: #333;
            font-weight: 600;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏭 FDI Smart Breaker Demo</h1>
            <p>Field Device Integration - Industrial Automation Workflow</p>
        </div>
        
        <div class="workflow">
            <div class="step" id="step1">
                <div class="step-number">1</div>
                <h3>📁 Load FDI File</h3>
                <div class="step-content">
                    <p>Load the Eaton Smart Breaker device description file (.fdi)</p>
                    <button class="btn" onclick="loadFDIFile()">Load FDI File</button>
                    <div id="device-info" class="device-info" style="display: none;">
                        <h4>Device Information</h4>
                        <div id="device-details"></div>
                    </div>
                </div>
            </div>
            
            <div class="step" id="step2">
                <div class="step-number">2</div>
                <h3>🔍 Discover Devices</h3>
                <div class="step-content">
                    <p>Scan the network for compatible devices</p>
                    <button class="btn" id="discover-btn" onclick="discoverDevices()" disabled>Discover Devices</button>
                    <div id="devices-list" style="display: none;">
                        <h4>Discovered Devices</h4>
                        <div id="devices-details"></div>
                    </div>
                </div>
            </div>
            
            <div class="step" id="step3">
                <div class="step-number">3</div>
                <h3>⚙️ Configure Device</h3>
                <div class="step-content">
                    <p>Apply configuration template to the device</p>
                    <button class="btn" id="configure-btn" onclick="showConfigOptions()" disabled>Configure Device</button>
                    <div id="config-options" style="display: none;">
                        <h4>Configuration Templates</h4>
                        <div id="templates-list"></div>
                    </div>
                </div>
            </div>
            
            <div class="step" id="step4">
                <div class="step-number">4</div>
                <h3>🎮 Send Commands</h3>
                <div class="step-content">
                    <p>Execute commands on the configured device</p>
                    <button class="btn" id="command-btn" onclick="showCommandOptions()" disabled>Send Commands</button>
                    <div id="command-options" style="display: none;">
                        <h4>Available Commands</h4>
                        <div id="commands-list"></div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="log-container">
            <h3>📋 Activity Log</h3>
            <div class="log-entries" id="log-entries">
                <div class="log-entry info">🚀 FDI Demo started. Ready to begin workflow...</div>
            </div>
        </div>
        
        <div class="config-container" id="config-container" style="display: none;">
            <h3>⚙️ Device Configuration</h3>
            <div class="config-details" id="config-details">
                <!-- Configuration details will be displayed here -->
            </div>
        </div>
    </div>

    <script>
        const socket = io();
        let currentStep = 'start';
        let deviceInfo = null;
        let templates = [];
        let commands = [];
        let devices = [];
        
        socket.on('log_event', function(event) {
            addLogEntry(event.message, event.level);
        });
        
        function addLogEntry(message, level = 'info') {
            const logContainer = document.getElementById('log-entries');
            const entry = document.createElement('div');
            entry.className = `log-entry ${level}`;
            entry.innerHTML = `[${new Date().toLocaleTimeString()}] ${message}`;
            logContainer.appendChild(entry);
            logContainer.scrollTop = logContainer.scrollHeight;
        }
        
        function updateStepStatus(step, status) {
            const stepElement = document.getElementById(step);
            stepElement.className = `step ${status}`;
        }
        
        async function loadFDIFile() {
            const btn = event.target;
            btn.disabled = true;
            btn.innerHTML = '<span class="loading"></span> Loading...';
            
            try {
                const response = await fetch('/api/load-fdi', { method: 'POST' });
                const data = await response.json();
                
                if (data.success) {
                    deviceInfo = data.device_info;
                    templates = data.templates;
                    commands = data.commands;
                    
                    updateStepStatus('step1', 'completed');
                    document.getElementById('discover-btn').disabled = false;
                    
                    // Display device info
                    const deviceDetails = document.getElementById('device-details');
                    deviceDetails.innerHTML = `
                        <p><strong>Type:</strong> ${deviceInfo.type}</p>
                        <p><strong>Manufacturer:</strong> ${deviceInfo.manufacturer}</p>
                        <p><strong>Model:</strong> ${deviceInfo.model}</p>
                        <p><strong>Serial Number:</strong> ${deviceInfo.serial_number}</p>
                        <p><strong>Version:</strong> ${deviceInfo.version}</p>
                        <p><strong>Description:</strong> ${deviceInfo.description}</p>
                    `;
                    document.getElementById('device-info').style.display = 'block';
                    
                    addLogEntry('✅ FDI file loaded successfully!', 'success');
                } else {
                    throw new Error(data.error);
                }
            } catch (error) {
                updateStepStatus('step1', 'error');
                addLogEntry(`❌ Failed to load FDI file: ${error.message}`, 'error');
            } finally {
                btn.disabled = false;
                btn.textContent = 'Load FDI File';
            }
        }
        
        async function discoverDevices() {
            const btn = event.target;
            btn.disabled = true;
            btn.innerHTML = '<span class="loading"></span> Discovering...';
            
            try {
                const response = await fetch('/api/discover-devices', { method: 'POST' });
                const data = await response.json();
                
                if (data.success) {
                    devices = data.devices;
                    updateStepStatus('step2', 'completed');
                    document.getElementById('configure-btn').disabled = false;
                    
                    // Display devices
                    const devicesDetails = document.getElementById('devices-details');
                    devicesDetails.innerHTML = devices.map(device => `
                        <div style="background: #e8f5e8; padding: 10px; border-radius: 8px; margin: 5px 0;">
                            <span class="status-indicator status-online"></span>
                            <strong>${device.name}</strong> (${device.id})<br>
                            <small>Type: ${device.type} | IP: ${device.ip}</small>
                        </div>
                    `).join('');
                    document.getElementById('devices-list').style.display = 'block';
                    
                    addLogEntry(`✅ Discovered ${devices.length} device(s)`, 'success');
                } else {
                    throw new Error(data.error);
                }
            } catch (error) {
                updateStepStatus('step2', 'error');
                addLogEntry(`❌ Device discovery failed: ${error.message}`, 'error');
            } finally {
                btn.disabled = false;
                btn.textContent = 'Discover Devices';
            }
        }
        
        function showConfigOptions() {
            const configOptions = document.getElementById('config-options');
            const templatesList = document.getElementById('templates-list');
            
            templatesList.innerHTML = templates.map(template => `
                <div style="background: #e3f2fd; padding: 15px; border-radius: 8px; margin: 10px 0; border-left: 4px solid #2196F3;">
                    <h4>${template.name}</h4>
                    <p>${template.description}</p>
                    <button class="btn btn-success" onclick="configureDevice('${template.name}')">Apply Template</button>
                </div>
            `).join('');
            
            configOptions.style.display = 'block';
        }
        
        async function configureDevice(templateName) {
            const btn = event.target;
            btn.disabled = true;
            btn.innerHTML = '<span class="loading"></span> Configuring...';
            
            try {
                const response = await fetch('/api/configure-device', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        device_id: devices[0].id,
                        template_name: templateName
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    updateStepStatus('step3', 'completed');
                    document.getElementById('command-btn').disabled = false;
                    addLogEntry(`✅ Configuration '${templateName}' applied successfully!`, 'success');
                } else {
                    throw new Error(data.error);
                }
            } catch (error) {
                updateStepStatus('step3', 'error');
                addLogEntry(`❌ Configuration failed: ${error.message}`, 'error');
            } finally {
                btn.disabled = false;
                btn.textContent = 'Apply Template';
            }
        }
        
        function showCommandOptions() {
            const commandOptions = document.getElementById('command-options');
            const commandsList = document.getElementById('commands-list');
            
            commandsList.innerHTML = commands.map(command => `
                <div style="background: #fff3e0; padding: 15px; border-radius: 8px; margin: 10px 0; border-left: 4px solid #ff9800;">
                    <h4>${command.name}</h4>
                    <p>${command.description}</p>
                    <button class="btn btn-warning" onclick="sendCommand('${command.name}')">Execute Command</button>
                </div>
            `).join('');
            
            commandOptions.style.display = 'block';
        }
        
        async function sendCommand(commandName) {
            const btn = event.target;
            btn.disabled = true;
            btn.innerHTML = '<span class="loading"></span> Executing...';
            
            try {
                const response = await fetch('/api/send-command', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        device_id: devices[0].id,
                        command_name: commandName
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    updateStepStatus('step4', 'completed');
                    addLogEntry(`✅ Command '${commandName}' executed successfully!`, 'success');
                    
                    // Handle specific command responses
                    if (commandName === 'get_configuration') {
                        showConfiguration();
                    }
                } else {
                    throw new Error(data.error);
                }
            } catch (error) {
                updateStepStatus('step4', 'error');
                addLogEntry(`❌ Command failed: ${error.message}`, 'error');
            } finally {
                btn.disabled = false;
                btn.textContent = 'Execute Command';
            }
        }
        
        function showConfiguration() {
            const configContainer = document.getElementById('config-container');
            const configDetails = document.getElementById('config-details');
            
            // Simulate configuration data (in real implementation, this would come from the device)
            const configData = {
                "device_id": "eaton-breaker-001",
                "configuration": {
                    "overcurrent_pickup": 100.0,
                    "overcurrent_delay": 1000.0,
                    "ground_fault_pickup": 5.0,
                    "ground_fault_delay": 500.0,
                    "arc_fault_pickup": 50.0,
                    "arc_fault_delay": 100.0,
                    "thermal_pickup": 120.0,
                    "thermal_delay": 300.0,
                    "rated_current": 100.0,
                    "rated_voltage": 480.0,
                    "rated_frequency": 60.0,
                    "breaking_capacity": 25.0,
                    "pole_count": 3,
                    "protection_class": "TypeB"
                },
                "timestamp": new Date().toISOString()
            };
            
            configDetails.innerHTML = `
                <div class="config-section">
                    <h4>🔧 Protection Settings</h4>
                    <div class="config-item">
                        <span class="config-label">Overcurrent Pickup:</span>
                        <span class="config-value">${configData.configuration.overcurrent_pickup} A</span>
                    </div>
                    <div class="config-item">
                        <span class="config-label">Overcurrent Delay:</span>
                        <span class="config-value">${configData.configuration.overcurrent_delay} ms</span>
                    </div>
                    <div class="config-item">
                        <span class="config-label">Ground Fault Pickup:</span>
                        <span class="config-value">${configData.configuration.ground_fault_pickup} A</span>
                    </div>
                    <div class="config-item">
                        <span class="config-label">Ground Fault Delay:</span>
                        <span class="config-value">${configData.configuration.ground_fault_delay} ms</span>
                    </div>
                    <div class="config-item">
                        <span class="config-label">Arc Fault Pickup:</span>
                        <span class="config-value">${configData.configuration.arc_fault_pickup} A</span>
                    </div>
                    <div class="config-item">
                        <span class="config-label">Arc Fault Delay:</span>
                        <span class="config-value">${configData.configuration.arc_fault_delay} ms</span>
                    </div>
                    <div class="config-item">
                        <span class="config-label">Thermal Pickup:</span>
                        <span class="config-value">${configData.configuration.thermal_pickup} A</span>
                    </div>
                    <div class="config-item">
                        <span class="config-label">Thermal Delay:</span>
                        <span class="config-value">${configData.configuration.thermal_delay} s</span>
                    </div>
                </div>
                
                <div class="config-section">
                    <h4>⚡ Electrical Ratings</h4>
                    <div class="config-item">
                        <span class="config-label">Rated Current:</span>
                        <span class="config-value">${configData.configuration.rated_current} A</span>
                    </div>
                    <div class="config-item">
                        <span class="config-label">Rated Voltage:</span>
                        <span class="config-value">${configData.configuration.rated_voltage} V</span>
                    </div>
                    <div class="config-item">
                        <span class="config-label">Rated Frequency:</span>
                        <span class="config-value">${configData.configuration.rated_frequency} Hz</span>
                    </div>
                    <div class="config-item">
                        <span class="config-label">Breaking Capacity:</span>
                        <span class="config-value">${configData.configuration.breaking_capacity} kA</span>
                    </div>
                    <div class="config-item">
                        <span class="config-label">Pole Count:</span>
                        <span class="config-value">${configData.configuration.pole_count}</span>
                    </div>
                    <div class="config-item">
                        <span class="config-label">Protection Class:</span>
                        <span class="config-value">${configData.configuration.protection_class}</span>
                    </div>
                </div>
                
                <div class="config-section">
                    <h4>📅 Last Updated</h4>
                    <div class="config-item">
                        <span class="config-label">Timestamp:</span>
                        <span class="config-value">${new Date(configData.timestamp).toLocaleString()}</span>
                    </div>
                </div>
            `;
            
            configContainer.style.display = 'block';
            configContainer.scrollIntoView({ behavior: 'smooth' });
        }
    </script>
</body>
</html>
    '''
    
    with open('templates/fdi_demo.html', 'w') as f:
        f.write(html_content)

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    
    # Create the HTML template
    create_html_template()
    
    print("🚀 Starting FDI Web Demo...")
    print("📱 Open your browser to: http://localhost:8088")
    print("🎯 This demonstrates the complete FDI workflow!")
    
    socketio.run(app, host='0.0.0.0', port=8088, debug=True) 