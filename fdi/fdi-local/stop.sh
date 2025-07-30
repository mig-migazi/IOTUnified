#!/bin/bash

echo "🛑 Stopping FDI Local Environment"
echo "=================================================="

# Kill all FDI-related Python processes
pkill -f "test_opcua_only" 2>/dev/null
pkill -f "smart_breaker" 2>/dev/null
pkill -f "fdi_communication" 2>/dev/null
pkill -f "web_client" 2>/dev/null

echo "✅ All components stopped" 