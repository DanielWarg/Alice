"""
Minimal Alice Backend Server
- Core FastAPI server utan extra dependencies  
- Basic health check endpoint
- LLM status endpoint
- Kan köras isolerat för att testa backend-connectivity
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from dotenv import load_dotenv
import os

# Load environment
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Alice Backend - Minimal",
    description="Core Alice backend server without voice dependencies",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Alice Backend - Minimal", "status": "running"}

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "ok",
        "timestamp": "2025-08-28",
        "service": "alice-backend-minimal"
    }

@app.get("/api/v1/llm/status")
async def llm_status():
    """Mock LLM status - will be replaced with real implementation"""
    return {
        "coordinator": "active",
        "models": {
            "primary": {
                "name": "minimal-mock",
                "failure_count": 0,
                "circuit_breaker_open": False,
                "health_status": {
                    "ok": True,
                    "tftt_ms": 100
                }
            },
            "fallback": {
                "name": "openai-gpt-4o-mini"
            }
        }
    }

@app.post("/api/chat")
async def chat_endpoint(request: dict):
    """Mock chat endpoint"""
    message = request.get("message", "")
    return {
        "response": f"Echo (backend): {message}",
        "timestamp": "2025-08-28",
        "model": "minimal-backend"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)