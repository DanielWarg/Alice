# 🎤 Alice Voice System Setup Guide

Setup guide for Alice's voice system - currently using Browser SpeechRecognition with local processing, with plans for advanced hybrid architecture.

> **🇸🇪 Svenska:** [docs/sv/VOICE_SETUP.md](docs/sv/VOICE_SETUP.md) - Full Swedish version available

## 🚀 **Current Implementation Status**

### **Current Voice System (v2.1 - LiveKit-Style Streaming):**
- ✅ **Stable Partial Detection** for sub-second response triggers (250ms)
- ✅ **Micro-Chunked TTS Streaming** with progressive audio playback
- ✅ **Local gpt-oss Processing** via Ollama for complete privacy
- ✅ **Smart Echo Control** with mute/unmute instead of recognition restart
- ✅ **Real-time TTFA Metrics** for performance monitoring
- ✅ **Sub-second response times** (~700ms Time-To-First-Audio achieved)

### **Key Performance Improvements:**
- 🎯 **7.8x faster** than previous batch processing (5.5s → 700ms TTFA)
- 🎯 **Progressive TTS** streams 3-5 word chunks with 20ms delay
- 🎯 **Continuous recognition** without restart delays
- 🎯 **WebSocket streaming** for real-time bidirectional communication

## 🚀 **Quick Start (Current System)**

### Prerequisites

- **Python 3.9+** with pip
- **Node.js 18+** with npm
- **Ollama** with gpt-oss:20B model installed
- **Modern browser** with microphone support
- **HTTPS environment** (for microphone access in production)

### Current Privacy-First Design

Alice's current implementation is **100% private**:

**Everything stays local:**
- Voice recognition via Browser SpeechRecognition API
- All AI processing with local Ollama gpt-oss:20B model
- Tool execution (calendar, weather, integrations)
- Personal data and conversations never leave your device
- Full Swedish language support and cultural context

### Basic Installation

```bash
# 1. Clone repository
git clone https://github.com/your-org/Alice.git
cd Alice

# 2. Setup backend
cd server
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Setup frontend
cd ../web
npm install

# 4. Install Ollama and models
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull gpt-oss:20b

# 5. Start services
# Terminal 1 - Backend
cd server && python run.py

# Terminal 2 - Frontend  
cd web && npm run dev
```

## ⚙️ **Environment Configuration**

### Backend Environment (.env in server/)

```bash
# Core Alice Settings
USE_HARMONY=true
USE_TOOLS=true
LOG_LEVEL=INFO
OLLAMA_BASE_URL=http://localhost:11434

# Voice Pipeline (Optional but Recommended)
OPENAI_API_KEY=sk-proj-...                    # Your OpenAI API key
VOICE_PIPELINE_MODE=dual                      # dual | voicebox | voiceclient
ENABLE_WEBRTC=true                           # Enable WebRTC features
VOICE_DEBUG=false                            # Enable voice debugging

# TTS Configuration
TTS_PROVIDER=piper                           # piper | openai | hybrid
TTS_VOICE_MODEL=sv_SE-nst-medium            # Swedish voice model
TTS_CACHE_ENABLED=true                      # Enable TTS caching
TTS_CACHE_SIZE=1000                         # Cache size (MB)

# Audio Enhancement
AUDIO_ENHANCEMENT_ENABLED=true               # Enable audio processing
NOISE_REDUCTION=true                        # Enable noise reduction
ECHO_CANCELLATION=true                      # Enable echo cancellation

# Google Services (Optional)
GOOGLE_CALENDAR_CREDENTIALS_JSON=path/to/credentials.json
GOOGLE_GMAIL_CREDENTIALS_JSON=path/to/gmail-credentials.json

# Spotify Integration (Optional)
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
```

### Frontend Environment (.env.local in web/)

