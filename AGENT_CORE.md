# 🤖 Alice Agent Core v1

**Autonomous Workflow Engine för intelligent task execution**

Agent Core v1 ger Alice förmågan att autonomt planera, exekvera och förbättra komplexa multi-step uppgifter genom en sofistikerad Planning → Execution → Criticism → Improvement cykel. Systemet inkluderar även en avancerad voice pipeline för real-time röstinteraktion.

## 🏗️ Arkitektur

Agent Core består av fyra huvudkomponenter:

### 🧠 AgentPlanner
Bryter ner komplexa mål i konkreta, exekverbara steg.

**Kapaciteter:**
- Regelbaserad task decomposition
- AI-integration ready (Ollama/OpenAI)
- Svenska språkstöd
- Dependency management
- Confidence scoring
- Duration estimation

**Exempel:**
```python
planner = AgentPlanner()
plan = await planner.create_plan("spela musik och sätt volym till 75")
# Skapar: [PLAY, SET_VOLUME(level=75)]
```

### ⚡ AgentExecutor  
Utför handlingsplaner med dependencies och parallellisering.

**Kapaciteter:**
- Dependency-aware execution
- Parallell action processing
- Progress tracking
- Error handling & recovery
- Retry logic med exponential backoff
- Execution hooks för monitoring
- Cancellation support

**Exempel:**
```python
executor = AgentExecutor(max_parallel_actions=3)
result = await executor.execute_plan(plan, progress_callback=callback)
# Exekverar alla actions enligt dependencies
```

### 🔍 AgentCritic
Analyserar execution-resultat och föreslår förbättringar.

**Analyserar:**
- Execution success rate
- Performance metrics
- Tool usage patterns
- Error patterns
- Dependency optimization
- Resource utilization

**Genererar:**
- Detailed insights med confidence scores  
- Prioriterade recommendations
- Performance metrics
- Improvement suggestions

**Exempel:**
```python
critic = AgentCritic()
report = await critic.evaluate_execution(plan, execution_result)
# Genererar detaljerad analys med rekommendationer
```

### 🎭 AgentOrchestrator
Koordinerar hela workflow med Planning→Execution→Criticism→Improvement cycles.

**Hanterar:**
- Fullständig workflow orchestration
- Automatic improvement cycles
- Multiple improvement strategies
- Progress monitoring
- Error recovery
- Workflow cancellation
- Parallel workflows

**Exempel:**
```python
orchestrator = AgentOrchestrator()
result = await orchestrator.execute_workflow("komplex uppgift")
# Automatisk Planning → Execution → Criticism → Improvement
```

## 🔄 Workflow Lifecycle

1. **PLANNING** - AgentPlanner skapar detaljerad handlingsplan
2. **EXECUTION** - AgentExecutor utför actions enligt dependencies  
3. **CRITICISM** - AgentCritic analyserar resultat och föreslår förbättringar
4. **IMPROVEMENT** - AgentOrchestrator tillämpar förbättringar och itererar

## 🎯 Förbättringsstrategier

### ADAPTIVE (Standard)
Intelligenta förbättringar baserat på critic recommendations:
- Remove problematic steps
- Modify parameters  
- Optimize execution order
- Retry failed actions

### RETRY_FAILED
Fokuserar på att retry misslyckade actions.

### OPTIMIZE_PLAN  
Optimerar hela planen strukturellt.

### NONE
Ingen automatisk förbättring.

## 📊 Test Coverage

Agent Core v1 har **100 tester** med full coverage:

- **24 AgentPlanner tester** - Planning logic, validation, error handling
- **21 AgentExecutor tester** - Execution, dependencies, parallellisering  
- **19 AgentCritic tester** - Analysis, insights, recommendations
- **23 AgentOrchestrator tester** - Workflow management, improvement cycles
- **13 Integration tester** - End-to-end scenarios, complex workflows

**100% Pass Rate** - Alla tester validerar funktionalitet.

## 🚀 Användning

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

### Med Progress Tracking
```python
def progress_callback(info):
    print(f"Progress: {info['message']}")

result = await orchestrator.execute_workflow(
    "komplex uppgift", 
    progress_callback=progress_callback
)
```

### Anpassad Konfiguration
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

### Parallella Workflows
```python
tasks = [
    orchestrator.execute_workflow("spela musik"),
    orchestrator.execute_workflow("kolla e-post"), 
    orchestrator.execute_workflow("visa kalender")
]

results = await asyncio.gather(*tasks)
```

## 🎤 Voice Pipeline Arkitektur

