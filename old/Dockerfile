# Alice Voice System - Production Docker Build
# Multi-stage build for optimized production deployment

# Backend Stage - Python/FastAPI
FROM python:3.11-slim-bullseye as backend

WORKDIR /app/server

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc g++ \
    libportaudio2 \
    portaudio19-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy Python requirements and install dependencies
COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY server/ .

# Frontend Stage - Node.js/Next.js
FROM node:18-alpine as frontend

WORKDIR /app/web

# Copy package files and install dependencies
COPY web/package*.json ./
RUN npm ci --only=production

# Copy frontend source and build
COPY web/ .
RUN npm run build

# Production Stage
FROM python:3.11-slim-bullseye as production

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libportaudio2 \
    ffmpeg \
    nginx \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Copy backend from backend stage
COPY --from=backend /app/server /app/server
COPY --from=backend /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=backend /usr/local/bin /usr/local/bin

# Copy frontend build from frontend stage
COPY --from=frontend /app/web/.next /app/web/.next
COPY --from=frontend /app/web/public /app/web/public
COPY --from=frontend /app/web/package.json /app/web/package.json
COPY --from=frontend /app/web/next.config.mjs /app/web/next.config.mjs
COPY --from=frontend /app/web/node_modules /app/web/node_modules

# Create necessary directories and users
RUN adduser --system --group alice && \
    mkdir -p /app/logs /app/data && \
    chown -R alice:alice /app

# Copy configuration files
COPY docker/nginx.conf /etc/nginx/nginx.conf
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Environment variables
ENV NODE_ENV=production
ENV PYTHON_ENV=production
ENV PORT=8000
ENV WEB_PORT=3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost/api/health || exit 1

# Expose ports
EXPOSE 80 443

# Start services with supervisor
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]