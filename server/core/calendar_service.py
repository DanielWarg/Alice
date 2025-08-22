"""
Google Calendar service för att hantera Calendar API-operationer.
Används av tool_registry för att skapa, läsa, söka, uppdatera och ta bort kalenderhändelser.
"""

import os
import pickle
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

try:
    import pytz
    PYTZ_AVAILABLE = True
except ImportError:
    PYTZ_AVAILABLE = False

try:
    from googleapiclient.discovery import build
    from google_auth_oauthlib.flow import Flow
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    CALENDAR_AVAILABLE = True
except ImportError:
    CALENDAR_AVAILABLE = False

class CalendarService:
    def __init__(self):
        self.service = None
        self.credentials_path = os.path.join(os.path.dirname(__file__), '..', 'calendar_credentials.json')
        self.token_path = os.path.join(os.path.dirname(__file__), '..', 'calendar_token.pickle')
        self.timezone = 'Europe/Stockholm'  # Swedish timezone
        
        # Intelligent scheduling preferences
        self.working_hours = {'start': 8, 'end': 18}  # 08:00 - 18:00
        self.preferred_meeting_lengths = [30, 60, 90, 120]  # minutes
        self.buffer_minutes = 15  # Buffer between meetings
        
        # Swedish language patterns for enhanced parsing
        self.time_patterns = {
            'exact': r'(?:kl\s*)?(?P<hour>\d{1,2})[:\.](?P<minute>\d{2})',
            'hour_only': r'(?:kl\s*)?(?P<hour>\d{1,2})(?:\s*(?:på\s*)?(?:morgonen|förmiddagen|eftermiddagen|kvällen))?',
            'relative': r'(?:om\s*)?(?P<num>\d+)\s*(?P<unit>timmar?|minuter?)',
        }
        
        self.date_keywords = {
            'idag': 0, 'imorgon': 1, 'övermorgon': 2, 'igår': -1, 'förrgår': -2,
            'nästa vecka': 7, 'kommande vecka': 7, 'denna vecka': 0,
            'nästa månad': 30, 'kommande månad': 30, 'i morgon': 1,
            'imorn': 1, 'på fredag': None, 'på måndag': None, 'på tisdag': None,
            'på onsdag': None, 'på torsdag': None, 'på lördag': None, 'på söndag': None
        }
        
        # Utökade svenska uttryck för tider
        self.time_expressions = {
            'morgon': [(6, 0), (11, 59)], 'förmiddag': [(9, 0), (11, 59)],
            'eftermiddag': [(12, 0), (17, 59)], 'kväll': [(18, 0), (22, 0)],
            'natt': [(22, 1), (5, 59)], 'lunch': [(11, 30), (13, 30)],
            'frukost': [(7, 0), (9, 30)], 'middag': [(17, 0), (20, 0)]
        }
        
        # Synonymer för vanliga ord
        self.word_synonyms = {
            'möte': ['möte', 'träff', 'sammanträde', 'conference', 'meeting'],
            'tid': ['tid', 'appointment', 'besök', 'bokning'],
            'skapa': ['skapa', 'boka', 'lägg till', 'planera', 'schemalägg', 'sätt upp', 'arrangera', 'reservera'],
            'visa': ['visa', 'lista', 'kolla', 'se', 'titta på', 'granska'],
            'sök': ['sök', 'hitta', 'leta', 'leta reda på', 'finn']
        }
        
    def _get_credentials(self):
        """Hämta eller skapa Calendar API-inloggning"""
        creds = None
        
        # Ladda sparad token
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as token:
                creds = pickle.load(token)
        
        # Om inga giltiga credentials finns, be användaren logga in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_path):
                    return None
                    
                flow = Flow.from_client_secrets_file(
                    self.credentials_path,
                    scopes=['https://www.googleapis.com/auth/calendar']
                )
                flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
                
                auth_url, _ = flow.authorization_url(prompt='consent')
                print(f"Öppna denna URL för att autentisera Calendar: {auth_url}")
                code = input("Klistra in auktoriseringskoden: ")
                
                flow.fetch_token(code=code)
                creds = flow.credentials
            
            # Spara credentials för nästa gång
            with open(self.token_path, 'wb') as token:
                pickle.dump(creds, token)
        
        return creds
    
    def _initialize_service(self):
        """Initialisera Calendar service"""
        if not CALENDAR_AVAILABLE:
            return False
            
        if self.service:
            return True
            
        creds = self._get_credentials()
        if not creds:
            return False
            
        try:
            self.service = build('calendar', 'v3', credentials=creds)
            return True
        except Exception:
            return False
    
    def _parse_swedish_datetime(self, date_str: str) -> datetime:
        """Enhanced Swedish date/time parsing with better natural language support"""
        if PYTZ_AVAILABLE:
            now = datetime.now(pytz.timezone(self.timezone))
        else:
            now = datetime.now()
        
        normalized_str = date_str.lower().strip()
        
        # Handle relative date keywords
        base_date = now
        for keyword, days_offset in self.date_keywords.items():
            if keyword in normalized_str and days_offset is not None:
                base_date = now + timedelta(days=days_offset)
                break
        
        # Enhanced weekday parsing
        swedish_weekdays = {
            'måndag': 0, 'tisdag': 1, 'onsdag': 2, 'torsdag': 3,
            'fredag': 4, 'lördag': 5, 'söndag': 6
        }
        
        for day_name, day_num in swedish_weekdays.items():
            if day_name in normalized_str:
                days_ahead = day_num - now.weekday()
                if days_ahead <= 0:  # Target day is today or has passed this week
                    days_ahead += 7
                if 'nästa' in normalized_str or 'kommande' in normalized_str:
                    days_ahead += 7
                base_date = now + timedelta(days=days_ahead)
                break
        
        # Enhanced time parsing with Swedish expressions
        hour, minute = 9, 0  # Default time
        
        # Check for time expressions first (lunch, middag, etc.)
        time_set = False
        for expression, time_range in self.time_expressions.items():
            if expression in normalized_str:
                start_time = time_range[0]
                hour, minute = start_time[0], start_time[1]
                time_set = True
                break
        
        if not time_set:
            # Exact time pattern (kl 14:30 or 14:30)
            exact_match = re.search(self.time_patterns['exact'], normalized_str)
            if exact_match:
                hour = int(exact_match.group('hour'))
                minute = int(exact_match.group('minute'))
            else:
                # Hour only pattern with context
                hour_match = re.search(self.time_patterns['hour_only'], normalized_str)
                if hour_match:
                    hour = int(hour_match.group('hour'))
                    minute = 0
                    
                    # Adjust for context clues
                    if 'förmiddagen' in normalized_str and hour < 12:
                        pass  # Keep as is
                    elif 'eftermiddagen' in normalized_str and hour < 12:
                        hour += 12
                    elif 'kvällen' in normalized_str and hour < 12:
                        hour += 12
                    elif hour < 8:  # Assume afternoon if very early hour
                        hour += 12
        
        # Handle relative time ("om 2 timmar")
        relative_match = re.search(self.time_patterns['relative'], normalized_str)
        if relative_match:
            num = int(relative_match.group('num'))
            unit = relative_match.group('unit')
            if 'timmar' in unit:
                return now + timedelta(hours=num)
            elif 'minuter' in unit:
                return now + timedelta(minutes=num)
        
        return base_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    def _format_datetime_for_api(self, dt: datetime) -> str:
        """Format datetime for Google Calendar API"""
        if dt.tzinfo is None and PYTZ_AVAILABLE:
            dt = pytz.timezone(self.timezone).localize(dt)
        return dt.isoformat()
    
    def suggest_meeting_times(self, duration_minutes: int = 60, 
                            date_preference: str = None, 
                            max_suggestions: int = 5) -> List[Dict[str, Any]]:
        """Föreslå lämpliga mötestider baserat på befintlig kalender"""
        if not self._initialize_service():
            return []
        
        try:
            # Bestäm datum att söka på
            if date_preference:
                search_date = self._parse_swedish_datetime(date_preference)
            else:
                search_date = datetime.now(pytz.timezone(self.timezone) if PYTZ_AVAILABLE else None)
            
            # Hämta befintliga händelser för dagen
            time_min = search_date.replace(hour=0, minute=0, second=0, microsecond=0)
            time_max = time_min + timedelta(days=1)
            
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=time_min.isoformat(),
                timeMax=time_max.isoformat(),
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            busy_periods = []
            for event in events_result.get('items', []):
                start = event['start'].get('dateTime')
                end = event['end'].get('dateTime')
                if start and end:
                    busy_periods.append({
                        'start': datetime.fromisoformat(start.replace('Z', '+00:00')),
                        'end': datetime.fromisoformat(end.replace('Z', '+00:00'))
                    })
            
            # Hitta lediga tider
            suggestions = []
            current_time = search_date.replace(
                hour=self.working_hours['start'], 
                minute=0, 
                second=0, 
                microsecond=0
            )
            end_of_day = search_date.replace(
                hour=self.working_hours['end'], 
                minute=0, 
                second=0, 
                microsecond=0
            )
            
            while current_time + timedelta(minutes=duration_minutes) <= end_of_day:
                proposed_end = current_time + timedelta(minutes=duration_minutes)
                
                # Kontrollera konflikt
                has_conflict = False
                for busy in busy_periods:
                    if (current_time < busy['end'] and proposed_end > busy['start']):
                        has_conflict = True
                        # Hoppa till efter den upptagna perioden
                        current_time = busy['end'] + timedelta(minutes=self.buffer_minutes)
                        break
                
                if not has_conflict:
                    suggestions.append({
                        'start_time': current_time,
                        'end_time': proposed_end,
                        'formatted': f"{current_time.strftime('%H:%M')} - {proposed_end.strftime('%H:%M')}",
                        'confidence': self._calculate_time_confidence(current_time)
                    })
                    
                    if len(suggestions) >= max_suggestions:
                        break
                    
                    current_time += timedelta(minutes=30)  # Try next 30-minute slot
                else:
                    continue
            
            return sorted(suggestions, key=lambda x: x['confidence'], reverse=True)
            
        except Exception as e:
            return []
    
    def _calculate_time_confidence(self, time: datetime) -> float:
        """Beräkna konfidenspoäng för en föreslagen tid"""
        hour = time.hour
        
        # Fördelning baserad på vanliga mötestider
        if 9 <= hour <= 11:  # Förmiddag - bra
            return 0.9
        elif 13 <= hour <= 15:  # Tidig eftermiddag - mycket bra
            return 1.0
        elif 8 <= hour <= 17:  # Arbetstid - okej
            return 0.7
        elif hour == 12:  # Lunchtid - mindre bra
            return 0.4
        else:  # Utanför arbetstid
            return 0.2
    
    def check_conflicts(self, start_time: str, end_time: str = None, 
                       exclude_event_id: str = None) -> Dict[str, Any]:
        """Kontrollera om en föreslagen tid har konflikter"""
        if not self._initialize_service():
            return {'has_conflict': True, 'message': 'Calendar-tjänst inte tillgänglig'}
        
        try:
            start_dt = self._parse_swedish_datetime(start_time)
            if end_time:
                end_dt = self._parse_swedish_datetime(end_time)
            else:
                end_dt = start_dt + timedelta(hours=1)
            
            # Hämta händelser i den föreslagna tidsperioden
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=start_dt.isoformat(),
                timeMax=end_dt.isoformat(),
                singleEvents=True
            ).execute()
            
            conflicts = []
            for event in events_result.get('items', []):
                if exclude_event_id and event.get('id') == exclude_event_id:
                    continue
                    
                event_start = event['start'].get('dateTime', event['start'].get('date'))
                event_end = event['end'].get('dateTime', event['end'].get('date'))
                
                if event_start and event_end:
                    conflicts.append({
                        'title': event.get('summary', 'Utan titel'),
                        'start': event_start,
                        'end': event_end,
                        'id': event.get('id')
                    })
            
            if conflicts:
                # Föreslå alternativa tider
                suggestions = self.suggest_meeting_times(
                    duration_minutes=int((end_dt - start_dt).total_seconds() / 60),
                    date_preference=start_time
                )
                
                return {
                    'has_conflict': True,
                    'conflicts': conflicts,
                    'message': f'Konflikt upptäckt med {len(conflicts)} befintlig(a) händelse(r)',
                    'suggestions': suggestions[:3]  # Top 3 suggestions
                }
            
            return {
                'has_conflict': False,
                'message': 'Ingen konflikt upptäckt',
                'suggestions': []
            }
            
        except Exception as e:
            return {
                'has_conflict': True,
                'message': f'Fel vid konfliktkolning: {str(e)}',
                'suggestions': []
            }
    
    def create_event(self, title: str, start_time: str, end_time: str = None, 
                    description: str = None, attendees: List[str] = None, 
                    check_conflicts_first: bool = True) -> str:
        """Skapa en kalenderhändelse med intelligent konfliktkolning"""
        if not self._initialize_service():
            return "Calendar-tjänst inte tillgänglig. Kontrollera credentials och internetanslutning."
        
        try:
            # Parse start time
            start_dt = self._parse_swedish_datetime(start_time)
            
            # Parse or calculate end time
            if end_time:
                end_dt = self._parse_swedish_datetime(end_time)
            else:
                end_dt = start_dt + timedelta(hours=1)  # Default 1 hour duration
            
            # Kontrollera konflikter först om önskat
            if check_conflicts_first:
                conflict_check = self.check_conflicts(
                    start_time, 
                    end_time or (start_dt + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M')
                )
                
                if conflict_check['has_conflict']:
                    conflicts_info = f"VARNING: {conflict_check['message']}\n"
                    
                    if conflict_check.get('suggestions'):
                        conflicts_info += "Föreslagna alternativa tider:\n"
                        for i, suggestion in enumerate(conflict_check['suggestions'], 1):
                            conflicts_info += f"{i}. {suggestion['formatted']}\n"
                    
                    conflicts_info += "\nVill du fortfarande skapa händelsen? (Skapar ändå...)"
                    # I en verklig implementation skulle vi kunna returnera detta för användarbekräftelse
            
            # Prepare event data
            event = {
                'summary': title,
                'start': {
                    'dateTime': self._format_datetime_for_api(start_dt),
                    'timeZone': self.timezone,
                },
                'end': {
                    'dateTime': self._format_datetime_for_api(end_dt),
                    'timeZone': self.timezone,
                },
            }
            
            if description:
                event['description'] = description
            
            if attendees:
                event['attendees'] = [{'email': email} for email in attendees]
            
            # Create the event
            result = self.service.events().insert(calendarId='primary', body=event).execute()
            
            result_msg = f"Kalenderhändelse '{title}' skapad för {start_dt.strftime('%Y-%m-%d %H:%M')}"
            
            # Lägg till konfliktinformation om det finns
            if check_conflicts_first:
                conflict_check = self.check_conflicts(
                    start_time, 
                    end_time or (start_dt + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M'),
                    exclude_event_id=result.get('id')
                )
                if conflict_check['has_conflict']:
                    result_msg += f"\n⚠️ {conflict_check['message']}"
            
            return result_msg
            
        except Exception as e:
            return f"Fel vid skapande av kalenderhändelse: {str(e)}"
    
    def list_events(self, max_results: int = 10, time_min: str = None, time_max: str = None) -> str:
        """Lista kommande kalenderhändelser"""
        if not self._initialize_service():
            return "Calendar-tjänst inte tillgänglig. Kontrollera credentials och internetanslutning."
        
        try:
            # Set default time range
            if PYTZ_AVAILABLE:
                now = datetime.now(pytz.timezone(self.timezone))
            else:
                now = datetime.now()
            if not time_min:
                time_min = now.isoformat()
            else:
                time_min_dt = self._parse_swedish_datetime(time_min)
                time_min = self._format_datetime_for_api(time_min_dt)
            
            if time_max:
                time_max_dt = self._parse_swedish_datetime(time_max)
                time_max = self._format_datetime_for_api(time_max_dt)
            
            # Fetch events
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            if not events:
                return "Inga kommande händelser hittades."
            
            event_summaries = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                if 'T' in start:  # datetime format
                    start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                    start_str = start_dt.strftime('%Y-%m-%d %H:%M')
                else:  # date format
                    start_str = start
                
                summary = event.get('summary', 'Ingen titel')
                event_summaries.append(f"• {summary}\n  Tid: {start_str}")
            
            return f"Kommande {len(event_summaries)} händelser:\n\n" + "\n\n".join(event_summaries)
            
        except Exception as e:
            return f"Fel vid hämtning av kalenderhändelser: {str(e)}"
    
    def search_events(self, query: str, max_results: int = 20) -> str:
        """Sök kalenderhändelser"""
        if not self._initialize_service():
            return "Calendar-tjänst inte tillgänglig. Kontrollera credentials och internetanslutning."
        
        try:
            # Search events
            events_result = self.service.events().list(
                calendarId='primary',
                q=query,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            if not events:
                return f"Inga händelser hittades för sökningen: '{query}'"
            
            event_summaries = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                if 'T' in start:
                    start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                    start_str = start_dt.strftime('%Y-%m-%d %H:%M')
                else:
                    start_str = start
                
                summary = event.get('summary', 'Ingen titel')
                event_id = event.get('id', '')
                event_summaries.append(f"• {summary}\n  Tid: {start_str}\n  ID: {event_id}")
            
            return f"Hittade {len(event_summaries)} händelser för '{query}':\n\n" + "\n\n".join(event_summaries)
            
        except Exception as e:
            return f"Fel vid sökning av kalenderhändelser: {str(e)}"
    
    def delete_event(self, event_id: str) -> str:
        """Ta bort en kalenderhändelse"""
        if not self._initialize_service():
            return "Calendar-tjänst inte tillgänglig. Kontrollera credentials och internetanslutning."
        
        try:
            # First, get the event to show what we're deleting
            event = self.service.events().get(calendarId='primary', eventId=event_id).execute()
            event_title = event.get('summary', 'Okänd händelse')
            
            # Delete the event
            self.service.events().delete(calendarId='primary', eventId=event_id).execute()
            
            return f"Kalenderhändelse '{event_title}' borttagen"
            
        except Exception as e:
            return f"Fel vid borttagning av kalenderhändelse: {str(e)}"
    
    def update_event(self, event_id: str, title: str = None, start_time: str = None, 
                    end_time: str = None, description: str = None) -> str:
        """Uppdatera en kalenderhändelse"""
        if not self._initialize_service():
            return "Calendar-tjänst inte tillgänglig. Kontrollera credentials och internetanslutning."
        
        try:
            # Get existing event
            event = self.service.events().get(calendarId='primary', eventId=event_id).execute()
            
            # Update fields if provided
            if title:
                event['summary'] = title
            
            if start_time:
                start_dt = self._parse_swedish_datetime(start_time)
                event['start'] = {
                    'dateTime': self._format_datetime_for_api(start_dt),
                    'timeZone': self.timezone,
                }
            
            if end_time:
                end_dt = self._parse_swedish_datetime(end_time)
                event['end'] = {
                    'dateTime': self._format_datetime_for_api(end_dt),
                    'timeZone': self.timezone,
                }
            elif start_time and not end_time:
                # If only start time is updated, adjust end time accordingly
                start_dt = self._parse_swedish_datetime(start_time)
                end_dt = start_dt + timedelta(hours=1)
                event['end'] = {
                    'dateTime': self._format_datetime_for_api(end_dt),
                    'timeZone': self.timezone,
                }
            
            if description is not None:
                event['description'] = description
            
            # Update the event
            updated_event = self.service.events().update(
                calendarId='primary', 
                eventId=event_id, 
                body=event
            ).execute()
            
            event_title = updated_event.get('summary', 'Okänd händelse')
            return f"Kalenderhändelse '{event_title}' uppdaterad"
            
        except Exception as e:
            return f"Fel vid uppdatering av kalenderhändelse: {str(e)}"

# Global instans
calendar_service = CalendarService()