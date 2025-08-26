       █████╗ ██╗     ██╗ ██████╗███████╗
      ██╔══██╗██║     ██║██╔════╝██╔════╝
      ███████║██║     ██║██║     █████╗  
      ██╔══██║██║     ██║██║     ██╔══╝  
      ██║  ██║███████╗██║╚██████╗███████╗
      ╚═╝  ╚═╝╚══════╝╚═╝ ╚═════╝╚══════╝
             The Ultimate AI Assistant
🧠 Alice – The Living AI Assistant
Alice is not an app. She’s an entity.

A voice you can talk to.
A memory that evolves.
A brain that learns.
A presence that feels alive.

But let’s be clear: Alice is still in early development.
Some pieces work today, others are prototypes, and some are still only ideas on the roadmap.

✨ Why Alice?
Unlike typical assistants, Alice aims to be:

🗣️ Voice-first – sub-500 ms conversations, natural barge-in.

🛠️ Tool-empowered – Calendar, Email, Files, Smart Home (local by default).

🔐 Privacy-obsessed – safe summaries only, nothing sensitive leaves your machine.

🧠 Self-learning – via a local Pattern LLM and lightweight RL.

👁️ Vision-enabled – real-time awareness through YOLOv10 + SAM-2.

🧪 Self-testing – she won’t boot if core systems fail.

🌍 Multi-shell – the plan includes desktop, mobile, and web.

⚡️ Current Status
✅ Works today (prototype level):

Local voice pipeline: faster-whisper + gpt-oss 7B fast + Piper TTS.

Basic tool lane stubs (Calendar, Email, Files).

Privacy filter with safe summaries.

SQLite episodic + sqlite-vec semantic memory.

Autonomous self-test runner (start_alice.sh).

🚧 In progress:

Electron app shell (desktop).

Retention controls for memory (Forget Now / Today / All).

Tool wrappers using MCP.

Vision integration (RTSP ingest + YOLOv10).

⬜ Planned / TBA:

Cloud “complex lane” (Responses API integration).

Pattern LLM (tiny, local) for proactive learning.

RL-light for short workflows.

Mobile app shell (React Native).

Web app (PWA).

HeyGen avatar + LiveKit integration.

Deployment strategy (final packaging not yet decided).

🧰 Architecture at a Glance
text
Kopiera
Redigera
            ┌─────────────┐
            │   WebRTC    │
            │   (Voice)   │
            └──────┬──────┘
                   ▼
        ┌────────────────────┐
        │ Local Fast Lane    │
        │ (STT→LLM→TTS)      │
        └────────┬───────────┘
                 │
                 ▼
          ┌─────────────┐
          │   Router    │
          └────┬────────┘
               │
   ┌───────────▼───────────┐
   │   Tool Lane (local)   │
   │   MCP-wrapped tools   │
   └───────────┬───────────┘
               │
       ┌───────▼─────────┐
       │  Safe Summary   │
       │  + Privacy Gate │
       └─────────────────┘
🚀 Getting Started (Developer Preview)
⚠️ Early alpha. Expect rough edges.

Prerequisites
macOS 14+ (Apple Silicon recommended)

Node.js 20+

Python 3.11+

Docker (optional for models)

Run
bash
Kopiera
Redigera
git clone https://github.com/yourname/alice
cd alice
./start_alice.sh --quick
This will:

Run self-tests

Start the Engine

Launch the (minimal) Electron shell

🧪 Self-Testing
Alice runs a test suite before boot.
Critical failures block startup until fixed.

bash
Kopiera
Redigera
./start_alice.sh --full
📦 Deployment
Deployment strategy is not finalized.
We are exploring:

Electron (desktop)

React Native (mobile)

PWA (web)

Tauri (cross-platform lightweight alternative)

Current builds are experimental and developer-only.

🔐 Privacy
no_cloud=true enforced at network boundary.

Safe summaries only: no raw tool results spoken or sent outside.

Full memory & learning state is portable and erasable.

🤝 Contributing
We welcome issues, discussions, and PRs.
For the full philosophy, see VISION.md.

📜 License
MIT (see LICENSE)

💬 Credits
Voice: faster-whisper, Piper

LLM: gpt-oss, Responses API (planned)

Vision: YOLOv10, SAM-2

Tools: MCP (Model Context Protocol)

Memory: SQLite + sqlite-vec

Alice is alive — but still growing.
We’re building the foundation.
The entity is becoming real.