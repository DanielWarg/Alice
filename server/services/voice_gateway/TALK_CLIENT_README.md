# OpenAI Realtime Talk Client

🎙️ Production-ready WebRTC client for direct communication with OpenAI Realtime API

## Overview

The Talk Client provides seamless integration between WebRTC and OpenAI's Realtime API for ultra-low latency voice conversations. It features intelligent audio buffering, barge-in support, comprehensive performance monitoring, and robust error handling.

## Features

### Core Functionality
- **Direct WebRTC Communication**: Stream audio directly to/from OpenAI Realtime API
- **Jitter Buffering (80-120ms)**: Smooth audio playback with adaptive buffering
- **Barge-in Support**: Intelligent audio ducking when user interrupts AI
- **English Voice Support**: Optimized for `alloy` and `nova` voices
- **Real-time Performance Monitoring**: P50/P95 latency tracking

### Advanced Features
- **Safe Summary Integration**: Handle local tool execution seamlessly  
- **Automatic Reconnection**: Resilient connection management
- **Comprehensive Error Handling**: Production-grade error recovery
- **Performance Metrics**: Detailed latency and performance analytics
- **Thread-safe Audio Processing**: Robust concurrent audio handling

## Quick Start

### Basic Usage

```python
from talk_client import create_talk_client
import asyncio

async def main():
    # Create client with OpenAI API key
    client = create_talk_client(
        api_key="sk-...",  # Or set OPENAI_API_KEY env var
        voice="alloy",     # or "nova"
        instructions="You are Alice, speak concisely in 1-2 sentences."
    )
    
    # Set up event handlers
    client.on_transcript = lambda text, final: print(f"Transcript: {text}")
    client.on_audio_start = lambda: print("AI started speaking")
    client.on_error = lambda error: print(f"Error: {error}")
    
    # Initialize and handle WebRTC offer
    await client.initialize()
    answer_sdp = await client.handle_webrtc_offer(offer_sdp)
    
    # Client is now ready for real-time voice communication!

asyncio.run(main())
```

### Integration with Existing Voice Gateway

```python
from talk_client import create_talk_client
from webrtc import WebRTCManager
from metrics import VoiceMetrics

class VoiceGateway:
    def __init__(self):
        self.talk_clients = {}
        self.metrics = VoiceMetrics()
    
    async def handle_webrtc_offer(self, session_id: str, offer_sdp: str):
        # Create talk client for this session
        client = create_talk_client(voice="nova")
        await client.initialize()
        
        # Handle WebRTC offer
        answer_sdp = await client.handle_webrtc_offer(offer_sdp)
        
        # Store client for session
        self.talk_clients[session_id] = client
        
        return answer_sdp
    
    async def send_tool_result(self, session_id: str, result: str):
        """Send local tool execution result to AI"""
        if session_id in self.talk_clients:
            await self.talk_clients[session_id].send_safe_summary(result)
```

## Configuration

### RealtimeConfig Options

```python
from talk_client import RealtimeConfig, create_talk_client

config = RealtimeConfig(
    api_key="sk-...",
    voice="alloy",           # "alloy" or "nova" (English voices)
    language="en",           # Language code
    temperature=0.7,         # Response creativity (0.0-1.0)
    max_response_output_tokens=150,  # Short responses for low latency
    instructions="Custom system prompt...",
    vad_threshold=0.5,       # Voice activity detection sensitivity
    vad_silence_duration_ms=500,  # Silence before response (lower = faster)
    vad_prefix_padding_ms=300,    # Audio padding before speech
)

client = OpenAIRealtimeTalkClient(config)
```

### Environment Variables

```bash
# Required
export OPENAI_API_KEY="sk-..."

# Optional (with defaults)
export TALK_CLIENT_LOG_LEVEL="INFO"
export TALK_CLIENT_RECONNECT_ATTEMPTS="3"
export TALK_CLIENT_JITTER_BUFFER_MS="100"
```

## Audio Processing Pipeline

```
Microphone → WebRTC → PCM16 Conversion → OpenAI Realtime API
                                              ↓
Browser ← WebRTC ← Jitter Buffer ← PCM16 Audio ← OpenAI Response
```

### Jitter Buffer Configuration

The jitter buffer ensures smooth audio playback despite network variability:

