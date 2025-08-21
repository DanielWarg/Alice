"""
Alice Whisper STT Integration
Hybrid voice system: Browser API för snabba kommandon, Whisper för kvalitet
"""

import os
import tempfile
import uuid
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import UploadFile, HTTPException

logger = logging.getLogger("alice.stt")

# Global Whisper model instance
_whisper_model = None

def get_whisper_model():
    """
    Lazy loading av Whisper-modellen
    Använder samma approach som SupaWhisp
    """
    global _whisper_model
    if _whisper_model is None:
        try:
            # Import här för att undvika startup-delay om Whisper inte används
            from faster_whisper import WhisperModel
            
            # Använd samma konfiguration som SupaWhisp
            _whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
            logger.info("Whisper STT model loaded successfully")
        except ImportError:
            logger.warning("faster-whisper not installed, Whisper STT disabled")
            _whisper_model = None
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            _whisper_model = None
    return _whisper_model

async def transcribe_audio_file(audio_file: UploadFile) -> Dict[str, Any]:
    """
    Transkribera ljudfil med Whisper
    Returnerar samma format som SupaWhisp för kompatibilitet
    """
    model = get_whisper_model()
    if model is None:
        raise HTTPException(
            status_code=503, 
            detail="Whisper STT model not available. Install faster-whisper: pip install faster-whisper"
        )
    
    # Validera att fil existerar
    if not audio_file.filename:
        raise HTTPException(status_code=400, detail="No audio file provided")
    
    # Skapa temporär fil för ljudet
    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
        content = await audio_file.read()
        temp_file.write(content)
        temp_filename = temp_file.name
    
    try:
        # Transkribera med svensk språkstöd
        logger.info(f"Transcribing audio file: {audio_file.filename}")
        segments, info = model.transcribe(temp_filename, language="sv")
        
        # Samla alla segment till en text (samma som SupaWhisp)
        transcription_text = ""
        segments_list = []
        
        for segment in segments:
            transcription_text += segment.text + " "
            segments_list.append({
                'start': segment.start,
                'end': segment.end,
                'text': segment.text.strip()
            })
        
        # Skapa transkriptions-objekt kompatibelt med Alice
        result = {
            'success': True,
            'id': str(uuid.uuid4()),
            'text': transcription_text.strip(),
            'segments': segments_list,
            'language': info.language,
            'language_probability': info.language_probability,
            'duration': info.duration,
            'created_at': datetime.now().isoformat(),
            'filename': audio_file.filename,
            'provider': 'whisper'
        }
        
        logger.info(f"Transcription completed successfully. Duration: {info.duration}s, Language: {info.language}")
        return result
        
    except Exception as e:
        logger.error(f"Whisper transcription error: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
        
    finally:
        # Rensa upp temporär fil
        if os.path.exists(temp_filename):
            os.unlink(temp_filename)

def is_whisper_available() -> bool:
    """Kontrollera om Whisper är tillgängligt"""
    try:
        model = get_whisper_model()
        return model is not None
    except Exception:
        return False

async def get_stt_status() -> Dict[str, Any]:
    """
    Returnera status för STT-systemet
    Inkluderar både Browser API och Whisper status
    """
    return {
        'whisper_available': is_whisper_available(),
        'browser_api_supported': True,  # Alltid tillgängligt i moderna browsers
        'recommended_mode': 'hybrid',   # Rekommenderad approach
        'timestamp': datetime.now().isoformat()
    }