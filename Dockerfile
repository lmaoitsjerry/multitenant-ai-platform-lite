# Multi-Tenant AI Platform - Production Dockerfile
# Security: Runs as non-root user (uid 1000) for production hardening

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for WeasyPrint and health checks (as root)
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user and group (uid/gid 1000)
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# Copy requirements first for better caching (install as root)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code with proper ownership
COPY --chown=appuser:appgroup . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Switch to non-root user
USER appuser

# Health check using curl (works without root privileges)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run the application
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT}
