#!/bin/bash

echo "🚀 Setting up FDI Local Environment"
echo "=================================================="

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is not available. Please install pip."
    exit 1
fi

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment and install dependencies
echo "📦 Installing dependencies..."
source venv/bin/activate
pip install -r requirements.txt

# Install protobuf compiler if not available
if ! command -v protoc &> /dev/null; then
    echo "📦 Installing protobuf compiler..."
    if command -v brew &> /dev/null; then
        brew install protobuf
    else
        echo "⚠️  protoc not found. Please install protobuf compiler manually:"
        echo "   macOS: brew install protobuf"
        echo "   Ubuntu: sudo apt-get install protobuf-compiler"
        echo "   Windows: Download from https://github.com/protocolbuffers/protobuf/releases"
    fi
fi

# Generate protobuf files
echo "🔧 Generating protobuf files..."
cd simulators/proto
protoc --python_out=. sparkplug_b.proto

# Fix protobuf compatibility issues
echo "🔧 Fixing protobuf compatibility..."
python3 -c "
import re
with open('sparkplug_b_pb2.py', 'r') as f:
    content = f.read()

# Remove runtime_version import and validation
content = re.sub(r'from google\.protobuf import runtime_version as _runtime_version\n', '', content)
content = re.sub(r'_runtime_version\.ValidateProtobufRuntimeVersion\([^)]*\)\n', '', content)

with open('sparkplug_b_pb2.py', 'w') as f:
    f.write(content)
print('Protobuf files fixed successfully!')
"

cd ../..

# Create logs directory
mkdir -p logs

echo ""
echo "✅ Setup completed successfully!"
echo ""
echo "To start the FDI environment:"
echo "   ./start.sh"
echo ""
echo "To stop the FDI environment:"
echo "   ./stop.sh"
echo ""
echo "Web UI will be available at: http://localhost:8080" 