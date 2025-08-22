"""
OpenAI Realtime API Dependencies and Configuration
Konfigurationshantering för OpenAI Realtime integration med Alice.
"""

from __future__ import annotations

import os
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger("alice.deps")


class VoiceModel(str, Enum):
    """Tillgängliga röstmodeller för OpenAI TTS"""
    ALLOY = "alloy"
    ECHO = "echo" 
    FABLE = "fable"
    ONYX = "onyx"
    NOVA = "nova"
    SHIMMER = "shimmer"


class TTSModel(str, Enum):
    """TTS-modeller för OpenAI"""
    TTS_1 = "tts-1"
    TTS_1_HD = "tts-1-hd"


class STTModel(str, Enum):
    """STT-modeller för OpenAI"""
    WHISPER_1 = "whisper-1"


class RealtimeModel(str, Enum):
    """Realtime API-modeller"""
    GPT_4O_REALTIME_PREVIEW = "gpt-4o-realtime-preview"
    GPT_4O_REALTIME_PREVIEW_2024_10_01 = "gpt-4o-realtime-preview-2024-10-01"


@dataclass
class VoiceSettings:
    """Röstinställningar för TTS"""
    model: TTSModel = TTSModel.TTS_1
    voice: VoiceModel = VoiceModel.NOVA
    speed: float = 1.0  # 0.25 - 4.0
    response_format: str = "mp3"  # mp3, opus, aac, flac, wav, pcm


@dataclass
class RealtimeSessionConfig:
    """Konfiguration för Realtime API-session"""
    model: RealtimeModel = RealtimeModel.GPT_4O_REALTIME_PREVIEW
    voice: VoiceModel = VoiceModel.NOVA
    instructions: str = ""
    modalities: List[str] = field(default_factory=lambda: ["text", "audio"])
    input_audio_format: str = "pcm16"
    output_audio_format: str = "pcm16" 
    input_audio_transcription: Optional[Dict[str, Any]] = None
    turn_detection: Optional[Dict[str, Any]] = None
    tools: List[Dict[str, Any]] = field(default_factory=list)
    tool_choice: str = "auto"
    temperature: float = 0.8
    max_response_output_tokens: int = 4096


@dataclass
class OpenAISettings:
    """Huvud-konfiguration för OpenAI-integration"""
    # API-konfiguration
    api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    organization: Optional[str] = field(default_factory=lambda: os.getenv("OPENAI_ORG_ID"))
    base_url: str = "https://api.openai.com/v1"
    
    # Realtime API
    realtime_url: str = "wss://api.openai.com/v1/realtime"
    realtime_model: RealtimeModel = RealtimeModel.GPT_4O_REALTIME_PREVIEW
    
    # Standardmodeller
    chat_model: str = field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    embedding_model: str = "text-embedding-3-small"
    
    # TTS/STT
    voice_settings: VoiceSettings = field(default_factory=VoiceSettings)
    stt_model: STTModel = STTModel.WHISPER_1
    
    # Session-konfiguration
    session_config: RealtimeSessionConfig = field(default_factory=RealtimeSessionConfig)
    
    # Timeouts och gränser
    timeout_seconds: int = 30
    max_tokens: int = 4096
    temperature: float = 0.7
    
    # Rate limiting
    max_requests_per_minute: int = 3000  # Tier 1 limit
    max_tokens_per_minute: int = 200000  # Tier 1 limit
    
    def __post_init__(self):
        """Validera konfiguration efter initialisering"""
        if not self.api_key:
            logger.warning("OpenAI API key saknas. Sätt OPENAI_API_KEY i environment.")
        
        # Sätt standard-instruktioner för Alice
        if not self.session_config.instructions:
            self.session_config.instructions = self._get_alice_instructions()
    
    def _get_alice_instructions(self) -> str:
        """Hämta Alice's systeminstruktioner för Realtime API"""
        return """Du är Alice, en svensk AI-assistent. Du svarar alltid på svenska och är hjälpsam, vänlig och engagerad.

Du har tillgång till olika verktyg för att hjälpa användaren:
- Musikstyrning (spela, pausa, volym, etc.)
- Kalenderhantering
- E-postfunktioner
- Allmän assistans

När du använder verktyg, förklara kort vad du gör på svenska.
Håll dina svar koncisa men informativa.
Använd naturligt svenskt språk utan att låta robotisk."""

    @property
    def headers(self) -> Dict[str, str]:
        """Hämta HTTP-headers för OpenAI API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Alice-Assistant/1.0"
        }
        
        if self.organization:
            headers["OpenAI-Organization"] = self.organization
            
        return headers
    
    @property
    def websocket_headers(self) -> Dict[str, str]:
        """Headers för WebSocket-anslutning till Realtime API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "OpenAI-Beta": "realtime=v1"
        }
        
        if self.organization:
            headers["OpenAI-Organization"] = self.organization
            
        return headers


