# Alice Swedish STT (Whisper) Implementation Guide

Comprehensive guide for Alice's Swedish Speech-to-Text system using Whisper with performance optimization and fallback strategies.

## Overview

Alice uses a hybrid STT approach combining OpenAI Whisper for high-quality Swedish transcription with browser Speech Recognition API for real-time responsiveness. This guide covers configuration, optimization, and deployment strategies.

## Architecture

```
Audio Input → Voice Activity Detection → STT Engine Selection → Swedish Post-Processing → Command Processing
                                      ↓
                              ┌─────────────┬─────────────┐
                              │   Whisper   │   Browser   │
                              │  (Quality)  │   (Speed)   │
                              └─────────────┴─────────────┘
```

## Whisper Model Configuration

### Swedish-Optimized Models

Alice supports multiple Whisper models with Swedish optimization:

```python
# Model selection by use case
WHISPER_MODELS = {
    'tiny': {
        'model_name': 'tiny',
        'size_mb': 39,
        'speed': 'fastest',
        'swedish_accuracy': 'fair',
        'use_case': 'embedded_devices',
        'latency_target_ms': 200,
    },
    'small': {  # RECOMMENDED for Alice
        'model_name': 'small', 
        'size_mb': 244,
        'speed': 'fast',
        'swedish_accuracy': 'good',
        'use_case': 'production',
        'latency_target_ms': 500,
    },
    'medium': {
        'model_name': 'medium',
        'size_mb': 769,
        'speed': 'medium',
        'swedish_accuracy': 'very_good',
        'use_case': 'high_quality',
        'latency_target_ms': 1000,
    },
    'large-v3': {
        'model_name': 'large-v3',
        'size_mb': 1550,
        'speed': 'slow', 
        'swedish_accuracy': 'excellent',
        'use_case': 'batch_processing',
        'latency_target_ms': 2000,
    }
}
```

### Production Configuration

```python
# Alice production STT configuration
ALICE_STT_CONFIG = {
    # Primary model for Swedish
    'primary_model': 'small',
    'language': 'sv',
    'compute_type': 'int8',  # Optimized for production
    'device': 'cpu',         # CPU for consistent performance
    'download_root': './models/whisper',
    
    # Swedish-specific optimizations
    'beam_size': 5,          # Higher for better accuracy
    'best_of': 3,            # Multiple candidates
    'temperature': 0.0,      # Deterministic
    'condition_on_previous_text': True,
    'initial_prompt': 'Detta är svenska tal med kommandon till AI-assistenten Alice.',
    'word_timestamps': True,
    
    # Performance settings
    'vad_filter': True,      # Voice Activity Detection
    'vad_threshold': 0.5,
    'min_silence_duration_ms': 500,
    'max_speech_duration_s': 30,
    
    # Fallback configuration
    'fallback_enabled': True,
    'fallback_model': 'tiny',
    'fallback_timeout_ms': 3000,
}
```

## Performance Targets and Optimization

### Latency Targets

| Model | Target Latency | Use Case |
|-------|----------------|----------|
| tiny  | < 200ms | Real-time commands |
| small | < 500ms | Interactive conversations |
| medium| < 1000ms | High-quality transcription |
| large | < 2000ms | Batch processing |

### CPU/GPU Fallback Strategy

```python
class AdaptiveSTTProcessor:
    def __init__(self):
        self.compute_strategies = {
            'gpu_cuda': {
                'device': 'cuda',
                'compute_type': 'float16',
                'priority': 1,
                'availability_check': self._check_cuda,
            },
            'cpu_optimized': {
                'device': 'cpu',
                'compute_type': 'int8', 
                'priority': 2,
                'availability_check': self._check_cpu_optimized,
            },
            'cpu_fallback': {
                'device': 'cpu',
                'compute_type': 'float32',
                'priority': 3,
                'availability_check': lambda: True,
            }
        }
        
    def select_optimal_strategy(self):
        """Select best available compute strategy"""
        for strategy_name, config in sorted(
            self.compute_strategies.items(),
            key=lambda x: x[1]['priority']
        ):
            if config['availability_check']():
                return strategy_name, config
        
        return 'cpu_fallback', self.compute_strategies['cpu_fallback']
```

