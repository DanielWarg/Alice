import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import datetime
from alice_core import AliceCore
from tools import AliceTools
import re

class AliceGUI:
    def __init__(self):
        self.alice = AliceCore()
        self.tools = AliceTools()
        self.setup_gui()
        self.listening = False
        
    def setup_gui(self):
        """Skapa GUI-komponenter"""
        self.root = tk.Tk()
        self.root.title("🤖 Alice - Din Svenska AI-Assistent")
        self.root.geometry("800x600")
        self.root.configure(bg='#2b2b2b')
        
        # Stil för dark theme
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TFrame', background='#2b2b2b')
        style.configure('TLabel', background='#2b2b2b', foreground='white')
        style.configure('TButton', background='#404040', foreground='white')
        
        # Konfigurera root grid
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Huvudframe
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # Titel
        title_label = ttk.Label(main_frame, text="🤖 Alice", font=('SF Pro Display', 24, 'bold'))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Status
        self.status_label = ttk.Label(main_frame, text="🔴 Ansluter till Ollama...", font=('SF Pro Display', 12))
        self.status_label.grid(row=1, column=0, columnspan=2, pady=(0, 10))
        
        # Chat-område
        self.chat_area = scrolledtext.ScrolledText(
            main_frame, 
            wrap=tk.WORD, 
            height=20, 
            width=70,
            bg='#1e1e1e',
            fg='white',
            font=('SF Mono', 11),
            insertbackground='white'
        )
        self.chat_area.grid(row=2, column=0, columnspan=2, pady=(0, 10), sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Input-fält
        self.input_var = tk.StringVar()
        self.input_entry = ttk.Entry(
            main_frame, 
            textvariable=self.input_var, 
            font=('SF Pro Display', 12),
            width=50
        )
        self.input_entry.grid(row=3, column=0, pady=5, padx=(0, 10), sticky=(tk.W, tk.E))
        self.input_entry.bind('<Return>', self.send_message)
        
        # Knappar
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=1, sticky=tk.E)
        
        self.send_button = ttk.Button(button_frame, text="📤 Skicka", command=self.send_message)
        self.send_button.grid(row=0, column=0, padx=(0, 5))
        
        self.voice_button = ttk.Button(button_frame, text="🎤 Röst", command=self.toggle_voice)
        self.voice_button.grid(row=0, column=1, padx=(0, 5))
        
        self.clear_button = ttk.Button(button_frame, text="🗑️ Rensa", command=self.clear_chat)
        self.clear_button.grid(row=0, column=2)
        
        
        # Testa Ollama-anslutning
        self.test_connection()
        
    def test_connection(self):
        """Testa Ollama-anslutning i bakgrunden"""
        def test():
            if self.alice.test_ollama_connection():
                self.status_label.configure(text="🟢 Alice redo att hjälpa!")
                self.add_to_chat("🤖 Alice", "Hej! Jag är Alice, din svenska AI-assistent. Hur kan jag hjälpa dig?")
            else:
                self.status_label.configure(text="🔴 Kan inte ansluta till Ollama. Kontrollera att GPT-OSS:20B körs.")
                
        threading.Thread(target=test, daemon=True).start()
        
    def add_to_chat(self, sender: str, message: str):
        """Lägg till meddelande i chatten"""
        timestamp = datetime.datetime.now().strftime("%H:%M")
        self.chat_area.insert(tk.END, f"[{timestamp}] {sender}: {message}\n\n")
        self.chat_area.see(tk.END)
        
    def process_command(self, text: str) -> str:
        """Bearbeta kommandon och verktyg"""
        text_lower = text.lower()
        
        # Väder
        weather_pattern = r'(?:väder|weather).*?(?:i|in)\s+(\w+)'
        match = re.search(weather_pattern, text_lower)
        if match:
            city = match.group(1)
            return self.tools.get_weather(city)
        
        # Websök
        if any(word in text_lower for word in ['sök', 'search', 'googla', 'leta']):
            query = re.sub(r'^.*?(?:sök|search|googla|leta)\s+(?:efter\s+|på\s+)?', '', text, flags=re.IGNORECASE)
            return self.tools.search_web(query)
        
        # Tid
        if any(word in text_lower for word in ['tid', 'klocka', 'time']):
            return self.tools.get_time()
        
        # Kalkylator
        calc_pattern = r'(?:räkna|calculate|beräkna).*?([0-9+\-*/\.\s\(\)]+)'
        match = re.search(calc_pattern, text)
        if match:
            expression = match.group(1).strip()
            return self.tools.calculate(expression)
        
        # Skicka till AI om inget verktyg matchar
        return self.alice.chat_with_ollama(text)
        
    def send_message(self, event=None):
        """Skicka meddelande"""
        message = self.input_var.get().strip()
        if not message:
            return
            
        self.add_to_chat("👤 Du", message)
        self.input_var.set("")
        
        # Bearbeta i bakgrunden
        def process():
            response = self.process_command(message)
            self.add_to_chat("🤖 Alice", response)
            
        threading.Thread(target=process, daemon=True).start()
        
    def toggle_voice(self):
        """Växla röstinmatning"""
        if not self.listening:
            self.listening = True
            self.voice_button.configure(text="🛑 Stoppa")
            self.status_label.configure(text="🎤 Lyssnar...")
            
            def listen():
                text = self.alice.listen()
                self.listening = False
                self.voice_button.configure(text="🎤 Röst")
                self.status_label.configure(text="🟢 Alice redo att hjälpa!")
                
                if text:
                    self.input_var.set(text)
                    self.send_message()
                    
            threading.Thread(target=listen, daemon=True).start()
        else:
            self.listening = False
            self.voice_button.configure(text="🎤 Röst")
            self.status_label.configure(text="🟢 Alice redo att hjälpa!")
            
    def clear_chat(self):
        """Rensa chathistorik"""
        self.chat_area.delete(1.0, tk.END)
        self.alice.conversation_history.clear()
        
    def run(self):
        """Starta GUI"""
        self.root.mainloop()

if __name__ == "__main__":
    app = AliceGUI()
    app.run()