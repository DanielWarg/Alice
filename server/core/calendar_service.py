"""
Google Calendar service för att hantera Calendar API-operationer.
Används av tool_registry för att skapa, läsa, söka, uppdatera och ta bort kalenderhändelser.
"""

import os
import pickle
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

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
        """Parse Swedish date/time strings to datetime object"""
        # Replace Swedish day/month names with English
        swedish_replacements = {
            'måndag': 'monday', 'tisdag': 'tuesday', 'onsdag': 'wednesday',
            'torsdag': 'thursday', 'fredag': 'friday', 'lördag': 'saturday', 'söndag': 'sunday',
            'januari': 'january', 'februari': 'february', 'mars': 'march', 'april': 'april',
            'maj': 'may', 'juni': 'june', 'juli': 'july', 'augusti': 'august',
            'september': 'september', 'oktober': 'october', 'november': 'november', 'december': 'december',
            'imorgon': 'tomorrow', 'idag': 'today', 'igår': 'yesterday'
        }
        
        normalized_str = date_str.lower()
        for swedish, english in swedish_replacements.items():
            normalized_str = normalized_str.replace(swedish, english)
        
        # Handle relative dates
        if PYTZ_AVAILABLE:
            now = datetime.now(pytz.timezone(self.timezone))
        else:
            now = datetime.now()
        
        if 'tomorrow' in normalized_str or 'imorgon' in date_str.lower():
            base_date = now + timedelta(days=1)
        elif 'today' in normalized_str or 'idag' in date_str.lower():
            base_date = now
        elif 'yesterday' in normalized_str or 'igår' in date_str.lower():
            base_date = now - timedelta(days=1)
        else:
            base_date = now
        
        # Extract time if present (format: kl 14:00 or 14:00)
        import re
        time_match = re.search(r'(?:kl\s*)?(\d{1,2}):(\d{2})', normalized_str)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2))
            return base_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        return base_date.replace(hour=9, minute=0, second=0, microsecond=0)  # Default 9 AM
    
    def _format_datetime_for_api(self, dt: datetime) -> str:
        """Format datetime for Google Calendar API"""
        if dt.tzinfo is None and PYTZ_AVAILABLE:
            dt = pytz.timezone(self.timezone).localize(dt)
        return dt.isoformat()
    
    def create_event(self, title: str, start_time: str, end_time: str = None, 
                    description: str = None, attendees: List[str] = None) -> str:
        """Skapa en kalenderhändelse"""
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
            
            return f"Kalenderhändelse '{title}' skapad för {start_dt.strftime('%Y-%m-%d %H:%M')}"
            
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