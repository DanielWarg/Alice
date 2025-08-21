import ollama
import speech_recognition as sr
import pyttsx3
import threading
import json
from typing import Dict, Any, List
from datetime import datetime

class AliceCore:
    def __init__(self):
        self.model_name = "gpt-oss:20b"
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.tts_engine = pyttsx3.init()
        self.setup_tts()
        self.conversation_history: List[Dict[str, str]] = []
        
    def setup_tts(self):
        """Konfigurera text-till-tal för svenska"""
        voices = self.tts_engine.getProperty('voices')
        for voice in voices:
            if 'swedish' in voice.name.lower() or 'sv' in voice.id.lower():
                self.tts_engine.setProperty('voice', voice.id)
                break
        self.tts_engine.setProperty('rate', 180)
        self.tts_engine.setProperty('volume', 0.9)
    
    def listen(self) -> str:
        """Lyssna på mikrofon och returnera text"""
        try:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source)
                print("🎤 Lyssnar...")
                audio = self.recognizer.listen(source, timeout=5)
            
            text = self.recognizer.recognize_google(audio, language='sv-SE')
            print(f"Du sa: {text}")
            return text
        except sr.UnknownValueError:
            return ""
        except sr.RequestError as e:
            print(f"Fel med taligenkänning: {e}")
            return ""
        except sr.WaitTimeoutError:
            return ""
    
    def speak(self, text: str):
        """Säg text högt"""
        print(f"Alice: {text}")
        self.tts_engine.say(text)
        self.tts_engine.runAndWait()
    
    def chat_with_ollama(self, prompt: str) -> str:
        """Chatta med GPT-OSS via Ollama"""
        try:
            system_prompt = """Du är Alice, en svensk AI-assistent. 
            Svara alltid på svenska om inte användaren specifikt frågar på annat språk.
            Var hjälpsam, vänlig och koncis i dina svar."""
            
            messages = [{"role": "system", "content": system_prompt}]
            
            # Lägg till konversationshistorik
            for msg in self.conversation_history[-5:]:  # Senaste 5 meddelanden
                messages.append(msg)
            
            messages.append({"role": "user", "content": prompt})
            
            response = ollama.chat(
                model=self.model_name,
                messages=messages,
                options={
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "num_predict": 512
                }
            )
            
            answer = response['message']['content']
            
            # Spara i historik
            self.conversation_history.append({"role": "user", "content": prompt})
            self.conversation_history.append({"role": "assistant", "content": answer})
            
            return answer
            
        except Exception as e:
            return f"Fel vid kommunikation med AI: {e}"
    
    def test_ollama_connection(self) -> bool:
        """Testa om Ollama och modellen fungerar"""
        try:
            response = ollama.chat(
                model=self.model_name,
                messages=[{"role": "user", "content": "Hej, säg bara 'hej' tillbaka"}]
            )
            return True
        except Exception as e:
            print(f"Ollama-fel: {e}")
            return False