### Swedish Language Optimization

```python
# Swedish-specific post-processing
SWEDISH_CORRECTIONS = {
    # Common Whisper Swedish transcription errors
    'whisper_errors': {
        'okay': 'okej',
        'ok': 'okej',
        'hello': 'hej',
        'hi': 'hej',
        'bye': 'hej då',
        'yes': 'ja',
        'no': 'nej',
        'please': 'tack',
        'thank you': 'tack',
        'sorry': 'förlåt',
    },
    
    # AI command translations
    'ai_commands': {
        'play music': 'spela musik',
        'stop music': 'stoppa musik',
        'pause music': 'pausa musik',
        'send email': 'skicka mejl',
        'read email': 'läs mejl',
        'what time': 'vad är klockan',
        "what's the time": 'vad är klockan',
    },
    
    # Swedish character corrections
    'character_fixes': {
        'å': 'å',
        'ä': 'ä',
        'ö': 'ö',
        'Alice': 'Alice',  # Always capitalized
    },
    
    # Regional pronunciation variants
    'regional_variants': {
        'stockholmska': {
            'allis': 'Alice',
            'alis': 'Alice',
        },
        'göteborgska': {
            'ales': 'Alice',
            'alees': 'Alice',
        },
        'skånska': {
            'alise': 'Alice',
            'ales': 'Alice',
        }
    }
}

def postprocess_swedish_text(text: str, region: str = 'standard') -> str:
    """Enhanced Swedish post-processing with regional support"""
    if not text:
        return text
        
    # Apply general corrections
    corrected = text
    for wrong, right in SWEDISH_CORRECTIONS['whisper_errors'].items():
        corrected = re.sub(rf'\b{re.escape(wrong)}\b', right, corrected, flags=re.IGNORECASE)
    
    # Apply AI command corrections
    for wrong, right in SWEDISH_CORRECTIONS['ai_commands'].items():
        corrected = re.sub(rf'\b{re.escape(wrong)}\b', right, corrected, flags=re.IGNORECASE)
    
    # Apply regional variants if specified
    if region in SWEDISH_CORRECTIONS['regional_variants']:
        for wrong, right in SWEDISH_CORRECTIONS['regional_variants'][region].items():
            corrected = re.sub(rf'\b{re.escape(wrong)}\b', right, corrected, flags=re.IGNORECASE)
    
    # Fix capitalization
    corrected = re.sub(r'\balice\b', 'Alice', corrected, flags=re.IGNORECASE)
    
    # Capitalize first letter
    if corrected:
        corrected = corrected[0].upper() + corrected[1:]
    
    return corrected.strip()
```

## Implementation

### Enhanced STT Service

