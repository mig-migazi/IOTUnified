#!/bin/bash

echo "🚀 Starting FDI Local Environment"
echo "=================================================="

# Kill any existing processes
pkill -f "python3.*test_opcua_only" 2>/dev/null
pkill -f "python3.*smart_breaker" 2>/dev/null
pkill -f "python3.*fdi_communication" 2>/dev/null
pkill -f "python3.*web_client" 2>/dev/null

# Create logs directory
mkdir -p logs

# Start FDI Communication Server (includes OPC UA server)
echo "Starting FDI Communication Server..."
nohup ./venv/bin/python server/fdi_communication_server.py > logs/fdi_server.log 2>&1 &
sleep 3

# Start Smart Breaker Simulator (NEW VERSION)
echo "Starting Smart Breaker Simulator (NEW)..."
nohup ./venv/bin/python simulators/smart_breaker_simulator_new.py > logs/smart_breaker.log 2>&1 &
sleep 3



# Start Web UI
echo "Starting Web UI..."
nohup ./venv/bin/python server/web_client_fdi_host_simulator.py > logs/web_ui.log 2>&1 &
sleep 3

echo ""
echo "🎉 FDI Local Environment is running!"
echo "🌐 Web UI available at: http://localhost:8080"
echo "📊 Monitor MQTT messages: mosquitto_sub -t 'spBv1.0/#' -v"
echo "📁 Logs available in: logs/"
echo "🔍 View logs: tail -f logs/*.log"
echo ""
echo "To stop all components: ./stop.sh" 