```bash
# OpenAI Configuration
OPENAI_API_KEY=sk-proj-...                           # Same as backend

# Voice Configuration
NEXT_PUBLIC_VOICE_MODE=dual                          # dual | voicebox | voiceclient
NEXT_PUBLIC_ALICE_BACKEND_URL=http://localhost:8000  # Backend URL
NEXT_PUBLIC_ENABLE_VOICE_DEBUG=false                 # Voice debugging
NEXT_PUBLIC_DEFAULT_PERSONALITY=alice                # alice | formal | casual
NEXT_PUBLIC_DEFAULT_EMOTION=friendly                 # neutral | happy | calm | confident | friendly

# WebRTC Settings
NEXT_PUBLIC_ENABLE_WEBRTC=true                       # Enable WebRTC features
NEXT_PUBLIC_WEBRTC_ICE_SERVERS=stun:stun.l.google.com:19302

# Development Settings  
NEXT_PUBLIC_DEVELOPMENT_MODE=true                    # Enable dev features
HTTPS=false                                         # Set to true for HTTPS in dev
PORT=3000                                           # Frontend port

# Production Settings (uncomment for production)
# NEXT_PUBLIC_VOICE_MODE=voiceclient
# NEXT_PUBLIC_ALICE_BACKEND_URL=https://your-alice-backend.com
# HTTPS=true
```

## 🔧 **Voice Modes Configuration**

Alice supports three voice pipeline modes:

### 1. VoiceBox Mode (Basic)
Best for: Development, testing, limited resources

```bash
# Backend
VOICE_PIPELINE_MODE=voicebox

# Frontend  
NEXT_PUBLIC_VOICE_MODE=voicebox
```

**Features:**
- Browser Speech Recognition
- Alice backend TTS
- Audio visualization
- Swedish post-processing
- Demo/fallback modes

### 2. VoiceClient Mode (Advanced) 
Best for: Production, professional use, low latency

```bash
# Backend
VOICE_PIPELINE_MODE=voiceclient
OPENAI_API_KEY=sk-proj-...

# Frontend
NEXT_PUBLIC_VOICE_MODE=voiceclient
OPENAI_API_KEY=sk-proj-...
```

**Features:**
- OpenAI Realtime API
- WebRTC streaming
- Professional audio processing
- Agent bridge architecture
- Barge-in support

### 3. Dual Mode (Recommended)
Best for: Maximum flexibility, automatic fallback

```bash
# Backend
VOICE_PIPELINE_MODE=dual
OPENAI_API_KEY=sk-proj-...  # Optional but recommended

# Frontend
NEXT_PUBLIC_VOICE_MODE=dual
OPENAI_API_KEY=sk-proj-...  # Optional
```

**Features:**
- Automatic mode selection based on capabilities
- OpenAI integration when available
- VoiceBox fallback when needed
- Runtime mode switching

## 📋 **Detailed Setup Steps**

### Step 1: OpenAI API Setup

1. **Get API Key:**
   ```bash
   # Visit https://platform.openai.com/api-keys
   # Create new API key with necessary permissions
   ```

2. **Test API Access:**
   ```bash
   curl -H "Authorization: Bearer sk-proj-..." \
        https://api.openai.com/v1/models
   ```

3. **Configure Environment:**
   ```bash
   # Add to both backend and frontend .env files
   echo "OPENAI_API_KEY=sk-proj-..." >> server/.env
   echo "OPENAI_API_KEY=sk-proj-..." >> web/.env.local
   ```

### Step 2: Swedish TTS Models

Alice uses Swedish TTS models for authentic voice interaction:

```bash
# Download Swedish Piper models (automatic on first run)
# Models will be stored in server/models/tts/

# Available models:
# - sv_SE-nst-medium.onnx (default, good quality)
# - sv_SE-nst-high.onnx (high quality, larger size)
# - sv_SE-lisa-medium.onnx (alternative voice)
```

### Step 3: Audio System Setup

