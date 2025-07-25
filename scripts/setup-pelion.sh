#!/bin/bash
# Setup Pelion API Key
# This script helps you configure your Pelion API key

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Check if config.env exists
if [ ! -f "../config.env" ] && [ ! -f "config.env" ]; then
    print_error "config.env file not found!"
    exit 1
fi

CONFIG_FILE=""
if [ -f "../config.env" ]; then
    CONFIG_FILE="../config.env"
elif [ -f "config.env" ]; then
    CONFIG_FILE="config.env"
fi

print_status "Setting up Pelion API Key..."
echo ""
echo "To get your Pelion API Key:"
echo "1. Go to https://portal.mbedcloud.com/"
echo "2. Log in to your account"
echo "3. Navigate to Access Management → API Keys"
echo "4. Create a new API key"
echo ""

# Prompt for API key
read -p "Enter your Pelion API Key: " PELION_API_KEY

if [ -z "$PELION_API_KEY" ]; then
    print_error "API key cannot be empty!"
    exit 1
fi

# Update the config file
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' "s/PELION_API_KEY=.*/PELION_API_KEY=$PELION_API_KEY/" "$CONFIG_FILE"
else
    # Linux
    sed -i "s/PELION_API_KEY=.*/PELION_API_KEY=$PELION_API_KEY/" "$CONFIG_FILE"
fi

print_success "Pelion API Key configured successfully!"
print_status "You can now run: ./scripts/deploy-redpanda-connector.sh" 