class OpenAIClient:
    """HTTP-klient för OpenAI API med Alice-specifika inställningar"""
    
    def __init__(self, settings: Optional[OpenAISettings] = None):
        self.settings = settings or OpenAISettings()
        self._client: Optional[httpx.AsyncClient] = None
    
    async def get_client(self) -> httpx.AsyncClient:
        """Hämta eller skapa async HTTP-klient"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.settings.base_url,
                headers=self.settings.headers,
                timeout=httpx.Timeout(self.settings.timeout_seconds)
            )
        return self._client
    
    async def close(self):
        """Stäng HTTP-klient"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    async def __aenter__(self):
        return await self.get_client()
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


def get_openai_settings() -> OpenAISettings:
    """Factory-funktion för att hämta OpenAI-inställningar"""
    return OpenAISettings()


def validate_openai_config(settings: Optional[OpenAISettings] = None) -> Dict[str, Any]:
    """
    Validera OpenAI-konfiguration och returnera status.
    
    Returns:
        Dict med validation results:
        - valid: bool
        - errors: List[str] 
        - warnings: List[str]
        - config_summary: Dict[str, Any]
    """
    if settings is None:
        settings = get_openai_settings()
    
    errors = []
    warnings = []
    
    # Validera API key
    if not settings.api_key:
        errors.append("OpenAI API key saknas (OPENAI_API_KEY)")
    elif len(settings.api_key) < 20:
        warnings.append("OpenAI API key verkar vara för kort")
    
    # Validera URL:er
    if not settings.base_url.startswith(("http://", "https://")):
        errors.append("Ogiltig base_url för OpenAI API")
    
    if not settings.realtime_url.startswith(("ws://", "wss://")):
        errors.append("Ogiltig realtime_url för WebSocket")
    
    # Validera numeriska värden
    if not (0.25 <= settings.voice_settings.speed <= 4.0):
        warnings.append("TTS-hastighet bör vara mellan 0.25 och 4.0")
    
    if not (0.0 <= settings.temperature <= 2.0):
        warnings.append("Temperature bör vara mellan 0.0 och 2.0")
    
    if settings.max_tokens > 128000:  # GPT-4o max context
        warnings.append("max_tokens överstiger rekommenderat värde")
    
    # Sammanställning
    config_summary = {
        "api_configured": bool(settings.api_key),
        "organization_set": bool(settings.organization),
        "realtime_model": settings.realtime_model.value,
        "chat_model": settings.chat_model,
        "voice_model": settings.voice_settings.voice.value,
        "tts_model": settings.voice_settings.model.value,
        "max_tokens": settings.max_tokens,
        "temperature": settings.temperature
    }
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "config_summary": config_summary
    }


# Global instans för att dela inställningar
_global_settings: Optional[OpenAISettings] = None

def get_global_openai_settings() -> OpenAISettings:
    """Hämta global OpenAI-inställningar (singleton)"""
    global _global_settings
    if _global_settings is None:
        _global_settings = OpenAISettings()
    return _global_settings


def set_global_openai_settings(settings: OpenAISettings):
    """Sätt global OpenAI-inställningar"""
    global _global_settings
    _global_settings = settings


# Convenience function för snabb klientaccess
async def get_openai_client() -> httpx.AsyncClient:
    """Skapa en OpenAI HTTP-klient med globala inställningar"""
    settings = get_global_openai_settings()
    client = OpenAIClient(settings)
    return await client.get_client()


# Environment variable helpers
def load_openai_env() -> Dict[str, str]:
    """Ladda alla OpenAI-relaterade miljövariabler"""
    env_vars = {}
    openai_keys = [
        "OPENAI_API_KEY",
        "OPENAI_ORG_ID", 
        "OPENAI_MODEL",
        "OPENAI_BASE_URL"
    ]
    
    for key in openai_keys:
        value = os.getenv(key)
        if value:
            env_vars[key] = value
    
    return env_vars


def check_openai_env() -> bool:
    """Snabb kontroll om OpenAI är konfigurerat"""
    return bool(os.getenv("OPENAI_API_KEY"))


if __name__ == "__main__":
    # Test-kod för att validera konfiguration
    settings = get_openai_settings()
    result = validate_openai_config(settings)
    
    print("=== OpenAI Configuration Validation ===")
    print(f"Valid: {result['valid']}")
    
    if result['errors']:
        print("\nErrors:")
        for error in result['errors']:
            print(f"  - {error}")
    
    if result['warnings']:
        print("\nWarnings:")
        for warning in result['warnings']:
            print(f"  - {warning}")
    
    print(f"\nConfiguration Summary:")
    for key, value in result['config_summary'].items():
        print(f"  {key}: {value}")