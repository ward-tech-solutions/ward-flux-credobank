# ═══════════════════════════════════════════════════════════════════
# WARD TECH SOLUTIONS - Docker Configuration
# ═══════════════════════════════════════════════════════════════════

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Force rebuild of pip dependencies (cache buster)
ARG CACHEBUST=1

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies with --force-reinstall to bypass cache
RUN pip install --no-cache-dir --force-reinstall -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/data /app/logs /app/static /app/templates

# Initialize database tables (setup wizard will be shown on first run)
RUN python init_setup_db.py || true

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=5001
ENV SETUP_MODE=enabled

# Expose port
EXPOSE 5001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5001/api/v1/health')" || exit 0

# Run application
CMD ["python", "run.py"]
