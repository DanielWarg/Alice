# Alice Deployment Guide

Denna guide täcker deployment av Alice AI Assistant Platform för production, staging och development environments.

## Översikt

Alice är en multi-komponent applikation som kräver:
- Python backend (FastAPI)
- Node.js frontend (Next.js)
- NLU agent (Node.js/TypeScript)
- Lokal AI-modell (Ollama)
- Databas (SQLite för utveckling, PostgreSQL för production)

## Production Deployment

### Serverspecifikationer

**Minimum krav:**
- CPU: 4 kärnor, 3.0GHz+
- RAM: 8GB (16GB rekommenderat för AI-modeller)
- Storage: 50GB SSD (100GB för AI-modeller och data)
- OS: Ubuntu 22.04 LTS eller senare

**Rekommenderat för production:**
- CPU: 8 kärnor, 3.2GHz+
- RAM: 32GB
- Storage: 200GB NVMe SSD
- GPU: NVIDIA med 8GB+ VRAM (för optimal AI-prestanda)

### 1. Systemförberedelser

#### Uppdatera system
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl wget git build-essential software-properties-common
```

#### Installera Python 3.11+
```bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip
```

#### Installera Node.js 18+
```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
```

#### Installera Ollama
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

#### Systemd tjänster för auto-start
```bash
sudo systemctl enable ollama
sudo systemctl start ollama
```

### 2. Applikations-deployment

#### Skapa deployment-användare
```bash
sudo adduser alice
sudo usermod -aG sudo alice
sudo su - alice
```

#### Klona och sätt upp applikationen
```bash
# Klona repository
git clone <your-repo-url> /home/alice/app
cd /home/alice/app

# Backend setup
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r server/requirements.txt

# Frontend setup
cd web
npm ci --production
npm run build

# NLU Agent setup
cd ../nlu-agent
npm ci --production
npm run build
```

### 3. Environment Konfiguration

#### Production .env
```bash
# Skapa production environment file
cat > /home/alice/app/.env.production << EOF
# Application Environment
NODE_ENV=production
PYTHONPATH=/home/alice/app/server

# Alice Core Configuration
USE_HARMONY=true
USE_TOOLS=true
ENABLED_TOOLS=PLAY,PAUSE,STOP,NEXT,PREV,SET_VOLUME,MUTE,UNMUTE,SHUFFLE,REPEAT,LIKE,UNLIKE
HARMONY_TEMPERATURE_COMMANDS=0.15
NLU_CONFIDENCE_THRESHOLD=0.85
JARVIS_MINIMAL=0

# API Configuration
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
FRONTEND_PORT=3000
NLU_AGENT_PORT=7071

# Database (SQLite för nu, PostgreSQL senare)
DATABASE_URL=sqlite:///home/alice/app/data/production.db

# Logging
LOG_LEVEL=INFO
LOG_FILE=/home/alice/app/logs/alice.log

# Security
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=your-domain.com,www.your-domain.com,localhost

# Spotify Integration (Production credentials)
SPOTIFY_CLIENT_ID=your_production_client_id
SPOTIFY_CLIENT_SECRET=your_production_client_secret
SPOTIFY_REDIRECT_URI=https://your-domain.com/spotify/callback

# AI Model Configuration
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=gpt-oss:20b
OLLAMA_TIMEOUT=60

# TTS Configuration
TTS_VOICE=sv_SE-nst-medium
TTS_SPEED=1.0

# Monitoring
ENABLE_METRICS=true
METRICS_PORT=9090
EOF
```

### 4. Systemd Services

#### Backend Service
```bash
sudo tee /etc/systemd/system/alice-backend.service << EOF
[Unit]
Description=Alice Backend API
After=network.target
Requires=network.target

[Service]
Type=exec
User=alice
Group=alice
WorkingDirectory=/home/alice/app
Environment=PATH=/home/alice/app/.venv/bin
EnvironmentFile=/home/alice/app/.env.production
ExecStart=/home/alice/app/.venv/bin/uvicorn server.app:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=10
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=alice-backend

[Install]
WantedBy=multi-user.target
EOF
```

#### Frontend Service
```bash
sudo tee /etc/systemd/system/alice-frontend.service << EOF
[Unit]
Description=Alice Frontend (Next.js)
After=network.target alice-backend.service
Requires=network.target

[Service]
Type=exec
User=alice
Group=alice
WorkingDirectory=/home/alice/app/web
EnvironmentFile=/home/alice/app/.env.production
ExecStart=/usr/bin/npm start
Restart=always
RestartSec=10
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=alice-frontend

