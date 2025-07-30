FROM python:3.11-slim

# Install system dependencies for numpy compilation
RUN apt-get update && apt-get install -y \
    build-essential \
    protobuf-compiler \
    libblas-dev \
    liblapack-dev \
    libatlas-base-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY device-simulators/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY device-simulators/ .

# Copy protobuf file from parent directory
COPY proto/sparkplug_b.proto shared/proto/

# Generate protobuf bindings
RUN protoc --python_out=. shared/proto/sparkplug_b.proto

# Create non-root user
RUN useradd -m -u 1000 device && chown -R device:device /app
USER device

# Default environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python shared/health_check.py

# Run the device simulator
CMD ["python", "shared/main.py"] 