from fastapi import APIRouter
import time

router = APIRouter()

# kan senare räkna anslutna devices från VoiceGateway
@router.get("/api/probe/health")
def probe_health():
    return {"ok": True, "ts": time.time(), "devices": 0}