#!/usr/bin/env python3
"""
🎵 Unit Tests for AudioProcessor
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
    
    def __init__(self, audio_data, sample_rate=48000):
        self.audio_data = audio_data
        self.sample_rate = sample_rate
    
    def to_ndarray(self):
        return self.audio_data

class TestAudioProcessor:
    """Test AudioProcessor PCM conversion and edge cases"""
    
    @pytest.fixture
    def processor(self):
        return AudioProcessor("test_session_001")
    
    def test_init(self, processor):
        """Test AudioProcessor initialization"""
        assert processor.session_id == "test_session_001"
        assert processor.sample_rate == 16000
        assert processor.channels == 1
        assert processor.chunk_size == 320  # 20ms at 16kHz
    
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
        frame = MockAudioFrame(stereo_data, sample_rate=16000)  # Same rate
        
        result = await processor.process_audio_frame(frame)
        
        assert result is not None
        assert len(result) == 320 * 2  # Converted to mono
    
    @pytest.mark.asyncio
    async def test_transposed_stereo_conversion(self, processor):
        """Test (2, 320) stereo layout conversion"""
        # Create transposed stereo (2 channels, 320 samples)
        stereo_data = np.random.uniform(-0.5, 0.5, (2, 320)).astype(np.float32)
        frame = MockAudioFrame(stereo_data, sample_rate=16000)
        
        result = await processor.process_audio_frame(frame)
        
        assert result is not None
        assert len(result) == 320 * 2
    
    @pytest.mark.asyncio
    async def test_3d_array_handling(self, processor):
        """Test 3D array flattening"""
        # Create 3D array that needs flattening
        audio_3d = np.random.uniform(-0.5, 0.5, (1, 320, 1)).astype(np.float32)
        frame = MockAudioFrame(audio_3d, sample_rate=16000)
        
        result = await processor.process_audio_frame(frame)
        
        assert result is not None
        assert len(result) == 320 * 2
    
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
        frame = MockAudioFrame(loud_audio)
        
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
    
    @pytest.mark.asyncio
    async def test_error_count_throttling(self, processor):
        """Test error logging throttling"""
        # Create frames that will cause errors
        bad_frame = Mock()
        bad_frame.to_ndarray.side_effect = Exception("Test error")
        
        # Process 100 bad frames
        results = []
        for i in range(100):
            result = await processor.process_audio_frame(bad_frame)
            results.append(result)
        
        # All should return None
        assert all(r is None for r in results)
        # Error counter should exist
        assert hasattr(processor, '_error_count')
        assert processor._error_count == 100
    
    @pytest.mark.asyncio
    async def test_single_channel_column_vector(self, processor):
        """Test (320, 1) single channel layout"""
        audio_data = np.random.uniform(-0.5, 0.5, (320, 1)).astype(np.float32)
        frame = MockAudioFrame(audio_data)
        
        result = await processor.process_audio_frame(frame)
        
        assert result is not None
        assert len(result) == 320 * 2
    
    @pytest.mark.asyncio
    async def test_single_channel_row_vector(self, processor):
        """Test (1, 320) single channel layout"""
        audio_data = np.random.uniform(-0.5, 0.5, (1, 320)).astype(np.float32)
        frame = MockAudioFrame(audio_data)
        
        result = await processor.process_audio_frame(frame)
        
        assert result is not None
        assert len(result) == 320 * 2
    
    def test_resample_audio_same_rate(self, processor):
        """Test resampling with same source and target rate"""
        audio = np.array([1.0, 2.0, 3.0, 4.0])
        result = processor._resample_audio(audio, 16000, 16000)
        
        np.testing.assert_array_equal(result, audio)
    
    def test_resample_audio_different_rate(self, processor):
        """Test basic resampling functionality"""
        audio = np.array([1.0, 2.0, 3.0, 4.0])
        result = processor._resample_audio(audio, 8000, 16000)
        
        # Should double the length
        assert len(result) == 8
        assert isinstance(result, np.ndarray)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])