```python
# Enhanced voice_stt.py implementation
import asyncio
import time
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path

class EnhancedSwedishSTT:
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or ALICE_STT_CONFIG
        self.primary_model = None
        self.fallback_model = None
        self.performance_metrics = {
            'total_requests': 0,
            'successful_requests': 0,
            'fallback_used': 0,
            'average_latency': 0,
            'swedish_accuracy_score': 0,
        }
        
        # Initialize models
        self._initialize_models()
        
    def _initialize_models(self):
        """Initialize primary and fallback Whisper models"""
        try:
            from faster_whisper import WhisperModel
            
            # Primary model (small for production)
            self.primary_model = WhisperModel(
                self.config['primary_model'],
                device=self.config['device'],
                compute_type=self.config['compute_type'],
                download_root=self.config['download_root']
            )
            
            # Fallback model (tiny for speed)
            if self.config['fallback_enabled']:
                self.fallback_model = WhisperModel(
                    self.config['fallback_model'],
                    device='cpu',  # Always CPU for fallback
                    compute_type='int8',
                    download_root=self.config['download_root']
                )
                
            logging.info(f"STT models initialized: primary={self.config['primary_model']}, fallback={self.config.get('fallback_model', 'none')}")
            
        except ImportError:
            logging.error("faster-whisper not installed. Install: pip install faster-whisper")
            raise
        except Exception as e:
            logging.error(f"Failed to initialize STT models: {e}")
            raise
    
    async def transcribe_with_fallback(
        self, 
        audio_file_path: str,
        prefer_quality: bool = True,
        region: str = 'standard'
    ) -> Dict[str, Any]:
        """Enhanced transcription with automatic fallback"""
        start_time = time.time()
        self.performance_metrics['total_requests'] += 1
        
        try:
            # Primary transcription attempt
            if prefer_quality and self.primary_model:
                result = await self._transcribe_with_model(
                    self.primary_model,
                    audio_file_path,
                    region,
                    model_name=self.config['primary_model']
                )
                result['processing_time'] = time.time() - start_time
                result['model_used'] = self.config['primary_model']
                result['fallback_used'] = False
                
                self.performance_metrics['successful_requests'] += 1
                self._update_performance_metrics(result['processing_time'])
                
                return result
                
        except Exception as e:
            logging.warning(f"Primary STT model failed: {e}")
            
        # Fallback transcription
        if self.fallback_model and self.config['fallback_enabled']:
            try:
                logging.info("Using fallback STT model")
                result = await self._transcribe_with_model(
                    self.fallback_model,
                    audio_file_path,
                    region,
                    model_name=self.config['fallback_model']
                )
                result['processing_time'] = time.time() - start_time
                result['model_used'] = self.config['fallback_model']
                result['fallback_used'] = True
                result['primary_error'] = str(e) if 'e' in locals() else 'Primary model unavailable'
                
                self.performance_metrics['successful_requests'] += 1
                self.performance_metrics['fallback_used'] += 1
                self._update_performance_metrics(result['processing_time'])
                
                return result
                
            except Exception as fallback_error:
                logging.error(f"Fallback STT also failed: {fallback_error}")
        
        # Both models failed
        raise Exception(f"All STT models failed. Primary: {e if 'e' in locals() else 'Not attempted'}, Fallback: {fallback_error if 'fallback_error' in locals() else 'Not available'}")
    
    async def _transcribe_with_model(
        self, 
        model,
        audio_file_path: str,
        region: str,
        model_name: str
    ) -> Dict[str, Any]:
        """Core transcription logic for a specific model"""
        
        # Perform transcription
        segments, info = model.transcribe(
            audio_file_path,
            language=self.config['language'],
            beam_size=self.config['beam_size'],
            best_of=self.config['best_of'],
            temperature=self.config['temperature'],
            condition_on_previous_text=self.config['condition_on_previous_text'],
            initial_prompt=self.config['initial_prompt'],
            word_timestamps=self.config['word_timestamps']
        )
        
        # Process segments
        text_segments = []
        word_level_data = []
        full_text = ""
        
        for segment in segments:
            clean_text = segment.text.strip()
            if clean_text:
                full_text += clean_text + " "
                
                segment_data = {
                    'start': segment.start,
                    'end': segment.end,
                    'text': clean_text,
                    'confidence': getattr(segment, 'avg_logprob', 0.0)
                }
                
                # Add word-level data if available
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
                
                text_segments.append(segment_data)
        
        # Swedish post-processing
        processed_text = postprocess_swedish_text(full_text.strip(), region)
        
        # Quality assessment
        quality_assessment = self._assess_transcription_quality(
            processed_text, info, text_segments
        )
        
        return {
            'success': True,
            'text': processed_text,
            'segments': text_segments,
            'words': word_level_data,
            'language': info.language,
            'language_probability': info.language_probability,
            'duration': info.duration,
            'model': model_name,
            'region_processed': region,
            'quality_assessment': quality_assessment,
            'swedish_optimizations_applied': True,
        }
    
    def _assess_transcription_quality(
        self, 
        text: str, 
        info, 
        segments: List[Dict]
    ) -> Dict[str, Any]:
        """Assess Swedish transcription quality"""
        
        # Basic quality metrics
        avg_confidence = sum(s.get('confidence', 0) for s in segments) / max(len(segments), 1)
        
        # Swedish-specific quality indicators
        swedish_indicators = {
            'has_swedish_chars': any(c in text for c in 'åäöÅÄÖ'),
            'has_alice_reference': 'alice' in text.lower(),
            'has_swedish_words': any(word in text.lower() for word in ['och', 'att', 'är', 'på', 'med', 'av']),
            'estimated_swedish_probability': min(1.0, info.language_probability + 0.1 if info.language == 'sv' else 0.3),
        }
        
        # Overall quality score
        quality_factors = [
            info.language_probability,
            avg_confidence,
            1.0 if swedish_indicators['has_swedish_chars'] else 0.5,
            1.0 if swedish_indicators['has_swedish_words'] else 0.7,
        ]
        
        overall_quality = sum(quality_factors) / len(quality_factors)
        
        quality_rating = 'excellent' if overall_quality >= 0.9 else \
                        'good' if overall_quality >= 0.7 else \
                        'fair' if overall_quality >= 0.5 else 'poor'
        
        return {
            'overall_score': overall_quality,
            'rating': quality_rating,
            'average_confidence': avg_confidence,
            'language_probability': info.language_probability,
            'duration': info.duration,
            'swedish_indicators': swedish_indicators,
            'recommendations': self._get_quality_recommendations(quality_rating, swedish_indicators)
        }
    
    def _get_quality_recommendations(self, rating: str, indicators: Dict) -> List[str]:
        """Generate recommendations for improving STT quality"""
        recommendations = []
        
        if rating == 'poor':
            recommendations.append('Consider using higher quality microphone')
            recommendations.append('Reduce background noise')
            recommendations.append('Speak closer to microphone (1-2 meters)')
            
        if not indicators['has_swedish_chars']:
            recommendations.append('Verify Swedish language detection is working')
            
        if not indicators['has_alice_reference'] and not indicators['has_swedish_words']:
            recommendations.append('Speech may not be in Swedish - verify language settings')
            
        if rating in ['fair', 'poor']:
            recommendations.append('Consider using medium or large model for better accuracy')
            
        return recommendations
    
    def _update_performance_metrics(self, processing_time: float):
        """Update running performance metrics"""
        current_avg = self.performance_metrics['average_latency']
        total_requests = self.performance_metrics['successful_requests']
        
        # Calculate new running average
        new_avg = ((current_avg * (total_requests - 1)) + processing_time) / total_requests
        self.performance_metrics['average_latency'] = new_avg
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        success_rate = (self.performance_metrics['successful_requests'] / 
                       max(self.performance_metrics['total_requests'], 1)) * 100
        
        fallback_rate = (self.performance_metrics['fallback_used'] / 
                        max(self.performance_metrics['successful_requests'], 1)) * 100
        
        return {
            'success_rate_percent': round(success_rate, 1),
            'fallback_usage_percent': round(fallback_rate, 1),
            'average_latency_ms': round(self.performance_metrics['average_latency'] * 1000),
            'total_requests': self.performance_metrics['total_requests'],
            'successful_requests': self.performance_metrics['successful_requests'],
            'primary_model': self.config['primary_model'],
            'fallback_model': self.config.get('fallback_model'),
            'targets_met': {
                'latency_target': self.performance_metrics['average_latency'] < 0.5,  # 500ms
                'success_rate_target': success_rate >= 95.0,
                'fallback_usage_target': fallback_rate <= 10.0,
            }
        }

# Global instance
enhanced_swedish_stt = EnhancedSwedishSTT()
```

