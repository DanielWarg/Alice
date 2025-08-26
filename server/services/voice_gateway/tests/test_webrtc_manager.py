#!/usr/bin/env python3
"""
🔗 Integration Tests for WebRTCManager
Validates session management, offer/answer handling, cleanup
"""
import pytest
import asyncio
import json
import time
from unittest.mock import Mock, AsyncMock, patch
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from webrtc import WebRTCManager, WebRTCSession

@pytest.fixture
async def redis_mock():
    """Mock Redis for testing"""
    redis = AsyncMock()
    redis.hset = AsyncMock()
    redis.hget = AsyncMock(return_value="false")
    redis.expire = AsyncMock()
    redis.delete = AsyncMock()
    return redis

@pytest.fixture
async def manager(redis_mock):
    """Create WebRTCManager with mocked Redis"""
    with patch('webrtc.redis.Redis', return_value=redis_mock):
        manager = WebRTCManager()
        await manager.initialize()
        yield manager
        await manager.cleanup()

class TestWebRTCManager:
    """Test WebRTCManager session management and lifecycle"""
    
    @pytest.mark.asyncio
    async def test_manager_initialization(self, manager):
        """Test WebRTCManager initialization"""
        assert manager.sessions == {}
        assert manager.cleanup_task is not None
        assert not manager.cleanup_task.done()
    
    @pytest.mark.asyncio
    async def test_basic_offer_handling(self, manager):
        """Test basic SDP offer/answer exchange"""
        session_id = "test_session_001"
        
        # Mock SDP offer (simplified)
        offer_sdp = """v=0
o=- 123456789 1 IN IP4 127.0.0.1
s=-
t=0 0
m=audio 9 RTP/AVP 0
a=sendrecv"""
        
        # Mock the WebRTC peer connection
        with patch('webrtc.RTCPeerConnection') as mock_pc:
            mock_instance = mock_pc.return_value
            mock_instance.setRemoteDescription = AsyncMock()
            mock_instance.createAnswer = AsyncMock()
            mock_instance.setLocalDescription = AsyncMock()
            mock_instance.localDescription = Mock()
            mock_instance.localDescription.sdp = "mock_answer_sdp"
            mock_instance.addTrack = Mock()
            
            answer_sdp = await manager.handle_offer(session_id, offer_sdp)
        
        assert answer_sdp == "mock_answer_sdp"
        assert session_id in manager.sessions
        assert manager.sessions[session_id].is_active
    
    @pytest.mark.asyncio
    async def test_session_replacement(self, manager):
        """Test that new session replaces existing one"""
        session_id = "test_session_002"
        offer_sdp = "v=0\no=- 123 1 IN IP4 127.0.0.1\ns=-\nt=0 0"
        
        with patch('webrtc.RTCPeerConnection') as mock_pc:
            mock_instance = mock_pc.return_value
            mock_instance.setRemoteDescription = AsyncMock()
            mock_instance.createAnswer = AsyncMock()
            mock_instance.setLocalDescription = AsyncMock()
            mock_instance.localDescription = Mock()
            mock_instance.localDescription.sdp = "answer1"
            mock_instance.addTrack = Mock()
            mock_instance.close = AsyncMock()
            
            # Create first session
            await manager.handle_offer(session_id, offer_sdp)
            first_session = manager.sessions[session_id]
            
            # Create second session with same ID
            mock_instance.localDescription.sdp = "answer2"
            await manager.handle_offer(session_id, offer_sdp)
            second_session = manager.sessions[session_id]
        
        assert first_session != second_session
        assert len(manager.sessions) == 1
    
    @pytest.mark.asyncio
    async def test_offer_handling_error(self, manager):
        """Test error handling in offer processing"""
        session_id = "test_session_error"
        offer_sdp = "invalid_sdp"
        
        with patch('webrtc.RTCPeerConnection') as mock_pc:
            mock_instance = mock_pc.return_value
            mock_instance.setRemoteDescription = AsyncMock(side_effect=Exception("SDP Error"))
            
            with pytest.raises(Exception):
                await manager.handle_offer(session_id, offer_sdp)
        
        # Failed session should be cleaned up
        assert session_id not in manager.sessions
    
    @pytest.mark.asyncio
    async def test_tts_stop_existing_session(self, manager):
        """Test TTS stop for existing session"""
        session_id = "test_session_tts"
        
        # Create a mock session
        mock_session = Mock()
        mock_session.stop_tts = AsyncMock()
        manager.sessions[session_id] = mock_session
        
        await manager.stop_tts(session_id)
        
        mock_session.stop_tts.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_tts_stop_nonexistent_session(self, manager):
        """Test TTS stop for non-existent session"""
        # Should not raise exception
        await manager.stop_tts("nonexistent_session")
    
    @pytest.mark.asyncio
    async def test_active_session_count(self, manager):
        """Test active session counting"""
        # Initially zero
        count = await manager.get_active_session_count()
        assert count == 0
        
        # Add active session
        mock_session1 = Mock()
        mock_session1.is_active = True
        manager.sessions["session1"] = mock_session1
        
        # Add inactive session
        mock_session2 = Mock()
        mock_session2.is_active = False
        manager.sessions["session2"] = mock_session2
        
        count = await manager.get_active_session_count()
        assert count == 1
    
    def test_status_reporting(self, manager):
        """Test manager status reporting"""
        # Add some mock sessions
        manager.sessions["s1"] = Mock(is_active=True)
        manager.sessions["s2"] = Mock(is_active=False)
        manager.sessions["s3"] = Mock(is_active=True)
        
        status = manager.get_status()
        
        assert status["total_sessions"] == 3
        assert status["active_sessions"] == 2
        assert status["status"] == "running"
    
    @pytest.mark.asyncio
    async def test_cleanup_task_runs(self, manager):
        """Test that cleanup task is running"""
        # Wait a short time to ensure task is running
        await asyncio.sleep(0.1)
        
        assert manager.cleanup_task is not None
        assert not manager.cleanup_task.done()
    
    @pytest.mark.asyncio
    async def test_manager_cleanup(self, manager):
        """Test full manager cleanup"""
        # Add mock sessions
        mock_session1 = Mock()
        mock_session1.close = AsyncMock()
        mock_session1.test_tone_track = Mock()
        mock_session1.test_tone_track.stop = Mock()
        
        mock_session2 = Mock()
        mock_session2.close = AsyncMock()
        mock_session2.test_tone_track = Mock()
        mock_session2.test_tone_track.stop = Mock()
        
        manager.sessions["s1"] = mock_session1
        manager.sessions["s2"] = mock_session2
        
        await manager.cleanup()
        
        # Verify all sessions were closed and test tones stopped
        mock_session1.test_tone_track.stop.assert_called_once()
        mock_session1.close.assert_called_once()
        mock_session2.test_tone_track.stop.assert_called_once()
        mock_session2.close.assert_called_once()
        
        assert len(manager.sessions) == 0
        assert manager.cleanup_task.cancelled()

class TestWebRTCSession:
    """Test individual WebRTC session functionality"""
    
    @pytest.fixture
    def session(self):
        return WebRTCSession("test_session")
    
    def test_session_initialization(self, session):
        """Test WebRTC session initialization"""
        assert session.session_id == "test_session"
        assert session.is_active == True
        assert session.pc is not None
        assert session.audio_processor is not None
        assert session.test_tone_track is not None
        assert session.created_at is not None
    
    @pytest.mark.asyncio
    async def test_session_close_stops_test_tone(self, session):
        """Test that session close stops test tone"""
        # Mock the peer connection
        session.pc = Mock()
        session.pc.close = AsyncMock()
        
        # Mock test tone track
        session.test_tone_track = Mock()
        session.test_tone_track.stop = Mock()
        
        await session.close()
        
        assert session.is_active == False
        session.test_tone_track.stop.assert_called_once()
        session.pc.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_session_tts_stop(self, session):
        """Test TTS stop mechanism"""
        # This is a placeholder - actual TTS implementation pending
        await session.stop_tts()
        # Should not raise exception

if __name__ == "__main__":
    pytest.main([__file__, "-v"])