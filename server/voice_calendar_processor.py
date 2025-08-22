"""
Voice command processor för kalenderoperationer i Alice.
Hanterar komplett flöde från svenska röstkommandon till kalender-API calls.
"""

import asyncio
import json
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import asdict

from voice_calendar_nlu import swedish_calendar_nlu, CalendarIntent
from voice_calendar_parser import swedish_event_parser, ParsedEvent
from core.calendar_service import calendar_service

class CalendarVoiceProcessor:
    """Processor för svenska röst-kommandon för kalender"""
    
    def __init__(self):
        self.nlu = swedish_calendar_nlu
        self.event_parser = swedish_event_parser
        self.calendar_service = calendar_service
        
    async def process_voice_command(self, text: str) -> Dict[str, Any]:
        """
        Huvudmetod för att processa svenska kalender-röstkommandon
        
        Args:
            text: Råtext från röstinput
            
        Returns:
            Dict med resultat och response
        """
        try:
            # 1. Analysera kommandot med NLU
            intent = self.nlu.parse_command(text)
            if not intent:
                return {
                    'success': False,
                    'message': 'Kunde inte förstå kalender-kommandot',
                    'text': text,
                    'intent': None
                }
            
            # 2. Kontrollera confidence-nivå
            if intent.confidence < 0.5:
                return {
                    'success': False,
                    'message': f'Osäker på kommandot (confidence: {intent.confidence:.2f})',
                    'text': text,
                    'intent': asdict(intent)
                }
            
            # 3. Processa baserat på action-typ
            result = await self._process_intent(intent)
            
            return {
                'success': result['success'],
                'message': result['message'],
                'text': text,
                'intent': asdict(intent),
                'action': intent.action,
                'entities': intent.entities,
                'confidence': intent.confidence
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Fel vid processning av kalender-kommando: {str(e)}',
                'text': text,
                'error': str(e)
            }
    
    async def _process_intent(self, intent: CalendarIntent) -> Dict[str, Any]:
        """Processa specifik intent baserat på action"""
        
        if intent.action == 'create':
            return await self._handle_create_event(intent)
        
        elif intent.action == 'list':
            return await self._handle_list_events(intent)
        
        elif intent.action == 'search':
            return await self._handle_search_events(intent)
        
        elif intent.action == 'delete':
            return await self._handle_delete_event(intent)
        
        elif intent.action == 'update':
            return await self._handle_update_event(intent)
        
        else:
            return {
                'success': False,
                'message': f'Okänd kalender-handling: {intent.action}'
            }
    
    async def _handle_create_event(self, intent: CalendarIntent) -> Dict[str, Any]:
        """Hantera skapande av kalenderhändelse"""
        try:
            # Parse event från entiteter
            event = self.event_parser.parse_event_from_entities(
                intent.action, 
                intent.entities, 
                intent.raw_text
            )
            
            # Validera att vi har tillräcklig information
            if not event.start_datetime:
                return {
                    'success': False,
                    'message': 'Kunde inte förstå när mötet ska äga rum. Försök specificera datum och tid.'
                }
            
            # Konvertera till format som calendar_service förstår
            start_time_str = event.start_datetime.datetime.strftime('%Y-%m-%d %H:%M')
            end_time_str = None
            if event.end_datetime:
                end_time_str = event.end_datetime.datetime.strftime('%Y-%m-%d %H:%M')
            
            # Skapa event via calendar service
            result_message = self.calendar_service.create_event(
                title=event.title or 'Nytt möte',
                start_time=start_time_str,
                end_time=end_time_str,
                description=event.description,
                attendees=event.attendees
            )
            
            # Kontrollera om skapandet lyckades
            if 'skapad' in result_message.lower() or 'created' in result_message.lower():
                return {
                    'success': True,
                    'message': result_message,
                    'event': asdict(event)
                }
            else:
                return {
                    'success': False,
                    'message': result_message
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f'Fel vid skapande av möte: {str(e)}'
            }
    
    async def _handle_list_events(self, intent: CalendarIntent) -> Dict[str, Any]:
        """Hantera listning av kalenderhändelser"""
        try:
            # Bestäm tidsintervall baserat på entiteter
            max_results = 10
            time_min = None
            time_max = None
            
            if 'date' in intent.entities:
                date_entity = intent.entities['date']
                date_type = date_entity.get('type', '')
                
                if date_type == 'today':
                    time_min = 'idag'
                    time_max = 'idag 23:59'
                elif date_type == 'tomorrow':
                    time_min = 'imorgon'
                    time_max = 'imorgon 23:59'
                elif 'next_week' in date_type:
                    time_min = 'nästa vecka'
                    max_results = 20
            
            # Hämta events
            result_message = self.calendar_service.list_events(
                max_results=max_results,
                time_min=time_min,
                time_max=time_max
            )
            
            return {
                'success': True,
                'message': result_message,
                'query_params': {
                    'max_results': max_results,
                    'time_min': time_min,
                    'time_max': time_max
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Fel vid hämtning av kalender: {str(e)}'
            }
    
    async def _handle_search_events(self, intent: CalendarIntent) -> Dict[str, Any]:
        """Hantera sökning av kalenderhändelser"""
        try:
            # Extrahera sökterm
            search_query = None
            
            if 'title' in intent.entities:
                search_query = intent.entities['title']
            elif 'people' in intent.entities and intent.entities['people']:
                search_query = intent.entities['people'][0]
            else:
                # Försök extrahera från raw text
                query_patterns = [
                    r'(?:med|om)\\s+(.+?)(?:\\s+(?:imorgon|idag|på)|\s*$)',
                    r'hitta\\s+(.+?)(?:\\s+(?:imorgon|idag|på)|\s*$)'
                ]
                
                import re
                for pattern in query_patterns:
                    match = re.search(pattern, intent.raw_text, re.IGNORECASE)
                    if match:
                        search_query = match.group(1).strip()
                        break
            
            if not search_query:
                return {
                    'success': False,
                    'message': 'Kunde inte förstå vad du vill söka efter. Försök "hitta möte med [person]" eller "sök efter [ämne]".'
                }
            
            # Sök events
            result_message = self.calendar_service.search_events(search_query)
            
            return {
                'success': True,
                'message': result_message,
                'search_query': search_query
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Fel vid sökning av möten: {str(e)}'
            }
    
    async def _handle_delete_event(self, intent: CalendarIntent) -> Dict[str, Any]:
        """Hantera borttagning av kalenderhändelse"""
        try:
            # För borttagning behöver vi först hitta event ID
            # Detta kräver en sökning först
            search_result = await self._handle_search_events(intent)
            
            if not search_result['success']:
                return {
                    'success': False,
                    'message': 'Kunde inte hitta mötet att ta bort. ' + search_result['message']
                }
            
            # I en riktig implementation skulle vi:
            # 1. Presentera hittade möten för användaren
            # 2. Be om bekräftelse
            # 3. Ta bort det specifika mötet
            
            return {
                'success': False,
                'message': 'Borttagning av möten kräver interaktiv bekräftelse. Hitta först mötet med "sök efter [möte]" och sedan kan jag hjälpa till att ta bort det.'
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Fel vid borttagning av möte: {str(e)}'
            }
    
    async def _handle_update_event(self, intent: CalendarIntent) -> Dict[str, Any]:
        """Hantera uppdatering av kalenderhändelse"""
        try:
            # Liknande som delete - kräver först sökning för att hitta event ID
            search_result = await self._handle_search_events(intent)
            
            if not search_result['success']:
                return {
                    'success': False,
                    'message': 'Kunde inte hitta mötet att uppdatera. ' + search_result['message']
                }
            
            return {
                'success': False,
                'message': 'Uppdatering av möten kräver interaktiv hantering. Hitta först mötet och specificera sedan vad som ska ändras.'
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Fel vid uppdatering av möte: {str(e)}'
            }
    
    def is_calendar_command(self, text: str) -> bool:
        """Kontrollera om en text är ett kalender-kommando"""
        intent = self.nlu.parse_command(text)
        return intent is not None and intent.confidence >= 0.5
    
    def get_command_confidence(self, text: str) -> float:
        """Få confidence-score för ett potentiellt kalender-kommando"""
        intent = self.nlu.parse_command(text)
        return intent.confidence if intent else 0.0
    
    def extract_calendar_entities(self, text: str) -> Optional[Dict[str, Any]]:
        """Extrahera kalender-entiteter från text för debugging"""
        intent = self.nlu.parse_command(text)
        if intent:
            return {
                'action': intent.action,
                'confidence': intent.confidence,
                'entities': intent.entities
            }
        return None

# Global instans för användning i voice_stream
calendar_voice_processor = CalendarVoiceProcessor()