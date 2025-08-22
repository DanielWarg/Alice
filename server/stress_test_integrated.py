#!/usr/bin/env python3
"""
Integrerat End-to-End Stresstest för Alice
Testar RAG + NLU + Chat pipeline under realistiska förhållanden
"""

import os
import asyncio
import aiohttp
import time
import json
import random
from typing import Dict, List, Any
import statistics

# Enable all tools for testing
os.environ["ENABLED_TOOLS"] = "PLAY,PAUSE,STOP,NEXT,PREV,SET_VOLUME,MUTE,UNMUTE,REPEAT,SHUFFLE,LIKE,UNLIKE,SEND_EMAIL,READ_EMAILS,SEARCH_EMAILS"

# Realistic conversation scenarios
CONVERSATION_SCENARIOS = [
    {
        "name": "Music Control Session",
        "messages": [
            "spela upp någon musik",
            "höj volymen lite",
            "nästa låt tack",
            "den här låten är bra, gilla den",
            "pausa musiken nu",
            "vad spelade vi förut?",
        ]
    },
    {
        "name": "Email Management",
        "messages": [
            "visa mina nya mail",
            "skicka mail till chef@företag.se om projektuppdatering",
            "sök mail från förra veckan",
            "har jag fått något viktigt mail idag?",
            "skicka tack-mail till teamet",
        ]
    },
    {
        "name": "Mixed Commands",
        "messages": [
            "spela lugn musik",
            "sätt volymen till 50%",
            "läs senaste mailen medan musiken spelar",
            "pausa musiken så jag kan koncentrera mig",
            "skicka mail till kunden",
            "återuppta musikuppspelning",
        ]
    },
    {
        "name": "Context Dependent",
        "messages": [
            "Alice, kan du hjälpa mig med mail?",
            "visa vad som kom in idag",
            "det där mailet från chefen, vad sa hen?",
            "skicka svar att projektet går bra",
            "spela sedan lite musik för att fira",
            "den låten igen tack",
        ]
    },
    {
        "name": "Long Content Processing",
        "messages": [
            """Hej Alice! Jag behöver hjälp med att organisera min dag. 
            
            Idag har jag flera viktiga möten: kl 9 med utvecklingsteamet där vi ska diskutera den nya funktionen för Gmail-integration som vi just implementerat. Den inkluderar både sändning och läsning av e-post via naturligt språk.
            
            Kl 11 har jag ett strategimöte med ledningen om AI-roadmapen. Vi ska prata om hur RAG-systemet förbättrats med semantic chunking och context tracking.
            
            På eftermiddagen kl 14 är det demo för kunder av Alice-systemet. Jag vill visa både musikstyrning och e-postfunktioner.
            
            Kan du komma ihåg detta och påminna mig om viktiga punkter?""",
            "vad hade jag för möten idag?",
            "berätta mer om Gmail-integrationen",
            "spela fokusmusik för strategimötet",
        ]
    }
]

# Edge cases och error scenarios
ERROR_SCENARIOS = [
    "invalid command that should fail gracefully",
    "",
    "   ",
    "a" * 500,  # Very long input
    "!@#$%^&*()",
    "mute unmute play pause stop" * 10,  # Conflicting commands
    "skicka mail til fel@adress utan ämne",  # Malformed email
    "sätt volymen till 150%",  # Invalid volume
    "spela låt nummer -5",  # Invalid parameters
]

