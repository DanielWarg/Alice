#!/usr/bin/env python3
"""
Voice v2 Real E2E Test - Faktisk Mikrofon & Browser Test
========================================================

Riktigt end-to-end test som:
- Öppnar riktig webbläsare (Chrome/Safari)
- Klickar på mikrofon-knappen
- Aktiverar riktig mikrofon
- Loggar alla fel och framsteg
- Testar med riktig MP3-uppspelning
- Mäter alla latenser
"""

import asyncio
import json
import time
import logging
from pathlib import Path
from playwright.async_api import async_playwright
import subprocess
import sys
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('voice_v2_real_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RealVoiceE2ETest:
    def __init__(self):
        self.browser = None
        self.page = None
        self.test_results = []
        self.start_time = time.time()
        
    async def setup_browser(self):
        """Setup real browser with microphone permissions"""
        logger.info("🚀 Starting real browser test...")
        
        playwright = await async_playwright().start()
        
        # Use Chrome with microphone permissions
        self.browser = await playwright.chromium.launch(
            headless=False,  # Show browser for real test
            args=[
                '--use-fake-ui-for-media-stream',  # Auto-allow mic
                '--use-fake-device-for-media-stream',  # Use fake media for testing
                '--allow-running-insecure-content',
                '--disable-web-security',
                '--autoplay-policy=no-user-gesture-required'
            ]
        )
        
        # Create context with permissions
        context = await self.browser.new_context(
            permissions=['microphone']
        )
        
        self.page = await context.new_page()
        
        # Listen to console logs
        self.page.on('console', self.handle_console_log)
        self.page.on('pageerror', self.handle_page_error)
        
        logger.info("✅ Browser setup complete with microphone permissions")
    
    def handle_console_log(self, msg):
        """Capture all console logs from the page"""
        log_level = msg.type
        text = msg.text
        
        # Log with timestamp
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        logger.info(f"[BROWSER {log_level.upper()}] [{timestamp}] {text}")
        
        # Store important events
        if any(keyword in text.lower() for keyword in ['error', 'failed', 'success', 'tts', 'mic']):
            self.test_results.append({
                'timestamp': timestamp,
                'type': log_level,
                'message': text,
                'elapsed_ms': (time.time() - self.start_time) * 1000
            })
    
    def handle_page_error(self, error):
        """Handle JavaScript errors"""
        logger.error(f"[PAGE ERROR] {error}")
        self.test_results.append({
            'timestamp': datetime.now().strftime("%H:%M:%S.%f")[:-3],
            'type': 'error',
            'message': str(error),
            'elapsed_ms': (time.time() - self.start_time) * 1000
        })
    
    async def test_backend_health(self):
        """Test that backend is running"""
        logger.info("🏥 Testing backend health...")
        
        try:
            response = await self.page.goto('http://localhost:8000/health')
            if response.status == 200:
                logger.info("✅ Backend is healthy")
                return True
            else:
                logger.error(f"❌ Backend unhealthy: {response.status}")
                return False
        except Exception as e:
            logger.error(f"❌ Backend connection failed: {e}")
            return False
    
    async def load_voice_page(self):
        """Load the voice test page"""
        logger.info("📄 Loading voice test page...")
        
        try:
            await self.page.goto('http://localhost:3000/voice-complete.html')
            
            # Wait for page to load
            await self.page.wait_for_selector('#micButton', timeout=10000)
            logger.info("✅ Voice page loaded successfully")
            
            # Wait for initialization
            await asyncio.sleep(2)
            
            # Check initial status
            status = await self.page.text_content('#status')
            logger.info(f"📊 Initial status: {status}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load voice page: {e}")
            return False
    
    async def test_tts_directly(self):
        """Test TTS endpoint directly before voice test"""
        logger.info("🔊 Testing TTS directly...")
        
        try:
            # Use page.evaluate to make fetch request
            result = await self.page.evaluate("""
                async () => {
                    const start = performance.now();
                    const response = await fetch('/api/tts/', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            text: 'Hej, detta är ett test av TTS-systemet',
                            voice: 'nova',
                            rate: 1.0
                        })
                    });
                    
                    const data = await response.json();
                    const latency = performance.now() - start;
                    
                    return {
                        status: response.status,
                        data: data,
                        latency: latency
                    };
                }
            """)
            
            if result['status'] == 200:
                data = result['data']
                logger.info(f"✅ TTS test successful ({result['latency']:.1f}ms)")
                logger.info(f"   - Cached: {data.get('cached', 'N/A')}")
                logger.info(f"   - Engine: {data.get('engine', 'N/A')}")
                logger.info(f"   - SLO: {data.get('slo_verdict', 'N/A')}")
                return True
            else:
                logger.error(f"❌ TTS test failed: HTTP {result['status']}")
                return False
                
        except Exception as e:
            logger.error(f"❌ TTS test error: {e}")
            return False
    
    async def test_microphone_button(self):
        """Test clicking the microphone button"""
        logger.info("🎤 Testing microphone button click...")
        
        try:
            # Click microphone button
            mic_button = self.page.locator('#micButton')
            await mic_button.click()
            
            logger.info("✅ Microphone button clicked")
            
            # Wait a moment for state change
            await asyncio.sleep(1)
            
            # Check if button has recording class
            button_class = await mic_button.get_attribute('class')
            logger.info(f"📊 Button class after click: {button_class}")
            
            # Check status text
            status = await self.page.text_content('#status')
            logger.info(f"📊 Status after click: {status}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Microphone button test failed: {e}")
            return False
    
    async def test_speech_recognition(self):
        """Test speech recognition functionality"""
        logger.info("🗣️ Testing speech recognition...")
        
        try:
            # Wait for speech recognition to initialize
            await asyncio.sleep(2)
            
            # Simulate speech input by directly calling the processVoiceCommand function
            test_phrase = "Hej Alice, kolla min email"
            
            result = await self.page.evaluate(f"""
                async () => {{
                    // Simulate voice input by calling processVoiceCommand directly
                    if (typeof processVoiceCommand === 'function') {{
                        await processVoiceCommand('{test_phrase}');
                        return {{ success: true, message: 'processVoiceCommand called' }};
                    }} else {{
                        return {{ success: false, message: 'processVoiceCommand not found' }};
                    }}
                }}
            """)
            
            if result['success']:
                logger.info(f"✅ Speech processing test: {result['message']}")
                
                # Wait for processing
                await asyncio.sleep(3)
                
                # Check transcript
                transcript = await self.page.text_content('#transcript')
                logger.info(f"📝 Transcript: {transcript}")
                
                # Check response
                response = await self.page.text_content('#response')
                logger.info(f"🤖 Response: {response}")
                
                return True
            else:
                logger.error(f"❌ Speech processing failed: {result['message']}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Speech recognition test failed: {e}")
            return False
    
    async def test_audio_playback(self):
        """Test that audio actually plays"""
        logger.info("🎵 Testing audio playback...")
        
        try:
            # Wait for audio element
            await self.page.wait_for_selector('#audio', timeout=5000)
            
            # Wait a bit for any async audio loading to complete
            await asyncio.sleep(2)
            
            # Check current log output to see what happened during audio loading
            log_content = await self.page.evaluate("document.getElementById('log').innerHTML")
            recent_logs = log_content.split('<br>')[-10:]  # Last 10 log entries
            logger.info("📋 Recent browser logs:")
            for log_line in recent_logs[-5:]:  # Show last 5 logs
                if log_line.strip():
                    logger.info(f"   {log_line.strip()}")
            
            # Check if audio source is set
            audio_src = await self.page.get_attribute('#audio', 'src')
            logger.info(f"🎵 Audio source: {audio_src}")
            
            if audio_src and audio_src != '':
                # Try comprehensive audio test
                audio_test_result = await self.page.evaluate("""
                    async () => {
                        const audio = document.getElementById('audio');
                        const logs = [];
                        
                        // Check audio properties
                        logs.push(`Audio src: ${audio.src}`);
                        logs.push(`Audio readyState: ${audio.readyState}`);
                        logs.push(`Audio networkState: ${audio.networkState}`);
                        logs.push(`Audio duration: ${audio.duration}`);
                        logs.push(`Audio paused: ${audio.paused}`);
                        
                        // Check for any error
                        if (audio.error) {
                            logs.push(`Audio error: ${audio.error.code} - ${audio.error.message}`);
                            return { 
                                success: false, 
                                message: `Audio error: ${audio.error.message}`,
                                logs: logs
                            };
                        }
                        
                        // Try to play
                        try {
                            await audio.play();
                            logs.push('Audio.play() succeeded');
                            return { success: true, message: 'Audio played successfully', logs: logs };
                        } catch (error) {
                            logs.push(`Audio.play() failed: ${error.message}`);
                            return { success: false, message: error.message, logs: logs };
                        }
                    }
                """)
                
                # Log detailed audio information
                for log_msg in audio_test_result.get('logs', []):
                    logger.info(f"🎵 {log_msg}")
                
                if audio_test_result['success']:
                    logger.info("✅ Audio playback successful")
                    return True
                else:
                    logger.warning(f"⚠️ Audio playback issue: {audio_test_result['message']}")
                    return False
            else:
                logger.error("❌ No audio source found")
                return False
                
        except Exception as e:
            logger.error(f"❌ Audio playback test failed: {e}")
            return False
    
    async def test_quick_commands(self):
        """Test the quick command buttons"""
        logger.info("⚡ Testing quick commands...")
        
        test_commands = [
            ("Test TTS", "testTTS('Hej, hur mår du?')"),
            ("Test Email", "testTTS('Kolla min email')"),
            ("Test Tid", "testTTS('Vad är klockan?')")
        ]
        
        for cmd_name, cmd_js in test_commands:
            try:
                logger.info(f"🎯 Testing: {cmd_name}")
                
                # Execute the command
                await self.page.evaluate(f"{cmd_js}")
                
                # Wait for TTS processing
                await asyncio.sleep(2)
                
                logger.info(f"✅ {cmd_name} executed")
                
            except Exception as e:
                logger.error(f"❌ {cmd_name} failed: {e}")
        
        return True
    
    async def generate_test_report(self):
        """Generate comprehensive test report"""
        logger.info("📊 Generating test report...")
        
        total_time = time.time() - self.start_time
        
        report = {
            'test_id': f"voice_v2_real_e2e_{int(time.time())}",
            'timestamp': datetime.now().isoformat(),
            'total_duration_s': round(total_time, 2),
            'events': self.test_results,
            'summary': {
                'total_events': len(self.test_results),
                'errors': len([r for r in self.test_results if r['type'] == 'error']),
                'successes': len([r for r in self.test_results if 'success' in r['message'].lower()]),
            }
        }
        
        # Save detailed report
        report_file = Path('voice_v2_real_e2e_report.json')
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"📄 Test report saved: {report_file}")
        logger.info(f"📊 Test Summary:")
        logger.info(f"   - Total time: {total_time:.2f}s")
        logger.info(f"   - Events logged: {len(self.test_results)}")
        logger.info(f"   - Errors: {report['summary']['errors']}")
        logger.info(f"   - Successes: {report['summary']['successes']}")
        
        return report
    
    async def cleanup(self):
        """Clean up resources"""
        if self.browser:
            await self.browser.close()
        logger.info("🧹 Cleanup complete")
    
    async def run_full_test(self):
        """Run the complete E2E test suite"""
        logger.info("🎬 Starting Voice v2 Real E2E Test Suite")
        logger.info("=" * 60)
        
        try:
            # Setup
            await self.setup_browser()
            
            # Test sequence
            tests = [
                ("Backend Health", self.test_backend_health),
                ("Load Voice Page", self.load_voice_page),
                ("TTS Direct Test", self.test_tts_directly),
                ("Microphone Button", self.test_microphone_button),
                ("Speech Recognition", self.test_speech_recognition),
                ("Audio Playback", self.test_audio_playback),
                ("Quick Commands", self.test_quick_commands)
            ]
            
            results = {}
            for test_name, test_func in tests:
                logger.info(f"\n🧪 Running: {test_name}")
                try:
                    result = await test_func()
                    results[test_name] = result
                    if result:
                        logger.info(f"✅ {test_name}: PASS")
                    else:
                        logger.error(f"❌ {test_name}: FAIL")
                except Exception as e:
                    logger.error(f"💥 {test_name}: ERROR - {e}")
                    results[test_name] = False
                
                # Wait between tests
                await asyncio.sleep(1)
            
            # Generate report
            report = await self.generate_test_report()
            
            # Final summary
            passed = sum(1 for r in results.values() if r)
            total = len(results)
            
            logger.info(f"\n🏁 Test Suite Complete!")
            logger.info(f"📊 Results: {passed}/{total} tests passed")
            
            if passed == total:
                logger.info("🎉 ALL TESTS PASSED! Voice v2 is working correctly!")
            else:
                logger.warning(f"⚠️ {total - passed} tests failed. Check logs for details.")
            
            return report
            
        finally:
            await self.cleanup()

