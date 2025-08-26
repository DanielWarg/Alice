#!/usr/bin/env python3
"""
🎭 Playwright E2E Tests for WebRTC Browser Integration
Tests real browser WebRTC functionality, getUserMedia, and audio processing
"""
import pytest
import asyncio
import time
from playwright.async_api import async_playwright, Page, Browser

@pytest.fixture(scope="session")
async def browser():
    """Launch browser for E2E tests"""
    async with async_playwright() as p:
        # Use Chrome/Chromium for WebRTC support
        browser = await p.chromium.launch(
            headless=False,  # Show browser for debugging
            args=[
                "--use-fake-ui-for-media-stream",  # Auto-grant microphone
                "--use-fake-device-for-media-stream",  # Use fake audio device
                "--allow-running-insecure-content",
                "--disable-web-security",
                "--autoplay-policy=no-user-gesture-required"
            ]
        )
        yield browser
        await browser.close()

@pytest.fixture
async def page(browser):
    """Create a page with WebRTC permissions"""
    context = await browser.new_context(
        permissions=["microphone", "camera"],
        extra_http_headers={"Accept-Language": "en-US,en;q=0.9"}
    )
    page = await context.new_page()
    
    # Set up console logging for debugging
    page.on("console", lambda msg: print(f"🖥️  Browser: {msg.text}"))
    page.on("pageerror", lambda error: print(f"❌ Page Error: {error}"))
    
    yield page
    await context.close()

