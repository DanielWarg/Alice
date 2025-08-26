#!/usr/bin/env python3
"""
🔍 Alice Real-time Monitoring & Logging System
Trackar och loggar all aktivitet i Alice-systemet för debugging och analys.
"""

import asyncio
import aiofiles
import json
import time
import psutil
import threading
from datetime import datetime
from pathlib import Path
import sys
import signal
import websockets
import requests
from collections import defaultdict, deque

class AliceMonitor:
    def __init__(self):
        self.running = True
        self.log_file = f"alice_monitor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        self.metrics_history = deque(maxlen=100)
        self.api_calls = defaultdict(int)
        self.websocket_events = deque(maxlen=50)
        self.start_time = time.time()
        
        # Färgkoder för terminal
        self.colors = {
            'HEADER': '\033[95m',
            'BLUE': '\033[94m',
            'CYAN': '\033[96m',
            'GREEN': '\033[92m',
            'YELLOW': '\033[93m',
            'RED': '\033[91m',
            'BOLD': '\033[1m',
            'UNDERLINE': '\033[4m',
            'END': '\033[0m'
        }
        
        print(f"{self.colors['HEADER']}{'='*80}{self.colors['END']}")
        print(f"{self.colors['BOLD']}🔍 Alice Real-time Monitor Started{self.colors['END']}")
        print(f"{self.colors['CYAN']}Loggfil: {self.log_file}{self.colors['END']}")
        print(f"{self.colors['HEADER']}{'='*80}{self.colors['END']}")
        
    def log(self, level, category, message, extra=None):
        """Loggar meddelande både till konsol och fil"""
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        
        # Färgkodning baserat på nivå
        color_map = {
            'INFO': self.colors['GREEN'],
            'WARN': self.colors['YELLOW'], 
            'ERROR': self.colors['RED'],
            'DEBUG': self.colors['CYAN'],
            'METRIC': self.colors['BLUE']
        }
        
        color = color_map.get(level, self.colors['END'])
        
        # Konsol-output
        console_msg = f"{color}[{timestamp}] {level:5} {category:15} {message}{self.colors['END']}"
        print(console_msg)
        
        # Fil-output med extra data
        log_entry = {
            'timestamp': timestamp,
            'level': level,
            'category': category, 
            'message': message,
            'extra': extra or {}
        }
        
        # Asynkron filskrivning
        asyncio.create_task(self.write_log(log_entry))
        
    async def write_log(self, entry):
        """Skriver loggpost till fil asynkront"""
        try:
            async with aiofiles.open(self.log_file, 'a') as f:
                await f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        except Exception as e:
            print(f"❌ Loggfel: {e}")

    async def monitor_system_metrics(self):
        """Övervakar systemresurser kontinuerligt"""
        while self.running:
            try:
                # CPU och minne
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                # Nätverkstrafik
                net_io = psutil.net_io_counters()
                
                metrics = {
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'memory_available_gb': memory.available / (1024**3),
                    'disk_percent': disk.percent,
                    'network_sent_mb': net_io.bytes_sent / (1024**2),
                    'network_recv_mb': net_io.bytes_recv / (1024**2)
                }
                
                self.metrics_history.append(metrics)
                
                # Logga om kritiska nivåer
                if cpu_percent > 80:
                    self.log('WARN', 'SYSTEM', f'Hög CPU-användning: {cpu_percent}%', metrics)
                elif memory.percent > 85:
                    self.log('WARN', 'SYSTEM', f'Hög minnesanvändning: {memory.percent}%', metrics)
                else:
                    self.log('METRIC', 'SYSTEM', f'CPU: {cpu_percent}% | RAM: {memory.percent}%', metrics)
                    
            except Exception as e:
                self.log('ERROR', 'SYSTEM', f'Metriker fel: {e}')
            
            await asyncio.sleep(5)
    
    async def monitor_api_calls(self):
        """Övervakar API-anrop till backend"""
        while self.running:
            try:
                # Kontrollera backend hälsa
                response = requests.get('http://localhost:8000/docs', timeout=2)
                if response.status_code == 200:
                    self.log('DEBUG', 'API', 'Backend hälsokontroll OK')
                else:
                    self.log('WARN', 'API', f'Backend svarar med status {response.status_code}')
                    
                # Testa ett simpelt API-anrop
                test_response = requests.post(
                    'http://localhost:8000/api/chat',
                    json={'prompt': 'systemtest'},
                    timeout=5
                )
                
                if test_response.status_code == 200:
                    data = test_response.json()
                    provider = data.get('provider', 'unknown')
                    engine = data.get('engine', 'unknown')
                    self.log('INFO', 'API', f'Chat API OK - {provider}:{engine}')
                    self.api_calls['chat_success'] += 1
                else:
                    self.log('WARN', 'API', f'Chat API fel: {test_response.status_code}')
                    self.api_calls['chat_error'] += 1
                    
            except requests.exceptions.ConnectionError:
                self.log('ERROR', 'API', 'Backend ej tillgänglig - anslutningsfel')
            except requests.exceptions.Timeout:
                self.log('ERROR', 'API', 'Backend timeout')
            except Exception as e:
                self.log('ERROR', 'API', f'API-övervakningsfel: {e}')
            
            await asyncio.sleep(10)
    
    async def monitor_websockets(self):
        """Övervakar WebSocket-anslutningar"""
        while self.running:
            try:
                # Testa WebSocket-anslutning till Alice
                async with websockets.connect('ws://localhost:8000/ws/alice') as websocket:
                    self.log('INFO', 'WEBSOCKET', 'Anslutning till /ws/alice OK')
                    
                    # Skicka testmeddelande
                    test_msg = {
                        'type': 'test_message',
                        'timestamp': datetime.now().isoformat(),
                        'data': 'monitor_test'
                    }
                    
                    await websocket.send(json.dumps(test_msg))
                    self.log('DEBUG', 'WEBSOCKET', 'Testmeddelande skickat')
                    
                    # Vänta på svar (med timeout)
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        self.log('INFO', 'WEBSOCKET', f'Mottaget svar: {response[:100]}...')
                        self.websocket_events.append({
                            'timestamp': datetime.now().isoformat(),
                            'type': 'response',
                            'data': response
                        })
                    except asyncio.TimeoutError:
                        self.log('WARN', 'WEBSOCKET', 'Timeout vid väntan på WebSocket-svar')
                        
            except ConnectionRefusedError:
                self.log('ERROR', 'WEBSOCKET', 'WebSocket-anslutning nekad')
            except Exception as e:
                self.log('ERROR', 'WEBSOCKET', f'WebSocket-fel: {e}')
            
            await asyncio.sleep(15)
    
    async def monitor_processes(self):
        """Övervakar Alice-relaterade processer"""
        while self.running:
            try:
                processes = []
                for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'cmdline']):
                    try:
                        cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                        
                        # Hitta Alice-relaterade processer
                        if any(keyword in cmdline.lower() for keyword in ['alice', 'ollama', 'uvicorn', 'next']):
                            processes.append({
                                'pid': proc.info['pid'],
                                'name': proc.info['name'],
                                'cpu': proc.info['cpu_percent'] or 0,
                                'memory': proc.info['memory_percent'] or 0,
                                'cmdline': cmdline[:100]
                            })
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                
                if processes:
                    self.log('DEBUG', 'PROCESSES', f'Aktiva Alice-processer: {len(processes)}', 
                           {'processes': processes})
                    
                    # Varna för höga resurser
                    for proc in processes:
                        if proc['cpu'] > 50:
                            self.log('WARN', 'PROCESSES', 
                                   f'Process {proc["name"]} (PID {proc["pid"]}) hög CPU: {proc["cpu"]}%')
                
            except Exception as e:
                self.log('ERROR', 'PROCESSES', f'Process-övervakningsfel: {e}')
            
            await asyncio.sleep(20)
    
    def print_stats(self):
        """Skriver ut sammanfattande statistik"""
        uptime = time.time() - self.start_time
        print(f"\n{self.colors['HEADER']}📊 Alice Monitor Statistik{self.colors['END']}")
        print(f"{self.colors['CYAN']}Upptid: {uptime:.1f} sekunder{self.colors['END']}")
        print(f"{self.colors['CYAN']}API-anrop: {dict(self.api_calls)}{self.colors['END']}")
        print(f"{self.colors['CYAN']}WebSocket-händelser: {len(self.websocket_events)}{self.colors['END']}")
        print(f"{self.colors['CYAN']}Systemmetriker sparade: {len(self.metrics_history)}{self.colors['END']}")
        
        if self.metrics_history:
            latest = self.metrics_history[-1]
            print(f"{self.colors['GREEN']}Senaste systemstatus:{self.colors['END']}")
            print(f"  CPU: {latest['cpu_percent']:.1f}%")
            print(f"  RAM: {latest['memory_percent']:.1f}%")
            print(f"  Disk: {latest['disk_percent']:.1f}%")
    
    def signal_handler(self, signum, frame):
        """Hanterar Ctrl+C gracefully"""
        print(f"\n{self.colors['YELLOW']}🛑 Stoppar Alice Monitor...{self.colors['END']}")
        self.running = False
        self.print_stats()
        sys.exit(0)
    
    async def run(self):
        """Huvudloop som kör all övervakning"""
        # Registrera signal handler
        signal.signal(signal.SIGINT, self.signal_handler)
        
        # Starta alla övervakningsuppgifter parallellt
        tasks = [
            self.monitor_system_metrics(),
            self.monitor_api_calls(),
            self.monitor_websockets(),
            self.monitor_processes()
        ]
        
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            self.log('INFO', 'MONITOR', 'Monitorn stoppades av användaren')
        except Exception as e:
            self.log('ERROR', 'MONITOR', f'Fel i huvudloop: {e}')
        finally:
            self.running = False

async def main():
    monitor = AliceMonitor()
    await monitor.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Alice Monitor avslutat")