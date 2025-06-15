# ComfyUI Model Resolver v2.0 - Docker Image
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY api/ ./api/
COPY frontend/ ./frontend/
COPY src/ ./src/
COPY data/ ./data/
COPY start.sh .
COPY .env.example .env

# Make start script executable
RUN chmod +x start.sh

# Create data directory
RUN mkdir -p data

# Expose ports
EXPOSE 5002 5001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5002/health || exit 1

# Default environment variables
ENV PYTHONUNBUFFERED=1
ENV COMFYUI_ROOT=/workspace/ComfyUI

# Start command
CMD ["./start.sh"]