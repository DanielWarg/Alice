# 🤖 Alice Agent Core v1

**Autonomous Workflow Engine for intelligent task execution**

Agent Core v1 gives Alice the ability to autonomously plan, execute, and improve complex multi-step tasks through a sophisticated Planning → Execution → Criticism → Improvement cycle. The system also includes an advanced voice pipeline for real-time voice interaction.

## 🏗️ Architecture

Agent Core consists of four main components:

### 🧠 AgentPlanner
Breaks down complex goals into concrete, executable steps.

**Capabilities:**
- Rule-based task decomposition
- AI-integration ready (Ollama/OpenAI)
- Swedish language support
- Dependency management
- Confidence scoring
- Duration estimation

**Example:**
```python
planner = AgentPlanner()
plan = await planner.create_plan("spela musik och sätt volym till 75")
# Creates: [PLAY, SET_VOLUME(level=75)]
```

### ⚡ AgentExecutor  
Executes action plans with dependencies and parallelization.

**Capabilities:**
- Dependency-aware execution
- Parallel action processing
- Progress tracking
- Error handling & recovery
- Retry logic with exponential backoff
- Execution hooks for monitoring
- Cancellation support

**Example:**
```python
executor = AgentExecutor(max_parallel_actions=3)
result = await executor.execute_plan(plan, progress_callback=callback)
# Executes all actions according to dependencies
```

### 🔍 AgentCritic
Analyzes execution results and suggests improvements.

**Analyzes:**
- Execution success rate
- Performance metrics
- Tool usage patterns
- Error patterns
- Dependency optimization
- Resource utilization

**Generates:**
- Detailed insights with confidence scores  
- Prioritized recommendations
- Performance metrics
- Improvement suggestions

**Example:**
```python
critic = AgentCritic()
report = await critic.evaluate_execution(plan, execution_result)
# Generates detailed analysis with recommendations
```

### 🎭 AgentOrchestrator
Coordinates the entire workflow with Planning→Execution→Criticism→Improvement cycles.

**Handles:**
- Complete workflow orchestration
- Automatic improvement cycles
- Multiple improvement strategies
- Progress monitoring
- Error recovery
- Workflow cancellation
- Parallel workflows

**Example:**
```python
orchestrator = AgentOrchestrator()
result = await orchestrator.execute_workflow("komplex uppgift")
# Automatic Planning → Execution → Criticism → Improvement
```

## 🔄 Workflow Lifecycle

1. **PLANNING** - AgentPlanner creates detailed action plan
2. **EXECUTION** - AgentExecutor performs actions according to dependencies  
3. **CRITICISM** - AgentCritic analyzes results and suggests improvements
4. **IMPROVEMENT** - AgentOrchestrator applies improvements and iterates

## 🎯 Improvement Strategies

### ADAPTIVE (Standard)
Intelligent improvements based on critic recommendations:
- Remove problematic steps
- Modify parameters  
- Optimize execution order
- Retry failed actions

### RETRY_FAILED
Focuses on retrying failed actions.

### OPTIMIZE_PLAN  
Optimizes the entire plan structurally.

### NONE
No automatic improvement.

## 📊 Test Coverage

Agent Core v1 has **100 tests** with full coverage:

- **24 AgentPlanner tests** - Planning logic, validation, error handling
- **21 AgentExecutor tests** - Execution, dependencies, parallelization  
- **19 AgentCritic tests** - Analysis, insights, recommendations
- **23 AgentOrchestrator tests** - Workflow management, improvement cycles
- **13 Integration tests** - End-to-end scenarios, complex workflows

**100% Pass Rate** - All tests validate functionality.

## 🚀 Usage

### Basic Autonomous Workflow
```python
from core import AgentOrchestrator

orchestrator = AgentOrchestrator()
result = await orchestrator.execute_workflow("spela musik")

if result.success:
    print(f"✅ Workflow completed! Score: {result.final_score}")
```

### Simple API
```python
success, summary = await orchestrator.execute_simple_goal("pausa musiken")
print(f"Success: {success}, Score: {summary['final_score']}")
```

### With Progress Tracking
```python
def progress_callback(info):
    print(f"Progress: {info['message']}")

result = await orchestrator.execute_workflow(
    "komplex uppgift", 
    progress_callback=progress_callback
)
```

### Custom Configuration
```python
from core import WorkflowConfig, ImprovementStrategy

config = WorkflowConfig(
    max_iterations=5,
    improvement_strategy=ImprovementStrategy.ADAPTIVE,
    min_success_score=0.9,
    auto_improve=True
)

orchestrator = AgentOrchestrator(config=config)
```

