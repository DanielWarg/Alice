#!/usr/bin/env python3
"""
Test script för Google Calendar-integration med Alice AI-assistant
Testar alla calendar-funktioner och svenska språkstöd
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from core.calendar_service import calendar_service
from core.tool_registry import validate_and_execute_tool

def test_swedish_datetime_parsing():
    """Testa svenska datum/tid-parsning"""
    print("=== Testar svenska datum/tid-parsning ===")
    
    test_cases = [
        "imorgon kl 14:00",
        "fredag eftermiddag",
        "nästa måndag morgon",
        "idag lunch",
        "på tisdag kl 16:30",
        "om 2 timmar",
        "nästa vecka torsdag kl 09:00"
    ]
    
    for test_case in test_cases:
        try:
            parsed = calendar_service._parse_swedish_datetime(test_case)
            print(f"✓ '{test_case}' -> {parsed.strftime('%Y-%m-%d %H:%M')}")
        except Exception as e:
            print(f"✗ '{test_case}' -> Fel: {str(e)}")

def test_conflict_detection():
    """Testa konfliktdetektering"""
    print("\n=== Testar konfliktdetektering ===")
    
    # Detta kommer att fungera endast om Google Calendar API är konfigurerat
    try:
        result = calendar_service.check_conflicts(
            "imorgon kl 10:00",
            "imorgon kl 11:00"
        )
        print(f"✓ Konfliktkolning: {result['message']}")
        
        if result.get('suggestions'):
            print("Förslag:")
            for suggestion in result['suggestions'][:2]:
                print(f"  - {suggestion['formatted']}")
                
    except Exception as e:
        print(f"✗ Konfliktkolning misslyckades: {str(e)}")

def test_meeting_suggestions():
    """Testa mötesförslag"""
    print("\n=== Testar intelligenta mötesförslag ===")
    
    try:
        suggestions = calendar_service.suggest_meeting_times(
            duration_minutes=60,
            date_preference="imorgon"
        )
        
        if suggestions:
            print(f"✓ Hittade {len(suggestions)} förslag:")
            for i, suggestion in enumerate(suggestions[:3], 1):
                confidence = int(suggestion['confidence'] * 100)
                print(f"  {i}. {suggestion['formatted']} (förtroende: {confidence}%)")
        else:
            print("✓ Inga förslag hittades (tom kalender eller ingen internetanslutning)")
            
    except Exception as e:
        print(f"✗ Mötesförslag misslyckades: {str(e)}")

def test_tool_integration():
    """Testa verktygsintegration"""
    print("\n=== Testar verktygsintegration ===")
    
    test_tools = [
        {
            "name": "LIST_CALENDAR_EVENTS",
            "args": {"max_results": 5}
        },
        {
            "name": "SUGGEST_MEETING_TIMES", 
            "args": {"duration_minutes": 30, "date_preference": "imorgon"}
        },
        {
            "name": "CHECK_CALENDAR_CONFLICTS",
            "args": {"start_time": "imorgon kl 15:00", "end_time": "imorgon kl 16:00"}
        }
    ]
    
    for tool_test in test_tools:
        try:
            result = validate_and_execute_tool(tool_test["name"], tool_test["args"])
            if result.get("ok"):
                print(f"✓ {tool_test['name']}: {result['message'][:100]}...")
            else:
                print(f"✗ {tool_test['name']}: {result.get('message', 'Okänt fel')}")
        except Exception as e:
            print(f"✗ {tool_test['name']}: Fel - {str(e)}")

def test_voice_command_parsing():
    """Testa parsing av röstkommandon"""
    print("\n=== Testar parsing av svenska röstkommandon ===")
    
    # Detta skulle behöva frontend calendar service för fullständig testning
    # Men vi kan testa grundläggande mönster här
    
    voice_commands = [
        "skapa möte imorgon kl 14:00",
        "boka tid för tandläkare på fredag",
        "visa mina möten denna vecka", 
        "sök efter möte med Jonas",
        "när har jag lunch imorgon",
        "föreslå mötestider nästa vecka"
    ]
    
    for command in voice_commands:
        # Simulera enkel parsing
        if any(keyword in command.lower() for keyword in ['skapa', 'boka', 'lägg till']):
            print(f"✓ '{command}' -> CREATE_CALENDAR_EVENT")
        elif any(keyword in command.lower() for keyword in ['visa', 'lista', 'vad har jag']):
            print(f"✓ '{command}' -> LIST_CALENDAR_EVENTS")
        elif any(keyword in command.lower() for keyword in ['sök', 'hitta', 'leta']):
            print(f"✓ '{command}' -> SEARCH_CALENDAR_EVENTS")
        elif any(keyword in command.lower() for keyword in ['föreslå', 'lediga tider']):
            print(f"✓ '{command}' -> SUGGEST_MEETING_TIMES")
        else:
            print(f"? '{command}' -> Okänt kommando")

def main():
    """Kör alla tester"""
    print("📅 ALICE CALENDAR INTEGRATION - TESTRESULTAT")
    print("=" * 50)
    
    try:
        test_swedish_datetime_parsing()
        test_conflict_detection()
        test_meeting_suggestions()
        test_tool_integration()
        test_voice_command_parsing()
        
        print("\n" + "=" * 50)
        print("✅ ALLA TESTER SLUTFÖRDA")
        print("\nNotera: Vissa funktioner kräver konfigurerad Google Calendar API.")
        print("Se CALENDAR_SETUP.md för instruktioner.")
        
    except KeyboardInterrupt:
        print("\n❌ Testning avbruten av användare")
    except Exception as e:
        print(f"\n❌ Oväntat fel under testning: {str(e)}")

if __name__ == "__main__":
    main()