class IntegratedStressTest:
    def __init__(self, server_url: str = "http://127.0.0.1:8000"):
        self.server_url = server_url
        self.results = {
            'response_times': [],
            'successful_requests': 0,
            'failed_requests': 0,
            'nlu_classifications': 0,
            'rag_contexts_found': 0,
            'memory_insertions': 0,
            'conversation_contexts': 0,
            'errors': [],
            'scenario_results': {}
        }
        
    async def test_server_health(self) -> bool:
        """Test att servern svarar"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.server_url}/api/health") as response:
                    return response.status == 200
        except Exception as e:
            print(f"❌ Server health check failed: {e}")
            return False
    
    async def send_chat_message(self, message: str, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """Skicka chat message till Alice"""
        start_time = time.time()
        
        try:
            payload = {
                "prompt": message,
                "model": "gpt-oss:20b",
                "provider": "local"
            }
            
            async with session.post(f"{self.server_url}/api/chat", json=payload) as response:
                response_time = time.time() - start_time
                self.results['response_times'].append(response_time)
                
                if response.status == 200:
                    data = await response.json()
                    self.results['successful_requests'] += 1
                    
                    # Analyzera svaret
                    if data.get('memory_id'):
                        self.results['memory_insertions'] += 1
                    
                    return {
                        'success': True,
                        'data': data,
                        'response_time': response_time,
                        'status': response.status
                    }
                else:
                    self.results['failed_requests'] += 1
                    error_text = await response.text()
                    return {
                        'success': False,
                        'error': f"HTTP {response.status}: {error_text}",
                        'response_time': response_time,
                        'status': response.status
                    }
                    
        except Exception as e:
            response_time = time.time() - start_time
            self.results['response_times'].append(response_time)
            self.results['failed_requests'] += 1
            return {
                'success': False,
                'error': str(e),
                'response_time': response_time,
                'status': 0
            }
    
    async def run_conversation_scenario(self, scenario: Dict[str, Any], session: aiohttp.ClientSession):
        """Kör en komplett konversations-scenario"""
        scenario_name = scenario['name']
        messages = scenario['messages']
        
        print(f"🗣️  Running scenario: {scenario_name}")
        
        scenario_results = {
            'total_messages': len(messages),
            'successful_messages': 0,
            'failed_messages': 0,
            'avg_response_time': 0,
            'context_continuity': 0,
            'errors': []
        }
        
        response_times = []
        
        for i, message in enumerate(messages):
            print(f"   Message {i+1}/{len(messages)}: {message[:50]}...")
            
            result = await self.send_chat_message(message, session)
            response_times.append(result['response_time'])
            
            if result['success']:
                scenario_results['successful_messages'] += 1
                
                # Check för context continuity (om Alice refererar till tidigare meddelanden)
                response_text = result.get('data', {}).get('text', '').lower()
                if any(word in response_text for word in ['tidigare', 'förut', 'innan', 'redan', 'minns']):
                    scenario_results['context_continuity'] += 1
                    
            else:
                scenario_results['failed_messages'] += 1
                scenario_results['errors'].append(result['error'])
                print(f"     ❌ Failed: {result['error']}")
            
            # Liten paus mellan meddelanden för realism
            await asyncio.sleep(0.1)
        
        if response_times:
            scenario_results['avg_response_time'] = statistics.mean(response_times)
        
        self.results['scenario_results'][scenario_name] = scenario_results
        
        success_rate = scenario_results['successful_messages'] / scenario_results['total_messages']
        context_rate = scenario_results['context_continuity'] / max(1, scenario_results['successful_messages'])
        
        print(f"   ✅ Success: {success_rate:.1%}, Context: {context_rate:.1%}, Avg: {scenario_results['avg_response_time']*1000:.0f}ms")
    
    async def test_concurrent_load(self):
        """Test concurrent belastning"""
        print("⚡ Testar concurrent load...")
        
        # Skapa flera sessions som kör samtidigt
        async def worker_session(worker_id: int, num_messages: int):
            try:
                async with aiohttp.ClientSession() as session:
                    worker_messages = []
                    for i in range(num_messages):
                        # Random message från olika kategorier
                        if random.random() < 0.6:  # 60% musik commands
                            message = random.choice([
                                "spela musik", "pausa", "nästa låt", "höj volym",
                                "gilla låten", "shuffle på", "stoppa musik"
                            ])
                        elif random.random() < 0.8:  # 20% email commands  
                            message = random.choice([
                                "visa mail", "skicka mail till test@example.com",
                                "sök mail", "nya mail", "läs senaste mail"
                            ])
                        else:  # 20% general chat
                            message = random.choice([
                                "hej alice", "vad gör du", "hjälp mig",
                                "tack så mycket", "ha det bra"
                            ])
                        
                        result = await self.send_chat_message(f"Worker{worker_id}: {message}", session)
                        worker_messages.append(result)
                        
                        if not result['success']:
                            print(f"Worker {worker_id} error: {result['error']}")
                    
                    return worker_messages
            except Exception as e:
                print(f"Worker {worker_id} crashed: {e}")
                return []
        
        # Starta 5 workers med 10 meddelanden var
        start_time = time.time()
        
        tasks = [worker_session(i, 10) for i in range(5)]
        worker_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        
        # Räkna resultat
        total_concurrent_messages = 0
        successful_concurrent = 0
        
        for worker_result in worker_results:
            if isinstance(worker_result, list):
                total_concurrent_messages += len(worker_result)
                successful_concurrent += sum(1 for r in worker_result if r.get('success'))
        
        concurrent_success_rate = successful_concurrent / max(1, total_concurrent_messages)
        concurrent_throughput = total_concurrent_messages / total_time
        
        print(f"🔄 Concurrent: {concurrent_success_rate:.1%} success, {concurrent_throughput:.1f} msg/s")
    
    async def test_error_handling(self):
        """Test error scenarios"""
        print("💥 Testar error handling...")
        
        async with aiohttp.ClientSession() as session:
            error_results = {'graceful_errors': 0, 'crashes': 0}
            
            for error_input in ERROR_SCENARIOS:
                result = await self.send_chat_message(error_input, session)
                
                if result['status'] in [200, 400, 422]:  # Expected error responses
                    error_results['graceful_errors'] += 1
                elif result['status'] >= 500:  # Server crashes
                    error_results['crashes'] += 1
                    print(f"💥 Server crash on: {error_input[:30]}")
                
                await asyncio.sleep(0.05)  # Brief pause
            
            crash_rate = error_results['crashes'] / len(ERROR_SCENARIOS)
            graceful_rate = error_results['graceful_errors'] / len(ERROR_SCENARIOS)
            
            print(f"🛡️  Error handling: {graceful_rate:.1%} graceful, {crash_rate:.1%} crashes")
    
    def performance_analysis(self):
        """Analysera overall prestanda"""
        print("\n📊 INTEGRERAT PRESTANDA ANALYS")
        print("=" * 60)
        
        # Overall request stats
        total_requests = self.results['successful_requests'] + self.results['failed_requests']
        if total_requests > 0:
            success_rate = self.results['successful_requests'] / total_requests
            print(f"🎯 Overall Success Rate: {success_rate:.1%} ({self.results['successful_requests']}/{total_requests})")
        
        # Response time stats
        if self.results['response_times']:
            times = self.results['response_times']
            avg_time = statistics.mean(times)
            median_time = statistics.median(times)
            p95_time = sorted(times)[int(0.95 * len(times))]
            max_time = max(times)
            
            print(f"\n⏱️  Response Times:")
            print(f"   Average: {avg_time*1000:.0f}ms")
            print(f"   Median: {median_time*1000:.0f}ms")
            print(f"   95th percentile: {p95_time*1000:.0f}ms") 
            print(f"   Max: {max_time*1000:.0f}ms")
            
            # Performance thresholds
            fast_responses = sum(1 for t in times if t < 0.5)  # < 500ms
            slow_responses = sum(1 for t in times if t > 2.0)  # > 2s
            
            print(f"   Fast (<500ms): {fast_responses/len(times):.1%}")
            print(f"   Slow (>2s): {slow_responses/len(times):.1%}")
        
        # Memory and context stats
        print(f"\n🧠 Memory & Context:")
        print(f"   Memory insertions: {self.results['memory_insertions']}")
        print(f"   NLU classifications: {self.results['nlu_classifications']}")
        print(f"   RAG contexts found: {self.results['rag_contexts_found']}")
        
        # Scenario performance
        print(f"\n🗣️  Scenario Results:")
        for scenario_name, results in self.results['scenario_results'].items():
            success_rate = results['successful_messages'] / results['total_messages']
            context_rate = results['context_continuity'] / max(1, results['successful_messages']) 
            avg_time = results['avg_response_time']
            
            print(f"   {scenario_name}:")
            print(f"     Success: {success_rate:.1%}, Context: {context_rate:.1%}, Time: {avg_time*1000:.0f}ms")
        
        # Errors
        if self.results['errors']:
            print(f"\n❌ Errors ({len(self.results['errors'])}):")
            error_types = {}
            for error in self.results['errors']:
                error_type = error.split(':')[0] if ':' in error else error
                error_types[error_type] = error_types.get(error_type, 0) + 1
            
            for error_type, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True):
                print(f"   {error_type}: {count}")
        else:
            print(f"\n✅ No errors detected!")
        
        # Performance verdict
        print(f"\n🏆 OVERALL VERDICT:")
        if success_rate >= 0.95 and avg_time < 1.0:
            print("   ✨ EXCELLENT - Alice performs very well under load!")
        elif success_rate >= 0.90 and avg_time < 2.0:
            print("   ✅ GOOD - Alice handles load well with minor issues")
        elif success_rate >= 0.80:
            print("   ⚠️  ACCEPTABLE - Alice works but has performance issues")
        else:
            print("   ❌ POOR - Alice struggles under load, needs optimization")
    
    async def run_all_tests(self):
        """Kör alla integrerade tester"""
        print("🚀 ALICE INTEGRERAT END-TO-END STRESSTEST")
        print("=" * 60)
        
        # Health check först
        if not await self.test_server_health():
            print("❌ Server is not responding. Make sure Alice is running on port 8000.")
            return
        
        print("✅ Server health check passed")
        
        start_time = time.time()
        
        async with aiohttp.ClientSession() as session:
            # Kör conversation scenarios
            for scenario in CONVERSATION_SCENARIOS:
                await self.run_conversation_scenario(scenario, session)
                await asyncio.sleep(0.2)  # Brief pause between scenarios
        
        # Concurrent load test
        await self.test_concurrent_load()
        
        # Error handling test  
        await self.test_error_handling()
        
        total_time = time.time() - start_time
        total_requests = self.results['successful_requests'] + self.results['failed_requests']
        throughput = total_requests / total_time if total_time > 0 else 0
        
        print(f"\n⏱️  Total test time: {total_time:.1f}s")
        print(f"📈 Overall throughput: {throughput:.1f} requests/sec")
        
        self.performance_analysis()

async def main():
    test = IntegratedStressTest()
    await test.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())