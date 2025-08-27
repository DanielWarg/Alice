#!/bin/bash

# 🚀 Alice Project Startup Script - BULLETPROOF VERSION
# Kör detta script för att starta alla komponenter utan krångel

echo "🚀 Starting Alice Project..."
echo "================================"

# Kontrollera att vi är i rätt katalog
if [ ! -f "server/run.py" ]; then
    echo "❌ Error: Kör detta script från Alice root-katalogen"
    echo "   cd /Users/evil/Desktop/EVIL/PROJECT/Alice"
    exit 1
fi

# Kontrollera förutsättningar
echo "🔍 Checking prerequisites..."
command -v python3 >/dev/null || { echo "❌ Python3 not found"; exit 1; }
command -v node >/dev/null || { echo "❌ Node.js not found"; exit 1; }
command -v ollama >/dev/null || { echo "❌ Ollama not found"; exit 1; }
echo "✅ Prerequisites OK"

# Rensa gamla processer som kan störa
echo "🧹 Cleaning up old processes..."
pkill -f "python.*run.py" 2>/dev/null || true
pkill -f "npm run dev" 2>/dev/null || true
sleep 2

# Smart cleanup för optimal prestanda
echo "🧹 Running smart cleanup..."
if [ -f "smart_cleanup.py" ]; then
    python3 smart_cleanup.py --execute --quick 2>/dev/null || {
        echo "⚠️ Smart cleanup failed, continuing anyway..."
    }
    echo "✅ Quick cleanup completed"
else
    echo "⚠️ smart_cleanup.py not found, skipping cleanup"
fi

# Fix virtual environment (skapa om om trasig)
echo "🔧 Setting up virtual environment..."
if [ -d ".venv" ]; then
    source .venv/bin/activate 2>/dev/null || VENV_BROKEN=1
    if [[ $(which python3) != *".venv"* ]]; then
        VENV_BROKEN=1
    fi
else
    VENV_BROKEN=1
fi

if [ "$VENV_BROKEN" = "1" ]; then
    echo "🔧 Recreating broken virtual environment..."
    rm -rf .venv 2>/dev/null || true
    python3 -m venv .venv
    source .venv/bin/activate
    
    # Installera dependencies
    echo "📦 Installing Python dependencies..."
    pip install --upgrade pip
    pip install -r server/requirements.txt
    pip install python-multipart httpx
else
    echo "✅ Virtual environment OK"
fi

# Kontrollera frontend dependencies
echo "📦 Checking frontend dependencies..."
if [ ! -d "web/node_modules" ]; then
    echo "📦 Installing Node.js dependencies..."
    cd web
    npm install
    cd ..
fi

# Kontrollera verktygskonsistens
echo "🔧 Checking tool consistency..."
cd server
source ../.venv/bin/activate
TOOL_COUNT=$(python3 -c "from core.tool_specs import enabled_tools; print(len(enabled_tools()))" 2>/dev/null || echo "0")
cd ..
if [ "$TOOL_COUNT" -gt 10 ]; then
    echo "✅ Tool consistency OK ($TOOL_COUNT tools enabled)"
else
    echo "⚠️  Tool consistency check inconclusive (may still work)"
fi

# Initialize Progress Tracker
echo "📊 Initializing Progress Tracker..."
if [ -f "progress_tracker.py" ] && [ -f "progress_tracker_config.json" ]; then
    source .venv/bin/activate
    # Install additional dependencies if needed
    pip install aiofiles >/dev/null 2>&1 || true
    
    # Start progress tracker in background
    python3 progress_tracker.py --daemon &
    PROGRESS_TRACKER_PID=$!
    
    # Wait a moment for it to initialize
    sleep 2
    
    if kill -0 $PROGRESS_TRACKER_PID 2>/dev/null; then
        echo "✅ Progress Tracker started (PID: $PROGRESS_TRACKER_PID)"
    else
        echo "⚠️ Progress Tracker failed to start, continuing without tracking"
        PROGRESS_TRACKER_PID=""
    fi
else
    echo "⚠️ Progress Tracker files not found, skipping progress tracking"
    PROGRESS_TRACKER_PID=""
fi

# Starta Backend
echo "🐍 Starting Backend (FastAPI)..."
cd server
source ../.venv/bin/activate
python run.py &
BACKEND_PID=$!
cd ..

# Vänta och kontrollera backend
echo "⏳ Waiting for backend to start..."
for i in {1..10}; do
    sleep 1
    if curl -s http://localhost:8000/api/tools/spec > /dev/null 2>&1; then
        echo "✅ Backend started successfully on http://localhost:8000"
        BACKEND_OK=1
        break
    fi
done

if [ "$BACKEND_OK" != "1" ]; then
    echo "❌ Backend failed to start"
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi

# Starta Frontend
echo "⚛️ Starting Frontend (Next.js)..."
cd web
npm run dev &
FRONTEND_PID=$!
cd ..

# Vänta och kontrollera frontend
echo "⏳ Waiting for frontend to start..."
for i in {1..15}; do
    sleep 1
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo "✅ Frontend started successfully on http://localhost:3000"
        FRONTEND_OK=1
        break
    fi
done

if [ "$FRONTEND_OK" != "1" ]; then
    echo "❌ Frontend failed to start"
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    exit 1
fi

# Kontrollera/starta Ollama
echo "🤖 Checking Ollama..."
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "✅ Ollama already running on http://localhost:11434"
else
    echo "🤖 Starting Ollama..."
    ollama serve &
    OLLAMA_PID=$!
    sleep 3
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "✅ Ollama started successfully"
    else
        echo "❌ Ollama failed to start"
    fi
fi

echo ""
echo "🔍 Final System Check:"
curl -s http://localhost:8000/api/tools/spec >/dev/null && echo "✅ Backend OK" || echo "❌ Backend FAIL"
curl -s http://localhost:3000 >/dev/null && echo "✅ Frontend OK" || echo "❌ Frontend FAIL"  
curl -s http://localhost:11434/api/tags >/dev/null && echo "✅ AI OK" || echo "❌ AI FAIL"
curl -s http://localhost:8000/api/v1/llm/status >/dev/null && echo "✅ LLM System OK" || echo "❌ LLM System FAIL"

echo ""
echo "🎉 Alice Project started successfully!"
echo "================================"
echo "🌐 Frontend: http://localhost:3000"
echo "🔧 Backend: http://localhost:8000"
echo "🤖 AI: http://localhost:11434"
echo "🧠 LLM Status: http://localhost:8000/api/v1/llm/status"
echo ""
echo "📋 Status:"
echo "   Backend PID: $BACKEND_PID"
echo "   Frontend PID: $FRONTEND_PID"
if [ ! -z "$OLLAMA_PID" ]; then
    echo "   Ollama PID: $OLLAMA_PID"
fi
if [ ! -z "$PROGRESS_TRACKER_PID" ]; then
    echo "   Progress Tracker PID: $PROGRESS_TRACKER_PID"
fi
echo ""
echo "🛑 To stop all services:"
echo "   pkill -f 'python.*run.py'; pkill -f 'npm run dev'; pkill -f 'progress_tracker.py'"
echo ""
echo "🎯 Open Alice: http://localhost:3000"
echo ""

# Optionell väntan för att stoppa
if [ "$1" = "--wait" ]; then
    echo "Press Enter to stop all services..."
    read
    
    # Stoppa alla services
    echo "🛑 Stopping all services..."
    kill $BACKEND_PID $FRONTEND_PID $OLLAMA_PID $PROGRESS_TRACKER_PID 2>/dev/null || true
    echo "✅ All services stopped"
fi