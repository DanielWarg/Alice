#!/usr/bin/env python3
"""
Test Alice's förmåga att skilja mellan tool commands och naturlig chatt
"""

import os
import asyncio
import aiohttp
import json
from core.router import classify

# Enable all tools for testing
os.environ["ENABLED_TOOLS"] = "PLAY,PAUSE,STOP,NEXT,PREV,SET_VOLUME,MUTE,UNMUTE,REPEAT,SHUFFLE,LIKE,UNLIKE,SEND_EMAIL,READ_EMAILS,SEARCH_EMAILS"

# Test cases - kommando vs chatt
TEST_CASES = [
    # MUSIC TOOL COMMANDS (should be classified)
    {
        "input": "spela back in black",
        "expected_type": "tool_command",
        "expected_tool": "PLAY",
        "description": "Direkt spelkommando"
    },
    {
        "input": "spela musik",
        "expected_type": "tool_command", 
        "expected_tool": "PLAY",
        "description": "Generellt spelkommando"
    },
    {
        "input": "pausa musiken",
        "expected_type": "tool_command",
        "expected_tool": "PAUSE", 
        "description": "Pauskommando"
    },
    {
        "input": "höj volymen",
        "expected_type": "tool_command",
        "expected_tool": "SET_VOLUME",
        "description": "Volymkommando"
    },
    
    # NATURAL CHAT (should NOT be classified as tool commands)
    {
        "input": "vad tycker du om back in black av ac/dc?",
        "expected_type": "natural_chat",
        "expected_tool": None,
        "description": "Fråga om musiksmak"
    },
    {
        "input": "berätta om ac/dc och deras historia",
        "expected_type": "natural_chat",
        "expected_tool": None, 
        "description": "Informationsfråga"
    },
    {
        "input": "vilka är de bästa låtarna av ac/dc?",
        "expected_type": "natural_chat",
        "expected_tool": None,
        "description": "Rekommendationsfråga"
    },
    {
        "input": "när grundades bandet ac/dc?",
        "expected_type": "natural_chat",
        "expected_tool": None,
        "description": "Faktafråga"
    },
    
    # AMBIGUOUS CASES (gränzfall)
    {
        "input": "kan du spela back in black?",
        "expected_type": "ambiguous",
        "expected_tool": "PLAY",
        "description": "Artig förfrågan om att spela"
    },
    {
        "input": "jag skulle vilja lyssna på ac/dc",
        "expected_type": "ambiguous", 
        "expected_tool": None,
        "description": "Indirekt önskan"
    },
    {
        "input": "spela något av ac/dc tack",
        "expected_type": "ambiguous",
        "expected_tool": "PLAY", 
        "description": "Specifik artist-förfrågan"
    },
    
    # EMAIL COMMANDS vs CHAT
    {
        "input": "skicka mail till chef@företag.se",
        "expected_type": "tool_command",
        "expected_tool": "SEND_EMAIL",
        "description": "E-postkommando"
    },
    {
        "input": "vad är e-post och hur fungerar det?",
        "expected_type": "natural_chat",
        "expected_tool": None,
        "description": "Informationsfråga om e-post"
    },
    {
        "input": "vem uppfann e-post systemet?",
        "expected_type": "natural_chat", 
        "expected_tool": None,
        "description": "Historisk fråga om e-post"
    }
]

async def test_with_alice_api(test_case, session):
    """Test med Alice's faktiska API"""
    try:
        payload = {
            "prompt": test_case["input"],
            "model": "gpt-oss:20b", 
            "provider": "local"
        }
        
        async with session.post("http://127.0.0.1:8000/api/chat", json=payload) as response:
            if response.status == 200:
                data = await response.json()
                response_text = data.get('text', '').lower()
                
                # Analysera svaret för att se om Alice förstod det som kommando eller chatt
                command_indicators = [
                    'spelar upp', 'pausar', 'stoppar', 'höjer volym', 'sänker volym',
                    'skickar mail', 'läser mail', 'söker mail'
                ]
                
                chat_indicators = [
                    'ac/dc', 'bandet', 'grundades', 'musikgrupp', 'rock', 'historia',
                    'album', 'låtar', 'sångare', 'gitarrist', 'e-post är', 'uppfann'
                ]
                
                has_command_response = any(indicator in response_text for indicator in command_indicators)
                has_chat_response = any(indicator in response_text for indicator in chat_indicators)
                
                return {
                    'api_response': response_text,
                    'seems_like_command': has_command_response,
                    'seems_like_chat': has_chat_response,
                    'response_length': len(response_text)
                }
            else:
                return {'error': f"HTTP {response.status}"}
    except Exception as e:
        return {'error': str(e)}

