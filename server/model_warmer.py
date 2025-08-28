"""
Model Warmer Service
Keeps gpt-oss:20b model warm with periodic heartbeat requests
"""
import asyncio
import httpx
import logging
import os
from datetime import datetime

logger = logging.getLogger("alice.model_warmer")

class ModelWarmer:
    """Background service to keep LLM models warm"""
    
    def __init__(self, model: str = "llama3:8b", interval_minutes: int = 8):
        self.model = model
        self.interval_seconds = interval_minutes * 60
        self.base_url = os.getenv("LLM_BASE_URL", "http://localhost:11434")
        self.keep_alive = os.getenv("LLM_KEEP_ALIVE", "10m")
        self.running = False
        
        # Minimal heartbeat prompt
        self.heartbeat_prompt = "hej"
        
        logger.info(f"ModelWarmer initialized: model={model}, interval={interval_minutes}m, keep_alive={self.keep_alive}")
    
    async def send_heartbeat(self) -> bool:
        """Send a minimal request to keep model warm"""
        try:
            payload = {
                "model": self.model,
                "prompt": self.heartbeat_prompt,
                "stream": False,
                "keep_alive": self.keep_alive,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 3  # Very short response
                }
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(f"{self.base_url}/api/generate", json=payload)
                
                if response.status_code == 200:
                    result = response.json()
                    logger.debug(f"Heartbeat sent successfully, response: {result.get('response', '')[:20]}...")
                    return True
                else:
                    logger.warning(f"Heartbeat failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"Heartbeat error: {e}")
            return False
    
    async def check_model_status(self) -> bool:
        """Check if model is currently loaded"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/ps")
                
                if response.status_code == 200:
                    data = response.json()
                    loaded_models = [m.get("name") for m in data.get("models", [])]
                    is_loaded = self.model in loaded_models
                    
                    if is_loaded:
                        # Find expiry time
                        model_info = next((m for m in data["models"] if m.get("name") == self.model), None)
                        expires_at = model_info.get("expires_at") if model_info else None
                        logger.debug(f"Model {self.model} loaded, expires: {expires_at}")
                    else:
                        logger.debug(f"Model {self.model} not loaded")
                    
                    return is_loaded
                else:
                    logger.warning(f"Status check failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"Status check error: {e}")
            return False
    
    async def warm_loop(self):
        """Main warming loop"""
        logger.info(f"Starting model warming loop for {self.model}")
        
        while self.running:
            try:
                # Check current status
                is_loaded = await self.check_model_status()
                
                if not is_loaded:
                    logger.info(f"Model {self.model} not loaded, sending warmup heartbeat...")
                    await self.send_heartbeat()
                else:
                    logger.debug(f"Model {self.model} already loaded, sending keep-alive heartbeat...")
                    await self.send_heartbeat()
                
                # Wait for next interval
                await asyncio.sleep(self.interval_seconds)
                
            except Exception as e:
                logger.error(f"Error in warming loop: {e}")
                # Wait a bit before retrying
                await asyncio.sleep(60)
    
    def start(self):
        """Start the warming service"""
        if not self.running:
            self.running = True
            # Start in background task
            asyncio.create_task(self.warm_loop())
            logger.info(f"ModelWarmer started for {self.model}")
    
    def stop(self):
        """Stop the warming service"""
        self.running = False
        logger.info(f"ModelWarmer stopped for {self.model}")


# Global warmer instance
warmer = None

def start_model_warmer():
    """Start the global model warmer"""
    global warmer
    if not warmer:
        warmer = ModelWarmer()
        warmer.start()

def stop_model_warmer():
    """Stop the global model warmer"""
    global warmer
    if warmer:
        warmer.stop()
        warmer = None