### API Endpoints

```python
# FastAPI endpoints for enhanced STT
from fastapi import APIRouter, UploadFile, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/stt", tags=["speech-to-text"])

class STTResponse(BaseModel):
    success: bool
    text: str
    confidence: float
    processing_time: float
    model_used: str
    fallback_used: bool
    quality_assessment: Dict[str, Any]

@router.post("/transcribe", response_model=STTResponse)
async def transcribe_audio(
    audio_file: UploadFile,
    region: str = 'standard',
    prefer_quality: bool = True
):
    """Enhanced Swedish transcription with fallback"""
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            content = await audio_file.read()
            temp_file.write(content)
            temp_filename = temp_file.name
        
        try:
            # Transcribe with enhanced STT
            result = await enhanced_swedish_stt.transcribe_with_fallback(
                temp_filename,
                prefer_quality=prefer_quality,
                region=region
            )
            
            return STTResponse(**result)
            
        finally:
            # Cleanup temp file
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

@router.get("/status")
async def get_stt_status():
    """Get STT system status and performance metrics"""
    return {
        'whisper_available': enhanced_swedish_stt.primary_model is not None,
        'fallback_available': enhanced_swedish_stt.fallback_model is not None,
        'performance_metrics': enhanced_swedish_stt.get_performance_metrics(),
        'swedish_optimization': True,
        'supported_regions': ['standard', 'stockholmska', 'göteborgska', 'skånska'],
        'models': {
            'primary': enhanced_swedish_stt.config['primary_model'],
            'fallback': enhanced_swedish_stt.config.get('fallback_model'),
        }
    }

@router.get("/performance")
async def get_performance_metrics():
    """Detailed performance metrics for monitoring"""
    return enhanced_swedish_stt.get_performance_metrics()
```

