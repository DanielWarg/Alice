"""
Alice Backend Server - Production Ready mit Guardian 2.0
========================================================
- FastAPI server with Ollama + OpenAI fallback
- Guardian 2.0 admission control middleware 
- Structured JSON logging with correlation
- Request timeout protection
- Brownout management with model switching
- Real LLM integration with circuit breaker
"""
from fastapi import FastAPI, HTTPException, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import logging
from dotenv import load_dotenv
import os
import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any

# Import Guardian 2.0 components
from mw_guardian_gate import GuardianGate
from mw_timeout import TimeoutMiddleware, PathTimeoutMiddleware
from log_json import configure_json_logger, jlog, rlog, set_request_context, track_e2e_latency
from brain_model import router as brain_router, get_current_brain_config

# Import LLM system
from llm.ollama import OllamaAdapter
from llm.openai import OpenAIAdapter
from llm.manager import ModelManager

# Import Agent Core system
from core.agent_orchestrator import AgentOrchestrator, WorkflowConfig
from core.tool_registry import validate_and_execute_tool
from model_warmer import start_model_warmer, stop_model_warmer

# Import Database & Chat Service
from database import init_database
# Import performance optimizations
from response_cache import response_cache
from request_batcher import get_request_batcher
from chat_service import chat_service

# Import Voice v2 system
from routes.tts import router as tts_router
from routes.asr import handle_asr_websocket, asr_health
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Load environment
load_dotenv()

# Configure structured logging
log_file = os.getenv("ALICE_LOG_FILE", "logs/alice.jsonl")
configure_json_logger(log_file)

# Configure traditional logging (för fallback)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Log startup
jlog("alice.startup", version="2.0", log_file=log_file)

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
    
    # Initialize Agent Orchestrator
    agent_config = WorkflowConfig(
        max_iterations=2,
        auto_improve=False,  # Keep simple for production
        enable_ai_planning=False,  # Use deterministic planning
        enable_ai_criticism=False  # Use deterministic criticism
    )
    agent_orchestrator = AgentOrchestrator(config=agent_config)
    logger.info("✅ Agent system initialized successfully")
    
except Exception as e:
    logger.error(f"❌ Failed to initialize systems: {e}")
    model_manager = None
    agent_orchestrator = None

# Create FastAPI app
app = FastAPI(
    title="Alice Backend - Production",
    description="Alice backend with Guardian 2.0 protection",
    version="2.0.0"
)

# ===== MIDDLEWARE REGISTRATION (ORDER MATTERS) =====

# 1. CORS (må være først för preflight)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Guardian Gate - admission control (kollar Guardian status) - Optimized
app.add_middleware(
    GuardianGate,
    guardian_url="http://localhost:8787/health",
    cache_ttl_ms=300,     # Längre cache (var 250ms) 
    timeout_s=0.5         # Längre timeout (var 0.25s) för stabilitet
)

# 3. Path-specific timeout middleware
timeout_config = {
    '/api/chat': 30.0,      # LLM generation needs time
    '/api/brain': 15.0,     # Model switching operations
    '/api/agent': 25.0,     # Agent toolchain operations
    '/api/upload': 45.0,    # File uploads
    'default': 10.0         # Standard API requests
}
app.add_middleware(PathTimeoutMiddleware, timeout_config=timeout_config)

# Include brain model router
app.include_router(brain_router)

# Include database router
from database_router import router as database_router
app.include_router(database_router)

# Include Voice v2 TTS router
app.include_router(tts_router)

# ASR WebSocket endpoint
@app.websocket("/ws/asr")
async def websocket_asr(websocket: WebSocket):
    await websocket.accept()
    await handle_asr_websocket(websocket)

# ASR health endpoint
@app.get("/api/asr/health")
async def get_asr_health():
    return await asr_health()

# Include Brain Mail Count stub API
from routes.brain_mail_count import router as brain_mail_router
app.include_router(brain_mail_router)

# Serve static audio files with proper MIME type
from pathlib import Path
AUDIO_DIR = Path(os.getenv("AUDIO_DIR", "./server/voice/audio"))
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

@app.get("/audio/{filename}")
async def serve_audio_file(filename: str):
    """Serve audio files with proper MIME type and CORS headers"""
    
    file_path = AUDIO_DIR / filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    # Determine MIME type based on file extension
    if filename.lower().endswith('.wav'):
        media_type = "audio/wav"
    elif filename.lower().endswith('.mp3'):
        media_type = "audio/mpeg"
    else:
        media_type = "audio/mpeg"  # Default to MP3
    
    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        headers={
            "Accept-Ranges": "bytes",
            "Cache-Control": "public, max-age=31536000, immutable",
            "Access-Control-Allow-Origin": "http://localhost:3000",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
            "Access-Control-Allow-Headers": "Range, Accept",
            "Cross-Origin-Resource-Policy": "cross-origin",
        }
    )

