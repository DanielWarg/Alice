#!/usr/bin/env python3
"""
🔍 Alice Simple Monitor - Enkel realtidsloggning
"""

import time
import json
import requests
import psutil
from datetime import datetime

def colored_print(text, color_code):
    """Enkel färgutskrift"""
    print(f"\033[{color_code}m{text}\033[0m")

def log_event(level, category, message):
    """Loggar händelse med timestamp"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    
    colors = {
        'INFO': '92',   # Grön
        'WARN': '93',   # Gul  
        'ERROR': '91',  # Röd
        'DEBUG': '94'   # Blå
    }
    
    color = colors.get(level, '0')
    colored_print(f"[{timestamp}] {level:5} {category:15} {message}", color)

def main():
    colored_print("="*80, '95')
    colored_print("🔍 Alice Simple Monitor Started", '1')
    colored_print("="*80, '95')
    
    while True:
        try:
            # System metrics
            cpu = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            log_event('INFO', 'SYSTEM', f'CPU: {cpu}% | RAM: {memory.percent}%')
            
            # Test backend
            try:
                response = requests.get('http://localhost:8000/docs', timeout=2)
                if response.status_code == 200:
                    log_event('DEBUG', 'BACKEND', 'Server OK')
                else:
                    log_event('WARN', 'BACKEND', f'Status: {response.status_code}')
            except Exception as e:
                log_event('ERROR', 'BACKEND', f'Fel: {str(e)[:50]}')
            
            # Test chat API
            try:
                chat_response = requests.post(
                    'http://localhost:8000/api/chat',
                    json={'prompt': 'test'},
                    timeout=5
                )
                if chat_response.status_code == 200:
                    data = chat_response.json()
                    provider = data.get('provider', '?')
                    log_event('INFO', 'CHAT', f'Chat API OK - Provider: {provider}')
                else:
                    log_event('WARN', 'CHAT', f'Chat fel: {chat_response.status_code}')
            except Exception as e:
                log_event('ERROR', 'CHAT', f'Chat fel: {str(e)[:50]}')
            
            time.sleep(10)
            
        except KeyboardInterrupt:
            colored_print("\n🛑 Monitor stoppad", '93')
            break
        except Exception as e:
            log_event('ERROR', 'MONITOR', f'Fel: {e}')
            time.sleep(5)

if __name__ == "__main__":
    main()