**Linux (Ubuntu/Debian):**
```bash
# Install audio dependencies
sudo apt-get install portaudio19-dev python3-pyaudio
sudo apt-get install alsa-utils pulseaudio

# Test microphone
arecord -d 5 -f cd -t wav test.wav && aplay test.wav
```

**macOS:**
```bash
# Install audio dependencies
brew install portaudio
pip install pyaudio

# Test microphone (built into system)
```

**Windows:**
```bash
# Install audio dependencies
pip install pyaudio

# Windows audio should work automatically
# Ensure microphone permissions are granted
```

### Step 4: HTTPS Setup (Production)

For production deployment with full voice features:

```bash
# Option 1: Self-signed certificate (development)
cd web
npm install --save-dev mkcert
npx mkcert create-ca
npx mkcert create-cert

# Option 2: Let's Encrypt (production)
sudo certbot certonly --standalone -d your-domain.com

# Option 3: Reverse proxy (recommended)
# Use nginx or Apache with SSL termination
```

### Step 5: Service Configuration

**Backend Service (systemd example):**
```bash
# Create service file
sudo tee /etc/systemd/system/alice-backend.service << EOF
[Unit]
Description=Alice Backend Service
After=network.target

[Service]
Type=simple
User=alice
WorkingDirectory=/opt/alice/server
Environment=PATH=/opt/alice/server/.venv/bin
ExecStart=/opt/alice/server/.venv/bin/python run.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable alice-backend
sudo systemctl start alice-backend
```

**Frontend Service (PM2 example):**
```bash
# Install PM2
npm install -g pm2

# Create ecosystem file
tee ecosystem.config.js << EOF
module.exports = {
  apps: [{
    name: 'alice-frontend',
    script: 'npm',
    args: 'run start',
    cwd: './web',
    env: {
      NODE_ENV: 'production',
      PORT: 3000
    }
  }]
}
EOF

# Start service
pm2 start ecosystem.config.js
pm2 save
pm2 startup
```

## 🔍 **Verification & Testing**

### Backend Health Check

```bash
# Test basic backend
curl http://localhost:8000/api/health

# Expected response:
{
  "status": "healthy",
  "version": "0.1.0",
  "components": {
    "database": {"status": "up"},
    "ollama": {"status": "up", "model_loaded": "gpt-oss:20b"},
    "tts_engine": {"status": "up", "voices_loaded": 1}
  }
}
```

### Voice Pipeline Test

```bash
# Test TTS endpoint
curl -X POST http://localhost:8000/api/tts/synthesize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hej! Jag är Alice.",
    "personality": "alice",
    "emotion": "friendly"
  }' --output test-audio.json

# Test OpenAI integration (if configured)
curl -X GET http://localhost:3000/api/realtime/ephemeral
```

### Frontend Components Test

```bash
# Start frontend
cd web && npm run dev

# Open test pages:
# - http://localhost:3000 (main HUD with VoiceBox)
# - http://localhost:3000/voice (voice demo page)

# Browser console tests:
# - Check for voice component initialization
# - Test microphone permissions
# - Verify WebRTC support
```

## 🐛 **Troubleshooting**

### Common Issues

**1. Microphone Access Denied**
```bash
# Solution 1: HTTPS requirement
HTTPS=true npm run dev

# Solution 2: Localhost exception (Chrome only)
# Visit chrome://flags/#unsafely-treat-insecure-origin-as-secure
# Add: http://localhost:3000

# Solution 3: Browser permissions
# Check browser settings → Privacy → Microphone
```

**2. OpenAI API Errors**
```bash
# Check API key validity
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
     https://api.openai.com/v1/models

# Common issues:
# - Invalid API key format
# - Insufficient API credits  
# - Rate limiting
# - Model access permissions
```