# Serve voice catalog
VOICE_DIR = Path("./voice")
VOICE_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/voice", StaticFiles(directory=str(VOICE_DIR)), name="voice")

# Startup/Shutdown events
@app.on_event("startup")
async def startup_event():
    """Start background services"""
    jlog("alice.backend.startup", version="2.0", guardian_enabled=True, database_enabled=True)
    logger.info("🚀 Starting Alice Backend with Guardian 2.0 + Database")
    
    # Initialize database
    try:
        init_database()
        jlog("alice.database.init", status="success")
        logger.info("🗄️ Database initialized successfully")
    except Exception as e:
        jlog("alice.database.init", status="failed", error=str(e), level="ERROR")
        logger.error(f"❌ Database initialization failed: {e}")
        # Continue startup - database is not critical for basic operation
    
    if model_manager:
        start_model_warmer()
        jlog("alice.model_warmer.start", status="success")
        logger.info("🔥 Model warmer started")
    
    # Validate Guardian connection
    try:
        import httpx
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get("http://localhost:8787/health")
            if response.status_code == 200:
                jlog("alice.guardian.connection", status="ok", level="INFO")
                logger.info("🛡️ Guardian connection validated")
            else:
                jlog("alice.guardian.connection", status="error", 
                     status_code=response.status_code, level="WARN")
                logger.warning(f"⚠️ Guardian returned {response.status_code}")
    except Exception as e:
        jlog("alice.guardian.connection", status="failed", error=str(e), level="ERROR")
        logger.error(f"❌ Guardian connection failed: {e}")

@app.on_event("shutdown") 
async def shutdown_event():
    """Stop background services"""
    jlog("alice.backend.shutdown", graceful=True)
    logger.info("🛑 Shutting down Alice Backend")
    stop_model_warmer()
    jlog("alice.model_warmer.stop", status="success")
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

# Guardian/Brownout related models
class ModelSwitchRequest(BaseModel):
    model: str
    reason: Optional[str] = None

class ConcurrencyRequest(BaseModel):
    concurrency: int

class ContextRequest(BaseModel):
    context_window: int

class RAGRequest(BaseModel):
    top_k: int

class ToolsDisableRequest(BaseModel):
    tools: List[str]
    reason: Optional[str] = None

class ToolsEnableRequest(BaseModel):
    reason: Optional[str] = None

# Global state for Guardian integration
class ServerState:
    def __init__(self):
        self.current_model = os.getenv("LLM_MODEL", "gpt-oss:20b")
        self.current_concurrency = 5
        self.context_window = 8
        self.rag_top_k = 8
        self.disabled_tools = set()
        self.intake_blocked = False
        self.degraded = False

