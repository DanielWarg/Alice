"""
Alice Whisper STT Integration
Hybrid voice system: Browser API för snabba kommandon, Whisper för kvalitet
"""

import os
import time
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
            
            # Optimerad konfiguration för svenskt tal
            # Använd small-modellen för bättre svensk accuracy vid rimlig prestanda
            _whisper_model = WhisperModel(
                "small", 
                device="cpu", 
                compute_type="int8",
                download_root="./models"  # Lokalt cache för modeller
            )
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
        # Transkribera med optimerade inställningar för svenska
        logger.info(f"Transcribing audio file: {audio_file.filename}")
        segments, info = model.transcribe(
            temp_filename, 
            language="sv",
            beam_size=5,  # Högre beam size för bättre accuracy
            best_of=3,    # Generera flera kandidater och välj bästa
            temperature=0.0,  # Deterministisk för konsistens
            condition_on_previous_text=True,  # Använd kontext
            initial_prompt="Detta är svenska tal med kommandon till AI-assistenten Alice.",  # Kontext för bättre igenkänning
            word_timestamps=True  # Aktivera ordtidsstämplar för framtida funktioner
        )
        
        # Samla alla segment med förbättrad textbehandling
        transcription_text = ""
        segments_list = []
        word_level_data = []
        
        for segment in segments:
            # Rensa bort onödiga mellanslag och normalisera text
            clean_text = segment.text.strip()
            if clean_text:  # Skippa tomma segment
                transcription_text += clean_text + " "
                segment_data = {
                    'start': segment.start,
                    'end': segment.end,
                    'text': clean_text,
                    'confidence': getattr(segment, 'avg_logprob', 0.0)  # Konfidenspoäng om tillgänglig
                }
                
                # Lägg till ordnivå-data om tillgängligt
                if hasattr(segment, 'words') and segment.words:
                    segment_data['words'] = [
                        {
                            'word': word.word.strip(),
                            'start': word.start,
                            'end': word.end,
                            'confidence': getattr(word, 'probability', 0.0)
                        } for word in segment.words if word.word.strip()
                    ]
                    word_level_data.extend(segment_data['words'])
                
                segments_list.append(segment_data)
        
        # Post-processing för svensk text
        transcription_text = transcription_text.strip()
        transcription_text = _postprocess_swedish_text(transcription_text)
        
        # Skapa förbättrat transkriptions-objekt kompatibelt med Alice
        result = {
            'success': True,
            'id': str(uuid.uuid4()),
            'text': transcription_text,
            'segments': segments_list,
            'words': word_level_data,
            'language': info.language,
            'language_probability': info.language_probability,
            'duration': info.duration,
            'created_at': datetime.now().isoformat(),
            'filename': audio_file.filename,
            'provider': 'whisper-enhanced',
            'model': 'small',
            'processing_time': None,  # Kommer fyllas i senare
            'audio_quality': _assess_audio_quality(info)  # Bedömning av ljudkvalitet
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

def _postprocess_swedish_text(text: str) -> str:
    """
    Post-processing för att förbättra svensk textaccuracy
    Hanterar vanliga Whisper-fel för svenska
    """
    if not text:
        return text
    
    # Vanliga svenska korrigeringar
    corrections = {
        # Whisper tenderar att skriva engelska ord istället för svenska
        "okay": "okej",
        "ok": "okej", 
        "hello": "hej",
        "hi": "hej",
        "bye": "hej då",
        "yes": "ja",
        "no": "nej",
        "please": "tack",
        "thank you": "tack",
        "sorry": "förlåt",
        
        # Vanliga svenska AI-kommandon som ofta missuppfattas
        "alice": "Alice",
        "allis": "Alice",
        "alis": "Alice",
        "play music": "spela musik",
        "stop music": "stoppa musik", 
        "pause music": "pausa musik",
        "send email": "skicka mejl",
        "read email": "läs mejl",
        "what time": "vad är klockan",
        "what's the time": "vad är klockan",
        
        # Svenska tal-specifika korrigeringar
        "å": "å",
        "ä": "ä", 
        "ö": "ö",
    }
    
    # Applicera korrigeringar (case-insensitive för de flesta)
    corrected_text = text
    for wrong, right in corrections.items():
        # Case-insensitive replacement men behåll original case för Alice
        if wrong.lower() != "alice":
            corrected_text = corrected_text.replace(wrong.lower(), right)
            corrected_text = corrected_text.replace(wrong.capitalize(), right.capitalize())
        else:
            # Special handling för Alice - alltid stor bokstav
            corrected_text = corrected_text.replace(wrong.lower(), right)
            corrected_text = corrected_text.replace(wrong.upper(), right)
    
    return corrected_text.strip()

def _assess_audio_quality(info) -> Dict[str, Any]:
    """
    Bedöm ljudkvaliteteten baserat på Whisper-info
    Hjälper med debugging och kvalitetsförbättringar
    """
    duration = info.duration
    
    # Grundläggande kvalitetsbedömning
    quality_score = "good"
    issues = []
    
    if duration < 1.0:
        quality_score = "poor"
        issues.append("very_short_audio")
    elif duration > 30.0:
        quality_score = "fair"
        issues.append("long_audio_may_affect_accuracy")
        
    # Språkprobabilitet som kvalitetsindikator
    if info.language_probability < 0.8:
        if quality_score == "good":
            quality_score = "fair"
        issues.append("low_language_confidence")
    
    return {
        "overall_score": quality_score,
        "duration": duration,
        "language_probability": info.language_probability,
        "detected_language": info.language,
        "issues": issues,
        "recommendations": _get_quality_recommendations(quality_score, issues)
    }

def _get_quality_recommendations(score: str, issues: list) -> list:
    """Generera rekommendationer baserat på kvalitetsbedömning"""
    recommendations = []
    
    if "very_short_audio" in issues:
        recommendations.append("Tala längre för bättre accuracy")
    
    if "long_audio_may_affect_accuracy" in issues:
        recommendations.append("Dela upp långa meddelanden för bättre resultat")
        
    if "low_language_confidence" in issues:
        recommendations.append("Tala tydligare svenska eller kontrollera mikrofonkvalitet")
    
    if score == "poor":
        recommendations.append("Kontrollera mikrofoninställningar och bakgrundsljud")
    
    return recommendations

async def transcribe_with_fallback(audio_file: UploadFile, prefer_quality: bool = True) -> Dict[str, Any]:
    """
    Förbättrad transkribering med fallback-strategier
    """
    start_time = time.time()
    
    try:
        # Primär transkribering
        result = await transcribe_audio_file(audio_file)
        result['processing_time'] = time.time() - start_time
        return result
        
    except Exception as e:
        logger.warning(f"Primary transcription failed: {e}")
        
        # Fallback: försök med enklare inställningar
        try:
            model = get_whisper_model()
            if model is None:
                raise Exception("Whisper model not available for fallback")
            
            # Skapa temporär fil
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
                content = await audio_file.read()
                temp_file.write(content)
                temp_filename = temp_file.name
            
            try:
                # Enklare inställningar för fallback
                segments, info = model.transcribe(
                    temp_filename,
                    language="sv",
                    beam_size=1,  # Snabbare men mindre accurate
                    temperature=0.0
                )
                
                # Förenklad textextrahering
                text = " ".join([segment.text.strip() for segment in segments if segment.text.strip()])
                text = _postprocess_swedish_text(text)
                
                result = {
                    'success': True,
                    'id': str(uuid.uuid4()),
                    'text': text,
                    'segments': [],  # Tomt för fallback
                    'words': [],
                    'language': info.language,
                    'language_probability': info.language_probability,
                    'duration': info.duration,
                    'created_at': datetime.now().isoformat(),
                    'filename': audio_file.filename,
                    'provider': 'whisper-fallback',
                    'model': 'small-fallback',
                    'processing_time': time.time() - start_time,
                    'fallback_used': True,
                    'original_error': str(e)
                }
                
                return result
                
            finally:
                if os.path.exists(temp_filename):
                    os.unlink(temp_filename)
                    
        except Exception as fallback_error:
            logger.error(f"Fallback transcription also failed: {fallback_error}")
            raise HTTPException(
                status_code=500,
                detail=f"Both primary and fallback transcription failed. Primary: {str(e)}, Fallback: {str(fallback_error)}"
            )

async def get_stt_status() -> Dict[str, Any]:
    """
    Returnera förbättrad status för STT-systemet
    Inkluderar både Browser API och Whisper status samt prestanda-info
    """
    whisper_available = is_whisper_available()
    
    status = {
        'whisper_available': whisper_available,
        'browser_api_supported': True,  # Alltid tillgängligt i moderna browsers
        'recommended_mode': 'hybrid',   # Rekommenderad approach
        'timestamp': datetime.now().isoformat(),
        'features': {
            'swedish_optimization': True,
            'post_processing': True,
            'fallback_transcription': True,
            'word_level_timestamps': whisper_available,
            'quality_assessment': True,
            'noise_handling': False,  # Kommer i nästa steg
            'voice_activity_detection': False,  # Kommer i nästa steg
            'wake_word': False  # Kommer i nästa steg
        }
    }
    
    if whisper_available:
        # Test model loading time
        start_time = time.time()
        model = get_whisper_model() 
        load_time = time.time() - start_time
        
        status['whisper_details'] = {
            'model': 'small',
            'language': 'sv',
            'load_time_seconds': round(load_time, 3),
            'compute_type': 'int8',
            'device': 'cpu'
        }
    
    return status