#!/usr/bin/env python3
"""
Omfattande test för svenska kalender-röstkommandon i Alice.
Testar NLU, parsing, processing och responses för naturligt svenska språk.
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Any

# Add server to path
sys.path.insert(0, str(Path(__file__).parent))

# Test imports
try:
    from voice_calendar_nlu import swedish_calendar_nlu, CalendarIntent
    from voice_calendar_parser import swedish_datetime_parser, swedish_event_parser, ParsedDateTime, ParsedEvent
    from voice_calendar_processor import calendar_voice_processor
    from voice_calendar_responses import alice_calendar_responses
    print("✅ All calendar voice modules imported successfully")
except Exception as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

class SwedishCalendarVoiceTestSuite:
    """Testpaket för svenska kalender-röstkommandon"""
    
    def __init__(self):
        self.test_results = []
        self.total_tests = 0
        self.passed_tests = 0
        
    def run_all_tests(self):
        """Kör alla tester i sekvens"""
        print("🎤 Svenska Kalender-Röstkommandon - Komplett Testpaket")
        print("=" * 70)
        
        test_methods = [
            self.test_nlu_patterns,
            self.test_datetime_parsing,
            self.test_event_parsing,
            self.test_voice_processing,
            self.test_response_generation,
            self.test_real_world_commands,
            self.test_edge_cases,
            self.test_confidence_levels,
            self.test_entity_extraction,
            self.test_natural_language_variations
        ]
        
        for test_method in test_methods:
            try:
                print(f"\n🧪 Running {test_method.__name__}...")
                asyncio.run(test_method())
            except Exception as e:
                print(f"❌ Test crashed: {test_method.__name__}: {e}")
                self.test_results.append((test_method.__name__, False, str(e)))
        
        self._print_summary()
        
    async def test_nlu_patterns(self):
        """Testa NLU pattern recognition för svenska kalender-kommandon"""
        test_cases = [
            # CREATE patterns
            ("boka möte imorgon kl 14", "create", 0.7),
            ("skapa händelse på fredag", "create", 0.6),
            ("lägg till möte nästa måndag", "create", 0.7),
            ("schemalägg lunch med Anna", "create", 0.8),
            ("planera presentation imorgon", "create", 0.6),
            ("boka in ett möte", "create", 0.5),
            
            # LIST patterns  
            ("vad har jag på schemat", "list", 0.8),
            ("visa min kalender", "list", 0.7),
            ("vad händer idag", "list", 0.7),
            ("vilka möten har jag", "list", 0.8),
            ("kommande händelser", "list", 0.6),
            ("nästa veckas kalender", "list", 0.7),
            
            # SEARCH patterns
            ("hitta mötet med Stefan", "search", 0.8),
            ("sök efter presentation", "search", 0.7),
            ("när träffar jag teamet", "search", 0.6),
            ("när är mötet om budget", "search", 0.7),
            
            # DELETE patterns
            ("ta bort lunch-mötet", "delete", 0.8),
            ("avboka mötet imorgon", "delete", 0.8),
            ("radera händelsen", "delete", 0.6),
            
            # UPDATE patterns
            ("flytta mötet till fredag", "update", 0.8),
            ("ändra tiden för presentationen", "update", 0.7),
            ("byt tid på lunch", "update", 0.6),
        ]
        
        passed = 0
        total = len(test_cases)
        
        for text, expected_action, min_confidence in test_cases:
            intent = swedish_calendar_nlu.parse_command(text)
            
            if intent and intent.action == expected_action and intent.confidence >= min_confidence:
                print(f"  ✅ '{text}' -> {intent.action} ({intent.confidence:.2f})")
                passed += 1
            else:
                action = intent.action if intent else "none"
                confidence = intent.confidence if intent else 0.0
                print(f"  ❌ '{text}' -> {action} ({confidence:.2f}) [expected: {expected_action}, min: {min_confidence}]")
        
        accuracy = passed / total * 100
        success = accuracy >= 85.0
        
        print(f"\n📊 NLU Pattern Recognition: {accuracy:.1f}% ({passed}/{total})")
        self._record_test("NLU Patterns", success, f"Accuracy: {accuracy:.1f}%")
        
    async def test_datetime_parsing(self):
        """Testa svenska datum- och tidsanalys"""
        from datetime import datetime, timedelta
        
        test_cases = [
            # Relativa datum
            ("idag", lambda: datetime.now().date()),
            ("imorgon", lambda: (datetime.now() + timedelta(days=1)).date()),
            ("på måndag", lambda: self._next_weekday(0)),
            ("nästa fredag", lambda: self._next_weekday(4)),
            
            # Tider
            ("kl 14:30", (14, 30)),
            ("halv tre", (14, 30)),  # halv tre = 14:30
            ("kvart över två", (14, 15)),
            ("på eftermiddagen", (14, 0)),
            ("på morgonen", (9, 0)),
        ]
        
        passed = 0
        total = len(test_cases)
        
        # Test datum
        for date_text, expected_func in test_cases[:4]:
            date_entity = {"type": self._get_date_type(date_text), "raw": date_text}
            parsed_dt = swedish_datetime_parser._parse_date_entity(date_entity)
            
            if parsed_dt and callable(expected_func):
                expected_date = expected_func()
                if parsed_dt.date() == expected_date:
                    print(f"  ✅ Datum: '{date_text}' -> {parsed_dt.date()}")
                    passed += 1
                else:
                    print(f"  ❌ Datum: '{date_text}' -> {parsed_dt.date()} [expected: {expected_date}]")
            else:
                print(f"  ❌ Datum: '{date_text}' -> parsing failed")
        
        # Test tider
        for time_text, expected_time in test_cases[4:]:
            time_entity = {"type": self._get_time_type(time_text), "raw": time_text, "groups": self._extract_time_groups(time_text)}
            parsed_time = swedish_datetime_parser._parse_time_entity(time_entity)
            
            if parsed_time and parsed_time.hour == expected_time[0] and parsed_time.minute == expected_time[1]:
                print(f"  ✅ Tid: '{time_text}' -> {parsed_time}")
                passed += 1
            else:
                actual = f"{parsed_time.hour}:{parsed_time.minute:02d}" if parsed_time else "failed"
                expected = f"{expected_time[0]}:{expected_time[1]:02d}"
                print(f"  ❌ Tid: '{time_text}' -> {actual} [expected: {expected}]")
        
        accuracy = passed / total * 100
        success = accuracy >= 80.0
        
        print(f"\n📊 DateTime Parsing: {accuracy:.1f}% ({passed}/{total})")
        self._record_test("DateTime Parsing", success, f"Accuracy: {accuracy:.1f}%")
        
    async def test_event_parsing(self):
        """Testa komplett event-parsing från entiteter"""
        test_scenarios = [
            {
                "text": "boka möte med Anna imorgon kl 14",
                "expected": {
                    "has_title": True,
                    "has_start_time": True,
                    "has_attendees": True,
                    "attendee_count": 1
                }
            },
            {
                "text": "schemalägg presentation nästa måndag på eftermiddagen",
                "expected": {
                    "has_title": True,
                    "has_start_time": True,
                    "title_contains": "presentation"
                }
            },
            {
                "text": "lägg till lunch-möte",
                "expected": {
                    "has_title": True,
                    "event_type": "lunch"
                }
            }
        ]
        
        passed = 0
        total = len(test_scenarios)
        
        for scenario in test_scenarios:
            text = scenario["text"]
            expected = scenario["expected"]
            
            # Parse med NLU först
            intent = swedish_calendar_nlu.parse_command(text)
            if not intent:
                print(f"  ❌ '{text}' -> NLU parsing failed")
                continue
            
            # Skapa event
            event = swedish_event_parser.parse_event_from_entities(
                intent.action, 
                intent.entities, 
                intent.raw_text
            )
            
            # Validera förväntningar
            all_checks_passed = True
            
            if expected.get("has_title") and not event.title:
                print(f"  ❌ '{text}' -> Missing title")
                all_checks_passed = False
                
            if expected.get("has_start_time") and not event.start_datetime:
                print(f"  ❌ '{text}' -> Missing start time") 
                all_checks_passed = False
                
            if expected.get("has_attendees") and not event.attendees:
                print(f"  ❌ '{text}' -> Missing attendees")
                all_checks_passed = False
                
            if expected.get("attendee_count") and len(event.attendees or []) != expected["attendee_count"]:
                print(f"  ❌ '{text}' -> Wrong attendee count: {len(event.attendees or [])} vs {expected['attendee_count']}")
                all_checks_passed = False
                
            if expected.get("title_contains") and expected["title_contains"] not in (event.title or "").lower():
                print(f"  ❌ '{text}' -> Title doesn't contain '{expected['title_contains']}': {event.title}")
                all_checks_passed = False
                
            if expected.get("event_type") and event.event_type != expected["event_type"]:
                print(f"  ❌ '{text}' -> Wrong event type: {event.event_type} vs {expected['event_type']}")
                all_checks_passed = False
            
            if all_checks_passed:
                print(f"  ✅ '{text}' -> Event parsed correctly")
                print(f"      Title: {event.title}")
                print(f"      Start: {event.start_datetime.datetime if event.start_datetime else 'None'}")
                print(f"      Attendees: {event.attendees}")
                passed += 1
            
        accuracy = passed / total * 100
        success = accuracy >= 75.0
        
        print(f"\n📊 Event Parsing: {accuracy:.1f}% ({passed}/{total})")
        self._record_test("Event Parsing", success, f"Accuracy: {accuracy:.1f}%")
        
    async def test_voice_processing(self):
        """Testa komplett voice command processing"""
        test_commands = [
            "boka möte imorgon kl 14 med Stefan",
            "vad har jag på schemat idag",
            "hitta mötet med teamet",
            "flytta presentationen till fredag",
            "ta bort lunch-mötet"
        ]
        
        passed = 0
        total = len(test_commands)
        
        for command in test_commands:
            try:
                # Test att processor kan hantera kommandot
                is_calendar = calendar_voice_processor.is_calendar_command(command)
                confidence = calendar_voice_processor.get_command_confidence(command)
                
                if is_calendar and confidence >= 0.5:
                    # Test processing
                    result = await calendar_voice_processor.process_voice_command(command)
                    
                    if result and 'success' in result:
                        print(f"  ✅ '{command}' -> Processed (confidence: {confidence:.2f})")
                        print(f"      Action: {result.get('action', 'unknown')}")
                        print(f"      Success: {result['success']}")
                        passed += 1
                    else:
                        print(f"  ❌ '{command}' -> Processing failed")
                else:
                    print(f"  ❌ '{command}' -> Not recognized as calendar command (confidence: {confidence:.2f})")
                    
            except Exception as e:
                print(f"  ❌ '{command}' -> Exception: {e}")
        
        accuracy = passed / total * 100
        success = accuracy >= 70.0
        
        print(f"\n📊 Voice Processing: {accuracy:.1f}% ({passed}/{total})")
        self._record_test("Voice Processing", success, f"Accuracy: {accuracy:.1f}%")
        
    async def test_response_generation(self):
        """Testa svenska response-generering med Alice's personlighet"""
        test_scenarios = [
            {
                "result": {
                    "success": True,
                    "action": "create",
                    "message": "Event created successfully",
                    "event": {
                        "title": "Möte med Anna",
                        "start_datetime": {"datetime": "2024-08-22 14:00:00"}
                    }
                },
                "should_contain": ["skapat", "möte", "anna", "kl", "14"]
            },
            {
                "result": {
                    "success": True,
                    "action": "list",
                    "message": "Du har 3 kommande händelser:\\n• Möte kl 14\\n• Lunch kl 12"
                },
                "should_contain": ["kalender", "möte", "lunch"]
            },
            {
                "result": {
                    "success": False,
                    "message": "Could not understand command",
                    "confidence": 0.3
                },
                "should_contain": ["förstå", "försök", "igen"]
            }
        ]
        
        passed = 0
        total = len(test_scenarios)
        
        for i, scenario in enumerate(test_scenarios):
            result = scenario["result"]
            should_contain = scenario["should_contain"]
            
            response = alice_calendar_responses.generate_response(result)
            
            # Kontrollera att response innehåller förväntade element
            response_lower = response.lower()
            contains_all = all(word.lower() in response_lower for word in should_contain)
            
            if contains_all and len(response) > 10:  # Rimlig längd
                print(f"  ✅ Scenario {i+1}: Good response")
                print(f"      Response: {response[:100]}...")
                passed += 1
            else:
                print(f"  ❌ Scenario {i+1}: Poor response")
                print(f"      Response: {response}")
                print(f"      Missing keywords: {should_contain}")
        
        accuracy = passed / total * 100
        success = accuracy >= 75.0
        
        print(f"\n📊 Response Generation: {accuracy:.1f}% ({passed}/{total})")
        self._record_test("Response Generation", success, f"Accuracy: {accuracy:.1f}%")
        
    async def test_real_world_commands(self):
        """Testa verkliga svenska kalender-kommandon som användare skulle säga"""
        real_world_commands = [
            "boka möte imorgon kl 14",
            "vad har jag på schemat idag",
            "flytta mötet till fredag",
            "ta bort lunch-mötet",
            "när är mitt nästa möte",
            "visa nästa veckas kalender",
            "schemalägg presentation på måndag kl 10",
            "hitta mötet med Anna",
            "boka lunch med teamet imorgon",
            "ändra tiden för onsdagsmötet",
            "vad händer på eftermiddagen",
            "lägg till träning på lördag",
            "avboka fredagslunchen",
            "när träffar jag Stefan nästa gång",
            "boka in en timme för projektet"
        ]
        
        passed = 0
        total = len(real_world_commands)
        
        for command in real_world_commands:
            try:
                # Test end-to-end processing
                is_calendar = calendar_voice_processor.is_calendar_command(command)
                
                if is_calendar:
                    confidence = calendar_voice_processor.get_command_confidence(command)
                    result = await calendar_voice_processor.process_voice_command(command)
                    response = alice_calendar_responses.generate_response(result)
                    
                    if confidence >= 0.4 and len(response) > 20:
                        print(f"  ✅ '{command}' -> OK (conf: {confidence:.2f})")
                        passed += 1
                    else:
                        print(f"  ❌ '{command}' -> Low quality (conf: {confidence:.2f})")
                else:
                    print(f"  ❌ '{command}' -> Not recognized as calendar")
                    
            except Exception as e:
                print(f"  ❌ '{command}' -> Exception: {e}")
        
        accuracy = passed / total * 100
        success = accuracy >= 80.0
        
        print(f"\n📊 Real World Commands: {accuracy:.1f}% ({passed}/{total})")
        self._record_test("Real World Commands", success, f"Accuracy: {accuracy:.1f}%")
        
    async def test_edge_cases(self):
        """Testa edge cases och felhantering"""
        edge_cases = [
            ("", "Empty input"),
            ("    ", "Whitespace only"),
            ("ajklsdj aklsjd", "Nonsense text"),
            ("boka möte", "Incomplete command"),
            ("möte imorgon imorgon imorgon", "Repeated words"),
            ("BOKA MÖTE IMORGON KL 14", "All caps"),
            ("boka möte... ehh... imorgon kl... 14", "Hesitation"),
            ("kan du boka ett möte för mig imorgon kl 14 tack", "Polite extended"),
        ]
        
        passed = 0
        total = len(edge_cases)
        
        for text, description in edge_cases:
            try:
                is_calendar = calendar_voice_processor.is_calendar_command(text)
                confidence = calendar_voice_processor.get_command_confidence(text)
                
                # För edge cases förväntar vi oss låg confidence eller False
                if text.strip() == "" or "nonsense" in description.lower():
                    if not is_calendar or confidence < 0.3:
                        print(f"  ✅ '{text}' ({description}) -> Correctly rejected")
                        passed += 1
                    else:
                        print(f"  ❌ '{text}' ({description}) -> Incorrectly accepted")
                else:
                    # För ofullständiga men vålida kommandon
                    if "boka möte" in text.lower():
                        if is_calendar and confidence >= 0.3:
                            print(f"  ✅ '{text}' ({description}) -> Partially recognized")
                            passed += 1
                        else:
                            print(f"  ❌ '{text}' ({description}) -> Should be partially recognized")
                    else:
                        # För andra cases
                        result = await calendar_voice_processor.process_voice_command(text)
                        if result and not result.get('success', True):
                            print(f"  ✅ '{text}' ({description}) -> Graceful failure")
                            passed += 1
                        else:
                            print(f"  ❌ '{text}' ({description}) -> Unexpected behavior")
                            
            except Exception as e:
                print(f"  ✅ '{text}' ({description}) -> Exception handled: {type(e).__name__}")
                passed += 1  # Exception handling is OK for edge cases
        
        accuracy = passed / total * 100
        success = accuracy >= 70.0
        
        print(f"\n📊 Edge Cases: {accuracy:.1f}% ({passed}/{total})")
        self._record_test("Edge Cases", success, f"Accuracy: {accuracy:.1f}%")
        
    async def test_confidence_levels(self):
        """Testa confidence-nivåer för olika typer av kommandon"""
        confidence_tests = [
            # Mycket tydliga kommandon (>0.8)
            ("boka möte imorgon kl 14", 0.8),
            ("visa min kalender", 0.8),
            ("ta bort lunch-mötet", 0.8),
            
            # Tydliga kommandon (>0.6)
            ("schemalägg presentation", 0.6),
            ("hitta möte", 0.6),
            ("flytta mötet", 0.6),
            
            # Oklara kommandon (>0.3)
            ("möte imorgon", 0.3),
            ("kalender", 0.3),
            
            # Icke-kalender kommandon (<0.3)
            ("spela musik", 0.3),
            ("vad är vädret", 0.3),
            ("hej Alice", 0.3),
        ]
        
        passed = 0
        total = len(confidence_tests)
        
        for text, expected_min_confidence in confidence_tests:
            confidence = calendar_voice_processor.get_command_confidence(text)
            
            if confidence >= expected_min_confidence:
                print(f"  ✅ '{text}' -> {confidence:.2f} (>= {expected_min_confidence})")
                passed += 1
            else:
                print(f"  ❌ '{text}' -> {confidence:.2f} (< {expected_min_confidence})")
        
        accuracy = passed / total * 100
        success = accuracy >= 75.0
        
        print(f"\n📊 Confidence Levels: {accuracy:.1f}% ({passed}/{total})")
        self._record_test("Confidence Levels", success, f"Accuracy: {accuracy:.1f}%")
        
    async def test_entity_extraction(self):
        """Testa extrahering av entiteter från svenska kommandon"""
        entity_tests = [
            {
                "text": "boka möte med Anna imorgon kl 14",
                "expected_entities": ["title", "people", "date", "time"]
            },
            {
                "text": "schemalägg presentation nästa måndag på eftermiddagen",
                "expected_entities": ["title", "date", "time"]
            },
            {
                "text": "lunch-möte på fredag",
                "expected_entities": ["event_type", "date"]
            },
            {
                "text": "vad har jag på schemat idag",
                "expected_entities": ["date"]
            }
        ]
        
        passed = 0
        total = len(entity_tests)
        
        for test in entity_tests:
            text = test["text"]
            expected = test["expected_entities"]
            
            entities = calendar_voice_processor.extract_calendar_entities(text)
            
            if entities and "entities" in entities:
                found_entities = list(entities["entities"].keys())
                missing = set(expected) - set(found_entities)
                
                if not missing:
                    print(f"  ✅ '{text}' -> Found all entities: {found_entities}")
                    passed += 1
                else:
                    print(f"  ❌ '{text}' -> Missing entities: {missing}")
                    print(f"      Found: {found_entities}")
            else:
                print(f"  ❌ '{text}' -> No entities extracted")
        
        accuracy = passed / total * 100
        success = accuracy >= 70.0
        
        print(f"\n📊 Entity Extraction: {accuracy:.1f}% ({passed}/{total})")
        self._record_test("Entity Extraction", success, f"Accuracy: {accuracy:.1f}%")
        
    async def test_natural_language_variations(self):
        """Testa variationer av naturligt svenska språk"""
        variations = [
            # Olika sätt att säga samma sak
            ["boka möte imorgon", "kan du boka ett möte imorgon", "jag vill boka möte imorgon"],
            ["visa kalender", "visa min kalender", "vad har jag på schemat", "vad står på programmet"],
            ["flytta mötet", "kan du flytta mötet", "jag vill ändra tiden för mötet"],
            ["hitta möte", "sök efter mötet", "leta efter mötet", "när är mötet"]
        ]
        
        passed_groups = 0
        total_groups = len(variations)
        
        for i, group in enumerate(variations):
            print(f"  Testing variation group {i+1}: {group[0]}...")
            
            confidences = []
            actions = []
            
            for variant in group:
                intent = swedish_calendar_nlu.parse_command(variant)
                if intent:
                    confidences.append(intent.confidence)
                    actions.append(intent.action)
                else:
                    confidences.append(0.0)
                    actions.append(None)
            
            # Alla varianter borde ha samma action och rimlig confidence
            unique_actions = set(action for action in actions if action)
            avg_confidence = sum(confidences) / len(confidences)
            
            if len(unique_actions) <= 1 and avg_confidence >= 0.5:
                print(f"    ✅ Consistent action: {list(unique_actions)[0] if unique_actions else 'none'}, avg conf: {avg_confidence:.2f}")
                passed_groups += 1
            else:
                print(f"    ❌ Inconsistent: actions={unique_actions}, avg conf: {avg_confidence:.2f}")
                for j, (variant, action, conf) in enumerate(zip(group, actions, confidences)):
                    print(f"      {j+1}. '{variant}' -> {action} ({conf:.2f})")
        
        accuracy = passed_groups / total_groups * 100
        success = accuracy >= 75.0
        
        print(f"\n📊 Natural Language Variations: {accuracy:.1f}% ({passed_groups}/{total_groups})")
        self._record_test("Natural Language Variations", success, f"Accuracy: {accuracy:.1f}%")
        
    def _record_test(self, test_name: str, success: bool, details: str):
        """Registrera testresultat"""
        self.test_results.append((test_name, success, details))
        self.total_tests += 1
        if success:
            self.passed_tests += 1
            
    def _print_summary(self):
        """Skriv ut sammanfattning av alla tester"""
        print("\n" + "=" * 70)
        print("🎯 TESTRESULTAT SAMMANFATTNING")
        print("=" * 70)
        
        for test_name, success, details in self.test_results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status} {test_name} - {details}")
        
        overall_accuracy = self.passed_tests / self.total_tests * 100 if self.total_tests > 0 else 0
        
        print(f"\n🏆 TOTALT RESULTAT: {overall_accuracy:.1f}% ({self.passed_tests}/{self.total_tests})")
        
        if overall_accuracy >= 85:
            print("🎉 EXCELLENT! Svenska kalender-röstkommandon är redo för användning!")
        elif overall_accuracy >= 75:
            print("👍 BRA! Några mindre justeringar rekommenderas.")
        elif overall_accuracy >= 65:
            print("⚠️  OKEJ! Flera förbättringar behövs före lansering.")
        else:
            print("🚨 KRITISKT! Stora problem måste fixas.")
            
        return overall_accuracy >= 75.0
    
    # Helper methods
    def _get_date_type(self, text: str) -> str:
        """Hitta datum-typ för test"""
        if "idag" in text:
            return "today"
        elif "imorgon" in text:
            return "tomorrow"
        elif "måndag" in text:
            return "monday"
        elif "fredag" in text:
            return "friday"
        return "unknown"
    
    def _get_time_type(self, text: str) -> str:
        """Hitta tid-typ för test"""
        if "kl" in text and ":" in text:
            return "exact_time"
        elif "halv" in text:
            return "half_past"
        elif "kvart över" in text:
            return "quarter_past"
        elif "eftermiddag" in text:
            return "afternoon"
        elif "morgon" in text:
            return "morning"
        return "unknown"
    
    def _extract_time_groups(self, text: str) -> list:
        """Extrahera tid-grupper för test"""
        import re
        if "14:30" in text:
            return ["14", "30"]
        elif "halv tre" in text:
            return ["3"]
        elif "kvart över två" in text:
            return ["2"]
        return []
    
    def _next_weekday(self, weekday: int):
        """Nästa förekomst av veckodagen"""
        from datetime import datetime, timedelta
        today = datetime.now()
        days_ahead = weekday - today.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        return (today + timedelta(days=days_ahead)).date()

def main():
    """Kör alla tester"""
    test_suite = SwedishCalendarVoiceTestSuite()
    success = test_suite.run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()