server_state = ServerState()

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
async def chat_endpoint(request: ChatRequest, http_request: Request):
    """Production chat endpoint with Guardian protection and structured logging"""
    
    # Setup request correlation
    request_id = getattr(http_request.state, 'request_id', 'unknown')
    set_request_context(request_id, user_id=None, lane="chat")
    start_time = datetime.now()
    
    # Check cache först för potential immediate response
    cached_response = await response_cache.get(
        message=request.message,
        model="default",
        context=""
    )
    
    if cached_response:
        rlog("chat.cache_hit", 
             message_len=len(request.message),
             hit_rate=response_cache.get_stats()['hit_rate_percent'],
             level="INFO")
        return cached_response
    
    # Process chat request with database persistence
    chat_request_result = chat_service.process_chat_request(
        user_message=request.message,
        username="alice_user",  # Default user for now
        conversation_id=getattr(request, 'conversation_id', None)
    )
    
    conversation_id = chat_request_result.get('conversation_id') if chat_request_result.get('success') else None
    
    # Log request
    rlog("chat.request_start", 
         message_len=len(request.message),
         conversation_id=conversation_id,
         level="INFO")
    
    if not model_manager:
        rlog("chat.request_failed", reason="llm_not_initialized", level="ERROR")
        raise HTTPException(status_code=503, detail="LLM system not initialized")
    
    # Check if intake is blocked (redundant with middleware but good for logging)
    if server_state.intake_blocked:
        rlog("chat.request_blocked", reason="intake_blocked", level="WARN")
        raise HTTPException(status_code=429, detail="System overloaded - requests temporarily blocked")
    
    try:
        # Get current brain config for brownout support
        brain_config = get_current_brain_config()
        
        # Build system message based on current mode
        if brain_config["mode"] == "brownout":
            system_content = "Du är Alice. Svara MYCKET kort och koncist på svenska (max 50 ord)."
            rlog("chat.brownout_mode", context_window=brain_config["context_window"])
        else:
            system_content = "Du är Alice, en hjälpsam svensk AI-assistent. Svara kort och vänligt på svenska."
        
        # Log agent request start
        rlog("chat.agent_request_start", 
             model=brain_config["model"],
             mode=brain_config["mode"])
        
        # Use agent orchestrator instead of direct LLM for tool support
        if agent_orchestrator:
            try:
                logger.info(f"🤖 Executing agent goal: {request.message}")
                success, agent_result = await agent_orchestrator.execute_simple_goal(
                    goal=request.message,
                    context={
                        "conversation_id": conversation_id,
                        "brownout_mode": brain_config["mode"] == "brownout",
                        "user": "alice_user"
                    }
                )
                logger.info(f"🤖 Agent result - Success: {success}, Results: {agent_result}")
                
                # Convert agent result to response format
                class MockResponse:
                    def __init__(self, text, provider, tftt_ms):
                        self.text = text
                        self.provider = provider
                        self.tftt_ms = tftt_ms
                
                response_time_ms = (datetime.now() - start_time).total_seconds() * 1000
                
                # Extract actual response from agent execution results
                agent_text = "Agent system processed request"
                
                # First, check if we have actual execution results with tool outputs
                if success and agent_result.get("execution_results"):
                    results = agent_result["execution_results"]
                    if results and len(results) > 0:
                        # execution_results is a dict with step_id -> ExecutionResult
                        # Get the first/any completed execution result
                        for step_id, exec_result in results.items():
                            if hasattr(exec_result, 'result') and exec_result.result:
                                message = exec_result.result.get('message')
                                if message:
                                    agent_text = message
                                    break
                elif success and agent_result.get("actions_completed", 0) > 0:
                    agent_text = agent_result.get("critic_summary", "Task completed successfully")
                elif not success:
                    # Agent couldn't handle request - fallback to LLM
                    logger.info(f"Agent failed, falling back to LLM for: {request.message}")
                    raise Exception("Agent workflow failed, falling back to LLM")
                
                response = MockResponse(
                    text=agent_text,
                    provider=f"agent:{brain_config['model']}",
                    tftt_ms=response_time_ms
                )
                
            except Exception as e:
                logger.error(f"Agent orchestrator failed: {e}")
                # Fallback to direct LLM on agent failure
                messages = [
                    {
                        "role": "system",
                        "content": system_content
                    },
                    {
                        "role": "user", 
                        "content": request.message
                    }
                ]
                
                response = await model_manager.ask(messages)
        else:
            # Fallback to direct LLM if agent not available
            messages = [
                {
                    "role": "system",
                    "content": system_content
                },
                {
                    "role": "user", 
                    "content": request.message
                }
            ]
            
            response = await model_manager.ask(messages)
            
        # Response ready from agent or LLM fallback
        
        # Calculate end-to-end latency
        e2e_latency = (datetime.now() - start_time).total_seconds() * 1000
        
        # Track KPIs
        track_e2e_latency(int(e2e_latency), request_id)
        
        # Save assistant response to database
        if conversation_id:
            save_result = chat_service.save_assistant_response(
                conversation_id=conversation_id,
                response_content=response.text,
                model_used=response.provider,
                response_time_ms=response.tftt_ms,
                extra_metadata={
                    "request_id": request_id,
                    "brain_config": brain_config,
                    "e2e_latency_ms": int(e2e_latency)
                }
            )
            if not save_result.get('success'):
                rlog("chat.database_save_failed", error=save_result.get('error'), level="WARN")
        
        # Cache response för future requests
        await response_cache.put(
            message=request.message,
            response=response.text,
            model=response.provider,
            tftt_ms=response.tftt_ms
        )
        
        # Log successful response with performance metrics
        rlog("chat.request_success",
             response_len=len(response.text),
             model_used=response.provider,
             tftt_ms=response.tftt_ms,
             e2e_ms=int(e2e_latency),
             cache_stats=response_cache.get_stats(),
             batch_stats=get_request_batcher().get_stats(),
             conversation_id=conversation_id)
        
        return ChatResponse(
            response=response.text,
            timestamp=datetime.now().isoformat(),
            model=response.provider,
            tftt_ms=response.tftt_ms
        )
        
    except Exception as e:
        # Calculate error latency
        error_latency = (datetime.now() - start_time).total_seconds() * 1000
        
        # Log error with full context
        rlog("chat.request_error", 
             error=str(e),
             error_type=type(e).__name__,
             e2e_ms=int(error_latency),
             level="ERROR")
        
        # Track fallback if this was a brownout-related error
        if "timeout" in str(e).lower() or "overload" in str(e).lower():
            from log_json import track_fallback
            track_fallback("llm_timeout", str(e), request_id)
        
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")

# === GUARDIAN INTEGRATION ENDPOINTS ===