## Deployment and Monitoring

### Docker Configuration

```dockerfile
# Optimized Dockerfile for Swedish STT
FROM python:3.9-slim

# Install system dependencies for audio processing
RUN apt-get update && apt-get install -y \
    ffmpeg \
    portaudio19-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Pre-download Whisper models
RUN python -c "
from faster_whisper import WhisperModel
WhisperModel('small', download_root='/app/models/whisper')
WhisperModel('tiny', download_root='/app/models/whisper')
"

COPY . /app
WORKDIR /app

# Set environment variables
ENV WHISPER_CACHE_DIR=/app/models/whisper
ENV STT_MODEL=small
ENV STT_FALLBACK_MODEL=tiny

EXPOSE 8000
CMD ["python", "run.py"]
```

### Performance Monitoring

```python
# Performance monitoring and alerting
class STTMonitor:
    def __init__(self, stt_service):
        self.stt = stt_service
        self.alerts = []
        
    async def check_performance(self):
        """Check STT performance against targets"""
        metrics = self.stt.get_performance_metrics()
        
        alerts = []
        
        # Latency check
        if metrics['average_latency_ms'] > 1000:  # 1 second threshold
            alerts.append({
                'level': 'warning',
                'message': f"High STT latency: {metrics['average_latency_ms']}ms",
                'metric': 'latency'
            })
            
        # Success rate check
        if metrics['success_rate_percent'] < 95:
            alerts.append({
                'level': 'critical',
                'message': f"Low STT success rate: {metrics['success_rate_percent']}%",
                'metric': 'success_rate'
            })
            
        # Fallback usage check
        if metrics['fallback_usage_percent'] > 25:
            alerts.append({
                'level': 'warning', 
                'message': f"High fallback usage: {metrics['fallback_usage_percent']}%",
                'metric': 'fallback_usage'
            })
            
        return alerts

# Health check endpoint
@router.get("/health")
async def stt_health_check():
    """Comprehensive STT health check"""
    monitor = STTMonitor(enhanced_swedish_stt)
    alerts = await monitor.check_performance()
    
    return {
        'status': 'healthy' if not alerts else 'degraded',
        'alerts': alerts,
        'performance': enhanced_swedish_stt.get_performance_metrics(),
        'timestamp': datetime.utcnow().isoformat()
    }
```