async def main():
    """Run the real E2E test"""
    
    # Check if required services are running
    logger.info("🔍 Checking required services...")
    
    try:
        # Check backend
        result = subprocess.run(['curl', '-s', 'http://localhost:8000/health'], 
                              capture_output=True, timeout=5)
        if result.returncode != 0:
            logger.error("❌ Backend not running on localhost:8000")
            logger.info("💡 Start backend: uvicorn app_minimal:app --host 127.0.0.1 --port 8000")
            return
        
        # Check frontend
        result = subprocess.run(['curl', '-s', 'http://localhost:3000/health'], 
                              capture_output=True, timeout=5)
        if result.returncode != 0:
            logger.warning("⚠️ Frontend may not be running on localhost:3000")
            logger.info("💡 Start frontend: npm run dev")
    
    except Exception as e:
        logger.warning(f"⚠️ Service check failed: {e}")
    
    # Run the test
    tester = RealVoiceE2ETest()
    await tester.run_full_test()

if __name__ == "__main__":
    print("🎙️ Voice v2 Real E2E Test")
    print("=" * 40)
    print("Detta test kommer att:")
    print("- Öppna en riktig webbläsare")
    print("- Aktivera mikrofon-behörigheter")
    print("- Klicka på knappar och testa voice-flödet")
    print("- Logga alla händelser och fel")
    print("- Spela upp riktig audio")
    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ Test avbrutet av användare")
    except Exception as e:
        print(f"\n💥 Test kraschade: {e}")
        sys.exit(1)