### Parallel Workflows
```python
tasks = [
    orchestrator.execute_workflow("spela musik"),
    orchestrator.execute_workflow("kolla e-post"), 
    orchestrator.execute_workflow("visa kalender")
]

results = await asyncio.gather(*tasks)
```

## 🎤 Voice Pipeline Architecture

Agent Core v1 includes a sophisticated voice pipeline that enables seamless voice interaction with Alice:

### Dual Voice System

**VoiceBox (Basic Interface)**
- Browser Speech Recognition API for Swedish
- Real-time audio visualization with ambient animation
- Post-processing of Swedish speech for better recognition
- Integration with Alice backend TTS system
- Fallback system for graceful degradation

**VoiceClient (Advanced Realtime)**
- OpenAI Realtime API integration via WebRTC
- Low-latency audio streaming for professional quality
- Agent bridge architecture with SSE streaming
- Real-time transcript processing
- Barge-in support for natural conversation

### Agent Bridge Architecture

The voice pipeline uses a sophisticated agent bridge to connect voice interaction to Alice's cognitive capabilities:

```
Voice Input → OpenAI Realtime → Transcript → Agent Bridge → Alice Core → Streaming Response → TTS → Audio Output
```

**Components:**
- **Speech-to-Text**: OpenAI Whisper via Realtime API
- **Agent Bridge**: `/api/agent/stream` endpoint with SSE
- **Alice Core**: Agent orchestration and tool execution  
- **Text-to-Speech**: Hybrid OpenAI TTS / Alice enhanced TTS
- **WebRTC**: Real-time audio streaming

### Real-time Communication Flow

1. **Audio Capture** - WebRTC MediaStream from microphone
2. **Speech Recognition** - OpenAI Realtime API transcribes in real-time
3. **Agent Processing** - Transcript sent to Alice agent via SSE
4. **Tool Execution** - Alice Agent Core executes tools when needed
5. **Response Generation** - Streaming text response from Alice
6. **Speech Synthesis** - TTS conversion and audio playback
7. **Barge-in Support** - User can interrupt and start new interaction

### Voice WebSocket Events

```javascript
// Voice events that integrate with Agent Core
const voiceEvents = {
  'voice_input': (transcript) => {
    // Send to AgentOrchestrator for processing
    orchestrator.execute_workflow(transcript);
  },
  
  'agent_response': (response) => {
    // Streaming response from Agent Core
    voiceClient.synthesizeAndPlay(response.content);
  },
  
  'tool_execution': (toolData) => {
    // Tool execution from Agent Executor
    voiceClient.emit('tool_executed', toolData);
  }
};
```

### Integration Points

**Agent Core → Voice Pipeline:**
- AgentOrchestrator triggers voice responses
- AgentExecutor tools can generate audio feedback
- AgentCritic analyzes conversation quality
- Real-time progress updates via voice synthesis

**Voice Pipeline → Agent Core:**
- Voice commands trigger Agent workflows  
- Continuous conversation state management
- Context awareness between voice sessions
- Memory integration for personalized responses

## 🔧 Integration with Alice

Agent Core v1 is fully integrated with Alice's existing system and voice pipeline:

### Tools (22 total)
- **Music Control:** PLAY, PAUSE, STOP, SET_VOLUME, etc.
- **Email:** READ_EMAILS, SEND_EMAIL, SEARCH_EMAILS
- **Calendar:** LIST_CALENDAR_EVENTS, CREATE_CALENDAR_EVENT, etc.

### NLU Integration
Agent Core works with Alice's Swedish NLU system to understand complex goals.

### Voice Integration  
Works seamlessly with Alice's voice control system.

## 📈 Performance

- **Sub-second planning** for simple tasks
- **Parallel execution** for independent actions
- **Intelligent retry logic** for robust execution
- **Memory efficient** with streaming progress updates
- **Scalable architecture** for complex workflows

## 🔮 Future Improvements

- **AI-based planning** with Ollama/OpenAI integration
- **Learning from experience** for better future planning  
- **Advanced multi-tool scenarios** with complex reasoning
- **Persistent workflow history** and analytics
- **Dynamic replanning** based on real-time feedback
- **Resource optimization** and load balancing

## 🎉 Status

**Agent Core v1 is COMPLETE and READY for production!**

✅ Full architecture implemented  
✅ 100 tests passing all  
✅ Integration with Alice's tools  
✅ Autonomous workflow capability  
✅ Comprehensive documentation  

Agent Core v1 transforms Alice from a reactive assistant to a proactive, intelligent agent that can independently plan and execute complex tasks!