**3. Swedish TTS Not Working**
```bash
# Check model files
ls -la server/models/tts/

# Manual model download
cd server/models/tts/
wget https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/sv/sv_SE/nst/medium/sv_SE-nst-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/sv/sv_SE/nst/medium/sv_SE-nst-medium.onnx.json

# Test TTS directly
python -c "
from audio_processor import enhance_tts_synthesis
result = enhance_tts_synthesis('Hej från Alice!', personality='alice')
print(f'TTS test: {result.get(\"success\", False)}')
"
```

**4. WebRTC Connection Issues**
```bash
# Check browser WebRTC support
# Open browser console and run:
console.log('RTCPeerConnection' in window);

# Test STUN server connectivity
# Use WebRTC troubleshooting tools:
# https://webrtc.github.io/samples/src/content/peerconnection/trickle-ice/

# Common fixes:
# - Check firewall settings
# - Verify STUN/TURN server access  
# - Test with different networks
```

**5. Backend Connection Failed**
```bash
# Check backend status
curl -v http://localhost:8000/api/health

# Check logs
tail -f server/server.log

# Common issues:
# - Port already in use (change PORT in .env)
# - Missing dependencies (run pip install -r requirements.txt)
# - Database connection issues
# - Ollama not running (ollama serve)
```

### Debug Mode

**Enable comprehensive debugging:**

```bash
# Backend debugging
LOG_LEVEL=DEBUG VOICE_DEBUG=true python run.py

# Frontend debugging  
NEXT_PUBLIC_ENABLE_VOICE_DEBUG=true npm run dev

# Browser console debugging
localStorage.setItem('alice_debug', 'true');
localStorage.setItem('voice_debug', 'true');
```

**Debug output locations:**
- Backend: `server/server.log`
- Frontend: Browser console + Network tab
- Voice: Browser console audio/WebRTC logs

## 📊 **Performance Optimization**

### Backend Optimization

```bash
# Production settings in .env
LOG_LEVEL=WARNING
TTS_CACHE_ENABLED=true
TTS_CACHE_SIZE=2000
AUDIO_ENHANCEMENT_ENABLED=true

# Database optimization
# Use SQLite WAL mode for better concurrency

# Resource monitoring
pip install psutil
# Monitor CPU, memory, disk usage
```

### Frontend Optimization

```bash
# Production build
npm run build
npm run start

# Bundle analysis
npm install --save-dev @next/bundle-analyzer
ANALYZE=true npm run build

# Audio optimization
# - Enable audio compression
# - Use audio buffering
# - Implement connection pooling
```

### Audio Quality Settings

```bash
# High quality (more resources)
TTS_VOICE_MODEL=sv_SE-nst-high
AUDIO_ENHANCEMENT_ENABLED=true
NOISE_REDUCTION=true
ECHO_CANCELLATION=true

# Balanced (recommended)
TTS_VOICE_MODEL=sv_SE-nst-medium
AUDIO_ENHANCEMENT_ENABLED=true  
NOISE_REDUCTION=true
ECHO_CANCELLATION=false

# Fast (less resources)
TTS_VOICE_MODEL=sv_SE-nst-medium
AUDIO_ENHANCEMENT_ENABLED=false
NOISE_REDUCTION=false
ECHO_CANCELLATION=false
```

## 🚀 **Production Deployment**

### Docker Deployment

```dockerfile
# Dockerfile.backend
FROM python:3.9-slim
WORKDIR /app
COPY server/requirements.txt .
RUN pip install -r requirements.txt
COPY server/ .
EXPOSE 8000
CMD ["python", "run.py"]

# Dockerfile.frontend  
FROM node:18-alpine
WORKDIR /app
COPY web/package*.json ./
RUN npm ci --only=production
COPY web/ .
RUN npm run build
EXPOSE 3000
CMD ["npm", "run", "start"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  alice-backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - VOICE_PIPELINE_MODE=dual
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      
  alice-frontend:
    build:
      context: .  
      dockerfile: Dockerfile.frontend
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - NEXT_PUBLIC_VOICE_MODE=dual
      - NEXT_PUBLIC_ALICE_BACKEND_URL=http://alice-backend:8000
    ports:
      - "3000:3000"
    depends_on:
      - alice-backend
```