@app.post("/api/brain/model/switch")
async def switch_model(request: ModelSwitchRequest):
    """Switch LLM model for brownout degradation"""
    try:
        # Validate model
        if request.model not in ["gpt-oss:20b", "gpt-oss:7b"]:
            raise HTTPException(status_code=400, detail=f"Unsupported model: {request.model}")
        
        old_model = server_state.current_model
        server_state.current_model = request.model
        
        # Update the LLM adapter if possible
        if model_manager and hasattr(model_manager.primary, 'model'):
            model_manager.primary.model = request.model
            logger.info(f"Model switched: {old_model} -> {request.model} (reason: {request.reason})")
        
        return {
            "status": "success",
            "previous_model": old_model,
            "current_model": request.model,
            "reason": request.reason,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Model switch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/guard/set-concurrency")
async def set_concurrency(request: ConcurrencyRequest):
    """Set system concurrency for auto-tuning"""
    try:
        if request.concurrency < 1 or request.concurrency > 20:
            raise HTTPException(status_code=400, detail="Concurrency must be between 1 and 20")
        
        old_concurrency = server_state.current_concurrency
        server_state.current_concurrency = request.concurrency
        
        logger.info(f"Concurrency updated: {old_concurrency} -> {request.concurrency}")
        
        return {
            "status": "success",
            "previous_concurrency": old_concurrency,
            "current_concurrency": request.concurrency,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Concurrency update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/brain/context/set")
async def set_context_window(request: ContextRequest):
    """Set context window for brownout degradation"""
    try:
        if request.context_window < 1 or request.context_window > 32:
            raise HTTPException(status_code=400, detail="Context window must be between 1 and 32")
        
        old_context = server_state.context_window
        server_state.context_window = request.context_window
        
        logger.info(f"Context window updated: {old_context} -> {request.context_window}")
        
        return {
            "status": "success",
            "previous_context_window": old_context,
            "current_context_window": request.context_window,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Context window update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/brain/rag/set")
async def set_rag_settings(request: RAGRequest):
    """Set RAG top_k for brownout degradation"""
    try:
        if request.top_k < 1 or request.top_k > 20:
            raise HTTPException(status_code=400, detail="RAG top_k must be between 1 and 20")
        
        old_top_k = server_state.rag_top_k
        server_state.rag_top_k = request.top_k
        
        logger.info(f"RAG top_k updated: {old_top_k} -> {request.top_k}")
        
        return {
            "status": "success",
            "previous_top_k": old_top_k,
            "current_top_k": request.top_k,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"RAG settings update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/brain/tools/disable")
async def disable_tools(request: ToolsDisableRequest):
    """Disable heavy toolchains for brownout degradation"""
    try:
        for tool in request.tools:
            server_state.disabled_tools.add(tool)
        
        logger.info(f"Tools disabled: {', '.join(request.tools)} (reason: {request.reason})")
        
        return {
            "status": "success",
            "disabled_tools": list(request.tools),
            "all_disabled_tools": list(server_state.disabled_tools),
            "reason": request.reason,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Tool disabling failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/brain/tools/enable-all")
async def enable_all_tools(request: ToolsEnableRequest):
    """Re-enable all tools after brownout recovery"""
    try:
        disabled_tools = list(server_state.disabled_tools)
        server_state.disabled_tools.clear()
        
        logger.info(f"All tools re-enabled (reason: {request.reason})")
        
        return {
            "status": "success",
            "previously_disabled_tools": disabled_tools,
            "reason": request.reason,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Tool enabling failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/guard/degrade")
async def degrade_system():
    """Basic system degradation"""
    server_state.degraded = True
    logger.warning("System degradation activated")
    return {"status": "degraded", "timestamp": datetime.now().isoformat()}

@app.post("/api/guard/stop-intake")
async def stop_intake():
    """Stop accepting new requests"""
    server_state.intake_blocked = True
    logger.error("Intake stopped - system overloaded")
    return {"status": "intake_blocked", "timestamp": datetime.now().isoformat()}

@app.post("/api/guard/resume-intake")
async def resume_intake():
    """Resume accepting new requests"""
    server_state.intake_blocked = False
    server_state.degraded = False
    logger.info("Intake resumed - system recovered")
    return {"status": "normal", "timestamp": datetime.now().isoformat()}

@app.get("/api/brain/status")
async def get_brain_status():
    """Get current brain/system status"""
    return {
        "current_model": server_state.current_model,
        "concurrency": server_state.current_concurrency,
        "context_window": server_state.context_window,
        "rag_top_k": server_state.rag_top_k,
        "disabled_tools": list(server_state.disabled_tools),
        "intake_blocked": server_state.intake_blocked,
        "degraded": server_state.degraded,
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)