```python
from talk_client import JitterBuffer

buffer = JitterBuffer(
    target_size_ms=100,  # Target buffer size (80-120ms recommended)
    max_buffer_ms=200,   # Maximum buffer to prevent excessive delay
    min_buffer_ms=50,    # Minimum buffer before playback starts
)
```

## Event Handlers

### Available Events

```python
# Transcript events (both partial and final)
client.on_transcript = lambda text, is_final: handle_transcript(text, is_final)

# Audio playback events  
client.on_audio_start = lambda: print("AI started speaking")
client.on_audio_end = lambda: print("AI finished speaking")

# Connection events
client.on_connection_change = lambda connected: handle_connection(connected)

# Error handling
client.on_error = lambda error: handle_error(error)

# Local tool integration
client.on_safe_summary = lambda summary: execute_local_tools(summary)
```

### Transcript Processing Example

```python
def handle_transcript(text: str, is_final: bool):
    if is_final:
        print(f"User said: {text}")
        # Store in conversation history
        conversation.add_user_message(text)
    else:
        print(f"Partial: {text}")  # Show live transcription
```

## Barge-in Implementation

The client automatically handles user interruption of AI responses:

```python
# When user starts speaking during AI response:
# 1. AI audio is ducked to 10% volume
# 2. Jitter buffer is cleared to stop current response
# 3. OpenAI response is cancelled
# 4. New user input is processed
# 5. Audio volume is restored

# Barge-in is tracked in performance metrics
metrics = client.get_performance_metrics()
print(f"Average barge-in response time: {metrics['barge_in_avg_ms']}ms")
```

## Performance Monitoring

### Real-time Metrics

```python
# Get comprehensive performance data
metrics = client.get_performance_metrics()

print(f"Connection: {metrics['connection_state']}")
print(f"Latency P50: {metrics['latency_metrics']['p50']}ms")
print(f"Latency P95: {metrics['latency_metrics']['p95']}ms") 
print(f"First audio: {metrics['latency_metrics']['first_audio_avg']}ms")
print(f"Buffer size: {metrics['audio_state']['jitter_buffer_size_ms']}ms")
```

### Integration with Prometheus

```python
from metrics import VoiceMetrics
import prometheus_client

# Export metrics to Prometheus
voice_metrics = VoiceMetrics()
prometheus_client.generate_latest(voice_metrics.registry)

# Key metrics tracked:
# - voice_first_partial_ms: Time to first transcript
# - voice_first_audio_ms: Time to first AI audio (TTFA)
# - voice_barge_in_ms: Barge-in response time
# - voice_webrtc_active_sessions: Active sessions
```

## Safe Summary Integration

Handle local tool execution requests from the AI:

```python
async def handle_safe_summary_request(summary_request: str):
    """Process local tool execution request"""
    
    if "weather" in summary_request.lower():
        # Execute weather API call locally
        weather_data = await get_weather_locally()
        result = f"Weather: {weather_data['temperature']}°C, {weather_data['condition']}"
    
    elif "calendar" in summary_request.lower():
        # Check calendar locally
        events = await get_calendar_events()
        result = f"Next meeting: {events[0]['title']} at {events[0]['time']}"
    
    else:
        result = "I've processed that information locally."
    
    # Send result back to AI
    await client.send_safe_summary(result)

# Register the handler
client.on_safe_summary = handle_safe_summary_request
```

## Error Handling & Recovery

### Connection Management

```python
# The client handles various error scenarios automatically:

# 1. Network disconnection → Automatic reconnection with exponential backoff
# 2. WebSocket errors → Connection recovery and session restoration  
# 3. Audio processing errors → Graceful degradation and logging
# 4. OpenAI API errors → Error reporting and fallback behavior

# Custom error handling
def handle_error(error_msg: str):
    if "rate_limit" in error_msg.lower():
        # Implement rate limit backoff
        schedule_retry(delay=60)
    elif "authentication" in error_msg.lower():
        # Refresh API key
        refresh_openai_key()
    else:
        # Log and alert
        logger.error(f"Talk client error: {error_msg}")
        send_alert(error_msg)

client.on_error = handle_error
```

### Health Checks

```python
# Check client health
if client.is_connected():
    print("Client is healthy")
else:
    print(f"Client state: {client.state}")
    
    if client.state == TalkClientState.ERROR:
        # Attempt recovery
        await client.disconnect()
        await client.connect_to_openai()
```

