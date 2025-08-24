#!/usr/bin/env python3
"""
Minimal test server för att verifiera ambient memory endpoints
Använder bara de komponenter vi behöver
"""

import sys
import os
from pathlib import Path

# Lägg till server path
sys.path.insert(0, str(Path(__file__).parent / 'server'))

# Set up minimal environment
os.environ.setdefault('AMBIENT_RAW_TTL_MIN', '120')
os.environ.setdefault('OPENAI_API_KEY', 'test-key-disabled')

try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
    
    # Import our services
    from logger_config import setup_ambient_logging
    from services.ambient_memory import router as ambient_router
    from services.realtime_asr import router as asr_router
    from services.reflection import router as reflection_router
    
    # Setup logging
    setup_ambient_logging("INFO")
    
    # Create minimal FastAPI app
    app = FastAPI(title="Alice Ambient Memory Test Server", version="1.0.0")
    
    # Add CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"], 
        allow_headers=["*"],
    )
    
    # Include our routers
    app.include_router(ambient_router)
    app.include_router(asr_router)
    app.include_router(reflection_router)
    
    @app.get("/health")
    async def health_check():
        return {"status": "ok", "service": "alice-ambient-memory"}
    
    @app.get("/")
    async def root():
        return {
            "message": "Alice Ambient Memory Test Server",
            "endpoints": [
                "/health",
                "/api/memory/ambient/stats",
                "/api/memory/ambient/ingest-raw",
                "/api/memory/ambient/summary", 
                "/api/memory/ambient/clean",
                "/api/reflect/observe",
                "/api/reflect/questions",
                "/ws/realtime-asr"
            ]
        }
    
    if __name__ == "__main__":
        print("🚀 Starting Alice Ambient Memory Test Server...")
        print("📍 Available endpoints:")
        print("  GET  /health")
        print("  GET  /api/memory/ambient/stats")
        print("  POST /api/memory/ambient/ingest-raw") 
        print("  POST /api/memory/ambient/summary")
        print("  POST /api/memory/ambient/clean")
        print("  POST /api/reflect/observe")
        print("  GET  /api/reflect/questions")
        print("  WS   /ws/realtime-asr")
        print()
        
        uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
        
except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    print("💡 Run: cd server && source .venv/bin/activate && pip install fastapi uvicorn")
    sys.exit(1)