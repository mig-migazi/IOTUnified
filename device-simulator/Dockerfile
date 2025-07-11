FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    protobuf-compiler \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Generate protobuf bindings
RUN protoc --python_out=. proto/sparkplug_b.proto

# Create non-root user
RUN useradd -m -u 1000 device && chown -R device:device /app
USER device

# Default environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python health_check.py

# Run the device simulator
CMD ["python", "main.py"] 