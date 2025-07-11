FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    protobuf-compiler \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Generate protobuf bindings and ensure they're accessible
RUN protoc --python_out=. proto/sparkplug_b.proto && \
    ls -la proto/ && \
    touch proto/__init__.py

# Create non-root user
RUN useradd -m -u 1000 sparkplug && chown -R sparkplug:sparkplug /app
USER sparkplug

# Environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8081/health || exit 1

# Expose metrics port
EXPOSE 8081

# Run the Sparkplug B host application
CMD ["python", "main.py"] 