### Load Balancing

```nginx
# nginx.conf
upstream alice_backend {
    server alice-backend-1:8000;
    server alice-backend-2:8000;
    server alice-backend-3:8000;
}

upstream alice_frontend {
    server alice-frontend-1:3000;
    server alice-frontend-2:3000;
}

server {
    listen 443 ssl http2;
    server_name alice.your-domain.com;
    
    # SSL configuration
    ssl_certificate /etc/letsencrypt/live/alice.your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/alice.your-domain.com/privkey.pem;
    
    # Frontend
    location / {
        proxy_pass http://alice_frontend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
    
    # Backend API
    location /api/ {
        proxy_pass http://alice_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
    
    # WebSocket support
    location /ws/ {
        proxy_pass http://alice_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 📝 **Configuration Templates**

### Development Configuration

```bash
# server/.env.development
USE_HARMONY=true
USE_TOOLS=true
LOG_LEVEL=DEBUG
OLLAMA_BASE_URL=http://localhost:11434
OPENAI_API_KEY=sk-proj-...
VOICE_PIPELINE_MODE=dual
VOICE_DEBUG=true
TTS_CACHE_ENABLED=true
AUDIO_ENHANCEMENT_ENABLED=true

# web/.env.local.development
OPENAI_API_KEY=sk-proj-...
NEXT_PUBLIC_VOICE_MODE=dual
NEXT_PUBLIC_ALICE_BACKEND_URL=http://localhost:8000
NEXT_PUBLIC_ENABLE_VOICE_DEBUG=true
HTTPS=false
PORT=3000
```

### Production Configuration

```bash
# server/.env.production
USE_HARMONY=true
USE_TOOLS=true
LOG_LEVEL=WARNING
OLLAMA_BASE_URL=http://localhost:11434
OPENAI_API_KEY=sk-proj-...
VOICE_PIPELINE_MODE=voiceclient
VOICE_DEBUG=false
TTS_CACHE_ENABLED=true
TTS_CACHE_SIZE=2000
AUDIO_ENHANCEMENT_ENABLED=true
DATABASE_URL=postgresql://alice:password@localhost:5432/alice

# web/.env.local.production
OPENAI_API_KEY=sk-proj-...
NEXT_PUBLIC_VOICE_MODE=voiceclient
NEXT_PUBLIC_ALICE_BACKEND_URL=https://api.alice.your-domain.com
NEXT_PUBLIC_ENABLE_VOICE_DEBUG=false
NODE_ENV=production
```

## 🎓 **Next Steps**

After successful setup:

1. **Test Voice Features** - Try both VoiceBox and VoiceClient
2. **Configure Integrations** - Setup Google Calendar, Spotify, etc.
3. **Customize Personalities** - Adjust Alice's voice and behavior  
4. **Monitor Performance** - Check logs and resource usage
5. **Scale as Needed** - Add load balancing, database scaling

## 📚 **Additional Resources**

- **[API Documentation](API.md)** - Complete API reference
- **[Agent Core](AGENT_CORE.md)** - System architecture details
- **[Web README](web/README.md)** - Frontend component guide
- **[Troubleshooting Guide](TROUBLESHOOTING.md)** - Common issues and solutions

For support and questions, check the project documentation or create an issue in the repository.

**Note on Swedish Voice Features & Privacy:** Alice's hybrid voice pipeline is optimized for Swedish language interaction with privacy-first design. All Swedish cultural context, personality, and complex reasoning remain local using gpt-oss:20B, while simple voice transcripts may use OpenAI Realtime for optimal response speed. Commands like "Hej Alice" (Hello Alice), "spela musik" (play music), and "visa kalender" (show calendar) maintain Alice's authentic Swedish AI assistant character. Users have full control over privacy settings and can choose full offline mode if preferred.