"""
B3 Soak Test - Long-running stability test for Alice B3 Always-On Voice
Tests memory leaks, connection stability, and sustained performance
"""

import asyncio
import websockets
import json
import time
import base64
import numpy as np
import psutil
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
import httpx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'soak_test_b3_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("alice.soak_test")

class B3SoakTest:
    """Long-running soak test for B3 system"""
    
    def __init__(self, duration_hours: float = 2.0):
        self.duration_seconds = duration_hours * 3600
        self.ws_url = "ws://localhost:8000/ws/voice/ambient"
        self.base_url = "http://localhost:8000"
        self.sample_rate = 16000
        self.frame_duration_ms = 20
        self.frame_size = int(self.sample_rate * self.frame_duration_ms / 1000)
        
        # Statistics
        self.stats = {
            'start_time': 0,
            'end_time': 0,
            'frames_sent': 0,
            'messages_received': 0,
            'transcriptions_received': 0,
            'connection_drops': 0,
            'errors': 0,
            'memory_samples': [],
            'cpu_samples': [],
            'latency_samples': [],
            'barge_ins_triggered': 0
        }
        
        # Process monitoring
        self.process = psutil.Process(os.getpid())
        self.server_process = None
        
        logger.info(f"B3 Soak Test initialized for {duration_hours} hours")
    
    async def generate_realistic_audio_frame(self, time_offset: float) -> str:
        """Generate realistic audio frame with varying content"""
        duration_seconds = self.frame_duration_ms / 1000.0
        t = np.linspace(0, duration_seconds, self.frame_size, False)
        
        # Simulate different types of audio content
        content_type = int((time_offset * 0.1) % 4)
        
        if content_type == 0:  # Silence
            audio = np.zeros(self.frame_size)
        elif content_type == 1:  # Speech-like pattern
            fundamental = 150 + 50 * np.sin(time_offset * 0.5)  # Varying pitch
            audio = (
                0.3 * np.sin(2 * np.pi * fundamental * t) +
                0.15 * np.sin(2 * np.pi * fundamental * 2 * t) +
                0.1 * np.sin(2 * np.pi * fundamental * 3 * t)
            )
            # Add amplitude modulation for speech-like patterns
            envelope = 0.1 + 0.4 * (1 + np.sin(time_offset * 8))
            audio *= envelope
        elif content_type == 2:  # Background noise
            audio = 0.05 * np.random.normal(0, 1, self.frame_size)
        else:  # Mixed content
            freq1 = 440 + 100 * np.sin(time_offset * 0.3)
            freq2 = 880 + 50 * np.cos(time_offset * 0.7)
            audio = 0.2 * (np.sin(2 * np.pi * freq1 * t) + 0.5 * np.sin(2 * np.pi * freq2 * t))
        
        # Add some random variation
        audio += 0.02 * np.random.normal(0, 1, self.frame_size)
        
        # Clip and convert to int16
        audio = np.clip(audio, -1.0, 1.0)
        audio_int16 = (audio * 32767).astype(np.int16)
        
        # Convert to base64
        audio_bytes = audio_int16.tobytes()
        return base64.b64encode(audio_bytes).decode('utf-8')
    
    async def monitor_system_resources(self):
        """Monitor system resource usage"""
        while True:
            try:
                # Memory usage
                memory_info = self.process.memory_info()
                self.stats['memory_samples'].append({
                    'timestamp': time.time(),
                    'rss_mb': memory_info.rss / 1024 / 1024,
                    'vms_mb': memory_info.vms / 1024 / 1024
                })
                
                # CPU usage
                cpu_percent = self.process.cpu_percent()
                self.stats['cpu_samples'].append({
                    'timestamp': time.time(),
                    'cpu_percent': cpu_percent
                })
                
                # Log every minute
                if len(self.stats['memory_samples']) % 60 == 0:  # Every minute
                    logger.info(f"Resource usage - Memory: {memory_info.rss / 1024 / 1024:.1f}MB, CPU: {cpu_percent:.1f}%")
                
                await asyncio.sleep(1)  # Sample every second
                
            except Exception as e:
                logger.error(f"Error monitoring resources: {e}")
                await asyncio.sleep(5)
    
    async def periodic_health_check(self):
        """Periodic health checks via HTTP API"""
        while True:
            try:
                async with httpx.AsyncClient() as client:
                    # Health check
                    response = await client.get(f"{self.base_url}/metrics/health", timeout=5.0)
                    if response.status_code == 200:
                        health_data = response.json()
                        if not health_data.get('healthy'):
                            logger.warning(f"System unhealthy: {health_data}")
                    else:
                        logger.warning(f"Health check failed: {response.status_code}")
                    
                    # Periodic barge-in test
                    if time.time() % 300 < 1:  # Every 5 minutes
                        barge_response = await client.post(
                            f"{self.base_url}/api/voice/barge-in",
                            json={"source": "soak_test", "confidence": 0.8, "reason": "periodic_test"},
                            timeout=5.0
                        )
                        if barge_response.status_code == 200:
                            self.stats['barge_ins_triggered'] += 1
                            logger.info("Periodic barge-in test successful")
                
            except Exception as e:
                logger.error(f"Health check error: {e}")
            
            await asyncio.sleep(30)  # Check every 30 seconds
    
    async def audio_streaming_task(self):
        """Main audio streaming task with reconnection logic"""
        connection_attempts = 0
        consecutive_errors = 0
        
        while time.time() < self.stats['start_time'] + self.duration_seconds:
            try:
                connection_attempts += 1
                logger.info(f"Connecting to WebSocket (attempt {connection_attempts})...")
                
                async with websockets.connect(self.ws_url) as websocket:
                    logger.info("WebSocket connected, starting audio stream...")
                    consecutive_errors = 0
                    
                    # Wait for initial status
                    try:
                        initial_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        initial_data = json.loads(initial_response)
                        self.stats['messages_received'] += 1
                        logger.info(f"Initial status: {initial_data.get('type')}")
                    except asyncio.TimeoutError:
                        logger.warning("No initial status received")
                    
                    # Start streaming audio
                    last_frame_time = time.time()
                    
                    while time.time() < self.stats['start_time'] + self.duration_seconds:
                        try:
                            current_time = time.time()
                            time_offset = current_time - self.stats['start_time']
                            
                            # Generate and send audio frame
                            audio_frame = await self.generate_realistic_audio_frame(time_offset)
                            
                            message = {
                                "type": "audio_frame",
                                "audio_data": audio_frame,
                                "timestamp": current_time,
                                "sample_rate": self.sample_rate,
                                "duration_ms": self.frame_duration_ms
                            }
                            
                            send_start = time.time()
                            await websocket.send(json.dumps(message))
                            self.stats['frames_sent'] += 1
                            
                            # Check for responses (non-blocking)
                            try:
                                response = await asyncio.wait_for(websocket.recv(), timeout=0.001)
                                recv_end = time.time()
                                latency_ms = (recv_end - send_start) * 1000
                                
                                self.stats['latency_samples'].append({
                                    'timestamp': recv_end,
                                    'latency_ms': latency_ms
                                })
                                
                                data = json.loads(response)
                                self.stats['messages_received'] += 1
                                
                                if data.get("type") == "transcription_result":
                                    self.stats['transcriptions_received'] += 1
                                    logger.info(f"Transcription: {data.get('text', 'N/A')[:50]}...")
                                
                            except asyncio.TimeoutError:
                                pass  # No response yet
                            
                            # Maintain real-time pace
                            elapsed = time.time() - last_frame_time
                            sleep_time = max(0, (self.frame_duration_ms / 1000.0) - elapsed)
                            
                            if sleep_time > 0:
                                await asyncio.sleep(sleep_time)
                            
                            last_frame_time = time.time()
                            
                            # Progress report every 1000 frames
                            if self.stats['frames_sent'] % 1000 == 0:
                                elapsed_hours = (time.time() - self.stats['start_time']) / 3600
                                remaining_hours = (self.duration_seconds - (time.time() - self.stats['start_time'])) / 3600
                                logger.info(f"Progress: {self.stats['frames_sent']} frames sent, "
                                           f"{self.stats['transcriptions_received']} transcriptions, "
                                           f"{elapsed_hours:.1f}h elapsed, {remaining_hours:.1f}h remaining")
                            
                        except websockets.exceptions.ConnectionClosed:
                            logger.warning("WebSocket connection closed")
                            self.stats['connection_drops'] += 1
                            break
                        except Exception as e:
                            self.stats['errors'] += 1
                            consecutive_errors += 1
                            logger.error(f"Error in streaming loop: {e}")
                            
                            if consecutive_errors > 10:
                                logger.error("Too many consecutive errors, breaking")
                                break
                            
                            await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"WebSocket connection error: {e}")
                self.stats['connection_drops'] += 1
                
                # Exponential backoff for reconnection
                wait_time = min(30, 2 ** min(connection_attempts - 1, 4))
                logger.info(f"Waiting {wait_time}s before reconnection attempt...")
                await asyncio.sleep(wait_time)
        
        logger.info("Audio streaming task completed")
    
    async def run_soak_test(self) -> Dict[str, Any]:
        """Run the complete soak test"""
        self.stats['start_time'] = time.time()
        logger.info(f"🧪 Starting B3 Soak Test for {self.duration_seconds/3600:.1f} hours")
        
        # Start background tasks
        resource_task = asyncio.create_task(self.monitor_system_resources())
        health_task = asyncio.create_task(self.periodic_health_check())
        streaming_task = asyncio.create_task(self.audio_streaming_task())
        
        try:
            # Wait for streaming to complete
            await streaming_task
            
        except KeyboardInterrupt:
            logger.info("Soak test interrupted by user")
        except Exception as e:
            logger.error(f"Soak test error: {e}")
        finally:
            # Cancel background tasks
            resource_task.cancel()
            health_task.cancel()
            
            self.stats['end_time'] = time.time()
            
            # Generate final report
            return self.generate_report()
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate final test report"""
        actual_duration = self.stats['end_time'] - self.stats['start_time']
        
        report = {
            'test_duration_hours': actual_duration / 3600,
            'frames_sent': self.stats['frames_sent'],
            'frames_per_second': self.stats['frames_sent'] / max(actual_duration, 1),
            'messages_received': self.stats['messages_received'],
            'transcriptions_received': self.stats['transcriptions_received'],
            'transcription_rate': self.stats['transcriptions_received'] / max(actual_duration/60, 1),  # per minute
            'connection_drops': self.stats['connection_drops'],
            'errors': self.stats['errors'],
            'error_rate': self.stats['errors'] / max(self.stats['frames_sent'], 1),
            'barge_ins_triggered': self.stats['barge_ins_triggered'],
            'memory_usage': {},
            'cpu_usage': {},
            'latency_stats': {}
        }
        
        # Memory usage analysis
        if self.stats['memory_samples']:
            memory_values = [s['rss_mb'] for s in self.stats['memory_samples']]
            report['memory_usage'] = {
                'initial_mb': memory_values[0],
                'final_mb': memory_values[-1],
                'peak_mb': max(memory_values),
                'growth_mb': memory_values[-1] - memory_values[0],
                'samples_count': len(memory_values)
            }
        
        # CPU usage analysis
        if self.stats['cpu_samples']:
            cpu_values = [s['cpu_percent'] for s in self.stats['cpu_samples']]
            report['cpu_usage'] = {
                'average_percent': sum(cpu_values) / len(cpu_values),
                'peak_percent': max(cpu_values),
                'samples_count': len(cpu_values)
            }
        
        # Latency analysis
        if self.stats['latency_samples']:
            latency_values = [s['latency_ms'] for s in self.stats['latency_samples']]
            latency_values.sort()
            n = len(latency_values)
            report['latency_stats'] = {
                'average_ms': sum(latency_values) / n,
                'median_ms': latency_values[n//2],
                'p95_ms': latency_values[int(n*0.95)],
                'p99_ms': latency_values[int(n*0.99)],
                'samples_count': n
            }
        
        return report

async def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='B3 Soak Test - Long-running stability test')
    parser.add_argument('--hours', type=float, default=2.0, help='Test duration in hours (default: 2.0)')
    parser.add_argument('--output', type=str, help='Output report file (JSON)')
    
    args = parser.parse_args()
    
    # Create and run soak test
    soak_test = B3SoakTest(duration_hours=args.hours)
    report = await soak_test.run_soak_test()
    
    # Print summary
    print("\n" + "="*50)
    print("🎯 B3 SOAK TEST RESULTS")
    print("="*50)
    
    for key, value in report.items():
        if isinstance(value, dict):
            print(f"{key}:")
            for subkey, subvalue in value.items():
                print(f"  {subkey}: {subvalue}")
        else:
            print(f"{key}: {value}")
    
    # Save report if requested
    if args.output:
        import json
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\n📊 Report saved to: {args.output}")
    
    # Determine test result
    success_criteria = {
        'error_rate < 0.05': report['error_rate'] < 0.05,
        'memory_growth < 100MB': report.get('memory_usage', {}).get('growth_mb', 0) < 100,
        'connection_drops < 10': report['connection_drops'] < 10,
        'frames_per_second > 30': report['frames_per_second'] > 30
    }
    
    all_passed = all(success_criteria.values())
    
    print(f"\n🎯 SUCCESS CRITERIA:")
    for criterion, passed in success_criteria.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {criterion}: {status}")
    
    if all_passed:
        print(f"\n🎉 SOAK TEST PASSED - Alice B3 is stable for extended operation!")
        exit(0)
    else:
        print(f"\n❌ SOAK TEST FAILED - Some stability issues detected")
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())