Agent Core v1 inkluderar en sofistikerad voice pipeline som möjliggör seamless röstinteraktion med Alice:

### Dual Voice System

**VoiceBox (Basic Interface)**
- Browser Speech Recognition API för svenska
- Real-time audio visualisering med ambient animation
- Post-processing av svenska tal för bättre igenkänning
- Integration med Alice backend TTS system
- Fallback-system för graceful degradation

**VoiceClient (Advanced Realtime)**
- OpenAI Realtime API integration via WebRTC
- Low-latency audio streaming för professionell kvalitet
- Agent bridge arkitektur med SSE streaming
- Real-time transcript processing
- Barge-in support för naturlig konversation

### Agent Bridge Architecture

Voice pipeline använder en sofistikerad agent bridge för att koppla röstinteraktion till Alice's cognitive capabilities:

```
Voice Input → OpenAI Realtime → Transcript → Agent Bridge → Alice Core → Streaming Response → TTS → Audio Output
```

**Komponenter:**
- **Speech-to-Text**: OpenAI Whisper via Realtime API
- **Agent Bridge**: `/api/agent/stream` endpoint med SSE
- **Alice Core**: Agent orchestration och tool execution  
- **Text-to-Speech**: Hybrid OpenAI TTS / Alice enhanced TTS
- **WebRTC**: Real-time audio streaming

### Real-time Communication Flow

1. **Audio Capture** - WebRTC MediaStream från mikrofon
2. **Speech Recognition** - OpenAI Realtime API transkriberar i realtid
3. **Agent Processing** - Transcript skickas till Alice agent via SSE
4. **Tool Execution** - Alice Agent Core exekverar verktyg vid behov
5. **Response Generation** - Streaming text response från Alice
6. **Speech Synthesis** - TTS conversion och audio playback
7. **Barge-in Support** - Användaren kan avbryta och starta ny interaktion

### Voice WebSocket Events

```javascript
// Voice events som integrerar med Agent Core
const voiceEvents = {
  'voice_input': (transcript) => {
    // Skicka till AgentOrchestrator för processing
    orchestrator.execute_workflow(transcript);
  },
  
  'agent_response': (response) => {
    // Streaming response från Agent Core
    voiceClient.synthesizeAndPlay(response.content);
  },
  
  'tool_execution': (toolData) => {
    // Tool execution från Agent Executor
    voiceClient.emit('tool_executed', toolData);
  }
};
```

### Integration Points

**Agent Core → Voice Pipeline:**
- AgentOrchestrator trigger voice responses
- AgentExecutor verktyg kan generera audio feedback
- AgentCritic analyserar conversation quality
- Real-time progress updates via voice synthesis

**Voice Pipeline → Agent Core:**
- Voice commands triggar Agent workflows  
- Continuous conversation state management
- Context awareness mellan voice sessions
- Memory integration för personalized responses

## 🔧 Integration med Alice

Agent Core v1 är fullt integrerat med Alice's befintliga system och voice pipeline:

### Verktyg (22 stycken)
- **Musikstyrning:** PLAY, PAUSE, STOP, SET_VOLUME, etc.
- **E-post:** READ_EMAILS, SEND_EMAIL, SEARCH_EMAILS
- **Kalender:** LIST_CALENDAR_EVENTS, CREATE_CALENDAR_EVENT, etc.

### NLU Integration
Agent Core arbetar med Alice's svenska NLU system för att förstå komplexa mål.

### Voice Integration  
Fungerar seamless med Alice's röststyrningssystem.

## 📈 Performance

- **Sub-second planning** för enkla uppgifter
- **Parallell execution** för oberoende actions
- **Intelligent retry logic** för robust execution
- **Memory efficient** med streaming progress updates
- **Scalable architecture** för komplexa workflows

## 🔮 Framtida Förbättringar

- **AI-baserad planering** med Ollama/OpenAI integration
- **Learning from experience** för bättre framtida planering  
- **Advanced multi-tool scenarios** med komplex reasoning
- **Persistent workflow history** och analytics
- **Dynamic replanning** baserat på real-time feedback
- **Resource optimization** och load balancing

## 🎉 Status

**Agent Core v1 är KOMPLETT och REDO för produktion!**

✅ Full arkitektur implementerad  
✅ 100 tester passerar alla  
✅ Integration med Alice's verktyg  
✅ Autonomous workflow kapacitet  
✅ Comprehensive dokumentation  

Agent Core v1 transformerar Alice från en reaktiv assistent till en proaktiv, intelligent agent som kan självständigt planera och utföra komplexa uppgifter!