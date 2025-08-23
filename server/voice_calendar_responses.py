"""
Svenska språk-responses för kalender-feedback integrerat med Alice's personlighet.
Genererar naturliga, hjälpsamma svar på svenska för kalenderoperationer.
"""

import random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import asdict

class AliceCalendarResponses:
    """Alice's svenska responses för kalender-kommandon"""
    
    def __init__(self):
        self.personality_traits = {
            'helpful': True,
            'efficient': True,
            'warm': True,
            'confident': True,
            'swedish': True
        }
        
    def generate_response(self, result: Dict[str, Any]) -> str:
        """
        Generera en naturlig svensk response baserat på kalender-resultat
        
        Args:
            result: Resultat från calendar_voice_processor
            
        Returns:
            Naturlig svensk response-text
        """
        if not result.get('success', False):
            return self._generate_error_response(result)
        
        action = result.get('action', 'unknown')
        
        if action == 'create':
            return self._generate_create_response(result)
        elif action == 'list':
            return self._generate_list_response(result)
        elif action == 'search':
            return self._generate_search_response(result)
        elif action == 'delete':
            return self._generate_delete_response(result)
        elif action == 'update':
            return self._generate_update_response(result)
        else:
            return self._generate_generic_success_response(result)
    
    def _generate_error_response(self, result: Dict[str, Any]) -> str:
        """Generera felmeddelanden med Alice's personlighet"""
        message = result.get('message', 'Något gick fel')
        confidence = result.get('confidence', 0.0)
        
        # Personlighetsbaserade fel-responses
        empathy_responses = [
            "Hmm, det blev lite krångligt där.",
            "Aj då, det där gick inte som planerat.",
            "Oj, jag förstod inte riktigt det där.",
            "Det blev inte som jag tänkte mig."
        ]
        
        help_responses = [
            "Låt oss försöka igen på ett annat sätt.",
            "Kan du försöka säga det lite annorlunda?",
            "Jag hjälper dig att få det här att fungera.",
            "Vi fixar det här tillsammans."
        ]
        
        if confidence > 0.3:
            # Osäkerhet snarare än fel
            uncertainty_responses = [
                f"Jag är inte helt säker på vad du menar. {random.choice(help_responses)}",
                f"Det låter som ett kalenderproblem, men jag behöver mer info. {random.choice(help_responses)}",
                f"Jag tror jag förstår dig, men vill vara säker. {random.choice(help_responses)}"
            ]
            return random.choice(uncertainty_responses)
        
        # Klart fel
        return f"{random.choice(empathy_responses)} {message} {random.choice(help_responses)}"
    
    def _generate_create_response(self, result: Dict[str, Any]) -> str:
        """Generera response för skapade kalenderhändelser"""
        message = result.get('message', '')
        event = result.get('event', {})
        
        # Entusiastiska bekräftelser
        enthusiasm = [
            "Perfekt! ",
            "Klart det! ",
            "Fixat! ",
            "Där har du det! ",
            "Bra jobbat! "
        ]
        
        # Extrahera event-detaljer för personlig touch
        title = event.get('title', 'Mötet')
        start_dt = None
        if event.get('start_datetime', {}).get('datetime'):
            # Hantera datetime-string eller datetime-objekt
            start_dt_str = event['start_datetime']['datetime']
            if isinstance(start_dt_str, str):
                try:
                    start_dt = datetime.fromisoformat(start_dt_str.replace('Z', '+00:00'))
                except ValueError as e:
                    logger.warning(f"Failed to parse datetime string '{start_dt_str}': {e}")
                    pass
            else:
                start_dt = start_dt_str
        
        if start_dt:
            time_info = self._format_swedish_datetime(start_dt)
            confirmation_responses = [
                f"{random.choice(enthusiasm)}Jag har skapat '{title}' {time_info} i din kalender.",
                f"{random.choice(enthusiasm)}'{title}' är nu inbokat {time_info}.",
                f"{random.choice(enthusiasm)}Kalendern uppdaterad! '{title}' {time_info}.",
                f"{random.choice(enthusiasm)}Mötet '{title}' ligger nu {time_info} i din kalender."
            ]
        else:
            confirmation_responses = [
                f"{random.choice(enthusiasm)}Jag har skapat '{title}' i din kalender.",
                f"{random.choice(enthusiasm)}'{title}' är nu inlagt i kalendern.",
                f"{random.choice(enthusiasm)}Klar! '{title}' finns nu i din kalender."
            ]
        
        response = random.choice(confirmation_responses)
        
        # Lägg till extra hjälpsamhet om det är nära i tiden
        if start_dt and start_dt < datetime.now() + timedelta(hours=2):
            helpful_additions = [
                " Du har inte så lång tid på dig!",
                " Det är snart dags!",
                " Påminner om det när det närmar sig.",
                " Bra att vi fick in det i tid!"
            ]
            response += random.choice(helpful_additions)
        
        return response
    
    def _generate_list_response(self, result: Dict[str, Any]) -> str:
        """Generera response för kalenderlistning"""
        message = result.get('message', '')
        
        # Kontrollera om det finns händelser
        if 'inga' in message.lower() or 'no' in message.lower():
            empty_responses = [
                "Du har inga kommande möten just nu. Perfekt tillfälle att planera lite!",
                "Kalendern ser tom ut. Vill du boka in något?",
                "Inga möten på schemat. Du har fri tid!",
                "Tomt på agendan - njut av den lediga tiden!"
            ]
            return random.choice(empty_responses)
        
        # Det finns händelser
        intro_responses = [
            "Här kommer din kalender:",
            "Så här ser det ut på schemat:",
            "Det här har du kommande:",
            "Dina nästa möten:"
        ]
        
        # Lägg till personlig kommentar beroende på antal möten
        if 'händelser:' in message:
            # Räkna antal (ungefärligt)
            lines = message.split('\\n')
            event_lines = [line for line in lines if line.strip().startswith('•')]
            num_events = len(event_lines)
            
            if num_events > 5:
                comments = [
                    " Du har en ganska full kalender!",
                    " Många möten på gång!",
                    " Busy times ahead!",
                    " Mycket att stöta på!"
                ]
            elif num_events > 2:
                comments = [
                    " En hel del på schemat.",
                    " Lagom mycket att göra.",
                    " Några viktiga punkter.",
                    " Bra balans i kalendern."
                ]
            else:
                comments = [
                    " Inte så mycket på schemat.",
                    " Ganska lugnt framöver.",
                    " Bara några punkter.",
                    " Lagom med aktiviteter."
                ]
            
            intro = random.choice(intro_responses) + random.choice(comments)
        else:
            intro = random.choice(intro_responses)
        
        return f"{intro}\\n\\n{message}"
    
    def _generate_search_response(self, result: Dict[str, Any]) -> str:
        """Generera response för kalendersökning"""
        message = result.get('message', '')
        search_query = result.get('search_query', '')
        
        if 'inga' in message.lower() or 'hittades' not in message.lower():
            # Inga resultat
            not_found_responses = [
                f"Jag hittade inget möte som matchar '{search_query}'. Kanske är det inbokat under ett annat namn?",
                f"Hmm, inga träffar för '{search_query}'. Vill du att jag söker efter något annat?",
                f"Kunde inte hitta '{search_query}' i kalendern. Är du säker på namnet?",
                f"Inga möten hittades för '{search_query}'. Försök med ett annat sökord?"
            ]
            return random.choice(not_found_responses)
        
        # Resultat hittades
        found_responses = [
            f"Här är vad jag hittade för '{search_query}':",
            f"Jag hittade dessa möten som matchar '{search_query}':",
            f"Bingo! Här är träffarna för '{search_query}':",
            f"Här kommer sökresultatet för '{search_query}':"
        ]
        
        return f"{random.choice(found_responses)}\\n\\n{message}"
    
    def _generate_delete_response(self, result: Dict[str, Any]) -> str:
        """Generera response för borttagning"""
        message = result.get('message', '')
        
        # Eftersom delete ofta kräver bekräftelse
        cautious_responses = [
            "Okej, för att ta bort möten behöver jag vara extra försiktig. " + message,
            "Borttagning av möten är en känslig operation. " + message,
            "Jag vill vara säker innan jag tar bort något. " + message
        ]
        
        return random.choice(cautious_responses)
    
    def _generate_update_response(self, result: Dict[str, Any]) -> str:
        """Generera response för uppdatering"""
        message = result.get('message', '')
        
        # Uppdateringar kräver också försiktighet
        careful_responses = [
            "För att ändra möten gör jag det steg för steg. " + message,
            "Bra att du vill uppdatera kalendern! " + message,
            "Ändringar av möten kräver lite extra precision. " + message
        ]
        
        return random.choice(careful_responses)
    
    def _generate_generic_success_response(self, result: Dict[str, Any]) -> str:
        """Generera generisk framgångsresponse"""
        message = result.get('message', '')
        
        success_responses = [
            "Klart! " + message,
            "Fixat! " + message,
            "Där har du det! " + message,
            "Perfekt! " + message
        ]
        
        return random.choice(success_responses)
    
    def _format_swedish_datetime(self, dt: datetime) -> str:
        """Formatera datetime till naturlig svenska"""
        now = datetime.now()
        
        # Kontrollera om det är idag, imorgon etc.
        if dt.date() == now.date():
            return f"idag kl {dt.strftime('%H:%M')}"
        elif dt.date() == (now + timedelta(days=1)).date():
            return f"imorgon kl {dt.strftime('%H:%M')}"
        elif dt.date() == (now - timedelta(days=1)).date():
            return f"igår kl {dt.strftime('%H:%M')}"
        elif dt.date() < now.date() + timedelta(days=7):
            # Inom en vecka - använd veckodagsnamn
            weekdays = ['måndag', 'tisdag', 'onsdag', 'torsdag', 'fredag', 'lördag', 'söndag']
            weekday = weekdays[dt.weekday()]
            return f"på {weekday} kl {dt.strftime('%H:%M')}"
        else:
            # Längre bort - använd datum
            return f"den {dt.strftime('%d/%m')} kl {dt.strftime('%H:%M')}"
    
    def generate_confirmation_request(self, event_details: Dict[str, Any]) -> str:
        """Generera bekräftelsefråga för oklara kommandon"""
        title = event_details.get('title', 'mötet')
        
        confirmation_questions = [
            f"Vill du att jag bokar in '{title}'? Säg 'ja' för att bekräfta.",
            f"Ska jag skapa '{title}' i kalendern? Bekräfta med 'ja'.",
            f"Är det okej om jag lägger in '{title}'? Svara 'ja' för att fortsätta.",
            f"Stämmer det att du vill boka '{title}'? Säg 'ja' om det är rätt."
        ]
        
        return random.choice(confirmation_questions)
    
    def generate_clarification_request(self, missing_info: List[str]) -> str:
        """Generera fråga för att få mer information"""
        if 'time' in missing_info and 'date' in missing_info:
            return "När ska mötet vara? Säg datum och tid, till exempel 'imorgon kl 14'."
        elif 'time' in missing_info:
            return "Vilken tid ska mötet vara? Till exempel 'kl 14' eller 'på eftermiddagen'."
        elif 'date' in missing_info:
            return "Vilken dag ska mötet vara? Till exempel 'imorgon' eller 'på måndag'."
        elif 'title' in missing_info:
            return "Vad ska mötet handla om? Ge det en titel."
        else:
            return "Jag behöver lite mer information för att boka mötet."
    
    def generate_help_response(self) -> str:
        """Generera hjälpresponse för kalender-kommandon"""
        help_text = '''Jag kan hjälpa dig med kalendern på svenska! Här är några exempel:

📅 **Skapa möten:**
• "Boka möte imorgon kl 14"
• "Schemalägg lunch med Anna på fredag"
• "Lägg till presentation nästa måndag kl 10"

📋 **Se kalendern:**
• "Vad har jag på schemat idag?"
• "Visa nästa veckas kalender"
• "Vilka möten har jag imorgon?"

🔍 **Sök möten:**
• "Hitta mötet med Stefan"
• "När träffar jag teamet?"
• "Sök efter presentation"

Säg bara vad du vill göra så hjälper jag dig! 😊'''
        
        return help_text

# Global instans för användning
alice_calendar_responses = AliceCalendarResponses()