"""
Tool-registry för validering och exekvering av verktyg.
Använder core.tool_specs som enda sanningskälla.
"""

from typing import Dict, Any, Optional
from .tool_specs import TOOL_SPECS, enabled_tools, is_tool_enabled
from .gmail_service import gmail_service
from .calendar_service import calendar_service

# Dummy-implementationer för demo
def play() -> str:
    return "Spelar upp."

def pause() -> str:
    return "Pausar."

def stop() -> str:
    return "Stoppar uppspelning."

def next_track() -> str:
    return "Hoppar till nästa låt."

def prev_track() -> str:
    return "Går till föregående låt."

def set_volume(level: Optional[int] = None, delta: Optional[int] = None) -> str:
    if level is not None:
        return f"Volym satt till {level}%."
    if delta is not None:
        return f"Volym {'höjd' if delta > 0 else 'sänkt'} med {abs(delta)}%."
    return "Volym uppdaterad."

def mute() -> str:
    return "Ljudet avstängt."

def unmute() -> str:
    return "Ljudet påslaget."

def set_repeat(mode: str) -> str:
    modes = {"off": "av", "one": "låt", "all": "spellista"}
    return f"Upprepning: {modes.get(mode, mode)}."

def set_shuffle(enabled: bool) -> str:
    return "Shuffle " + ("på." if enabled else "av.")

def like_track() -> str:
    return "Låt gillad."

def unlike_track() -> str:
    return "Gilla-markering borttagen."

# Gmail-funktioner
def send_email(to: str, subject: str, body: str, cc: str = None, bcc: str = None) -> str:
    return gmail_service.send_email(to, subject, body, cc, bcc)

def read_emails(max_results: int = 10, query: str = None) -> str:
    return gmail_service.read_emails(max_results, query)

def search_emails(query: str, max_results: int = 20) -> str:
    return gmail_service.search_emails(query, max_results)

# Calendar-funktioner
def create_calendar_event(title: str, start_time: str, end_time: str = None, 
                         description: str = None, attendees: list = None, 
                         check_conflicts_first: bool = True) -> str:
    return calendar_service.create_event(title, start_time, end_time, description, attendees, check_conflicts_first)

def list_calendar_events(max_results: int = 10, time_min: str = None, time_max: str = None) -> str:
    return calendar_service.list_events(max_results, time_min, time_max)

def search_calendar_events(query: str, max_results: int = 20) -> str:
    return calendar_service.search_events(query, max_results)

def delete_calendar_event(event_id: str) -> str:
    return calendar_service.delete_event(event_id)

def update_calendar_event(event_id: str, title: str = None, start_time: str = None, 
                         end_time: str = None, description: str = None) -> str:
    return calendar_service.update_event(event_id, title, start_time, end_time, description)

def suggest_meeting_times(duration_minutes: int = 60, date_preference: str = None, 
                         max_suggestions: int = 5) -> str:
    suggestions = calendar_service.suggest_meeting_times(duration_minutes, date_preference, max_suggestions)
    if not suggestions:
        return "Inga lediga tider hittades för den angivna perioden."
    
    result = f"Föreslagna mötestider ({duration_minutes} minuter):\n\n"
    for i, suggestion in enumerate(suggestions, 1):
        confidence_pct = int(suggestion['confidence'] * 100)
        result += f"{i}. {suggestion['formatted']} (rekommendation: {confidence_pct}%)\n"
    
    return result

def check_calendar_conflicts(start_time: str, end_time: str = None, exclude_event_id: str = None) -> str:
    conflict_result = calendar_service.check_conflicts(start_time, end_time, exclude_event_id)
    
    if not conflict_result['has_conflict']:
        return "✅ Ingen konflikt - tiden är ledig!"
    
    message = f"⚠️ {conflict_result['message']}\n\n"
    
    if conflict_result.get('conflicts'):
        message += "Konflikterande händelser:\n"
        for conflict in conflict_result['conflicts']:
            message += f"• {conflict['title']} ({conflict['start']} - {conflict['end']})\n"
    
    if conflict_result.get('suggestions'):
        message += "\nAlternativa tider:\n"
        for i, suggestion in enumerate(conflict_result['suggestions'], 1):
            message += f"{i}. {suggestion['formatted']}\n"
    
    return message

# Verktygsexekverare som matchar TOOL_SPECS exakt - SAMMA NAMN!
EXECUTORS = {
    "PLAY": lambda _args: play(),
    "PAUSE": lambda _args: pause(),
    "STOP": lambda _args: stop(),
    "NEXT": lambda _args: next_track(),
    "PREV": lambda _args: prev_track(),
    "SET_VOLUME": lambda args: set_volume(args.level, args.delta),
    "MUTE": lambda _args: mute(),
    "UNMUTE": lambda _args: unmute(),
    "REPEAT": lambda args: set_repeat(args.mode),
    "SHUFFLE": lambda args: set_shuffle(args.enabled),
    "LIKE": lambda _args: like_track(),
    "UNLIKE": lambda _args: unlike_track(),
    "SEND_EMAIL": lambda args: send_email(args.to, args.subject, args.body, args.cc, args.bcc),
    "READ_EMAILS": lambda args: read_emails(args.max_results, args.query),
    "SEARCH_EMAILS": lambda args: search_emails(args.query, args.max_results),
    "CREATE_CALENDAR_EVENT": lambda args: create_calendar_event(args.title, args.start_time, args.end_time, args.description, args.attendees),
    "LIST_CALENDAR_EVENTS": lambda args: list_calendar_events(args.max_results, args.time_min, args.time_max),
    "SEARCH_CALENDAR_EVENTS": lambda args: search_calendar_events(args.query, args.max_results),
    "DELETE_CALENDAR_EVENT": lambda args: delete_calendar_event(args.event_id),
    "UPDATE_CALENDAR_EVENT": lambda args: update_calendar_event(args.event_id, args.title, args.start_time, args.end_time, args.description),
    "SUGGEST_MEETING_TIMES": lambda args: suggest_meeting_times(args.duration_minutes, args.date_preference, args.max_suggestions),
    "CHECK_CALENDAR_CONFLICTS": lambda args: check_calendar_conflicts(args.start_time, args.end_time, args.exclude_event_id),
}

def list_tool_specs() -> list[Dict[str, Any]]:
    """Lista alla tillgängliga verktyg och deras specifikationer"""
    from .tool_specs import build_harmony_tool_specs
    return build_harmony_tool_specs()

def validate_and_execute_tool(name: str, arguments: dict) -> Dict[str, Any]:
    """Validera och exekvera ett verktyg"""
    name = name.upper()
    
    # Kontrollera att verktyget är aktiverat
    if not is_tool_enabled(name):
        return {"ok": False, "message": f"Tool {name} is not enabled"}
    
    # Hitta spec och executor
    spec = TOOL_SPECS.get(name)
    if not spec or name not in EXECUTORS:
        return {"ok": False, "message": f"Unknown tool: {name}"}
    
    try:
        # Validera argument mot Pydantic-schema
        args_model = spec["args_model"]
        args = args_model(**(arguments or {}))
        
        # Exekvera verktyget
        res = EXECUTORS[name](args)
        return {"ok": True, "message": res or "OK"}
    except Exception as e:
        return {"ok": False, "message": str(e)}

def get_executor_names() -> list[str]:
    """Hämta lista över tillgängliga executors"""
    return sorted(list(EXECUTORS.keys()))
