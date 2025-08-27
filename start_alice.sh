#!/bin/bash

# 🚀 Alice FAS2 Startup Script  
# Updated for FAS2 Architecture (No Backend Server Required)

echo "🚀 Starting Alice FAS2..."
echo "==============================="

# Kontrollera att vi är i rätt katalog
if [ ! -f "web/package.json" ]; then
    echo "❌ Error: Kör detta script från Alice root-katalogen"
    echo "   cd /path/to/Alice"
    exit 1
fi

# Kontrollera förutsättningar
echo "🔍 Checking prerequisites..."
command -v node >/dev/null || { echo "❌ Node.js not found - install Node.js 18+"; exit 1; }
command -v npm >/dev/null || { echo "❌ npm not found - install npm"; exit 1; }

NODE_VERSION=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo "❌ Node.js version $NODE_VERSION < 18 - upgrade Node.js"
    exit 1
fi

echo "✅ Prerequisites OK (Node.js $NODE_VERSION)"

# Rensa gamla processer
echo "🧹 Cleaning up old processes..."
pkill -f "next dev" 2>/dev/null || true
pkill -f "npm run dev" 2>/dev/null || true
sleep 2

# Gå till web directory
cd web

# Kontrollera och installera dependencies
echo "📦 Checking dependencies..."
if [ ! -d "node_modules" ] || [ ! -f "node_modules/.package-lock.json" ]; then
    echo "📦 Installing Node.js dependencies..."
    npm install
else
    echo "✅ Dependencies OK"
fi

# Kontrollera environment
echo "🔧 Checking environment configuration..."
if [ ! -f ".env.local" ]; then
    if [ -f ".env.example" ]; then
        echo "📝 Creating .env.local from .env.example..."
        cp .env.example .env.local
        echo ""
        echo "⚠️  IMPORTANT: Add your OpenAI API key to .env.local"
        echo "   OPENAI_API_KEY=your-key-here"
        echo ""
    else
        echo "📝 Creating basic .env.local..."
        cat > .env.local << EOF
# FAS2 Environment Configuration
OPENAI_API_KEY=your-key-here
MEMORY_DRIVER=sqlite
INJECT_BUDGET_PCT=25
ARTIFACT_CONFIDENCE_MIN=0.7
BRAIN_SHADOW_ENABLED=on
EOF
        echo ""
        echo "⚠️  IMPORTANT: Add your OpenAI API key to .env.local"
        echo "   Edit .env.local and set OPENAI_API_KEY=your-key-here"
        echo ""
    fi
fi

# Kontrollera om OpenAI API key är satt
if grep -q "your-key-here" .env.local 2>/dev/null; then
    echo "⚠️  OpenAI API key not configured - some features may not work"
    echo "   Edit .env.local and set your OPENAI_API_KEY"
else
    echo "✅ Environment configuration OK"
fi

# Förbered databas och loggar
echo "💾 Preparing data directories..."
mkdir -p data logs alice/identity 2>/dev/null || true

# Starta Next.js development server
echo "⚛️  Starting Next.js (FAS2 System)..."
npm run dev &
NEXT_PID=$!

# Vänta och kontrollera Next.js
echo "⏳ Waiting for system to start..."
for i in {1..30}; do
    sleep 1
    if curl -s http://localhost:3000/api/health/simple > /dev/null 2>&1; then
        echo "✅ Alice FAS2 started successfully!"
        SYSTEM_OK=1
        break
    fi
    if [ $((i % 5)) -eq 0 ]; then
        echo "   ... still waiting (${i}s)"
    fi
done

if [ "$SYSTEM_OK" != "1" ]; then
    echo "❌ Alice failed to start"
    kill $NEXT_PID 2>/dev/null || true
    exit 1
fi

# Kör integration tester för att validera systemet
echo "🧪 Running integration tests..."
if npm run test:integration >/dev/null 2>&1; then
    echo "✅ Integration tests PASSED - System fully operational"
    TEST_STATUS="✅ All systems green"
else
    echo "⚠️  Integration tests FAILED - System may have issues"
    TEST_STATUS="⚠️  Some issues detected"
fi

# System status check
echo ""
echo "🔍 Final System Check:"
curl -s http://localhost:3000/api/health/simple >/dev/null && echo "✅ Health API OK" || echo "❌ Health API FAIL"
curl -s http://localhost:3000/api/metrics/summary >/dev/null && echo "✅ Metrics API OK" || echo "❌ Metrics API FAIL"
curl -s http://localhost:3000/api/brain/compose -X POST -H "Content-Type: application/json" -d '{"user_id":"test","session_id":"test","message":"test"}' >/dev/null 2>&1 && echo "✅ Brain API OK" || echo "❌ Brain API FAIL"

echo ""
echo "🎉 Alice FAS2 is running!"
echo "==============================="
echo "🌐 Main Interface:    http://localhost:3000"
echo "🧪 Test Suite:        http://localhost:3000/test_fas_system.html"  
echo "📊 System Health:     http://localhost:3000/api/health/simple"
echo "📈 Metrics:           http://localhost:3000/api/metrics/summary"
echo ""
echo "📋 System Status:"
echo "   Next.js PID: $NEXT_PID"
echo "   Test Status: $TEST_STATUS"
echo "   Architecture: FAS2 (Event-driven, Memory-enhanced)"
echo ""
echo "🧪 Validate Installation:"
echo "   npm run test:integration     # Full system validation"
echo ""
echo "🛑 To stop Alice:"
echo "   pkill -f 'next dev' OR press Ctrl+C"
echo ""

# FAS2 Feature Summary
echo "🏗️  FAS2 Features Available:"
echo "   ✅ FAS 0: Environment & Health endpoints"
echo "   ✅ FAS 1: Brain Compose API (/api/brain/compose)"  
echo "   ✅ FAS 2: Event Bus & Telemetry (logs/metrics.ndjson)"
echo "   ✅ FAS 3: Memory System (/api/memory/*)"
echo "   ✅ FAS 4: Context Injection (25% budget)"
echo "   🔄 FAS 5: Provider Switch (Next Phase)"
echo ""

# Quick start tips
echo "💡 Quick Start Tips:"
echo "   • Test the system: open http://localhost:3000/test_fas_system.html"
echo "   • View telemetry: tail -f logs/metrics.ndjson"  
echo "   • Check memory: ls -la data/"
echo "   • Monitor performance: curl http://localhost:3000/api/metrics/summary"
echo ""

# Wait for user input or run in background
if [ "$1" = "--wait" ]; then
    echo "Press Enter to stop Alice..."
    read
    
    # Stoppa Next.js
    echo "🛑 Stopping Alice..."
    kill $NEXT_PID 2>/dev/null || true
    echo "✅ Alice stopped"
elif [ "$1" != "--daemon" ]; then
    echo "Alice is running in background (PID: $NEXT_PID)"
    echo "Press Ctrl+C to stop, or run: kill $NEXT_PID"
    
    # Keep script running to catch Ctrl+C
    trap "echo '🛑 Stopping Alice...'; kill $NEXT_PID 2>/dev/null || true; echo '✅ Alice stopped'; exit 0" INT
    
    # Wait for the Next.js process
    wait $NEXT_PID
fi