[Install]
WantedBy=multi-user.target
EOF
```

#### NLU Agent Service
```bash
sudo tee /etc/systemd/system/alice-nlu.service << EOF
[Unit]
Description=Alice NLU Agent
After=network.target
Requires=network.target

[Service]
Type=exec
User=alice
Group=alice
WorkingDirectory=/home/alice/app/nlu-agent
EnvironmentFile=/home/alice/app/.env.production
ExecStart=/usr/bin/node dist/index.js
Restart=always
RestartSec=10
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=alice-nlu

[Install]
WantedBy=multi-user.target
EOF
```

#### Aktivera och starta tjänster
```bash
sudo systemctl daemon-reload
sudo systemctl enable alice-backend alice-frontend alice-nlu
sudo systemctl start alice-backend alice-frontend alice-nlu
```

### 5. Nginx Reverse Proxy

#### Installera Nginx
```bash
sudo apt install -y nginx
```

#### Nginx konfiguration
```bash
sudo tee /etc/nginx/sites-available/alice << EOF
# Rate limiting
limit_req_zone \$binary_remote_addr zone=api:10m rate=10r/s;
limit_req_zone \$binary_remote_addr zone=websocket:10m rate=5r/s;

# Upstream servers
upstream alice_backend {
    server 127.0.0.1:8000;
}

upstream alice_frontend {
    server 127.0.0.1:3000;
}

upstream alice_nlu {
    server 127.0.0.1:7071;
}