## Testing

Run the comprehensive test suite:

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run all tests
python test_talk_client.py

# Run specific test categories
python -m pytest test_talk_client.py::TestLatencyMetrics
python -m pytest test_talk_client.py::TestJitterBuffer
python -m pytest test_talk_client.py::TestTalkClientIntegration
```

### Performance Benchmarks

```bash
# Run performance benchmarks
python test_talk_client.py | grep "📊"

# Expected performance targets:
# - Jitter buffer operations: <1ms
# - Latency metrics calculation: <10ms
# - WebRTC offer processing: <100ms
# - First audio response: <300ms
# - Barge-in response: <120ms
```

## Production Deployment

### Docker Configuration

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Set production environment
ENV OPENAI_API_KEY=""
ENV LOG_LEVEL="INFO" 
ENV TALK_CLIENT_RECONNECT_ATTEMPTS="5"

EXPOSE 8000

CMD ["python", "example_integration.py", "production"]
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: alice-voice-gateway
spec:
  replicas: 3
  selector:
    matchLabels:
      app: alice-voice-gateway
  template:
    metadata:
      labels:
        app: alice-voice-gateway
    spec:
      containers:
      - name: voice-gateway
        image: alice/voice-gateway:latest
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: openai-secret
              key: api-key
        ports:
        - containerPort: 8000
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

### Monitoring & Alerting

```python
# Set up monitoring
from prometheus_client import start_http_server

# Start metrics server
start_http_server(8080)

# Configure alerts for:
# - High latency (P95 > 1000ms)
# - Connection failures (error rate > 5%)
# - Buffer underruns (underrun rate > 1%)
# - API rate limits (429 errors)

# Example Grafana dashboard queries:
# - Average latency: rate(voice_first_audio_ms_sum[5m]) / rate(voice_first_audio_ms_count[5m])
# - P95 latency: histogram_quantile(0.95, voice_first_audio_ms_bucket)
# - Active sessions: voice_webrtc_active_sessions
# - Error rate: rate(voice_errors_total[5m])
```

## Troubleshooting

### Common Issues

1. **High Latency (>500ms)**
   ```bash
   # Check network connectivity
   ping api.openai.com
   
   # Verify API key permissions
   curl -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models
   
   # Check jitter buffer configuration
   # Reduce target_size_ms if latency is too high
   ```

2. **Audio Quality Issues**
   ```bash
   # Verify WebRTC audio format
   # Ensure PCM16 24kHz mono format
   
   # Check jitter buffer underruns
   # Increase min_buffer_ms if audio is choppy
   ```

3. **Connection Drops**
   ```bash
   # Enable debug logging
   export LOG_LEVEL=DEBUG
   
   # Check reconnection attempts
   # Increase max_reconnect_attempts if needed
   ```

### Debug Mode

```python
# Enable comprehensive logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Add debug event handlers
client.on_connection_change = lambda connected: print(f"Debug: Connection {connected}")
client.on_error = lambda error: print(f"Debug: Error {error}")

# Monitor performance continuously  
async def monitor_performance():
    while True:
        metrics = client.get_performance_metrics()
        print(f"Debug: {metrics}")
        await asyncio.sleep(10)

asyncio.create_task(monitor_performance())
```

## API Reference

### Main Classes

- `OpenAIRealtimeTalkClient`: Main client class for WebRTC ↔ OpenAI communication
- `RealtimeConfig`: Configuration for OpenAI Realtime API connection  
- `JitterBuffer`: Audio buffering for smooth playback
- `AudioPlaybackTrack`: WebRTC audio track with ducking support
- `LatencyMetrics`: Performance monitoring and analytics

### Factory Functions

- `create_talk_client()`: Create client with sensible defaults
- `create_realtime_client()`: Create OpenAI client directly (legacy)

### Configuration Enums

- `TalkClientState`: Connection state management
- `AudioFormat`: Supported audio formats

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality  
4. Ensure all tests pass: `python test_talk_client.py`
5. Submit a pull request

## License

This code is part of the Alice Voice Gateway project. See the main project LICENSE for details.

---

**Built with ❤️ for ultra-low latency voice AI**

For questions or support, please open an issue in the main Alice project repository.