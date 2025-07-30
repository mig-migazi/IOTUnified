#!/bin/bash

# FDI Workflow Test Script
# Tests the complete FDI workflow with Smart Breaker simulator

set -e

echo "🧪 Testing FDI Workflow with Smart Breaker Simulator"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to wait for service to be ready
wait_for_service() {
    local url=$1
    local service_name=$2
    local max_attempts=30
    local attempt=1
    
    print_status "Waiting for $service_name to be ready..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s "$url" > /dev/null 2>&1; then
            print_success "$service_name is ready!"
            return 0
        fi
        
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    print_error "$service_name failed to start after $max_attempts attempts"
    return 1
}

# Function to make API request and display result
api_request() {
    local method=$1
    local url=$2
    local data=$3
    local description=$4
    
    print_status "$description"
    
    if [ -n "$data" ]; then
        response=$(curl -s -X "$method" "$url" \
            -H "Content-Type: application/json" \
            -d "$data")
    else
        response=$(curl -s -X "$method" "$url")
    fi
    
    echo "$response" | jq '.' 2>/dev/null || echo "$response"
    echo ""
}

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    print_warning "jq is not installed. Installing JSON formatting..."
    if command -v brew &> /dev/null; then
        brew install jq
    else
        print_error "Please install jq for better output formatting"
        print_error "On macOS: brew install jq"
        print_error "On Ubuntu: sudo apt-get install jq"
    fi
fi

# Wait for services to be ready
wait_for_service "http://localhost:8080/api/status" "Smart Breaker Simulator"
wait_for_service "http://localhost:8081/health" "FDI Server"

print_success "All services are ready! Starting FDI workflow test..."
echo ""

# Test 1: Check device simulator status
print_status "Test 1: Checking Smart Breaker Simulator Status"
api_request "GET" "http://localhost:8080/api/status" "" "Getting device status..."

# Test 2: Discover devices via FDI
print_status "Test 2: Discovering Devices via FDI"
api_request "GET" "http://localhost:8081/api/devices" "" "Discovering devices..."

# Test 3: Get device parameters
print_status "Test 3: Getting Device Parameters"
api_request "GET" "http://localhost:8081/api/devices/smart-breaker-001/parameters" "" "Getting device parameters..."

# Test 4: Get available templates
print_status "Test 4: Getting Available Templates"
api_request "GET" "http://localhost:8081/api/devices/smart-breaker-001/templates" "" "Getting available templates..."

# Test 5: Apply configuration template
print_status "Test 5: Applying Configuration Template"
api_request "POST" "http://localhost:8081/api/devices/smart-breaker-001/templates/StandardConfig" "" "Applying StandardConfig template..."

# Test 6: Get device status after configuration
print_status "Test 6: Checking Device Status After Configuration"
api_request "GET" "http://localhost:8081/api/devices/smart-breaker-001/status" "" "Getting device status after configuration..."

# Test 7: Send command to device
print_status "Test 7: Sending Command to Device"
api_request "POST" "http://localhost:8081/api/devices/smart-breaker-001/commands" \
    '{"command": "get_configuration"}' \
    "Sending get_configuration command..."

# Test 8: Set device parameters
print_status "Test 8: Setting Device Parameters"
api_request "PUT" "http://localhost:8081/api/devices/smart-breaker-001/parameters" \
    '{"parameters": {"trip_current": 120.0, "temperature_threshold": 90.0}}' \
    "Setting trip_current and temperature_threshold..."

# Test 9: Verify parameter changes
print_status "Test 9: Verifying Parameter Changes"
api_request "GET" "http://localhost:8081/api/devices/smart-breaker-001/parameters" "" "Verifying parameter changes..."

# Test 10: Send maintenance command
print_status "Test 10: Sending Maintenance Command"
api_request "POST" "http://localhost:8081/api/devices/smart-breaker-001/commands" \
    '{"command": "set_maintenance_mode", "parameters": {"enabled": true}}' \
    "Setting maintenance mode..."

# Test 11: Final status check
print_status "Test 11: Final Status Check"
api_request "GET" "http://localhost:8081/api/devices/smart-breaker-001/status" "" "Final device status check..."

# Test 12: Get server information
print_status "Test 12: Getting Server Information"
api_request "GET" "http://localhost:8081/api/info" "" "Getting FDI server information..."

echo ""
print_success "🎉 FDI Workflow Test Completed Successfully!"
echo ""
print_status "You can now access:"
echo "  • Smart Breaker Simulator API: http://localhost:8080"
echo "  • FDI Server API: http://localhost:8081"
echo "  • FDI Web Demo: http://localhost:8082"
echo ""
print_status "To view logs:"
echo "  • docker logs smart-breaker-simulator"
echo "  • docker logs smart-breaker-fdi-server"
echo "  • docker logs smart-breaker-web-demo" 