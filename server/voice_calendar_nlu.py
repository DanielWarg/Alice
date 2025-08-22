"""
Svenska NLU (Natural Language Understanding) för kalender-kommandon i Alice.
Hanterar parsing av svenska röst-kommandon för kalenderoperationer.
"""

import re
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass

@dataclass
class CalendarIntent:
    """Struktur för kalender-avsikt"""
    action: str  # 'create', 'list', 'search', 'delete', 'update'
    confidence: float
    entities: Dict[str, Any]
    raw_text: str

class SwedishCalendarNLU:
    """Svenska naturlig språkförståelse för kalender-kommandon"""
    
    def __init__(self):
        self.action_patterns = self._initialize_action_patterns()
        self.date_patterns = self._initialize_date_patterns()
        self.time_patterns = self._initialize_time_patterns()
        self.event_type_patterns = self._initialize_event_type_patterns()
        
    def _initialize_action_patterns(self) -> Dict[str, List[str]]:
        """Initialisera handlingsmönster för olika kalenderoperationer"""
        return {
            'create': [
                r'boka\s+(?:ett\s+)?(?:möte|lunch|presentation)',
                r'boka\s+(?:in\s+)?(?:ett\s+)?(?:möte|lunch|presentation)',
                r'skapa\s+(?:en\s+)?händelse',
                r'lägg\s+till\s+(?:ett\s+)?(?:möte|lunch|presentation)',
                r'schemalägg\s+(?:ett\s+)?(?:möte|lunch|presentation)',
                r'planera\s+(?:ett\s+)?(?:möte|lunch|presentation)',
                r'lägg\s+in\s+(?:i\s+)?kalendern',
                r'sätt\s+upp\s+(?:ett\s+)?möte',
                r'arrangera\s+(?:ett\s+)?möte',
                r'boka\s+(?:lunch|träning|presentation)',
                r'schemalägg\s+presentation',
                r'planera\s+presentation'
            ],
            'list': [
                r'vad\s+har\s+jag\s+(?:på\s+)?schemat',
                r'visa\s+(?:mina?\s+)?kalendern?',
                r'visa\s+min\s+kalender',
                r'vad\s+händer\s+(?:i\s*)?dag',
                r'vad\s+händer\s+(?:på\s+)?(?:eftermiddagen|morgonen|kvällen)',
                r'vilka\s+möten\s+har\s+jag',
                r'show\s+calendar',
                r'lista\s+(?:mina\s+)?händelser',
                r'vad\s+är\s+(?:på\s+)?agendan',
                r'vad\s+står\s+(?:på\s+)?programmet',
                r'nästa\s+veckas\s+kalender',
                r'kommande\s+(?:möten|händelser)',
                r'schema(?:t)?',
                r'kalender(?:n)?'
            ],
            'search': [
                r'hitta\s+(?:mötet?\s+)?(?:med|om)?',
                r'sök\s+(?:efter\s+)?(?:möte|presentation)',
                r'leta\s+(?:efter\s+)?(?:mötet?\s+)?(?:med|om)?',
                r'när\s+är\s+(?:mötet?\s+)?(?:med|om)?',
                r'när\s+träffar\s+jag',
                r'när\s+har\s+jag\s+möte',
                r'när\s+är\s+mitt\s+nästa\s+möte',
                r'hitta\s+möte',
                r'sök\s+efter\s+(?:möte|presentation|lunch)',
                r'när\s+är\s+mötet'
            ],
            'delete': [
                r'ta\s+bort\s+(?:mötet|händelsen|lunch-mötet)',
                r'avboka\s+(?:mötet|händelsen|lunchen|fredagslunchen)',
                r'cancel\s+(?:mötet|händelsen)',
                r'radera\s+(?:mötet|händelsen)',
                r'stryk\s+(?:mötet|händelsen)',
                r'remove\s+(?:mötet|händelsen)',
                r'ta\s+bort\s+lunch-mötet',
                r'avboka\s+(?:fredags)?lunchen'
            ],
            'update': [
                r'flytta\s+(?:mötet|händelsen|presentationen)',
                r'ändra\s+(?:mötet|händelsen|tiden\s+för\s+presentationen)',
                r'uppdatera\s+(?:mötet|händelsen)',
                r'byt\s+tid\s+(?:för|på)\s+(?:mötet|händelsen|lunch)',
                r'move\s+(?:mötet|händelsen)',
                r'reschedule\s+(?:mötet|händelsen)',
                r'ändra\s+tiden\s+för\s+(?:presentationen|mötet|onsdagsmötet)',
                r'flytta\s+(?:presentationen|mötet)',
                r'byt\s+tid\s+på\s+lunch'
            ]
        }
    
    def _initialize_date_patterns(self) -> List[Tuple[str, str]]:
        """Initialisera datum-mönster för svenska"""
        return [
            # Relativa datum
            (r'\b(?:i\s*)?dag\b', 'today'),
            (r'\b(?:i\s*)?morgon\b', 'tomorrow'),
            (r'\b(?:i\s*)?går\b', 'yesterday'),
            (r'\b(?:i\s*)?övermorgon\b', 'day_after_tomorrow'),
            (r'\b(?:i\s*)?förrgår\b', 'day_before_yesterday'),
            
            # Veckodagar
            (r'\b(?:på\s+)?måndag(?:en)?\b', 'monday'),
            (r'\b(?:på\s+)?tisdag(?:en)?\b', 'tuesday'),
            (r'\b(?:på\s+)?onsdag(?:en)?\b', 'wednesday'),
            (r'\b(?:på\s+)?torsdag(?:en)?\b', 'thursday'),
            (r'\b(?:på\s+)?fredag(?:en)?\b', 'friday'),
            (r'\b(?:på\s+)?lördag(?:en)?\b', 'saturday'),
            (r'\b(?:på\s+)?söndag(?:en)?\b', 'sunday'),
            
            # Nästa/denna/förra vecka
            (r'\b(?:nästa\s+)?vecka\b', 'next_week'),
            (r'\bdenna\s+vecka\b', 'this_week'),
            (r'\bförra\s+vecka\b', 'last_week'),
            
            # Månader
            (r'\bjanuar[i]?\b', 'january'),
            (r'\bfebruar[i]?\b', 'february'),
            (r'\bmars\b', 'march'),
            (r'\bapril\b', 'april'),
            (r'\bmaj\b', 'may'),
            (r'\bjuni\b', 'june'),
            (r'\bjuli\b', 'july'),
            (r'\baugusti\b', 'august'),
            (r'\bseptember\b', 'september'),
            (r'\boktober\b', 'october'),
            (r'\bnovember\b', 'november'),
            (r'\bdecember\b', 'december'),
            
            # Specifika datumformat
            (r'\b(\d{1,2})[\/\-\.](\d{1,2})(?:[\/\-\.](\d{2,4}))?\b', 'date_numeric'),
            (r'\b(\d{1,2})\s+(\w+)(?:\s+(\d{2,4}))?\b', 'date_written')
        ]
    
    def _initialize_time_patterns(self) -> List[Tuple[str, str]]:
        """Initialisera tidsmönster för svenska"""
        return [
            # Exakta tider
            (r'\b(?:kl\.?\s*)?(\d{1,2})[:\.](\d{2})\b', 'exact_time'),
            (r'\b(?:klockan\s+)?(\d{1,2})[:\.](\d{2})\b', 'exact_time_word'),
            
            # Halva och kvart
            (r'\bhalv\s+(\d{1,2})\b', 'half_past'),
            (r'\bkvart\s+över\s+(\d{1,2})\b', 'quarter_past'),
            (r'\bkvart\s+i\s+(\d{1,2})\b', 'quarter_to'),
            
            # Ungefärliga tider
            (r'\b(?:runt|cirka|ca\.?\s+)?kl\.?\s*(\d{1,2})\b', 'approximate_time'),
            (r'\b(?:på\s+)?(?:morgon|morgonen)\b', 'morning'),
            (r'\b(?:på\s+)?(?:förmiddag|förmiddagen)\b', 'forenoon'),
            (r'\b(?:på\s+)?(?:lunch|lunchtid|lunchen)\b', 'lunch'),
            (r'\b(?:på\s+)?(?:eftermiddag|eftermiddagen)\b', 'afternoon'),
            (r'\b(?:på\s+)?(?:kväll|kvällen)\b', 'evening'),
            (r'\b(?:på\s+)?(?:natt|natten)\b', 'night'),
            
            # Tidslängd
            (r'\b(\d+)\s+(?:timmar?|tim|h)\b', 'duration_hours'),
            (r'\b(\d+)\s+(?:minuter?|min|m)\b', 'duration_minutes'),
            (r'\ben\s+(?:timme?|tim)\b', 'one_hour'),
            (r'\b(?:en\s+)?halvtimme?\b', 'half_hour')
        ]
    
    def _initialize_event_type_patterns(self) -> Dict[str, List[str]]:
        """Initialisera event-typmönster"""
        return {
            'meeting': [
                r'\bmöte\b', r'\bmötena?\b', r'\bkonferens\b', 
                r'\bsammanträde\b', r'\bsammankomst\b'
            ],
            'lunch': [
                r'\blunch\b', r'\blunchträff\b', r'\blunchmöte\b'
            ],
            'presentation': [
                r'\bpresentation\b', r'\bframställning\b', r'\bvisning\b'
            ],
            'training': [
                r'\butbildning\b', r'\bträning\b', r'\bkurs\b', r'\bworkshop\b'
            ],
            'social': [
                r'\bsocialt?\b', r'\bfest\b', r'\bmingel\b', r'\bträff\b'
            ],
            'personal': [
                r'\bprivat\b', r'\bpersonligt?\b', r'\bfamilj\b'
            ]
        }
    
    def parse_command(self, text: str) -> Optional[CalendarIntent]:
        """Huvudmetod för att analysera ett svenska kalender-kommando"""
        text = text.lower().strip()
        
        # Identifiera handlingstyp
        action, action_confidence = self._identify_action(text)
        if not action:
            return None
        
        # Extrahera entiteter
        entities = self._extract_entities(text)
        
        # Beräkna total confidence
        confidence = action_confidence * 0.7 + self._calculate_entity_confidence(entities) * 0.3
        
        return CalendarIntent(
            action=action,
            confidence=confidence,
            entities=entities,
            raw_text=text
        )
    
    def _identify_action(self, text: str) -> Tuple[Optional[str], float]:
        """Identifiera vilken kalender-handling som avses"""
        best_action = None
        best_confidence = 0.0
        
        for action, patterns in self.action_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    # Beräkna confidence baserat på matchens kvalitet
                    confidence = len(match.group(0)) / len(text)
                    confidence = min(confidence * 2, 1.0)  # Normalisera
                    
                    if confidence > best_confidence:
                        best_action = action
                        best_confidence = confidence
        
        return best_action, best_confidence
    
    def _extract_entities(self, text: str) -> Dict[str, Any]:
        """Extrahera entiteter som datum, tid, personer etc."""
        entities = {}
        
        # Extrahera datum
        date_info = self._extract_date(text)
        if date_info:
            entities['date'] = date_info
        
        # Extrahera tid
        time_info = self._extract_time(text)
        if time_info:
            entities['time'] = time_info
        
        # Extrahera event-typ
        event_type = self._extract_event_type(text)
        if event_type:
            entities['event_type'] = event_type
        
        # Extrahera deltagare/personer
        people = self._extract_people(text)
        if people:
            entities['people'] = people
        
        # Extrahera event-titel/ämne
        title = self._extract_title(text)
        if title:
            entities['title'] = title
        
        # Extrahera varaktighet
        duration = self._extract_duration(text)
        if duration:
            entities['duration'] = duration
        
        return entities
    
    def _extract_date(self, text: str) -> Optional[Dict[str, Any]]:
        """Extrahera datuminformation från text"""
        for pattern, date_type in self.date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return {
                    'type': date_type,
                    'raw': match.group(0),
                    'groups': match.groups() if match.groups() else []
                }
        return None
    
    def _extract_time(self, text: str) -> Optional[Dict[str, Any]]:
        """Extrahera tidsinformation från text"""
        for pattern, time_type in self.time_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return {
                    'type': time_type,
                    'raw': match.group(0),
                    'groups': match.groups() if match.groups() else []
                }
        return None
    
    def _extract_event_type(self, text: str) -> Optional[str]:
        """Extrahera typ av händelse"""
        for event_type, patterns in self.event_type_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return event_type
        return None
    
    def _extract_people(self, text: str) -> List[str]:
        """Extrahera personer/deltagare från text"""
        people = []
        
        # Leta efter "med [person]" mönster
        with_pattern = r'\bmed\s+(\w+(?:\s+\w+)*)'
        matches = re.findall(with_pattern, text, re.IGNORECASE)
        people.extend(matches)
        
        # Leta efter email-adresser
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        people.extend(emails)
        
        return people
    
    def _extract_title(self, text: str) -> Optional[str]:
        """Extrahera titel/ämne för händelsen"""
        # Leta efter mönster som "boka möte om [ämne]"
        title_patterns = [
            r'(?:möte|händelse)\s+om\s+(.+?)(?:\s+(?:med|på|kl|imorgon|idag)|\s*$)',
            r'(?:boka|skapa|lägg till)\s+(.+?)(?:\s+(?:med|på|kl|imorgon|idag)|\s*$)',
            r'"([^"]+)"',  # Text inom citattecken
            r'\'([^\']+)\''  # Text inom apostrofer
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                title = match.group(1).strip()
                # Filtrera bort vanliga ord som inte är titlar
                if len(title) > 2 and title not in ['ett', 'en', 'det', 'med', 'på']:
                    return title
        
        return None
    
    def _extract_duration(self, text: str) -> Optional[Dict[str, Any]]:
        """Extrahera varaktighet för händelsen"""
        for pattern, duration_type in self.time_patterns:
            if 'duration' in duration_type or 'hour' in duration_type:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    return {
                        'type': duration_type,
                        'raw': match.group(0),
                        'groups': match.groups() if match.groups() else []
                    }
        return None
    
    def _calculate_entity_confidence(self, entities: Dict[str, Any]) -> float:
        """Beräkna confidence baserat på antalet och kvaliteten av extraherade entiteter"""
        if not entities:
            return 0.0
        
        # Vikta olika entiteter
        weights = {
            'date': 0.3,
            'time': 0.3,
            'title': 0.2,
            'people': 0.1,
            'event_type': 0.05,
            'duration': 0.05
        }
        
        confidence = 0.0
        for entity_type, weight in weights.items():
            if entity_type in entities:
                confidence += weight
        
        return min(confidence, 1.0)

# Global instans för användning i voice_stream
swedish_calendar_nlu = SwedishCalendarNLU()