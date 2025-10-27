# WARD FLUX - Production Docker Image
# Multi-stage build for minimal image size

# Stage 1: Build React Frontend
FROM node:20-alpine as frontend-builder

WORKDIR /frontend

# Copy frontend package files
COPY frontend/package*.json ./

# Install frontend dependencies
RUN npm ci --prefer-offline --no-audit --legacy-peer-deps

# Cache buster - this invalidates the cache when source changes
ARG CACHE_BUST=unknown
RUN echo "Cache bust: ${CACHE_BUST}"

# Copy frontend source
COPY frontend/ ./

# Build React app - force clean build
RUN rm -rf dist .vite node_modules/.vite && \
    npm run build

# Stage 2: Build Python Dependencies
FROM python:3.11-slim as python-builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    libsnmp-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 3: Production Image
FROM python:3.11-slim

# Create non-root user
RUN useradd -m -u 1000 ward && \
    mkdir -p /app /data /logs && \
    chown -R ward:ward /app /data /logs

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    libpq5 \
    libsnmp40 \
    snmp \
    curl \
    iputils-ping \
    mtr-tiny \
    traceroute \
    && rm -rf /var/lib/apt/lists/* \
    && chmod u+s /usr/bin/traceroute.db

# Copy entrypoint script
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh && chown ward:ward /app/docker-entrypoint.sh

# Copy Python packages from builder
COPY --from=python-builder /root/.local /home/ward/.local

# Copy application code FIRST
COPY --chown=ward:ward . .

# Remove the frontend source directory to prevent confusion
# (it's already built and will be served from static_new)
RUN rm -rf /app/frontend

# Copy built frontend from frontend-builder AFTER (overwrites empty frontend/dist)
# This ensures the built assets are not overwritten by the source directory
COPY --from=frontend-builder --chown=ward:ward /frontend/dist /app/static_new

# Set environment variables
ENV PATH=/home/ward/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DATABASE_PATH=/data/ward_flux.db \
    REDIS_URL=redis://redis:6379/0 \
    VICTORIA_URL=http://victoriametrics:8428

# Switch to non-root user
USER ward

# Expose port
EXPOSE 5001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5001/api/v1/health || exit 1

# Default command
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5001"]
