from fastapi import WebSocket, WebSocketDisconnect
from fastapi.routing import APIRouter
import json

router = APIRouter()

async def voice_ws(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            msg = await websocket.receive()
            if "bytes" in msg and msg["bytes"] is not None:
                # binära audioframes – bara räkna / släpp igenom i v0
                continue
            if "text" in msg and msg["text"] is not None:
                try:
                    obj = json.loads(msg["text"])
                except Exception:
                    await websocket.send_text(json.dumps({"type":"error","code":"BAD_JSON"}))
                    continue
                # echo minimal
                if obj.get("type") in ("hello","segment.start","segment.stop"):
                    await websocket.send_text(json.dumps({"type":"state","ok":True,"echo":obj.get("type")}))
    except WebSocketDisconnect:
        pass

def setup(app):
    app.router.add_api_websocket_route("/ws/voice-gateway", voice_ws)

# auto-register if imported
def __getattr__(name):
    if name == "router":
        class _Hook:
            def __init__(self, app=None): pass
        return _Hook()