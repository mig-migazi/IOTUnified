#!/usr/bin/env python3
"""
Web Client - FDI Host Simulator
This web application simulates an FDI Host (like Siemens PDM, ABB FIM, Emerson AMS) by connecting to our OPC UA Communication Server
and providing a web interface for device discovery and configuration.

Architecture:
[Web Browser] ← HTTP → [This Web Client] ← OPC UA → [OPC UA Communication Server] ← MQTT → [Smart Breaker Device]
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
import structlog

# OPC UA imports
try:
    from asyncua import Client
    OPCUA_AVAILABLE = True
except ImportError:
    OPCUA_AVAILABLE = False
    print("OPC UA not available. Install: pip install asyncua")

# Web framework imports
try:
    from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
    from fastapi.responses import HTMLResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.templating import Jinja2Templates
    import uvicorn
    WEB_AVAILABLE = True
except ImportError:
    WEB_AVAILABLE = False
    print("Web framework not available. Install: pip install fastapi uvicorn jinja2")

logger = structlog.get_logger()

class FDIHostSimulator:
    """FDI Host Simulator - Web Client"""
    
    def __init__(self, opcua_server_url: str = "opc.tcp://localhost:4840"):
        self.opcua_server_url = opcua_server_url
        self.opcua_client = None
        self.devices = {}
        self.fdi_packages = {}
        
        if not OPCUA_AVAILABLE:
            raise ImportError("OPC UA library not available")
        if not WEB_AVAILABLE:
            raise ImportError("Web framework not available")
        
        # Create FastAPI app
        self.app = FastAPI(title="FDI Host Simulator", version="1.0.0")
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def home():
            """Home page"""
            return """
            <!DOCTYPE html>
            <html>
            <head>
                <title>FDI Host Simulator</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; }
                    .header { background: #007acc; color: white; padding: 20px; border-radius: 5px; }
                    .content { margin-top: 20px; }
                    .button { background: #007acc; color: white; padding: 10px 20px; border: none; border-radius: 3px; cursor: pointer; }
                    .button:hover { background: #005a9e; }
                    .device-list { margin-top: 20px; }
                    .device-item { border: 1px solid #ddd; padding: 10px; margin: 5px 0; border-radius: 3px; }
                    .status-online { color: green; }
                    .status-offline { color: red; }
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>🔧 FDI Host Simulator</h1>
                    <p>Field Device Integration Client</p>
                </div>
                
                <div class="content">
                    <h2>Device Discovery</h2>
                    <button class="button" onclick="discoverDevices()">Discover Devices</button>
                    <button class="button" onclick="refreshDevices()">Refresh</button>
                    
                    <div id="device-list" class="device-list">
                        <p>Click "Discover Devices" to find available devices...</p>
                    </div>
                </div>
                
                <script>
                    async function discoverDevices() {
                        try {
                            const response = await fetch('/api/devices/discover');
                            const devices = await response.json();
                            displayDevices(devices);
                        } catch (error) {
                            console.error('Error discovering devices:', error);
                            document.getElementById('device-list').innerHTML = '<p style="color: red;">Error discovering devices</p>';
                        }
                    }
                    
                    async function refreshDevices() {
                        try {
                            const response = await fetch('/api/devices');
                            const devices = await response.json();
                            displayDevices(devices);
                        } catch (error) {
                            console.error('Error refreshing devices:', error);
                        }
                    }
                    
                    function displayDevices(devices) {
                        const deviceList = document.getElementById('device-list');
                        if (devices.length === 0) {
                            deviceList.innerHTML = '<p>No devices found</p>';
                            return;
                        }
                        
                        let html = '<h3>Discovered Devices:</h3>';
                        devices.forEach(device => {
                            const statusClass = device.status === 'online' ? 'status-online' : 'status-offline';
                            html += `
                                <div class="device-item">
                                    <h4>${device.device_id}</h4>
                                    <p><strong>Type:</strong> ${device.device_type}</p>
                                    <p><strong>Status:</strong> <span class="${statusClass}">${device.status}</span></p>
                                    <button class="button" onclick="configureDevice('${device.device_id}')">Configure</button>
                                    <button class="button" onclick="viewParameters('${device.device_id}')">View Parameters</button>
                                </div>
                            `;
                        });
                        deviceList.innerHTML = html;
                    }
                    
                    async function configureDevice(deviceId) {
                        console.log('=== CONFIGURE DEVICE START ===');
                        console.log('configureDevice called with deviceId:', deviceId);
                        
                        try {
                            // Get writable parameters from FDI definition
                            console.log('Fetching writable parameters...');
                            const response = await fetch(`/api/devices/${deviceId}/writable-parameters`);
                            const writableParams = await response.json();
                            console.log('Writable parameters:', writableParams);
                            
                            // Get current device parameters
                            console.log('Fetching current parameters...');
                            const paramsResponse = await fetch(`/api/devices/${deviceId}/parameters`);
                            const currentParams = await paramsResponse.json();
                            console.log('Current parameters:', currentParams);
                            
                            // Get current device configuration
                            console.log('Fetching current configuration...');
                            const currentConfigResponse = await fetch(`/api/devices/${deviceId}/current-configuration`);
                            const currentConfig = await currentConfigResponse.json();
                            console.log('Current configuration:', currentConfig);
                            
                            // Open configuration dialog
                            console.log('Creating configuration dialog...');
                            
                            // Check for existing modals
                            const existingModals = document.querySelectorAll('[id*="modal"]');
                            console.log('Existing modals found:', existingModals.length);
                            existingModals.forEach((modal, index) => {
                                console.log(`Modal ${index}:`, modal.id, modal.innerHTML.length);
                            });
                            
                            // Remove any existing modals first
                            const existingConfigModal = document.getElementById('config-modal');
                            if (existingConfigModal) {
                                console.log('Removing existing config modal');
                                existingConfigModal.remove();
                            }
                            
                            // Create simple modal using direct injection approach
                            const modalContent = `
                                <div id="config-modal" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000;">
                                    <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); background: white; padding: 20px; border-radius: 5px; max-width: 800px; max-height: 80vh; overflow-y: auto;">
                                        <h3>Configure Device: ${deviceId}</h3>
                                        
                                        <div style="display: flex; gap: 20px;">
                                            <!-- Configuration Parameters -->
                                            <div style="flex: 1;">
                                                <h4>Configuration Parameters</h4>
                                                <form id="config-form">
                                                    ${createConfigurationForm(writableParams, currentParams, currentConfig)}

                                                </form>
                                            </div>
                                            
                                            <!-- Templates and Commands -->
                                            <div style="flex: 1;">
                                                <h4>Quick Actions</h4>
                                                ${createTemplatesSection(writableParams)}
                                                ${createCommandsSection(writableParams)}
                                            </div>
                                        </div>
                                        
                                        <div style="margin-top: 20px;">
                                            <button type="button" class="button" onclick="closeModal()">Cancel</button>
                                        </div>
                                    </div>
                                </div>
                            `;
                            
                            console.log('Injecting simple modal...');
                            document.body.insertAdjacentHTML('beforeend', modalContent);
                            console.log('Simple modal injected');
                            
                            // Debug: Check what's actually in the modal
                            setTimeout(() => {
                                const modal = document.getElementById('config-modal');
                                if (modal) {
                                    console.log('Modal found:', modal);
                                    console.log('Modal innerHTML length:', modal.innerHTML.length);
                                    console.log('Modal innerHTML preview:', modal.innerHTML.substring(0, 500));
                                    
                                    // Check if form content exists
                                    const form = modal.querySelector('#config-form');
                                    if (form) {
                                        console.log('Form found:', form);
                                        console.log('Form innerHTML length:', form.innerHTML.length);
                                        console.log('Form innerHTML:', form.innerHTML);
                                    } else {
                                        console.log('Form NOT found in modal');
                                    }
                                } else {
                                    console.log('Modal NOT found');
                                }
                            }, 100);
                            
                            console.log('=== CONFIGURE DEVICE END ===');
                        } catch (error) {
                            console.error('Error getting device configuration options:', error);
                            alert('Error opening configuration dialog: ' + error.message);
                        }
                    }
                    
                    function createConfigurationDialog(deviceId, writableParams, currentParams, currentConfig) {
                        console.log('createConfigurationDialog called with:', { deviceId, writableParams, currentParams, currentConfig });
                        
                        // SIMPLE TEST - Just show some basic content
                        return `
                            <div id="config-modal" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000; display: block !important; visibility: visible !important;">
                                <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); background: white; padding: 20px; border-radius: 5px; max-width: 800px; max-height: 80vh; overflow-y: auto; display: block !important; visibility: visible !important; opacity: 1 !important;">
                                    <h3>Configure Device: ${deviceId}</h3>
                                    
                                    <!-- SIMPLE TEST CONTENT -->
                                    <div style="background: yellow; padding: 10px; margin: 10px 0; border: 2px solid red; display: block !important; visibility: visible !important;">
                                        <h4>TEST CONTENT - This should be visible!</h4>
                                        <p>If you can see this yellow box with red border, the modal is working.</p>
                                        <p>Device ID: ${deviceId}</p>
                                        <p>Functions count: ${Object.keys(writableParams.functions || {}).length}</p>
                                        <p>Commands count: ${Object.keys(writableParams.commands || {}).length}</p>
                                        <p>Templates count: ${Object.keys(writableParams.templates || {}).length}</p>
                                    </div>
                                    
                                    <!-- SIMPLE FORM TEST -->
                                    <div style="background: lightblue; padding: 10px; margin: 10px 0; border: 2px solid blue; display: block !important; visibility: visible !important;">
                                        <h4>FORM TEST</h4>
                                        <form id="config-form" style="display: block !important; visibility: visible !important;">
                                            <div style="margin: 10px 0;">
                                                <label>Test Input 1:</label>
                                                <input type="text" name="test1" value="test value 1" style="margin-left: 10px;">
                                            </div>
                                            <div style="margin: 10px 0;">
                                                <label>Test Input 2:</label>
                                                <input type="number" name="test2" value="42" style="margin-left: 10px;">
                                            </div>
                                            <div style="margin: 10px 0;">
                                                <label>Test Boolean:</label>
                                                <select name="test3" style="margin-left: 10px;">
                                                    <option value="true">True</option>
                                                    <option value="false" selected>False</option>
                                                </select>
                                            </div>
                                        </form>
                                    </div>
                                    
                                    <div style="margin-top: 20px;">
                                        <button type="button" class="button" onclick="closeModal()">Cancel</button>
                                    </div>
                                </div>
                            </div>
                        `;
                    }
                    
                    function createConfigurationForm(writableParams, currentParams, currentConfig) {
                        console.log('createConfigurationForm called with:', { writableParams, currentParams, currentConfig });
                        
                        let html = '<div style="margin-bottom: 20px;">';
                        html += '<h5>Configuration Parameters</h5>';
                        
                        console.log('writableParams.functions:', writableParams.functions);
                        console.log('Object.entries(writableParams.functions):', Object.entries(writableParams.functions || {}));
                        
                        // Create forms for each function
                        for (const [funcName, funcData] of Object.entries(writableParams.functions || {})) {
                            console.log('Processing function:', funcName, funcData);
                            html += `
                                <div style="margin-bottom: 20px; border: 1px solid #ddd; padding: 10px; border-radius: 5px;">
                                    <h5>${funcName} (${funcData.category})</h5>
                                    <p style="font-size: 12px; color: #666;">${funcData.description}</p>
                            `;
                            
                            console.log('funcData.parameters:', funcData.parameters);
                            for (const [paramName, paramInfo] of Object.entries(funcData.parameters || {})) {
                                console.log('Processing parameter:', paramName, paramInfo);
                                const currentValue = currentParams.metrics?.[paramName] || paramInfo.default || '';
                                const units = paramInfo.units ? ` ${paramInfo.units}` : '';
                                const range = paramInfo.range ? ` [${paramInfo.range}]` : '';
                                const description = paramInfo.description ? ` - ${paramInfo.description}` : '';
                                
                                html += `
                                    <div style="margin: 10px 0; padding: 8px; border: 1px solid #eee; border-radius: 3px;">
                                        <label><strong>${paramName}</strong></label>
                                        ${description ? `<br><span style="font-size: 11px; color: #666;">${description}</span>` : ''}
                                        <div style="display: flex; gap: 10px; align-items: center; margin: 5px 0;">
                                            <span style="font-size: 11px; color: #888; min-width: 80px;">Current:</span>
                                            <span style="font-size: 12px; color: #333; font-weight: bold;">${currentValue}${units}</span>
                                        </div>
                                        <div style="display: flex; gap: 10px; align-items: center; margin: 5px 0;">
                                            <span style="font-size: 11px; color: #0066cc; min-width: 80px;">New:</span>
                                            ${createInputField(paramName, paramInfo, currentValue)}
                                            <span style="font-size: 11px; color: #666;">${units}${range}</span>
                                        </div>
                                    </div>
                                `;
                            }
                            
                            html += '</div>';
                        }
                        
                        console.log('Generated HTML length:', html.length);
                        return html;
                    }
                    
                    function createInputField(paramName, paramInfo, currentValue) {
                        const type = paramInfo.type || 'String';
                        const units = paramInfo.units ? ` (${paramInfo.units})` : '';
                        const range = paramInfo.range ? ` [${paramInfo.range}]` : '';
                        const min = paramInfo.min;
                        const max = paramInfo.max;
                        const step = paramInfo.step;
                        
                        if (type === 'Boolean') {
                            return `
                                <select name="${paramName}" style="padding: 4px; border: 1px solid #ccc; border-radius: 3px;">
                                    <option value="true" ${currentValue === true ? 'selected' : ''}>True</option>
                                    <option value="false" ${currentValue === false ? 'selected' : ''}>False</option>
                                </select>
                            `;
                        } else if (type === 'Integer' && paramInfo.values) {
                            return `
                                <select name="${paramName}" style="padding: 4px; border: 1px solid #ccc; border-radius: 3px;">
                                    ${paramInfo.values.map(val => `<option value="${val}" ${currentValue == val ? 'selected' : ''}>${val}</option>`).join('')}
                                </select>
                            `;
                        } else if (type === 'Float' || type === 'Double') {
                            const stepAttr = step ? ` step="${step}"` : '';
                            const minAttr = min ? ` min="${min}"` : '';
                            const maxAttr = max ? ` max="${max}"` : '';
                            return `
                                <input type="number" name="${paramName}" value="${currentValue}" 
                                       placeholder="${type}${units}${range}" 
                                       style="padding: 4px; border: 1px solid #ccc; border-radius: 3px; width: 120px;"
                                       ${stepAttr} ${minAttr} ${maxAttr}>
                            `;
                        } else if (type === 'Integer') {
                            const minAttr = min ? ` min="${min}"` : '';
                            const maxAttr = max ? ` max="${max}"` : '';
                            return `
                                <input type="number" name="${paramName}" value="${currentValue}" 
                                       placeholder="${type}${units}${range}" 
                                       style="padding: 4px; border: 1px solid #ccc; border-radius: 3px; width: 120px;"
                                       ${minAttr} ${maxAttr}>
                            `;
                        } else {
                            return `
                                <input type="text" name="${paramName}" value="${currentValue}" 
                                       placeholder="${type}${units}${range}"
                                       style="padding: 4px; border: 1px solid #ccc; border-radius: 3px; width: 120px;">
                            `;
                        }
                    }
                    
                    function createTemplatesSection(writableParams) {
                        console.log('createTemplatesSection called with:', writableParams);
                        
                        let html = '<div style="margin-bottom: 20px;">';
                        html += '<h5>Configuration Templates</h5>';
                        html += '<p style="font-size: 12px; color: #666; margin-bottom: 10px;">Predefined configurations for common scenarios:</p>';
                        
                        console.log('Templates:', writableParams.templates);
                        
                        for (const [templateName, templateData] of Object.entries(writableParams.templates || {})) {
                            console.log('Creating template:', templateName, templateData);
                            
                            html += `
                                <div style="margin: 10px 0; padding: 15px; border: 1px solid #eee; border-radius: 5px; background: #fafafa;">
                                    <div style="display: flex; justify-content: space-between; align-items: start;">
                                        <div style="flex: 1;">
                                            <strong style="color: #0066cc;">${templateName}</strong><br>
                                            <span style="font-size: 12px; color: #666;">${templateData.description}</span>
                                        </div>
                                        <button type="button" class="button" onclick="previewTemplateSimple('${templateName}')" style="background: #0066cc; color: white; font-size: 11px; padding: 5px 10px;">
                                            Preview
                                        </button>
                                    </div>
                                    <div style="margin-top: 10px;">
                                        <button type="button" class="button" onclick="applyTemplate('${templateName}', ${JSON.stringify(templateData.settings)})" style="background: #4CAF50; color: white; font-size: 11px; padding: 5px 10px;">
                                            Apply Template
                                        </button>
                                    </div>
                                </div>
                            `;
                        }
                        
                        html += '</div>';
                        console.log('Generated templates HTML length:', html.length);
                        return html;
                    }
                    
                    function previewTemplateSimple(templateName) {
                        console.log('previewTemplateSimple called with:', templateName);
                        
                        // Get the template data from writable parameters
                        fetch(`/api/devices/smart-breaker-000/writable-parameters`)
                            .then(response => response.json())
                            .then(writableParams => {
                                console.log('Writable params for preview:', writableParams);
                                
                                const templateData = writableParams.templates?.[templateName];
                                if (!templateData) {
                                    console.error('Template not found:', templateName);
                                    showMessage(`Template "${templateName}" not found`, 'error');
                                    return;
                                }
                                
                                console.log('Template data:', templateData);
                                
                                // Get current parameters for comparison
                                return getCurrentDeviceParameters().then(currentParams => {
                                    console.log('Current params for preview:', currentParams);
                                    
                                    let previewHtml = '<div style="margin: 10px 0; padding: 15px; background: #f0f8ff; border: 1px solid #0066cc; border-radius: 5px;">';
                                    previewHtml += `<h4 style="color: #0066cc; margin-bottom: 10px;">Template Preview: ${templateName}</h4>`;
                                    previewHtml += `<p style="font-size: 12px; color: #666; margin-bottom: 15px;">${templateData.description}</p>`;
                                    previewHtml += '<p style="font-size: 12px; color: #666; margin-bottom: 15px;">This template will update the following parameters:</p>';
                                    
                                    for (const [paramName, value] of Object.entries(templateData.settings || {})) {
                                        const currentValue = currentParams.metrics?.[paramName] || 'N/A';
                                        const units = getParameterUnits(paramName);
                                        const hasChange = currentValue !== value;
                                        
                                        previewHtml += `
                                            <div style="margin: 8px 0; padding: 8px; background: white; border-radius: 3px; border-left: 3px solid ${hasChange ? '#0066cc' : '#ccc'};">
                                                <div style="display: flex; justify-content: space-between; align-items: center;">
                                                    <div>
                                                        <strong>${paramName}</strong><br>
                                                        <span style="color: #888; font-size: 11px;">Current: ${currentValue}${units}</span>
                                                    </div>
                                                    <div style="text-align: right;">
                                                        <span style="color: #0066cc; font-weight: bold;">New: ${value}${units}</span><br>
                                                        ${hasChange ? '<span style="color: #0066cc; font-size: 11px;">✓ Will change</span>' : '<span style="color: #666; font-size: 11px;">No change</span>'}
                                                    </div>
                                                </div>
                                            </div>
                                        `;
                                    }
                                    
                                    previewHtml += `
                                        <div style="margin-top: 15px; padding-top: 10px; border-top: 1px solid #ccc;">
                                            <button type="button" class="button" onclick="applyTemplate('${templateName}', ${JSON.stringify(templateData.settings)})" style="background: #4CAF50; color: white;">
                                                Apply Template
                                            </button>
                                            <button type="button" class="button" onclick="closePreview()" style="background: #666; color: white; margin-left: 10px;">
                                                Close
                                            </button>
                                        </div>
                                    </div>`;
                                    
                                    // Show preview modal
                                    showPreviewModal(previewHtml);
                                });
                            })
                            .catch(error => {
                                console.error('Error loading template data:', error);
                                showMessage('Error loading template data', 'error');
                            });
                    }
                    
                    function createCommandsSection(writableParams) {
                        console.log('createCommandsSection called with:', writableParams);
                        
                        let html = '<div style="margin-bottom: 20px;">';
                        html += '<h5>Device Commands</h5>';
                        html += '<p style="font-size: 12px; color: #666; margin-bottom: 10px;">Execute device operations:</p>';
                        
                        console.log('Commands:', writableParams.commands);
                        
                        for (const [commandName, commandData] of Object.entries(writableParams.commands || {})) {
                            console.log('Creating command button for:', commandName, commandData);
                            
                            html += `
                                <div style="margin: 10px 0; padding: 15px; border: 1px solid #eee; border-radius: 5px; background: #fafafa;">
                                    <div style="display: flex; justify-content: space-between; align-items: start;">
                                        <div style="flex: 1;">
                                            <strong style="color: #0066cc;">${commandName}</strong><br>
                                            <span style="font-size: 12px; color: #666;">${commandData.description}</span>
                                        </div>
                                        <button type="button" class="button" onclick="executeCommandSimple('${commandName}')" style="background: #ff6600; color: white; font-size: 11px; padding: 5px 10px;">
                                            Execute
                                        </button>
                                    </div>
                                </div>
                            `;
                        }
                        
                        html += '</div>';
                        console.log('Generated commands HTML length:', html.length);
                        return html;
                    }
                    
                    function executeCommandSimple(commandName) {
                        console.log('executeCommandSimple called with:', commandName);
                        
                        // Special handling for set_configuration command

                        
                        // Show a simple confirmation for other commands
                        const confirmationHtml = `
                            <div style="margin: 10px 0; padding: 15px; background: #fff3cd; border: 1px solid #ffc107; border-radius: 5px;">
                                <h4 style="color: #856404; margin-bottom: 10px;">Confirm Command: ${commandName}</h4>
                                <p style="font-size: 12px; color: #666; margin-bottom: 15px;">Are you sure you want to execute this command?</p>
                                <div style="margin-top: 15px; padding-top: 10px; border-top: 1px solid #ccc;">
                                    <button type="button" class="button" onclick="sendCommandSimple('${commandName}')" style="background: #dc3545; color: white;">
                                        Execute Command
                                    </button>
                                    <button type="button" class="button" onclick="closePreview()" style="background: #666; color: white; margin-left: 10px;">
                                        Cancel
                                    </button>
                                </div>
                            </div>
                        `;
                        
                        console.log('Showing confirmation modal...');
                        showPreviewModal(confirmationHtml);
                    }
                    
                    async function sendCommandSimple(commandName) {
                        console.log('sendCommandSimple called with:', commandName);
                        
                        try {
                            const deviceId = document.querySelector('#config-modal h3').textContent.split(': ')[1];
                            console.log('Device ID:', deviceId);
                            
                            const payload = {
                                command: commandName,
                                parameters: {}
                            };
                            console.log('Sending payload:', payload);
                            
                            const response = await fetch(`/api/devices/${deviceId}/command`, {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json',
                                },
                                body: JSON.stringify(payload)
                            });
                            
                            console.log('Response status:', response.status);
                            
                            if (!response.ok) {
                                const errorText = await response.text();
                                console.error('HTTP error response:', errorText);
                                throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
                            }
                            
                            const result = await response.json();
                            console.log('Command result:', result);
                            
                            // Close the confirmation modal
                            closePreview();
                            
                            // Show the result
                            showMessage(`Command "${commandName}" executed successfully!`, 'info');
                            
                            // If it's get_configuration, show the result in a modal
                            if (commandName === 'get_configuration') {
                                const resultHtml = `
                                    <div style="margin: 10px 0; padding: 15px; background: #d4edda; border: 1px solid #c3e6cb; border-radius: 5px;">
                                        <h4 style="color: #155724; margin-bottom: 10px;">Configuration Result</h4>
                                        <pre style="background: white; padding: 10px; border-radius: 3px; overflow-x: auto; font-size: 12px;">${JSON.stringify(result, null, 2)}</pre>
                                        <div style="margin-top: 15px;">
                                            <button type="button" class="button" onclick="closePreview()" style="background: #666; color: white;">
                                                Close
                                            </button>
                                        </div>
                                    </div>
                                `;
                                showPreviewModal(resultHtml);
                            }
                            
                            return result;
                        } catch (error) {
                            console.error('Error sending command:', error);
                            closePreview();
                            showMessage(`Error executing command "${commandName}": ${error}`, 'error');
                            throw error;
                        }
                    }
                    
                    function confirmCommand(commandName, commandData) {
                        console.log('confirmCommand called with:', commandName, commandData);
                        
                        let confirmationHtml = '<div style="margin: 10px 0; padding: 15px; background: #fff3cd; border: 1px solid #ffc107; border-radius: 5px;">';
                        confirmationHtml += `<h4 style="color: #856404; margin-bottom: 10px;">Confirm Command: ${commandName}</h4>`;
                        confirmationHtml += `<p style="font-size: 12px; color: #666; margin-bottom: 15px;">${commandData.description}</p>`;
                        
                        // Show parameters if any
                        if (commandData.parameters && Object.keys(commandData.parameters).length > 0) {
                            confirmationHtml += '<p style="font-size: 12px; color: #666; margin-bottom: 10px;">Command parameters:</p>';
                            for (const [paramName, paramInfo] of Object.entries(commandData.parameters)) {
                                confirmationHtml += `
                                    <div style="margin: 5px 0; padding: 5px; background: white; border-radius: 3px;">
                                        <strong>${paramName}:</strong> ${paramInfo.type} ${paramInfo.required ? '(required)' : '(optional)'}
                                        ${paramInfo.default ? ` - Default: ${paramInfo.default}` : ''}
                                    </div>
                                `;
                            }
                        }
                        
                        confirmationHtml += `
                            <div style="margin-top: 15px; padding-top: 10px; border-top: 1px solid #ccc;">
                                <button type="button" class="button" onclick="executeCommand('${commandName}', ${JSON.stringify(commandData)})" style="background: #dc3545; color: white;">
                                    Execute Command
                                </button>
                                <button type="button" class="button" onclick="closePreview()" style="background: #666; color: white; margin-left: 10px;">
                                    Cancel
                                </button>
                            </div>
                        </div>`;
                        
                        // Show confirmation modal
                        console.log('Showing confirmation modal...');
                        showPreviewModal(confirmationHtml);
                    }
                    
                    function executeCommand(commandName, commandData) {
                        console.log('executeCommand called with:', commandName, commandData);
                        
                        // Close confirmation modal
                        closePreview();
                        
                        // Execute the command
                        console.log('Sending command to backend...');
                        sendCommand(commandName, commandData.parameters || {})
                            .then(response => {
                                console.log('Command executed successfully:', response);
                                showMessage(`Command "${commandName}" executed successfully!`, 'info');
                            })
                            .catch(error => {
                                console.error('Error executing command:', error);
                                showMessage(`Error executing command "${commandName}": ${error}`, 'error');
                            });
                    }
                    
                    async function sendCommand(commandName, parameters) {
                        console.log('sendCommand called with:', commandName, parameters);
                        
                        try {
                            const deviceId = document.querySelector('#config-modal h3').textContent.split(': ')[1];
                            console.log('Device ID:', deviceId);
                            
                            const payload = {
                                command: commandName,
                                parameters: parameters
                            };
                            console.log('Sending payload:', payload);
                            
                            const response = await fetch(`/api/devices/${deviceId}/command`, {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json',
                                },
                                body: JSON.stringify(payload)
                            });
                            
                            console.log('Response status:', response.status);
                            
                            if (!response.ok) {
                                const errorText = await response.text();
                                console.error('HTTP error response:', errorText);
                                throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
                            }
                            
                            const result = await response.json();
                            console.log('Command result:', result);
                            return result;
                        } catch (error) {
                            console.error('Error sending command:', error);
                            throw error;
                        }
                    }
                    
                    function applyTemplate(templateName, settings) {
                        console.log('Applying template:', templateName, settings);
                        
                        // Show preview of changes
                        let previewHtml = '<div style="margin: 10px 0; padding: 10px; background: #f0f8ff; border: 1px solid #0066cc; border-radius: 5px;">';
                        previewHtml += `<h4>Template Preview: ${templateName}</h4>`;
                        previewHtml += '<p style="font-size: 12px; color: #666;">The following parameters will be updated:</p>';
                        
                        // Get current parameters for comparison
                        const currentParams = getCurrentDeviceParameters();
                        
                        for (const [paramName, value] of Object.entries(settings)) {
                            const currentValue = currentParams.metrics?.[paramName] || 'N/A';
                            const units = getParameterUnits(paramName);
                            previewHtml += `
                                <div style="margin: 5px 0; padding: 5px; background: white; border-radius: 3px;">
                                    <strong>${paramName}:</strong><br>
                                    <span style="color: #888; font-size: 11px;">Current: ${currentValue}${units}</span> → 
                                    <span style="color: #0066cc; font-weight: bold;">New: ${value}${units}</span>
                                </div>
                            `;
                        }
                        
                        previewHtml += `
                            <div style="margin-top: 10px;">
                                <button type="button" class="button" onclick="confirmApplyTemplate('${templateName}', ${JSON.stringify(settings)})" style="background: #0066cc; color: white;">
                                    Apply Template
                                </button>
                                <button type="button" class="button" onclick="closePreview()" style="background: #666; color: white; margin-left: 10px;">
                                    Cancel
                                </button>
                            </div>
                        </div>`;
                        
                        // Show preview modal
                        showPreviewModal(previewHtml);
                    }
                    
                    function confirmApplyTemplate(templateName, settings) {
                        // Fill form fields with template values
                        for (const [paramName, value] of Object.entries(settings)) {
                            const input = document.querySelector(`input[name="${paramName}"], select[name="${paramName}"]`);
                            if (input) {
                                input.value = value;
                            }
                        }
                        
                        // Close preview and show success message
                        closePreview();
                        showMessage(`Template "${templateName}" applied to form. Review and click "Apply Configuration" to save.`, 'info');
                    }
                    
                    function showPreviewModal(content) {
                        const modalHtml = `
                            <div id="preview-modal" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 2000;">
                                <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); background: white; padding: 20px; border-radius: 5px; max-width: 600px; max-height: 80vh; overflow-y: auto;">
                                    ${content}
                                </div>
                            </div>
                        `;
                        document.body.insertAdjacentHTML('beforeend', modalHtml);
                    }
                    
                    function closePreview() {
                        const modal = document.getElementById('preview-modal');
                        if (modal) {
                            modal.remove();
                        }
                    }
                    
                    function getCurrentDeviceParameters() {
                        // Get current parameters from the current configuration
                        const deviceId = document.querySelector('#config-modal h3').textContent.split(': ')[1];
                        return fetch(`/api/devices/${deviceId}/current-configuration`)
                            .then(response => response.json())
                            .catch(error => {
                                console.error('Error getting current parameters:', error);
                                return { metrics: {} };
                            });
                    }
                    
                    function getParameterUnits(paramName) {
                        // Extract units from parameter name or return empty string
                        if (paramName.includes('Current')) return ' A';
                        if (paramName.includes('Voltage')) return ' V';
                        if (paramName.includes('Power')) return ' W';
                        if (paramName.includes('Temperature')) return ' °C';
                        if (paramName.includes('Delay')) return ' ms';
                        if (paramName.includes('Pickup')) return ' A';
                        if (paramName.includes('Interval')) return ' ms';
                        if (paramName.includes('Hours')) return ' hours';
                        return '';
                    }
                    
                    function showMessage(message, type = 'info') {
                        const messageHtml = `
                            <div id="message" style="position: fixed; top: 20px; right: 20px; padding: 10px 20px; border-radius: 5px; z-index: 3000; background: ${type === 'info' ? '#0066cc' : '#cc0000'}; color: white;">
                                ${message}
                            </div>
                        `;
                        document.body.insertAdjacentHTML('beforeend', messageHtml);
                        
                        // Remove message after 3 seconds
                        setTimeout(() => {
                            const messageEl = document.getElementById('message');
                            if (messageEl) {
                                messageEl.remove();
                            }
                        }, 3000);
                    }
                    
                    // Add form submission handler
                    document.addEventListener('DOMContentLoaded', function() {
                        document.addEventListener('submit', function(e) {
                            if (e.target.id === 'config-form') {
                                e.preventDefault();
                                handleConfigurationSubmit(e.target);
                            }
                        });
                    });
                    
                    async function handleConfigurationSubmit(form) {
                        const deviceId = document.querySelector('#config-modal h3').textContent.split(': ')[1];
                        const formData = new FormData(form);
                        const configuration = {};
                        
                        // Collect form data
                        for (const [key, value] of formData.entries()) {
                            if (value !== '') {
                                // Convert string values to appropriate types
                                if (value === 'true') {
                                    configuration[key] = true;
                                } else if (value === 'false') {
                                    configuration[key] = false;
                                } else if (!isNaN(value) && value.includes('.')) {
                                    configuration[key] = parseFloat(value);
                                } else if (!isNaN(value)) {
                                    configuration[key] = parseInt(value);
                                } else {
                                    configuration[key] = value;
                                }
                            }
                        }
                        
                        try {
                            const response = await fetch(`/api/devices/${deviceId}/configure`, {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json',
                                },
                                body: JSON.stringify(configuration)
                            });
                            
                            if (response.ok) {
                                showMessage('Configuration applied successfully!', 'info');
                                closeModal();
                                // Refresh device list to show updated values
                                setTimeout(() => {
                                    location.reload();
                                }, 1000);
                            } else {
                                const error = await response.json();
                                showMessage(`Error applying configuration: ${error.error || 'Unknown error'}`, 'error');
                            }
                        } catch (error) {
                            console.error('Error submitting configuration:', error);
                            showMessage('Error applying configuration', 'error');
                        }
                    }
                    
                    async function viewParameters(deviceId) {
                        try {
                            const response = await fetch(`/api/devices/${deviceId}/parameters`);
                            const parameters = await response.json();
                            
                            // Display parameters in a modal
                            const modalHtml = createParametersModal(deviceId, parameters);
                            document.body.insertAdjacentHTML('beforeend', modalHtml);
                        } catch (error) {
                            console.error('Error getting device parameters:', error);
                        }
                    }
                    
                    function createConfigurationDialog(deviceId, parameters) {
                        return `
                            <div id="config-modal" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000;">
                                <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); background: white; padding: 20px; border-radius: 5px; max-width: 600px; max-height: 80vh; overflow-y: auto;">
                                    <h3>Configure Device: ${deviceId}</h3>
                                    <form id="config-form">
                                        ${createConfigurationForm(parameters)}
                                        <div style="margin-top: 20px;">
                                            <button type="button" class="button" onclick="closeModal()">Cancel</button>
                                        </div>
                                    </form>
                                </div>
                            </div>
                        `;
                    }
                    
                    function createConfigurationForm(parameters) {
                        let html = '';
                        if (parameters.configurable_parameters) {
                            parameters.configurable_parameters.forEach(paramName => {
                                const paramInfo = parameters.capabilities?.[paramName];
                                if (paramInfo) {
                                    html += `
                                        <div style="margin: 10px 0;">
                                            <label><strong>${paramName.replace(/_/g, ' ').toUpperCase()}:</strong></label><br>
                                            ${createInputField(paramName, paramInfo)}
                                        </div>
                                    `;
                                }
                            });
                        }
                        return html;
                    }
                    
                    function createParametersModal(deviceId, parameters) {
                        let html = `
                            <div id="params-modal" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000;">
                                <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); background: white; padding: 20px; border-radius: 5px; max-width: 800px; max-height: 80vh; overflow-y: auto;">
                                    <h3>Device Parameters: ${deviceId}</h3>
                                    <table style="width: 100%; border-collapse: collapse;">
                                        <tr style="background: #f0f0f0;">
                                            <th style="border: 1px solid #ddd; padding: 8px;">Parameter</th>
                                            <th style="border: 1px solid #ddd; padding: 8px;">Type</th>
                                            <th style="border: 1px solid #ddd; padding: 8px;">Value</th>
                                            <th style="border: 1px solid #ddd; padding: 8px;">Details</th>
                                        </tr>
                        `;
                        
                        if (parameters.capabilities) {
                            for (const [paramName, paramInfo] of Object.entries(parameters.capabilities)) {
                                const value = parameters.metrics?.[paramName] || 'N/A';
                                const details = [];
                                if (paramInfo.units) details.push(`Units: ${paramInfo.units}`);
                                if (paramInfo.range) details.push(`Range: ${paramInfo.range}`);
                                if (paramInfo.values) details.push(`Values: ${paramInfo.values.join(', ')}`);
                                
                                html += `
                                    <tr>
                                        <td style="border: 1px solid #ddd; padding: 8px;">${paramName.replace(/_/g, ' ')}</td>
                                        <td style="border: 1px solid #ddd; padding: 8px;">${paramInfo.type}</td>
                                        <td style="border: 1px solid #ddd; padding: 8px;">${value}</td>
                                        <td style="border: 1px solid #ddd; padding: 8px;">${details.join(' | ')}</td>
                                    </tr>
                                `;
                            }
                        }
                        
                        html += `
                                    </table>
                                    <div style="margin-top: 20px;">
                                        <button class="button" onclick="closeModal()">Close</button>
                                    </div>
                                </div>
                            </div>
                        `;
                        
                        return html;
                    }
                    
                    function closeModal() {
                        const modals = document.querySelectorAll('#config-modal, #params-modal');
                        modals.forEach(modal => modal.remove());
                    }
                    
                    // Auto-refresh every 5 seconds
                    setInterval(refreshDevices, 5000);

                    
                    

                </script>
            </body>
            </html>
            """
        
        @self.app.get("/api/devices/discover")
        async def discover_devices():
            """Discover devices via OPC UA"""
            try:
                await self._ensure_opcua_connection()
                
                # Get the FDI object directly by node ID
                fdi_obj = self.opcua_client.get_node("ns=2;i=1")
                logger.info(f"Found FDI object: {fdi_obj}")
                
                if fdi_obj is None:
                    logger.error("FDI object not found")
                    return []
                
                # Find the DiscoverDevices method directly under FDI object
                fdi_children = await fdi_obj.get_children()
                logger.info(f"FDI object children: {[await child.read_browse_name() for child in fdi_children]}")
                
                discover_method = None
                for child in fdi_children:
                    browse_name = await child.read_browse_name()
                    if browse_name.Name == "DiscoverDevices":
                        discover_method = child
                        break
                
                if discover_method is None:
                    logger.error("DiscoverDevices method not found")
                    return []
                
                # Call the method
                result = await discover_method.call_method(discover_method.nodeid)
                devices = json.loads(result)
                self.devices = {device['device_id']: device for device in devices}
                
                logger.info("Devices discovered", device_count=len(devices))
                return devices
                
            except Exception as e:
                logger.error("Error discovering devices", error=str(e))
                import traceback
                logger.error("Discovery traceback", traceback=traceback.format_exc())
                return []
        
        @self.app.get("/api/devices")
        async def get_devices():
            """Get current devices"""
            return list(self.devices.values())
        
        @self.app.get("/api/devices/{device_id}/parameters")
        async def get_device_parameters(device_id: str):
            """Get device parameters via OPC UA"""
            try:
                logger.info("Getting device parameters", device_id=device_id)

                await self._ensure_opcua_connection()
                
                # Get the GetDeviceParameters method directly under FDI object
                fdi_obj = self.opcua_client.get_node("ns=2;i=1")
                get_params_method = None
                
                fdi_children = await fdi_obj.get_children()
                for child in fdi_children:
                    browse_name = await child.read_browse_name()
                    if browse_name.Name == "GetDeviceParameters":
                        get_params_method = child
                        break
                
                if get_params_method is None:
                    logger.error("GetDeviceParameters method not found")
                    return {"device_id": device_id, "metrics": {}, "capabilities": {}}
                
                # Call the method
                result = await get_params_method.call_method(get_params_method.nodeid, device_id)
                
                if result:
                    logger.info("Retrieved device parameters via OPC UA", device_id=device_id)
                    # Parse the JSON string returned from OPC UA
                    if isinstance(result, str):
                        return json.loads(result)
                    else:
                        return result
                else:
                    logger.warning("No device parameters returned from OPC UA", device_id=device_id)
                    return {"device_id": device_id, "metrics": {}, "capabilities": {}}

            except Exception as e:
                logger.error("Error getting device parameters", device_id=device_id, error=str(e))
                return {"device_id": device_id, "metrics": {}, "capabilities": {}}
        
        @self.app.post("/api/devices/{device_id}/configure")
        async def configure_device(device_id: str, configuration: Dict[str, Any]):
            """Configure device via OPC UA"""
            try:
                await self._ensure_opcua_connection()
                
                # Get the SetDeviceParameters method directly under FDI object (same approach as GetDeviceParameters)
                fdi_obj = self.opcua_client.get_node("ns=2;i=1")
                set_params_method = None
                
                fdi_children = await fdi_obj.get_children()
                for child in fdi_children:
                    browse_name = await child.read_browse_name()
                    if browse_name.Name == "SetDeviceParameters":
                        set_params_method = child
                        break
                
                if set_params_method is None:
                    logger.error("SetDeviceParameters method not found")
                    raise HTTPException(status_code=500, detail="SetDeviceParameters method not found")
                
                # Call the method
                result = await set_params_method.call_method(set_params_method.nodeid, device_id, json.dumps(configuration))
                
                logger.info("Device configured", device_id=device_id, configuration=configuration)
                return {"message": "Device configured successfully"}
                
            except Exception as e:
                logger.error("Error configuring device", device_id=device_id, error=str(e))
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/devices/{device_id}/command")
        async def send_device_command(device_id: str, command: Dict[str, Any]):
            """Send command to device via OPC UA"""
            try:
                await self._ensure_opcua_connection()
                
                command_name = command.get('command', '')
                parameters = command.get('parameters', {})
                
                # Special handling for get_configuration command
                if command_name == 'get_configuration':
                    # Get the GetDeviceParameters method to retrieve current configuration
                    fdi_obj = self.opcua_client.get_node("ns=2;i=1")
                    get_params_method = None
                    
                    fdi_children = await fdi_obj.get_children()
                    for child in fdi_children:
                        browse_name = await child.read_browse_name()
                        if browse_name.Name == "GetDeviceParameters":
                            get_params_method = child
                            break
                    
                    if get_params_method is None:
                        logger.error("GetDeviceParameters method not found")
                        raise HTTPException(status_code=500, detail="GetDeviceParameters method not found")
                    
                    # Call the method to get current device data (same as get_parameters)
                    result = await get_params_method.call_method(get_params_method.nodeid, device_id)
                    
                    if result:
                        logger.info("Retrieved device parameters for configuration", device_id=device_id)
                        # Parse the JSON string returned from OPC UA
                        if isinstance(result, str):
                            return json.loads(result)
                        else:
                            return result
                    else:
                        logger.warning("No device parameters returned", device_id=device_id)
                        return {"device_id": device_id, "metrics": {}, "capabilities": {}}
                
                # For other commands, send via OPC UA
                fdi_obj = self.opcua_client.get_node("ns=2;i=1")
                send_command_method = None
                
                fdi_children = await fdi_obj.get_children()
                for child in fdi_children:
                    browse_name = await child.read_browse_name()
                    if browse_name.Name == "SendDeviceCommand":
                        send_command_method = child
                        break
                
                if send_command_method is None:
                    logger.error("SendDeviceCommand method not found")
                    raise HTTPException(status_code=500, detail="SendDeviceCommand method not found")
                
                # Call the method
                result = await send_command_method.call_method(
                    send_command_method.nodeid,
                    device_id, 
                    command_name, 
                    json.dumps(parameters)
                )
                
                logger.info("Device command sent", device_id=device_id, command=command)
                return {"message": "Command sent successfully"}
                
            except Exception as e:
                logger.error("Error sending device command", device_id=device_id, error=str(e))
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/devices/{device_id}/writable-parameters")
        async def get_writable_parameters(device_id: str):
            """Get writable parameters and templates from FDI definition"""
            try:
                await self._ensure_opcua_connection()
                
                # Get the FDI object and call the get writable parameters method
                fdi_obj = self.opcua_client.get_node("ns=2;i=1")
                get_writable_method = None
                
                fdi_children = await fdi_obj.get_children()
                for child in fdi_children:
                    browse_name = await child.read_browse_name()
                    if browse_name.Name == "GetWritableParameters":
                        get_writable_method = child
                        break
                
                if get_writable_method is None:
                    # Call the FDI server's parse_fdi_writable_parameters method
                    # This will parse the actual FDI definition file
                    parse_method = None
                    for child in fdi_children:
                        browse_name = await child.read_browse_name()
                        if browse_name.Name == "ParseFDIWritableParameters":
                            parse_method = child
                            break
                    
                    if parse_method:
                        result = await parse_method.call_method(parse_method.nodeid, "SmartCircuitBreaker")
                        if result:
                            return json.loads(result)
                    
                    # If no method exists, return empty (FDI server should provide this)
                    return {"functions": {}, "commands": {}, "templates": {}}
                
                # Call the method if it exists
                result = await get_writable_method.call_method(get_writable_method.nodeid, device_id)
                
                if result:
                    return json.loads(result)
                else:
                    return {"functions": {}, "commands": {}, "templates": {}}
                    
            except Exception as e:
                logger.error("Error getting writable parameters", device_id=device_id, error=str(e))
                return {"functions": {}, "commands": {}, "templates": {}}
        
        @self.app.get("/api/devices/{device_id}/current-configuration")
        async def get_current_configuration(device_id: str):
            """Get current device configuration using device parameters"""
            try:
                # Ensure OPC UA connection
                await self._ensure_opcua_connection()
                
                # Get the GetDeviceParameters method
                fdi_obj = self.opcua_client.get_node("ns=2;i=1")
                get_params_method = None
                fdi_children = await fdi_obj.get_children()
                for child in fdi_children:
                    browse_name = await child.read_browse_name()
                    if browse_name.Name == "GetDeviceParameters":
                        get_params_method = child
                        break
                
                if get_params_method is None:
                    logger.error("GetDeviceParameters method not found")
                    return {"error": "GetDeviceParameters method not found"}
                
                # Call the method
                result = await get_params_method.call_method(get_params_method.nodeid, device_id)
                
                if result:
                    logger.info("Retrieved device parameters via OPC UA", device_id=device_id)
                    # Parse the JSON string returned from OPC UA
                    if isinstance(result, str):
                        return json.loads(result)
                    else:
                        return result
                else:
                    logger.warning("No device parameters returned from OPC UA", device_id=device_id)
                    return {"device_id": device_id, "metrics": {}, "capabilities": {}}
                    
            except Exception as e:
                logger.error(f"Error getting current configuration: {e}")
                return {"error": str(e)}
    
    async def _ensure_opcua_connection(self):
        """Ensure OPC UA connection is established"""
        if self.opcua_client is None:
            await self._connect_opcua()
        else:
            # Check if connection is still alive
            try:
                # Try a simple operation to test connection
                root = self.opcua_client.get_root_node()
                await root.get_children()
            except Exception as e:
                logger.warning("OPC UA connection lost, reconnecting", error=str(e))
                await self._connect_opcua()
    
    async def _connect_opcua(self):
        """Connect to OPC UA server"""
        try:
            # Disconnect existing client if any
            if self.opcua_client:
                try:
                    await self.opcua_client.disconnect()
                except:
                    pass
                self.opcua_client = None
            
            logger.info("Attempting to connect to OPC UA server", url=self.opcua_server_url)
            self.opcua_client = Client(self.opcua_server_url)
            await self.opcua_client.connect()
            logger.info("Connected to OPC UA server", url=self.opcua_server_url)
            
        except Exception as e:
            logger.error("Failed to connect to OPC UA server", error=str(e), url=self.opcua_server_url)
            import traceback
            logger.error("Connection traceback", traceback=traceback.format_exc())
            raise
    
    async def start(self, host: str = "0.0.0.0", port: int = 8080):
        """Start the web server"""
        try:
            config = uvicorn.Config(self.app, host=host, port=port, log_level="info")
            server = uvicorn.Server(config)
            
            logger.info("Starting FDI Host Simulator", host=host, port=port)
            await server.serve()
            
        except Exception as e:
            logger.error("Failed to start web server", error=str(e))
            raise
    
    async def stop(self):
        """Stop the web server"""
        try:
            if self.opcua_client:
                await self.opcua_client.disconnect()
            
            logger.info("FDI Host Simulator stopped")
            
        except Exception as e:
            logger.error("Error stopping web server", error=str(e))

async def main():
    """Main function"""
    try:
        # Create FDI Host Simulator
        simulator = FDIHostSimulator()
        
        # Start web server
        await simulator.start()
        
    except KeyboardInterrupt:
        print("Shutting down...")
    except Exception as e:
        logger.error("Error in main", error=str(e))
    finally:
        if 'simulator' in locals():
            await simulator.stop()

if __name__ == "__main__":
    asyncio.run(main()) 
