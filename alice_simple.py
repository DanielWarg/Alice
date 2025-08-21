#!/usr/bin/env python3
"""
Enkel Alice Agent baserad på videon
Följer exact samma struktur som Friday Jarvis i transkripten
"""

import asyncio
import logging
import os
from dotenv import load_dotenv

# LiveKit imports
from livekit import agents, rtc
from livekit.agents import Agent, cli, WorkerOptions
from livekit.plugins import silero

# Våra egna moduler  
from tools import AliceTools
import ollama

# Ladda miljövariabler
load_dotenv()

# Konfigurera logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("alice-agent")

class AliceAssistant(Agent):
    def __init__(self):
        super().__init__(
            instructions="""Du är Alice, en svensk AI-assistent som fungerar som en Jarvis-klon.
            
            Du är hjälpsam, intelligent och kan:
            - Svara på svenska (primärt språk)  
            - Hjälpa med väder, beräkningar, sökningar
            - Ha naturliga konversationer
            - Utföra praktiska uppgifter
            
            Håll svaren naturliga och inte för långa. Du pratar med användaren via röst.
            
            Du är som en butler - artig, hjälpsam och professionell.""",
        )
        self.alice_tools = AliceTools()
        
    async def generate_response(self, prompt: str) -> str:
        """Generera svar med lokal Ollama"""
        try:
            logger.info(f"🤖 Alice genererar svar för: {prompt[:50]}...")
            
            response = ollama.chat(
                model="gpt-oss:20b",
                messages=[
                    {
                        "role": "system", 
                        "content": self.instructions
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                options={
                    "temperature": 0.8,  # Lite mer personlighet
                    "top_p": 0.9,
                    "num_predict": 256
                }
            )
            
            answer = response['message']['content']
            logger.info(f"✅ Alice svarade: {answer[:100]}...")
            return answer
            
        except Exception as e:
            logger.error(f"❌ Ollama-fel: {e}")
            return "Ursäkta, jag har problem med AI-servern just nu."

async def entrypoint(ctx: agents.JobContext):
    """Entrypoint för Alice agent - baserat på videons kod"""
    logger.info("🤖 Alice startar...")
    
    # Skapa agent
    alice = AliceAssistant()
    
    # Vänta på anslutning
    await ctx.connect()
    logger.info("✅ Alice ansluten till rummet!")
    
    # Välkomstmeddelande
    try:
        # Skicka välkomstmeddelande via chat (om möjligt)
        if hasattr(ctx.room, 'local_participant'):
            await ctx.room.local_participant.publish_data(
                "Hej! Jag är Alice, din svenska AI-assistent. Hur kan jag hjälpa dig?"
            )
            logger.info("📢 Välkomstmeddelande skickat")
    except Exception as e:
        logger.warning(f"Kunde inte skicka välkomstmeddelande: {e}")
    
    # Lyssna på meddelanden
    @ctx.room.on("data_received")
    def on_data_received(data, participant=None, **kwargs):
        # Hantera olika callback-signaturer
        if participant is None:
            # Nyare LiveKit version - participant kan vara i kwargs
            participant = kwargs.get('participant')
        
        if participant:
            logger.info(f"📨 Mottog meddelande från {participant.identity}")
        else:
            logger.info("📨 Mottog meddelande från okänd deltagare")
        
        # Hantera meddelande i bakgrunden  
        asyncio.create_task(handle_message(ctx, alice, data, participant))
    
    # Håll agenten vid liv
    logger.info("👂 Alice lyssnar på meddelanden...")
    
    # Vänta tills rummet stängs
    await asyncio.sleep(3600)  # 1 timme max
    logger.info("👋 Alice avslutar sessionen")

async def handle_message(ctx, alice, data, participant):
    """Hantera inkommande meddelanden"""
    try:
        message = data.decode('utf-8')
        participant_id = participant.identity if participant else "okänd"
        logger.info(f"💬 Meddelande från {participant_id}: {message}")
        
        # Generera svar
        response = await alice.generate_response(message)
        
        # Skicka tillbaka svar
        await ctx.room.local_participant.publish_data(response)
        logger.info(f"📤 Svar skickat: {response[:50]}...")
        
    except Exception as e:
        logger.error(f"❌ Fel vid meddelandehantering: {e}")

if __name__ == "__main__":
    # Kör agent med LiveKit CLI (som i videon)
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))