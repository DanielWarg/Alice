# Alice AI Assistant - Enhanced Production Docker Image
# Multi-stage build with comprehensive production optimization

# =============================================================================
# Builder Stage - Install dependencies and build assets
# =============================================================================
FROM python:3.11-slim as builder

# Metadata
LABEL maintainer="Alice AI Team"
LABEL version="1.0.0"
LABEL description="Alice AI Assistant Production Backend"

# Build arguments
ARG INSTALL_DEV_DEPS=false
ARG PYTHON_VERSION=3.11
ARG BUILD_DATE
ARG VCS_REF

# Environment variables for build optimization
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_CACHE_DIR=/opt/poetry_cache \
    POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=1 \
    PATH="/opt/venv/bin:$PATH"

# Install system dependencies for building
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    pkg-config \
    libffi-dev \
    libssl-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv

# Copy dependency files
WORKDIR /build
COPY server/requirements.txt server/requirements-dev.txt ./

# Install Python dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt && \
    if [ "$INSTALL_DEV_DEPS" = "true" ]; then pip install -r requirements-dev.txt; fi && \
    pip cache purge

# =============================================================================
# Production Stage - Optimized runtime environment
# =============================================================================
FROM python:3.11-slim as production

# Build metadata
ARG BUILD_DATE
ARG VCS_REF
LABEL org.opencontainers.image.created=$BUILD_DATE
LABEL org.opencontainers.image.revision=$VCS_REF
LABEL org.opencontainers.image.title="Alice AI Assistant"
LABEL org.opencontainers.image.description="Production-ready AI assistant with voice capabilities"

# Production environment variables with secure defaults
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PATH="/opt/venv/bin:$PATH" \
    \
    # Application configuration
    ALICE_ENV=production \
    ALICE_DEBUG=false \
    ALICE_LOG_LEVEL=INFO \
    ALICE_HOST=0.0.0.0 \
    ALICE_PORT=8000 \
    ALICE_WORKERS=4 \
    ALICE_WORKER_CLASS=uvicorn.workers.UvicornWorker \
    ALICE_WORKER_CONNECTIONS=1000 \
    ALICE_MAX_REQUESTS=1000 \
    ALICE_MAX_REQUESTS_JITTER=100 \
    ALICE_TIMEOUT=120 \
    ALICE_KEEPALIVE=5 \
    \
    # Database configuration
    DATABASE_URL=sqlite:///./data/alice.db \
    DATABASE_POOL_SIZE=5 \
    DATABASE_POOL_MAX_OVERFLOW=10 \
    DATABASE_POOL_TIMEOUT=30 \
    DATABASE_POOL_RECYCLE=3600 \
    \
    # Performance configuration
    TTS_CACHE_MAX_SIZE_MB=500 \
    TTS_CACHE_EXPIRY_HOURS=168 \
    VOICE_BUFFER_SIZE_MB=50 \
    PERFORMANCE_MONITORING_ENABLED=true \
    PERFORMANCE_MONITORING_INTERVAL=30 \
    \
    # Security configuration
    SECURE_COOKIES=true \
    CORS_ORIGINS=* \
    RATE_LIMIT_PER_MINUTE=60 \
    RATE_LIMIT_BURST=120 \
    \
    # B1/B2 System configuration
    AMBIENT_RAW_TTL_MIN=120 \
    BARGE_IN_SENSITIVITY=0.7 \
    ECHO_CANCELLATION_ENABLED=true \
    VOICE_ACTIVITY_THRESHOLD=0.02

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Runtime essentials
    curl \
    ca-certificates \
    tzdata \
    # Audio processing dependencies
    portaudio19-dev \
    pulseaudio \
    alsa-utils \
    # System monitoring
    procps \
    htop \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create application user with proper permissions
RUN groupadd -r alice && \
    useradd -r -g alice -d /app -s /bin/bash alice && \
    mkdir -p /app/data /app/logs /app/tmp /app/models && \
    chown -R alice:alice /app

# Copy virtual environment from builder
COPY --from=builder --chown=alice:alice /opt/venv /opt/venv

# Set working directory
WORKDIR /app

# Copy application code with proper permissions
COPY --chown=alice:alice server/ ./
COPY --chown=alice:alice docker/entrypoints/production-entrypoint.sh ./entrypoint.sh
COPY --chown=alice:alice docker/scripts/ ./scripts/

# Set executable permissions
RUN chmod +x ./entrypoint.sh && \
    chmod +x ./scripts/*.sh

# Create configuration directories
RUN mkdir -p /app/config /app/data/performance_profiles /app/data/soak_test_results && \
    chown -R alice:alice /app/config /app/data

# Switch to non-root user
USER alice

# Expose application port
EXPOSE 8000

# Volume mounts for persistent data
VOLUME ["/app/data", "/app/logs", "/app/models", "/app/config"]

# Health check with comprehensive status validation
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
    CMD ./scripts/health-check.sh || exit 1

# Startup probe for Kubernetes environments
LABEL healthcheck.startup.command="./scripts/startup-check.sh"
LABEL healthcheck.startup.interval="5s"
LABEL healthcheck.startup.timeout="3s"
LABEL healthcheck.startup.retries="30"

# Production entrypoint
ENTRYPOINT ["./entrypoint.sh"]
CMD ["production"]

# =============================================================================
# Development Stage - Extended with development tools
# =============================================================================
FROM production as development

# Development environment overrides
ENV ALICE_ENV=development \
    ALICE_DEBUG=true \
    ALICE_LOG_LEVEL=DEBUG \
    ALICE_RELOAD=true \
    PERFORMANCE_MONITORING_INTERVAL=10

# Switch back to root for development tool installation
USER root

# Install development dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Development tools
    vim \
    git \
    ssh \
    # Debugging tools
    gdb \
    strace \
    tcpdump \
    # Performance profiling
    linux-perf \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install development Python packages
COPY --from=builder /opt/venv /opt/venv
RUN pip install --no-cache-dir \
    debugpy \
    pytest-cov \
    black \
    flake8 \
    mypy

# Copy development configuration
COPY --chown=alice:alice docker/entrypoints/development-entrypoint.sh ./dev-entrypoint.sh
RUN chmod +x ./dev-entrypoint.sh

# Switch back to application user
USER alice

# Development command
CMD ["development"]

# =============================================================================
# Testing Stage - Optimized for CI/CD testing
# =============================================================================
FROM builder as testing

# Testing environment
ENV ALICE_ENV=testing \
    ALICE_DEBUG=false \
    ALICE_LOG_LEVEL=WARNING \
    DATABASE_URL=sqlite:///:memory: \
    TESTING=true

# Install testing dependencies
RUN pip install --no-cache-dir \
    pytest \
    pytest-asyncio \
    pytest-cov \
    pytest-xdist \
    coverage \
    factory-boy \
    faker

# Copy test configuration
WORKDIR /app
COPY --chown=alice:alice server/ ./
COPY --chown=alice:alice tests/ ./tests/
COPY --chown=alice:alice docker/entrypoints/testing-entrypoint.sh ./test-entrypoint.sh
RUN chmod +x ./test-entrypoint.sh

# Testing user
USER alice

# Testing command
CMD ["./test-entrypoint.sh"]