server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com www.your-domain.com;
    
    # SSL Configuration (använd Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    # Main application (frontend)
    location / {
        proxy_pass http://alice_frontend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        proxy_read_timeout 86400;
    }
    
    # API endpoints
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://alice_backend;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 60;
    }
    
    # WebSocket connections
    location /ws/ {
        limit_req zone=websocket burst=5 nodelay;
        proxy_pass http://alice_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 86400;
    }
    
    # NLU Agent endpoints
    location /nlu/ {
        proxy_pass http://alice_nlu/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    # Static files caching
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)\$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
        proxy_pass http://alice_frontend;
    }
}
EOF
```

#### Aktivera site
```bash
sudo ln -s /etc/nginx/sites-available/alice /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 6. SSL Certificates (Let's Encrypt)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

### 7. Monitoring och Logging

#### Logrotate konfiguration
```bash
sudo tee /etc/logrotate.d/alice << EOF
/home/alice/app/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    sharedscripts
    postrotate
        systemctl reload alice-backend alice-frontend alice-nlu
    endscript
}
EOF
```

#### Prometheus monitoring (valfritt)
```bash
# Installera Prometheus och Grafana för monitoring
sudo apt install -y prometheus grafana
```

## Staging Environment

### Staging konfiguration
```bash
# Skapa staging environment
cat > /home/alice/app/.env.staging << EOF
NODE_ENV=staging
USE_HARMONY=true
USE_TOOLS=true
BACKEND_PORT=8001
FRONTEND_PORT=3000
NLU_AGENT_PORT=7072

# Staging Spotify credentials
SPOTIFY_CLIENT_ID=staging_client_id
SPOTIFY_CLIENT_SECRET=staging_client_secret
SPOTIFY_REDIRECT_URI=https://staging.your-domain.com/spotify/callback

# Reduced model for faster testing
OLLAMA_MODEL=gpt-oss:7b
EOF
```

## Docker Deployment (Alternativ)

### Docker Compose
```yaml
# docker-compose.production.yml
version: '3.8'

services:
  alice-backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    ports:
      - "8000:8000"
    env_file:
      - .env.production
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    restart: unless-stopped
    depends_on:
      - ollama

  alice-frontend:
    build:
      context: ./web
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    env_file:
      - .env.production
    restart: unless-stopped
    depends_on:
      - alice-backend

  alice-nlu:
    build:
      context: ./nlu-agent
      dockerfile: Dockerfile
    ports:
      - "7071:7071"
    env_file:
      - .env.production
    restart: unless-stopped

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf
      - ./ssl:/etc/nginx/ssl
    restart: unless-stopped
    depends_on:
      - alice-frontend
      - alice-backend

volumes:
  ollama_data:
```

### Dockerfiles

#### Backend Dockerfile
```dockerfile
# Dockerfile.backend
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server/ ./server/
COPY .env.production .env

ENV PYTHONPATH=/app/server
EXPOSE 8000

CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Prestanda Optimering

### Backend optimering
```bash
# Uvicorn med flera workers
uvicorn server.app:app --host 0.0.0.0 --port 8000 --workers 4 --worker-class uvicorn.workers.UvicornWorker

# Systemkonfiguration
echo 'fs.file-max = 65536' | sudo tee -a /etc/sysctl.conf
echo 'alice soft nofile 65536' | sudo tee -a /etc/security/limits.conf
echo 'alice hard nofile 65536' | sudo tee -a /etc/security/limits.conf
```

### Database optimering
```python
# SQLite optimering för production
# I app.py, lägg till:
import sqlite3

def optimize_sqlite():
    conn = sqlite3.connect('data/production.db')
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA synchronous=NORMAL')
    conn.execute('PRAGMA cache_size=10000')
    conn.execute('PRAGMA temp_store=MEMORY')
    conn.close()
```

## Säkerhet

### Firewall konfiguration
```bash
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw deny 8000/tcp  # Block direct API access
sudo ufw deny 3000/tcp  # Block direct frontend access
```

### Säkerhetsuppdateringar
```bash
# Automatiska säkerhetsuppdateringar
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure unattended-upgrades
```

### Backup strategi
```bash
#!/bin/bash
# /home/alice/scripts/backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/alice"

# Skapa backup directory
mkdir -p $BACKUP_DIR

# Backup databas
cp /home/alice/app/data/production.db $BACKUP_DIR/db_$DATE.db

# Backup loggar
tar -czf $BACKUP_DIR/logs_$DATE.tar.gz /home/alice/app/logs/

# Backup konfiguration
cp /home/alice/app/.env.production $BACKUP_DIR/env_$DATE

# Ta bort gamla backups (behåll 30 dagar)
find $BACKUP_DIR -type f -mtime +30 -delete

# Cron entry (lägg till i alice's crontab)
# 0 2 * * * /home/alice/scripts/backup.sh
```

## Hälsokontroller

### Health Check Script
```bash
#!/bin/bash
# /home/alice/scripts/health-check.sh

BACKEND_URL="http://localhost:8000/api/health"
FRONTEND_URL="http://localhost:3000"
NLU_URL="http://localhost:7071/nlu/classify"

# Kontrollera backend
if ! curl -f $BACKEND_URL > /dev/null 2>&1; then
    echo "Backend down, restarting..."
    sudo systemctl restart alice-backend
fi

# Kontrollera frontend  
if ! curl -f $FRONTEND_URL > /dev/null 2>&1; then
    echo "Frontend down, restarting..."
    sudo systemctl restart alice-frontend
fi

# Kontrollera NLU
if ! curl -f -X POST $NLU_URL -d '{"text":"test"}' -H "Content-Type: application/json" > /dev/null 2>&1; then
    echo "NLU down, restarting..."
    sudo systemctl restart alice-nlu
fi

# Cron entry för hälsokontroller var 5:e minut
# */5 * * * * /home/alice/scripts/health-check.sh
```

## Felsökning

### Loggar
```bash
# Systemd service loggar
sudo journalctl -u alice-backend -f
sudo journalctl -u alice-frontend -f  
sudo journalctl -u alice-nlu -f

# Applikationsloggar
tail -f /home/alice/app/logs/alice.log

# Nginx loggar
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Service status
```bash
sudo systemctl status alice-backend alice-frontend alice-nlu nginx ollama
```

### Prestanda debugging
```bash
# CPU och minnesanvändning
htop
iotop

# Nätverkstrafik
iftop

# Disk usage
df -h
du -sh /home/alice/app/*
```

## Uppdateringsprocess

### Rolling update
```bash
#!/bin/bash
# /home/alice/scripts/update.sh

cd /home/alice/app

# Backup innan uppdatering
./scripts/backup.sh

# Hämta senaste ändringar
git fetch origin
git checkout main
git reset --hard origin/main

# Uppdatera dependencies
source .venv/bin/activate
pip install -r server/requirements.txt

cd web
npm ci
npm run build

cd ../nlu-agent  
npm ci
npm run build

# Starta om tjänster
sudo systemctl restart alice-backend
sleep 10
sudo systemctl restart alice-frontend
sleep 5  
sudo systemctl restart alice-nlu

# Verifiera att allt fungerar
curl -f http://localhost:8000/api/health || echo "Backend health check failed"
curl -f http://localhost:3000 || echo "Frontend health check failed"
```

---

**Deployment checklist:**
- [ ] Server specifikationer uppfyllda
- [ ] Systemd services konfigurerade
- [ ] Nginx reverse proxy setup
- [ ] SSL certificates installerade
- [ ] Monitoring och logging aktiverat
- [ ] Backup strategi implementerad
- [ ] Säkerhetskonfiguration tillämpade
- [ ] Hälsokontroller aktiverade
- [ ] Uppdateringsprocess testad