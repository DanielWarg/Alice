#!/usr/bin/env python3
"""
🎵 Fixed Unit Tests for AudioProcessor
Validates PCM conversion, resampling, and edge cases
"""
import pytest
import numpy as np
import asyncio
from unittest.mock import Mock, AsyncMock
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from webrtc import AudioProcessor

class MockAudioFrame:
    """Mock aiortc AudioFrame for testing"""
    
    def __init__(self, audio_data, sample_rate=16000):
        self.audio_data = audio_data
        self.sample_rate = sample_rate
    
    def to_ndarray(self):
        return self.audio_data

class TestAudioProcessorFixed:
    """Test AudioProcessor PCM conversion and edge cases"""
    
    @pytest.fixture
    def processor(self):
        return AudioProcessor("test_session_001")
    
    @pytest.mark.asyncio
    async def test_mono_audio_processing(self, processor):
        """Test mono audio frame processing"""
        # Create 1D mono audio (320 samples = 20ms at 16kHz)
        audio_data = np.random.uniform(-0.5, 0.5, 320).astype(np.float32)
        frame = MockAudioFrame(audio_data, sample_rate=16000)  # Same rate, no resampling
        
        result = await processor.process_audio_frame(frame)
        
        assert result is not None
        assert isinstance(result, bytes)
        # Should be 320 samples * 2 bytes = 640 bytes (no resampling)
        assert len(result) == 320 * 2
    
    @pytest.mark.asyncio
    async def test_stereo_to_mono_conversion(self, processor):
        """Test stereo to mono conversion"""
        # Create 2D stereo audio (320 samples, 2 channels)
        stereo_data = np.random.uniform(-0.5, 0.5, (320, 2)).astype(np.float32)
        frame = MockAudioFrame(stereo_data, sample_rate=16000)
        
        result = await processor.process_audio_frame(frame)
        
        assert result is not None
        assert len(result) == 320 * 2  # Converted to mono
    
    @pytest.mark.asyncio
    async def test_empty_audio_handling(self, processor):
        """Test empty audio array handling"""
        empty_data = np.array([]).astype(np.float32)
        frame = MockAudioFrame(empty_data, sample_rate=16000)
        
        result = await processor.process_audio_frame(frame)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_normalization(self, processor):
        """Test audio normalization"""
        # Create audio with values outside [-1, 1]
        loud_audio = np.array([2.0, -3.0, 1.5, -2.5] * 80).astype(np.float32)
        frame = MockAudioFrame(loud_audio, sample_rate=16000)
        
        result = await processor.process_audio_frame(frame)
        
        assert result is not None
        # Convert back to check normalization
        pcm_data = np.frombuffer(result, dtype=np.int16)
        float_data = pcm_data.astype(np.float32) / 32767
        assert np.max(np.abs(float_data)) <= 0.95  # Headroom check
    
    @pytest.mark.asyncio
    async def test_frame_conversion_error(self, processor):
        """Test frame conversion error handling"""
        # Create mock frame that raises exception
        frame = Mock()
        frame.to_ndarray.side_effect = Exception("Conversion failed")
        
        result = await processor.process_audio_frame(frame)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_sample_rate_resampling(self, processor):
        """Test basic resampling (44.1kHz -> 16kHz)"""
        # Create 44.1kHz audio (441 samples = 10ms)
        source_rate = 44100
        audio_data = np.random.uniform(-0.5, 0.5, 441).astype(np.float32)
        
        frame = MockAudioFrame(audio_data, sample_rate=source_rate)
        
        result = await processor.process_audio_frame(frame)
        
        assert result is not None
        # Should be resampled to ~160 samples (10ms at 16kHz)
        expected_samples = int(441 * 16000 / 44100)
        assert len(result) == expected_samples * 2

if __name__ == "__main__":
    pytest.main([__file__, "-v"])