## Testing

### Automated Testing

```python
# test_swedish_stt.py
import pytest
import asyncio
from pathlib import Path

class TestSwedishSTT:
    
    @pytest.fixture
    def stt_service(self):
        return EnhancedSwedishSTT()
    
    @pytest.mark.asyncio
    async def test_swedish_transcription_accuracy(self, stt_service):
        """Test Swedish transcription accuracy"""
        test_audio = "tests/fixtures/swedish_test_audio.wav"
        expected_text = "Hej Alice, vad är klockan?"
        
        result = await stt_service.transcribe_with_fallback(test_audio)
        
        assert result['success']
        assert result['language'] == 'sv'
        assert 'alice' in result['text'].lower()
        assert result['quality_assessment']['rating'] in ['good', 'excellent']
    
    @pytest.mark.asyncio
    async def test_fallback_mechanism(self, stt_service):
        """Test fallback when primary model fails"""
        # Simulate primary model failure
        stt_service.primary_model = None
        
        test_audio = "tests/fixtures/simple_swedish.wav"
        result = await stt_service.transcribe_with_fallback(test_audio)
        
        assert result['success']
        assert result['fallback_used']
        assert result['model_used'] == stt_service.config['fallback_model']
    
    def test_swedish_post_processing(self):
        """Test Swedish text post-processing"""
        test_cases = [
            ("hello alice", "Hej Alice"),
            ("play music please", "Spela musik tack"),
            ("what time is it", "Vad är klockan"),
        ]
        
        for input_text, expected in test_cases:
            result = postprocess_swedish_text(input_text)
            assert expected.lower() in result.lower()
    
    def test_regional_variants(self):
        """Test Swedish regional pronunciation handling"""
        test_cases = [
            ("allis", "göteborgska", "Alice"),
            ("ales", "skånska", "Alice"),
        ]
        
        for input_text, region, expected in test_cases:
            result = postprocess_swedish_text(input_text, region)
            assert expected in result
```

### Performance Benchmarking

```bash
# Benchmark script
#!/bin/bash

echo "=== Alice Swedish STT Performance Benchmark ==="

# Test different model sizes
for model in tiny small medium; do
    echo "Testing model: $model"
    python benchmark_stt.py --model $model --language sv --test-duration 60
done

# Test Swedish regional variants
for region in standard stockholmska göteborgska skånska; do
    echo "Testing region: $region"
    python benchmark_stt.py --region $region --test-file tests/fixtures/${region}_audio.wav
done

# Generate performance report
python generate_stt_report.py --output stt_performance_report.html
```

## Production Checklist

### Pre-deployment Verification

- [ ] **Model Setup**
  - [ ] Whisper models downloaded and cached
  - [ ] Primary model (small) initialization successful
  - [ ] Fallback model (tiny) initialization successful
  - [ ] Model file integrity verified

- [ ] **Swedish Language Support**
  - [ ] Swedish language pack installed
  - [ ] Post-processing rules tested
  - [ ] Regional variants configured
  - [ ] Swedish character encoding working

- [ ] **Performance Testing**
  - [ ] Latency targets met (< 500ms for small model)
  - [ ] Success rate > 95% on test dataset
  - [ ] Fallback mechanism tested
  - [ ] CPU usage within limits (< 50%)

- [ ] **Quality Assurance**
  - [ ] Manual testing with Swedish speakers completed
  - [ ] Regional accent testing completed
  - [ ] False positive/negative rates acceptable
  - [ ] Alice wake-word recognition working

### Monitoring Setup

- [ ] Performance metrics dashboard configured
- [ ] Alerting rules set up (latency, success rate, errors)
- [ ] Log aggregation configured
- [ ] Health check endpoints tested

---

**Last Updated:** 2025-01-22  
**Version:** 1.0  
**Swedish Language Optimized** ✅