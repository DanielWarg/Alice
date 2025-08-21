#!/bin/bash

# 🚀 Alice Project Startup Script
# Kör detta script för att starta alla komponenter

echo "🚀 Starting Alice Project..."
echo "================================"

# Kontrollera att vi är i rätt katalog
if [ ! -f "server/run.py" ]; then
    echo "❌ Error: Kör detta script från Alice root-katalogen"
    echo "   cd /Users/evil/Desktop/EVIL/PROJECT/Alice"
    exit 1
fi

# Kontrollera att .venv finns
if [ ! -d ".venv" ]; then
    echo "❌ Error: Virtuell miljö saknas. Skapa den först:"
    echo "   python3 -m venv .venv"
    echo "   source .venv/bin/activate"
    echo "   pip3 install -r server/requirements.txt"
    echo "   pip3 install python-multipart"
    exit 1
fi

# Kontrollera att Ollama finns
if ! command -v ollama &> /dev/null; then
    echo "❌ Error: Ollama är inte installerat"
    echo "   Installera med: curl -fsSL https://ollama.ai/install.sh | sh"
    exit 1
fi

echo "✅ Förutsättningar kontrollerade"
echo ""

# Kontrollera verktygskonsistens
echo "🔧 Checking tool consistency..."
cd server
source ../.venv/bin/activate
TOOL_COUNT=$(python3 -c "from core.tool_specs import enabled_tools; print(len(enabled_tools()))" 2>/dev/null || echo "0")
cd ..
if [ "$TOOL_COUNT" -gt 10 ]; then
    echo "✅ Tool consistency OK ($TOOL_COUNT tools enabled)"
else
    echo "❌ Tool consistency check failed"
    exit 1
fi

# Starta Backend
echo "🐍 Starting Backend (FastAPI)..."
cd server
source ../.venv/bin/activate
python3 run.py &
BACKEND_PID=$!
cd ..

# Vänta lite för att backend ska starta
sleep 3

# Kontrollera backend
if curl -s http://localhost:8000/api/tools/spec > /dev/null 2>&1; then
    echo "✅ Backend started successfully on http://localhost:8000"
else
    echo "❌ Backend failed to start"
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

# Starta Frontend
echo "⚛️ Starting Frontend (Next.js)..."
cd web
npm run dev &
FRONTEND_PID=$!
cd ..

# Vänta lite för att frontend ska starta
sleep 5

# Kontrollera frontend
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo "✅ Frontend started successfully on http://localhost:3000"
else
    echo "❌ Frontend failed to start"
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit 1
fi

# Starta Ollama (om den inte redan körs)
echo "🤖 Starting Ollama..."
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    ollama serve &
    OLLAMA_PID=$!
    sleep 3
else
    echo "✅ Ollama already running"
    OLLAMA_PID=""
fi

# Kontrollera Ollama
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "✅ Ollama started successfully on http://localhost:11434"
else
    echo "❌ Ollama failed to start"
    kill $BACKEND_PID $FRONTEND_PID $OLLAMA_PID 2>/dev/null
    exit 1
fi

echo ""
echo "🎉 Alice Project started successfully!"
echo "================================"
echo "🌐 Frontend: http://localhost:3000"
echo "🔧 Backend: http://localhost:8000"
echo "🤖 AI: http://localhost:11434"
echo ""
echo "📋 Status:"
echo "   Backend PID: $BACKEND_PID"
echo "   Frontend PID: $FRONTEND_PID"
if [ ! -z "$OLLAMA_PID" ]; then
    echo "   Ollama PID: $OLLAMA_PID"
fi
echo ""
echo "🛑 To stop all services:"
echo "   kill $BACKEND_PID $FRONTEND_PID $OLLAMA_PID"
echo ""
echo "📖 For help, see STARTUP.md"
echo ""

# Vänta på användarinput för att stoppa
echo "Press Enter to stop all services..."
read

# Stoppa alla services
echo "🛑 Stopping all services..."
kill $BACKEND_PID $FRONTEND_PID $OLLAMA_PID 2>/dev/null
echo "✅ All services stopped"
