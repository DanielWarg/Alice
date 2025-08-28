"""
Alice Backend Server - Real LLM Integration
- FastAPI server with Ollama + OpenAI fallback
- Real LLM status endpoint with health checks
- Text chat endpoint with agent system integration
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import logging
from dotenv import load_dotenv
import os
import asyncio
from datetime import datetime

# Import LLM system
from llm.ollama import OllamaAdapter
from llm.openai import OpenAIAdapter
from llm.manager import ModelManager
from model_warmer import start_model_warmer, stop_model_warmer

# Load environment
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize LLM system
try:
    # Primary: Ollama with gpt-oss:20b
    primary_llm = OllamaAdapter(
        base_url=os.getenv("LLM_BASE_URL", "http://localhost:11434"),
        model=os.getenv("LLM_MODEL", "gpt-oss:20b")
    )
    
    # Fallback: OpenAI GPT-4o-mini
    fallback_llm = OpenAIAdapter(
        api_key=os.getenv("OPENAI_API_KEY"),
        model=os.getenv("FALLBACK_MODEL", "gpt-4o-mini")
    )
    
    # Create model manager with circuit breaker
    model_manager = ModelManager(primary=primary_llm, fallback=fallback_llm)
    logger.info("✅ LLM system initialized successfully")
    
except Exception as e:
    logger.error(f"❌ Failed to initialize LLM system: {e}")
    model_manager = None

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

# Startup/Shutdown events
@app.on_event("startup")
async def startup_event():
    """Start background services"""
    logger.info("🚀 Starting Alice Backend")
    if model_manager:
        start_model_warmer()
        logger.info("🔥 Model warmer started")

@app.on_event("shutdown") 
async def shutdown_event():
    """Stop background services"""
    logger.info("🛑 Shutting down Alice Backend")
    stop_model_warmer()
    logger.info("❄️ Model warmer stopped")

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

# Request/Response models
class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    timestamp: str
    model: str
    tftt_ms: float = None

@app.get("/api/v1/llm/status")
async def llm_status():
    """Real LLM status with health checks"""
    if not model_manager:
        return {
            "coordinator": "error",
            "error": "LLM system not initialized",
            "models": {}
        }
    
    try:
        status = model_manager.get_status()
        return {
            "coordinator": "active",
            "models": status
        }
    except Exception as e:
        logger.error(f"Failed to get LLM status: {e}")
        return {
            "coordinator": "error", 
            "error": str(e),
            "models": {}
        }

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """Real chat endpoint with Alice AI"""
    if not model_manager:
        raise HTTPException(status_code=503, detail="LLM system not initialized")
    
    try:
        # Convert to OpenAI message format
        messages = [
            {
                "role": "system",
                "content": "Du är Alice, en hjälpsam svensk AI-assistent. Svara kort och vänligt på svenska."
            },
            {
                "role": "user", 
                "content": request.message
            }
        ]
        
        # Send to LLM via model manager (with automatic failover)
        response = await model_manager.ask(messages)
        
        return ChatResponse(
            response=response.text,
            timestamp=datetime.now().isoformat(),
            model=response.provider,
            tftt_ms=response.tftt_ms
        )
        
    except Exception as e:
        logger.error(f"Chat request failed: {e}")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)