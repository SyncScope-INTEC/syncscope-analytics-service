# Multi-stage build for SyncScope Analytics Service
FROM python:3.13-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies required for building Python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Production stage
FROM python:3.13-slim as production

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Create non-root user for security
RUN groupadd -r analytics && \
    useradd -r -g analytics -d /app -s /bin/bash analytics && \
    mkdir -p /app /app/logs /app/static /app/media && \
    chown -R analytics:analytics /app

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=analytics:analytics . .

# Make start script executable and create necessary directories
RUN chmod +x start.sh && \
    mkdir -p /app/logs /app/static /app/media && \
    chown -R analytics:analytics /app

# Switch to non-root user
USER analytics

# Collect static files
RUN python manage.py collectstatic --noinput --clear

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/health/ || exit 1

# Expose port
EXPOSE 8080

# Default command - use start.sh script
CMD ["./start.sh"]

# Development stage (optional)
FROM production as development

# Switch back to root to install development dependencies
USER root

# Install development tools
RUN apt-get update && apt-get install -y \
    git \
    vim \
    postgresql-client \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

# Install development Python packages
COPY requirements-dev.txt* ./
RUN if [ -f requirements-dev.txt ]; then pip install -r requirements-dev.txt; fi

# Switch back to analytics user
USER analytics

# Override default command for development
CMD ["python", "manage.py", "runserver", "0.0.0.0:8080"]