def test_nlu_classification():
    """Test NLU router classification"""
    print("🧠 TESTAR NLU CLASSIFICATION")
    print("=" * 50)
    
    correct_classifications = 0
    total_tests = 0
    
    for test_case in TEST_CASES:
        nlu_result = classify(test_case["input"])
        total_tests += 1
        
        input_text = test_case["input"]
        expected_type = test_case["expected_type"]
        expected_tool = test_case["expected_tool"]
        description = test_case["description"]
        
        print(f"\n📝 Test: {description}")
        print(f"   Input: '{input_text}'")
        print(f"   Expected: {expected_type} -> {expected_tool}")
        
        if nlu_result:
            classified_tool = nlu_result.get('tool')
            confidence = nlu_result.get('confidence', 0)
            print(f"   NLU: {classified_tool} (confidence: {confidence:.2f})")
            
            # Check om klassificering stämmer
            if expected_type == "tool_command":
                if classified_tool == expected_tool:
                    print(f"   ✅ KORREKT - Identifierad som tool command")
                    correct_classifications += 1
                else:
                    print(f"   ❌ FEL - Förväntade {expected_tool}, fick {classified_tool}")
            elif expected_type == "natural_chat":
                print(f"   ❌ FEL - Klassificerades som tool när det borde vara chatt")
            elif expected_type == "ambiguous":
                if classified_tool == expected_tool:
                    print(f"   ⚠️  AMBIGUOUS - Klassificerad som {classified_tool} (kan vara OK)")
                    correct_classifications += 0.5  # Halv poäng för ambiguous
                else:
                    print(f"   ⚠️  AMBIGUOUS - Ingen classification (kan också vara OK)")
                    correct_classifications += 0.5
                    
        else:
            print(f"   NLU: None (no classification)")
            if expected_type == "natural_chat":
                print(f"   ✅ KORREKT - Ingen tool classification för chatt")
                correct_classifications += 1
            elif expected_type == "tool_command":
                print(f"   ❌ FEL - Missade tool command")
            elif expected_type == "ambiguous":
                print(f"   ⚠️  AMBIGUOUS - Ingen classification (kan vara OK)")
                correct_classifications += 0.5
    
    accuracy = correct_classifications / total_tests
    print(f"\n📊 NLU Classification Accuracy: {accuracy:.1%} ({correct_classifications:.1f}/{total_tests})")
    return accuracy

async def test_alice_responses():
    """Test Alice's faktiska svar för att se hur hon hanterar olika inputs"""
    print("\n🤖 TESTAR ALICE'S FAKTISKA SVAR")
    print("=" * 50)
    
    correct_responses = 0
    total_tests = 0
    
    async with aiohttp.ClientSession() as session:
        for test_case in TEST_CASES[:8]:  # Testa de första 8 för att spara tid
            total_tests += 1
            input_text = test_case["input"]
            expected_type = test_case["expected_type"]
            description = test_case["description"]
            
            print(f"\n📝 Test: {description}")
            print(f"   Input: '{input_text}'")
            
            api_result = await test_with_alice_api(test_case, session)
            
            if 'error' not in api_result:
                response_text = api_result['api_response']
                seems_command = api_result['seems_like_command']
                seems_chat = api_result['seems_like_chat']
                
                print(f"   Alice: '{response_text[:100]}{'...' if len(response_text) > 100 else ''}'")
                
                # Bedöm om svaret matchar förväntningen
                if expected_type == "tool_command" and seems_command:
                    print(f"   ✅ KORREKT - Alice svarade som tool command")
                    correct_responses += 1
                elif expected_type == "natural_chat" and seems_chat:
                    print(f"   ✅ KORREKT - Alice svarade med chattinformation")
                    correct_responses += 1
                elif expected_type == "ambiguous":
                    print(f"   ⚠️  AMBIGUOUS - Alice's svar: {'command-like' if seems_command else 'chat-like'}")
                    correct_responses += 0.5
                else:
                    print(f"   ❌ FEL - Alice's svar matchar inte förväntad typ")
            else:
                print(f"   💥 ERROR: {api_result['error']}")
            
            await asyncio.sleep(0.1)  # Kort paus mellan requests
    
    accuracy = correct_responses / total_tests if total_tests > 0 else 0
    print(f"\n📊 Alice Response Accuracy: {accuracy:.1%} ({correct_responses:.1f}/{total_tests})")
    return accuracy

async def main():
    print("🎭 ALICE COMMAND vs CHAT DISCRIMINATION TEST")
    print("=" * 60)
    print("Testar Alice's förmåga att skilja mellan:")
    print("  • Tool commands (spela musik, höj volym)")
    print("  • Natural chat (berätta om AC/DC)")
    print("  • Ambiguous cases (kan du spela...)")
    
    # Test 1: NLU Classification
    nlu_accuracy = test_nlu_classification()
    
    # Test 2: Alice API responses  
    api_accuracy = await test_alice_responses()
    
    # Final verdict
    print(f"\n🏆 FINAL RESULTS")
    print("=" * 30)
    print(f"NLU Classification: {nlu_accuracy:.1%}")
    print(f"Alice API Responses: {api_accuracy:.1%}")
    
    overall = (nlu_accuracy + api_accuracy) / 2
    print(f"Overall Accuracy: {overall:.1%}")
    
    if overall >= 0.9:
        print("✨ EXCELLENT - Alice skiljer mycket väl mellan commands och chatt!")
    elif overall >= 0.8:
        print("✅ GOOD - Alice hanterar de flesta fall korrekt")
    elif overall >= 0.7:
        print("⚠️  OK - Alice fungerar men kan förbättras")
    else:
        print("❌ NEEDS WORK - Alice har svårt att skilja commands från chatt")

if __name__ == "__main__":
    asyncio.run(main())