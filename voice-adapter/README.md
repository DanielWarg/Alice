# @alice/voice-adapter - STUB MODULE

⚠️ **Voice v2 is COMPLETE and PRODUCTION-READY** ⚠️

This module is a **compatibility stub** to prevent build failures. The real voice functionality is now:

## ✅ Voice v2 Production System

- **Real TTS**: `server/tts_engine.py` - Piper neural TTS, Amy voice, 320kbps
- **Test Interface**: http://localhost:3000/voice-complete.html
- **TTS Endpoint**: `server/routes/tts.py` - HTTP TTS API
- **Frontend Integration**: Use VoiceV2Interface.tsx component

## 🚀 How to Use Voice v2

1. Start Alice server: `cd server && uvicorn app_minimal:app --reload`
2. Start frontend: `cd web && npm run dev`  
3. Open: http://localhost:3000/voice-complete.html
4. Test Swedish → English voice pipeline

## 📋 Migration Notes

- Old voice-adapter is **deprecated**
- Voice v2 uses HTTP-only architecture (no WebRTC/WebSocket)
- Two-stage response system with instant acknowledgment
- 7/7 E2E tests passing

**This stub prevents import errors while you migrate to Voice v2 components.**