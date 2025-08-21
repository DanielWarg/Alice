#!/usr/bin/env python3
"""
Alice Agent - Jarvis-klon med lokal Ollama istället för Google Realtime
Bygger på original Friday Jarvis arkitektur
"""

import asyncio
import logging
from dotenv import load_dotenv

from livekit import agents
from livekit.agents import Agent, AgentSession, WorkerOptions, cli, RoomInputOptions
from livekit.plugins import silero
from livekit.agents.llm import LLM, LLMStream, ChatContext, ChatMessage
from livekit import rtc

from tools import AliceTools
import ollama

load_dotenv()

# Konfigurera logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("alice-agent")

AGENT_INSTRUCTION = """Du är Alice, en svensk AI-assistent som fungerar som en Jarvis-klon.

Du är hjälpsam, intelligent och kan:
- Svara på svenska (primärt språk)
- Hjälpa med väder, beräkningar, webbsökning
- Ha naturliga konversationer
- Utföra praktiska uppgifter

Håll svaren naturliga och inte för långa. Du pratar med användaren via röst.
Du är som en butler - artig, hjälpsam och professionell."""

class OllamaLLM(LLM):
    """Custom Ollama LLM wrapper för LiveKit Agents"""
    
    def __init__(self, model_name: str = "gpt-oss:20b"):
        self._model_name = model_name
        self._label = f"Ollama-{model_name}"
    
    @property 
    def label(self) -> str:
        return self._label
        
    async def chat(self, *, chat_ctx: ChatContext, conn_options=None, fnc_ctx=None) -> "LLMStream":
        """Implementera chat-funktionen för LiveKit"""
        # Konvertera LiveKit meddelanden till Ollama format
        messages = []
        for msg in chat_ctx.messages:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        try:
            response = ollama.chat(
                model=self._model_name,
                messages=messages,
                options={
                    "temperature": 0.8,
                    "top_p": 0.9,
                    "num_predict": 200
                }
            )
            
            # Skapa en enkel stream-simulation
            content = response['message']['content']
            logger.info(f"🤖 Ollama svarade: {content[:100]}...")
            
            # Returnera en mock LLMStream med innehållet
            return MockLLMStream(content)
            
        except Exception as e:
            logger.error(f"❌ Ollama-fel: {e}")
            return MockLLMStream("Ursäkta, jag har problem med AI-servern just nu.")

class MockLLMStream:
    """Enkel mock av LLMStream för Ollama"""
    
    def __init__(self, content: str):
        self.content = content
        self._done = False
    
    async def __aiter__(self):
        yield self.content
        self._done = True
    
    async def aclose(self):
        pass

class AliceAssistant(Agent):
    def __init__(self):
        # Alice använder verktyg från tools.py
        self.alice_tools = AliceTools()
        
        super().__init__(
            instructions=AGENT_INSTRUCTION,
            llm=OllamaLLM("gpt-oss:20b"),  # Lokal Ollama LLM
            # Kommenterar bort TTS för nu - fokus på att få anslutningen att fungera
            # tts=silero.TTS(language="sv", speaker="aidar"),  # Svenska TTS
            tools=[
                self.get_weather_tool,
                self.search_web_tool,
                self.calculate_tool,
                self.get_time_tool
            ]
        )
    
    async def get_weather_tool(self, city: str) -> str:
        """Hämta väder för en stad"""
        logger.info(f"🌤️ Hämtar väder för {city}")
        return self.alice_tools.get_weather(city)
    
    async def search_web_tool(self, query: str) -> str:
        """Sök på webben"""
        logger.info(f"🔍 Söker: {query}")
        return self.alice_tools.search_web(query, max_results=3)
    
    async def calculate_tool(self, expression: str) -> str:
        """Utför beräkning"""
        logger.info(f"🔢 Räknar: {expression}")
        return self.alice_tools.calculate(expression)
    
    async def get_time_tool(self) -> str:
        """Hämta aktuell tid"""
        logger.info("⏰ Hämtar tid")
        return self.alice_tools.get_time()

    async def generate_response(self, text: str) -> str:
        """Generera svar med lokal Ollama istället för Google Realtime"""
        try:
            logger.info(f"🤖 Alice genererar svar för: {text[:50]}...")
            
            response = ollama.chat(
                model="gpt-oss:20b",
                messages=[
                    {"role": "system", "content": AGENT_INSTRUCTION},
                    {"role": "user", "content": text}
                ],
                options={
                    "temperature": 0.8,  # Som original Jarvis
                    "top_p": 0.9,
                    "num_predict": 200  # Kortare för röst
                }
            )
            
            answer = response['message']['content']
            logger.info(f"✅ Alice svarade: {answer[:100]}...")
            return answer
            
        except Exception as e:
            logger.error(f"❌ Ollama-fel: {e}")
            return "Ursäkta, jag har problem med AI-servern just nu."

async def entrypoint(ctx: agents.JobContext):
    """LiveKit Agent entrypoint - samma struktur som Jarvis"""
    logger.info("🤖 Alice startar...")
    
    # Skapa agent session (som original Jarvis)
    session = AgentSession()
    
    # Starta session med Alice agent
    await session.start(
        room=ctx.room,
        agent=AliceAssistant(),
        room_input_options=RoomInputOptions(
            video_enabled=True,
            audio_enabled=True,
            # Vi kör lokalt så ingen noise cancellation från LiveKit Cloud
        )
    )
    
    logger.info("✅ Alice session startad!")
    
    # Anslut till rummet
    await ctx.connect()
    logger.info("✅ Alice ansluten till rummet!")

if __name__ == "__main__":
    # Kör agent med LiveKit CLI (exakt som Jarvis)
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))