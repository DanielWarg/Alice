"""
Svenska naturlig språkanalys för datum, tider och event-detaljer.
Konverterar svenska språkuttryck till konkreta datumtider och event-information.
"""

import re
from datetime import datetime, timedelta, time
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
import pytz

@dataclass
class ParsedDateTime:
    """Struktur för parsad datumtid"""
    datetime: datetime
    confidence: float
    is_relative: bool
    original_text: str

@dataclass
class ParsedEvent:
    """Struktur för parsad event-information"""
    title: Optional[str] = None
    start_datetime: Optional[ParsedDateTime] = None
    end_datetime: Optional[ParsedDateTime] = None
    duration_minutes: Optional[int] = None
    attendees: list = None
    event_type: Optional[str] = None
    description: Optional[str] = None

class SwedishDateTimeParser:
    """Parser för svenska datum- och tidsuttryck"""
    
    def __init__(self, timezone: str = 'Europe/Stockholm'):
        self.timezone = pytz.timezone(timezone)
        self.swedish_months = {
            'januari': 1, 'februari': 2, 'mars': 3, 'april': 4,
            'maj': 5, 'juni': 6, 'juli': 7, 'augusti': 8,
            'september': 9, 'oktober': 10, 'november': 11, 'december': 12
        }
        self.swedish_weekdays = {
            'måndag': 0, 'tisdag': 1, 'onsdag': 2, 'torsdag': 3,
            'fredag': 4, 'lördag': 5, 'söndag': 6
        }
        
    def now(self) -> datetime:
        """Få nuvarande tid i korrekt tidszon"""
        return datetime.now(self.timezone)
    
    def parse_date_time(self, date_entity: Dict[str, Any], time_entity: Dict[str, Any] = None) -> Optional[ParsedDateTime]:
        """Kombinera datum- och tidsentiteter till konkret datetime"""
        base_date = self._parse_date_entity(date_entity)
        if not base_date:
            return None
            
        if time_entity:
            parsed_time = self._parse_time_entity(time_entity)
            if parsed_time:
                base_date = base_date.replace(
                    hour=parsed_time.hour,
                    minute=parsed_time.minute,
                    second=0,
                    microsecond=0
                )
        else:
            # Standardtid om ingen tid specificerad
            base_date = base_date.replace(hour=9, minute=0, second=0, microsecond=0)
        
        # Säkerställ rätt tidszon
        if base_date.tzinfo is None:
            base_date = self.timezone.localize(base_date)
        
        return ParsedDateTime(
            datetime=base_date,
            confidence=0.8,
            is_relative=date_entity.get('type', '') in ('today', 'tomorrow', 'yesterday', 'day_after_tomorrow', 'day_before_yesterday') or date_entity.get('type', '') in self.swedish_weekdays,
            original_text=f"{date_entity.get('raw', '')} {time_entity.get('raw', '') if time_entity else ''}".strip()
        )
    
    def _parse_date_entity(self, date_entity: Dict[str, Any]) -> Optional[datetime]:
        """Parse datum-entitet till datetime"""
        if not date_entity or date_entity.get('type') is None:
            return None
            
        date_type = date_entity.get('type', '')
        now = self.now()
        
        if date_type == 'today':
            return now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        elif date_type == 'tomorrow':
            return (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        
        elif date_type == 'yesterday':
            return (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        
        elif date_type == 'day_after_tomorrow':
            return (now + timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0)
        
        elif date_type == 'day_before_yesterday':
            return (now - timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0)
        
        elif date_type.replace('på ', '') in self.swedish_weekdays:
            weekday_name = date_type.replace('på ', '')
            return self._get_next_weekday(now, self.swedish_weekdays[weekday_name])
        
        elif date_type == 'next_week':
            # Måndag nästa vecka
            return self._get_next_weekday(now, 0) + timedelta(days=7)
        
        elif date_type == 'this_week':
            # Denna måndag
            return self._get_this_weekday(now, 0)
        
        elif date_type == 'last_week':
            # Förra måndag
            return self._get_this_weekday(now, 0) - timedelta(days=7)
        
        elif date_type == 'date_numeric':
            return self._parse_numeric_date(date_entity)
        
        elif date_type == 'date_written':
            return self._parse_written_date(date_entity)
        
        return None
    
    def _parse_time_entity(self, time_entity: Dict[str, Any]) -> Optional[time]:
        """Parse tids-entitet till time-objekt"""
        time_type = time_entity.get('type', '')
        groups = time_entity.get('groups', [])
        
        if time_type in ['exact_time', 'exact_time_word']:
            if len(groups) >= 2:
                try:
                    hour = int(groups[0])
                    minute = int(groups[1])
                    if 0 <= hour <= 23 and 0 <= minute <= 59:
                        return time(hour, minute)
                except (ValueError, TypeError):
                    return None
        
        elif time_type == 'half_past':
            if groups:
                try:
                    hour = int(groups[0]) - 1 + 12  # "halv tre" = 2:30 PM (14:30) - "halv" means 30 minutes before the hour
                    if hour > 23:
                        hour -= 12  # Hantera morgontider
                    if 0 <= hour <= 23:
                        return time(hour, 30)
                except (ValueError, TypeError):
                    return None
        
        elif time_type == 'quarter_past':
            if groups:
                try:
                    hour = int(groups[0]) + 12  # "kvart över två" = 14:15
                    if hour > 23:
                        hour -= 12
                    if 0 <= hour <= 23:
                        return time(hour, 15)
                except (ValueError, TypeError):
                    return None
        
        elif time_type == 'quarter_to':
            if groups:
                try:
                    hour = int(groups[0]) + 12 - 1  # "kvart i tre" = 14:45
                    if hour > 23:
                        hour -= 12
                    if 0 <= hour <= 23:
                        return time(hour, 45)
                except (ValueError, TypeError):
                    return None
        
        elif time_type == 'approximate_time':
            if groups:
                try:
                    hour = int(groups[0])
                    if 0 <= hour <= 23:
                        return time(hour, 0)
                except (ValueError, TypeError):
                    return None
        
        elif time_type == 'morning':
            return time(9, 0)  # 09:00
        
        elif time_type == 'forenoon':
            return time(10, 0)  # 10:00
        
        elif time_type == 'lunch':
            return time(12, 0)  # 12:00
        
        elif time_type == 'afternoon':
            return time(14, 0)  # 14:00
        
        elif time_type == 'evening':
            return time(18, 0)  # 18:00
        
        elif time_type == 'night':
            return time(20, 0)  # 20:00
        
        return None
    
    def _get_next_weekday(self, from_date: datetime, weekday: int) -> datetime:
        """Få nästa förekomst av veckodagen (0=måndag, 6=söndag)"""
        days_ahead = weekday - from_date.weekday()
        if days_ahead <= 0:  # Måldagen har redan varit denna vecka
            days_ahead += 7
        return (from_date + timedelta(days=days_ahead)).replace(hour=0, minute=0, second=0, microsecond=0)
    
    def _get_this_weekday(self, from_date: datetime, weekday: int) -> datetime:
        """Få denna veckas förekomst av veckodagen"""
        days_diff = weekday - from_date.weekday()
        return (from_date + timedelta(days=days_diff)).replace(hour=0, minute=0, second=0, microsecond=0)
    
    def _parse_numeric_date(self, date_entity: Dict[str, Any]) -> Optional[datetime]:
        """Parse numeriskt datum (DD/MM eller DD/MM/YYYY)"""
        groups = date_entity.get('groups', [])
        if len(groups) >= 2:
            day = int(groups[0])
            month = int(groups[1])
            year = int(groups[2]) if len(groups) >= 3 and groups[2] else self.now().year
            
            # Hantera tvåsiffriga år
            if year < 100:
                year += 2000
            
            try:
                return datetime(year, month, day)
            except ValueError:
                return None
        return None
    
    def _parse_written_date(self, date_entity: Dict[str, Any]) -> Optional[datetime]:
        """Parse skrivet datum (t.ex. "15 mars" eller "15 mars 2024")"""
        groups = date_entity.get('groups', [])
        if len(groups) >= 2:
            day = int(groups[0])
            month_name = groups[1].lower()
            year = int(groups[2]) if len(groups) >= 3 and groups[2] else self.now().year
            
            month = self.swedish_months.get(month_name)
            if month:
                try:
                    return datetime(year, month, day)
                except ValueError:
                    return None
        return None
    
    def parse_duration(self, duration_entity: Dict[str, Any]) -> Optional[int]:
        """Parse varaktighet till minuter"""
        duration_type = duration_entity.get('type', '')
        groups = duration_entity.get('groups', [])
        
        if duration_type == 'duration_hours' and groups:
            return int(groups[0]) * 60
        
        elif duration_type == 'duration_minutes' and groups:
            return int(groups[0])
        
        elif duration_type == 'one_hour':
            return 60
        
        elif duration_type == 'half_hour':
            return 30
        
        return None

class SwedishEventParser:
    """Parser för att skapa kompletta event-objekt från svenska kommandon"""
    
    def __init__(self):
        self.datetime_parser = SwedishDateTimeParser()
        
    def parse_event_from_entities(self, action: str, entities: Dict[str, Any], raw_text: str) -> ParsedEvent:
        """Skapa ett ParsedEvent från extraherade entiteter"""
        event = ParsedEvent()
        
        # Parse titel
        event.title = entities.get('title') or self._generate_default_title(action, entities, raw_text)
        
        # Parse start-tid
        if 'date' in entities:
            start_dt = self.datetime_parser.parse_date_time(
                entities['date'], 
                entities.get('time')
            )
            event.start_datetime = start_dt
        
        # Parse varaktighet och beräkna slut-tid
        if 'duration' in entities:
            duration_minutes = self.datetime_parser.parse_duration(entities['duration'])
            if duration_minutes:
                event.duration_minutes = duration_minutes
                if event.start_datetime:
                    end_dt = event.start_datetime.datetime + timedelta(minutes=duration_minutes)
                    event.end_datetime = ParsedDateTime(
                        datetime=end_dt,
                        confidence=event.start_datetime.confidence,
                        is_relative=event.start_datetime.is_relative,
                        original_text=entities['duration'].get('raw', '')
                    )
        
        # Standardvaraktighet om ingen angiven
        if not event.end_datetime and event.start_datetime:
            default_duration = self._get_default_duration(entities.get('event_type'))
            end_dt = event.start_datetime.datetime + timedelta(minutes=default_duration)
            event.end_datetime = ParsedDateTime(
                datetime=end_dt,
                confidence=event.start_datetime.confidence * 0.8,  # Lägre confidence för estimerad tid
                is_relative=event.start_datetime.is_relative,
                original_text='(standardvaraktighet)'
            )
            event.duration_minutes = default_duration
        
        # Parse deltagare
        if 'people' in entities:
            event.attendees = entities['people']
        
        # Parse event-typ
        if 'event_type' in entities:
            event.event_type = entities['event_type']
        
        # Generera beskrivning
        event.description = self._generate_description(action, entities, raw_text)
        
        return event
    
    def _generate_default_title(self, action: str, entities: Dict[str, Any], raw_text: str) -> str:
        """Generera en standardtitel baserat på kommandot"""
        event_type = entities.get('event_type', 'möte')
        people = entities.get('people', [])
        
        if people:
            if len(people) == 1:
                return f"{event_type.capitalize()} med {people[0]}"
            else:
                return f"{event_type.capitalize()} med {', '.join(people[:-1])} och {people[-1]}"
        
        # Försök extrahera titel från raw text
        title_indicators = ['om ', 'angående ', 'gällande ']
        for indicator in title_indicators:
            if indicator in raw_text.lower():
                parts = raw_text.lower().split(indicator, 1)
                if len(parts) > 1:
                    potential_title = parts[1].split()[0:3]  # Ta första 3 orden
                    return f"{event_type.capitalize()} om {' '.join(potential_title)}"
        
        return event_type.capitalize()
    
    def _get_default_duration(self, event_type: Optional[str]) -> int:
        """Få standardvaraktighet baserat på event-typ (i minuter)"""
        durations = {
            'meeting': 60,
            'lunch': 60,
            'presentation': 45,
            'training': 120,
            'social': 90,
            'personal': 60
        }
        return durations.get(event_type, 60)  # Standard 60 minuter
    
    def _generate_description(self, action: str, entities: Dict[str, Any], raw_text: str) -> str:
        """Generera en beskrivning av eventet"""
        parts = [f"Skapad via röstkommando: '{raw_text}'"]
        
        if entities.get('event_type'):
            parts.append(f"Typ: {entities['event_type']}")
        
        if entities.get('people'):
            parts.append(f"Deltagare: {', '.join(entities['people'])}")
        
        return " | ".join(parts)

# Global instanser
swedish_datetime_parser = SwedishDateTimeParser()
swedish_event_parser = SwedishEventParser()