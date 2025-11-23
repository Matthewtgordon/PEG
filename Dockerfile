# APEG System Dockerfile
# Multi-stage build for production deployment
# Optimized for Raspberry Pi and small Linux servers

FROM python:3.11-slim AS base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    APEG_TEST_MODE=true \
    APEG_HOST=0.0.0.0 \
    APEG_PORT=8000

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY config/ ./config/
COPY webui/ ./webui/
COPY *.json ./

# Create non-root user for security
RUN useradd -m -u 1000 apeg && \
    chown -R apeg:apeg /app

# Create logs directory
RUN mkdir -p /app/logs && chown apeg:apeg /app/logs

USER apeg

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Set Python path
ENV PYTHONPATH=/app/src

# Run application
CMD ["python", "-m", "uvicorn", "apeg_core.server:app", "--host", "0.0.0.0", "--port", "8000"]