class TestWebRTCE2E:
    """End-to-end WebRTC browser tests"""
    
    GATEWAY_URL = "http://localhost:8001"
    TEST_PAGE_URL = "http://localhost:3000/test_webrtc_gateway.html"
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_page_loads_successfully(self, page: Page):
        """Test that WebRTC test page loads"""
        await page.goto(self.TEST_PAGE_URL)
        
        # Wait for page to load
        await page.wait_for_selector("#startWebRTC")
        
        # Check essential elements
        start_button = page.locator("#startWebRTC")
        assert await start_button.is_visible()
        
        status_div = page.locator("#status")
        assert await status_div.is_visible()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_webrtc_connection_establishment(self, page: Page):
        """Test full WebRTC connection establishment"""
        await page.goto(self.TEST_PAGE_URL)
        
        # Wait for page elements
        await page.wait_for_selector("#startWebRTC")
        
        # Start WebRTC connection
        start_button = page.locator("#startWebRTC")
        
        # Measure connection time
        start_time = time.time()
        await start_button.click()
        
        # Wait for connection establishment
        await page.wait_for_selector(".status-success", timeout=10000)
        connection_time = (time.time() - start_time) * 1000
        
        print(f"\\n🔗 WebRTC Connection Time: {connection_time:.1f}ms")
        
        # Validate connection status
        status = await page.locator("#status").inner_text()
        assert "Connected" in status or "ICE connected" in status
        
        # Check for audio track indicators
        await page.wait_for_function(
            "document.querySelector('#audioStatus')?.innerText.includes('Audio')",
            timeout=5000
        )
        
        # Performance validation
        assert connection_time < 5000, f"Connection took {connection_time:.1f}ms (>5s)"
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_microphone_access_granted(self, page: Page):
        """Test that microphone access is properly granted"""
        await page.goto(self.TEST_PAGE_URL)
        
        # Start WebRTC
        await page.click("#startWebRTC")
        
        # Wait for microphone access
        await page.wait_for_function(
            "navigator.mediaDevices && navigator.mediaDevices.getUserMedia",
            timeout=3000
        )
        
        # Check for microphone stream indicator
        await page.wait_for_selector("#micStatus", timeout=5000)
        mic_status = await page.locator("#micStatus").inner_text()
        
        print(f"🎤 Microphone Status: {mic_status}")
        assert "granted" in mic_status.lower() or "active" in mic_status.lower()
    
    @pytest.mark.asyncio
    @pytest.mark.integration 
    async def test_audio_processing_pipeline(self, page: Page):
        """Test that audio processing pipeline is working"""
        await page.goto(self.TEST_PAGE_URL)
        
        # Start WebRTC connection
        await page.click("#startWebRTC")
        
        # Wait for connection
        await page.wait_for_selector(".status-success", timeout=10000)
        
        # Check for audio processing indicators
        await page.wait_for_function(
            "document.querySelector('#audioLevel') !== null",
            timeout=5000
        )
        
        # Wait for audio level updates (indicates processing)
        await page.wait_for_function(
            """() => {
                const levelElement = document.querySelector('#audioLevel');
                return levelElement && levelElement.style.width !== '0%';
            }""",
            timeout=3000
        )
        
        audio_level = await page.locator("#audioLevel").get_attribute("style")
        print(f"🎵 Audio Level: {audio_level}")
        
        # Should have some audio activity from fake device
        assert "width" in audio_level and "%" in audio_level
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_test_tone_playback(self, page: Page):
        """Test that test tone is played back properly"""
        await page.goto(self.TEST_PAGE_URL)
        
        # Start connection
        await page.click("#startWebRTC")
        await page.wait_for_selector(".status-success", timeout=10000)
        
        # Check for audio element or remote stream
        await page.wait_for_function(
            "document.querySelector('audio') !== null",
            timeout=5000
        )
        
        # Verify audio is playing
        audio_playing = await page.evaluate(
            """() => {
                const audio = document.querySelector('audio');
                return audio && !audio.paused && audio.readyState >= 2;
            }"""
        )
        
        print(f"🔊 Test Tone Playing: {audio_playing}")
        assert audio_playing, "Test tone should be playing"
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_connection_cleanup_on_disconnect(self, page: Page):
        """Test proper cleanup when disconnecting"""
        await page.goto(self.TEST_PAGE_URL)
        
        # Establish connection
        await page.click("#startWebRTC") 
        await page.wait_for_selector(".status-success", timeout=10000)
        
        # Find and click disconnect button
        disconnect_button = page.locator("#stopWebRTC")
        if await disconnect_button.is_visible():
            await disconnect_button.click()
        else:
            # Alternative: reload page to trigger cleanup
            await page.reload()
        
        # Wait for cleanup
        await asyncio.sleep(2)
        
        # Check status updated
        try:
            await page.wait_for_selector(".status-disconnected", timeout=3000)
            status_ok = True
        except:
            # Check if status shows disconnected
            status = await page.locator("#status").inner_text()
            status_ok = "disconnect" in status.lower() or "closed" in status.lower()
        
        print(f"🔄 Cleanup Status: {'OK' if status_ok else 'FAILED'}")
        assert status_ok, "Connection should be properly cleaned up"
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_handshake_performance_e2e(self, page: Page):
        """Test end-to-end WebRTC handshake performance"""
        await page.goto(self.TEST_PAGE_URL)
        
        # Measure multiple handshakes
        handshake_times = []
        
        for i in range(3):
            print(f"\\n🎯 Handshake Test {i+1}/3")
            
            # Reload page for fresh test
            if i > 0:
                await page.reload()
                await page.wait_for_selector("#startWebRTC")
            
            # Measure handshake time
            start_time = time.time()
            await page.click("#startWebRTC")
            
            # Wait for ICE connected state
            await page.wait_for_selector(".status-success", timeout=10000)
            
            elapsed = (time.time() - start_time) * 1000
            handshake_times.append(elapsed)
            
            print(f"   ⏱️ Handshake {i+1}: {elapsed:.1f}ms")
            
            # Small delay between tests
            await asyncio.sleep(1)
        
        # Performance analysis
        avg_time = sum(handshake_times) / len(handshake_times)
        max_time = max(handshake_times)
        
        print(f"\\n📊 E2E Handshake Performance:")
        print(f"   Average: {avg_time:.1f}ms")
        print(f"   Maximum: {max_time:.1f}ms")
        print(f"   All times: {[f'{t:.1f}ms' for t in handshake_times]}")
        
        # Validate performance (more lenient for E2E)
        assert avg_time < 5000, f"Average handshake time {avg_time:.1f}ms too slow"
        assert max_time < 10000, f"Max handshake time {max_time:.1f}ms too slow"
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_multiple_session_handling(self, page: Page):
        """Test that multiple sessions can be created in sequence"""
        await page.goto(self.TEST_PAGE_URL)
        
        # Create 3 sessions in sequence
        for i in range(3):
            print(f"\\n🔄 Session Test {i+1}/3")
            
            # Start connection
            await page.click("#startWebRTC")
            await page.wait_for_selector(".status-success", timeout=10000)
            
            # Verify connection
            status = await page.locator("#status").inner_text()
            assert "connected" in status.lower() or "success" in status.lower()
            
            # Disconnect (if button exists) or reload
            disconnect_button = page.locator("#stopWebRTC")
            if await disconnect_button.is_visible():
                await disconnect_button.click()
                await asyncio.sleep(1)
            else:
                await page.reload()
                await page.wait_for_selector("#startWebRTC")
        
        print("✅ Multiple sessions handled successfully")
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_browser_console_errors(self, page: Page):
        """Test that no critical JavaScript errors occur"""
        console_errors = []
        
        # Capture console errors
        def handle_console(msg):
            if msg.type == "error":
                console_errors.append(msg.text)
        
        page.on("console", handle_console)
        
        # Load page and perform WebRTC operations
        await page.goto(self.TEST_PAGE_URL)
        await page.click("#startWebRTC")
        
        try:
            await page.wait_for_selector(".status-success", timeout=10000)
        except:
            pass  # Connection might fail, but we want to check errors
        
        # Wait a bit for any delayed errors
        await asyncio.sleep(2)
        
        # Filter out non-critical errors
        critical_errors = [
            error for error in console_errors 
            if not any(ignore in error.lower() for ignore in [
                "favicon", "analytics", "websocket", "cors"
            ])
        ]
        
        print(f"\\n🐛 Console Errors Found: {len(critical_errors)}")
        for error in critical_errors[:5]:  # Show first 5 errors
            print(f"   ❌ {error}")
        
        # Should have minimal critical errors
        assert len(critical_errors) <= 2, f"Too many console errors: {critical_errors}"

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])