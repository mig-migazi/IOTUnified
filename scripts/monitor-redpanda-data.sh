#!/bin/bash

# Real-time Redpanda Data Flow Monitor
# This script monitors the MQTT-Redpanda bridge and data flow

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to print colored output
print_header() {
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}  Redpanda Data Flow Monitor${NC}"
    echo -e "${CYAN}========================================${NC}"
}

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

# Function to get current metrics
get_bridge_metrics() {
    local health_data=$(curl -s http://localhost:8087/health)
    local messages_bridged=$(echo $health_data | jq -r '.messages_bridged')
    local bridge_errors=$(echo $health_data | jq -r '.bridge_errors')
    local mqtt_connected=$(echo $health_data | jq -r '.mqtt_connected')
    local kafka_connected=$(echo $health_data | jq -r '.kafka_connected')
    
    echo "$messages_bridged|$bridge_errors|$mqtt_connected|$kafka_connected"
}

# Function to get topic message counts
get_topic_counts() {
    local sparkplug_data=$(docker exec iot-redpanda rpk topic describe iot.telemetry.sparkplug.data --format json 2>/dev/null | jq -r '.partitions[0].leader.high_watermark // 0')
    local lwm2m_reg=$(docker exec iot-redpanda rpk topic describe iot.telemetry.lwm2m.registration --format json 2>/dev/null | jq -r '.partitions[0].leader.high_watermark // 0')
    
    echo "$sparkplug_data|$lwm2m_reg"
}

# Function to display current status
display_status() {
    clear
    print_header
    
    # Get current metrics
    local metrics=$(get_bridge_metrics)
    local messages_bridged=$(echo $metrics | cut -d'|' -f1)
    local bridge_errors=$(echo $metrics | cut -d'|' -f2)
    local mqtt_connected=$(echo $metrics | cut -d'|' -f3)
    local kafka_connected=$(echo $metrics | cut -d'|' -f4)
    
    # Get topic counts
    local topic_counts=$(get_topic_counts)
    local sparkplug_count=$(echo $topic_counts | cut -d'|' -f1)
    local lwm2m_count=$(echo $topic_counts | cut -d'|' -f2)
    
    echo -e "${GREEN}📊 Bridge Status:${NC}"
    echo -e "  • Messages Bridged: ${CYAN}$messages_bridged${NC}"
    echo -e "  • Bridge Errors: ${YELLOW}$bridge_errors${NC}"
    echo -e "  • MQTT Connected: $([ "$mqtt_connected" = "true" ] && echo -e "${GREEN}✅${NC}" || echo -e "${RED}❌${NC}")"
    echo -e "  • Kafka Connected: $([ "$kafka_connected" = "true" ] && echo -e "${GREEN}✅${NC}" || echo -e "${RED}❌${NC}")"
    
    echo ""
    echo -e "${GREEN}📈 Topic Message Counts:${NC}"
    echo -e "  • Sparkplug B Data: ${CYAN}$sparkplug_count${NC}"
    echo -e "  • LwM2M Registration: ${CYAN}$lwm2m_count${NC}"
    
    echo ""
    echo -e "${GREEN}🔗 Service URLs:${NC}"
    echo -e "  • Grafana Dashboard: ${CYAN}http://localhost:3000${NC} (admin/admin)"
    echo -e "  • Bridge Health: ${CYAN}http://localhost:8087/health${NC}"
    echo -e "  • Bridge Metrics: ${CYAN}http://localhost:8087/metrics${NC}"
    
    echo ""
    echo -e "${GREEN}📋 Available Commands:${NC}"
    echo -e "  • ${CYAN}Press 'r'${NC} - Refresh data"
    echo -e "  • ${CYAN}Press 't'${NC} - Show recent messages"
    echo -e "  • ${CYAN}Press 'q'${NC} - Quit"
    echo ""
    echo -e "${YELLOW}Last updated: $(date '+%H:%M:%S')${NC}"
}

# Function to show recent messages
show_recent_messages() {
    echo ""
    echo -e "${CYAN}📨 Recent Sparkplug B Messages:${NC}"
    docker exec iot-redpanda rpk topic consume iot.telemetry.sparkplug.data --num 2 --format json 2>/dev/null | jq -r '.value' | head -2 || echo "No messages available"
    
    echo ""
    echo -e "${CYAN}📨 Recent LwM2M Messages:${NC}"
    docker exec iot-redpanda rpk topic consume iot.telemetry.lwm2m.registration --num 1 --format json 2>/dev/null | jq -r '.value' | head -1 || echo "No messages available"
    
    echo ""
    read -p "Press Enter to continue..."
}

# Main monitoring loop
main() {
    print_status "Starting Redpanda Data Flow Monitor..."
    print_status "Press 'q' to quit, 'r' to refresh, 't' to show recent messages"
    
    while true; do
        display_status
        
        # Read user input (non-blocking)
        if read -t 5 -n 1 key; then
            case $key in
                q|Q)
                    echo ""
                    print_status "Exiting monitor..."
                    exit 0
                    ;;
                r|R)
                    print_status "Refreshing data..."
                    ;;
                t|T)
                    show_recent_messages
                    ;;
            esac
        fi
        
        # Auto-refresh every 5 seconds
        sleep 5
    done
}

# Check if required tools are available
if ! command -v jq &> /dev/null; then
    print_error "jq is required but not installed. Please install jq and try again."
    exit 1
fi

if ! command -v curl &> /dev/null; then
    print_error "curl is required but not installed. Please install curl and try again."
    exit 1
fi

# Check if services are running
if ! curl -s http://localhost:8087/health > /dev/null 2>&1; then
    print_error "Bridge health endpoint is not accessible. Make sure the services are running."
    exit 1
fi

# Start monitoring
main 