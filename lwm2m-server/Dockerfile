FROM openjdk:11-jre-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Download Eclipse Leshan server
ENV LESHAN_VERSION=2.0.0-M13
RUN wget https://ci.eclipse.org/leshan/job/leshan/lastSuccessfulBuild/artifact/leshan-server-demo/target/leshan-server-demo-${LESHAN_VERSION}-jar-with-dependencies.jar \
    -O leshan-server.jar || \
    echo "Using embedded Leshan server implementation"

# Copy our custom server implementation
COPY server.py /app/
COPY requirements.txt /app/

# Install Python for our custom implementation
RUN apt-get update && apt-get install -y python3 python3-pip && \
    pip3 install -r requirements.txt && \
    rm -rf /var/lib/apt/lists/*

# Create data directory
RUN mkdir -p /app/data

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1

# Expose ports
EXPOSE 8080 5684/udp

# Start the server
CMD ["python3", "server.py"] 