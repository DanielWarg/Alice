"""
ENDA sanningskällan för alla verktyg i Alice-systemet.
Denna fil driver tool-registry, Harmony-specs och router-mapping.
"""

import os
from typing import Dict, Any, List
from pydantic import BaseModel, Field

# ----- Pydantic-scheman för verktygsargument -----
class SetVolumeArgs(BaseModel):
    level: int = Field(None, ge=0, le=100, description="Absolut volymnivå (0-100%)")
    delta: int = Field(None, ge=-100, le=100, description="Relativ volymändring (-100 till +100)")

class RepeatArgs(BaseModel):
    mode: str = Field("off", description="Upprepningsläge: off=ingen, one=en låt, all=hela spellistan")

class ShuffleArgs(BaseModel):
    enabled: bool = Field(description="true=slå på shuffle, false=slå av shuffle")

class SendEmailArgs(BaseModel):
    to: str = Field(description="Mottagarens e-postadress")
    subject: str = Field(description="E-postens ämne")
    body: str = Field(description="E-postens innehåll")
    cc: str = Field(None, description="Kopia till (valfritt)")
    bcc: str = Field(None, description="Dold kopia till (valfritt)")

class ReadEmailArgs(BaseModel):
    max_results: int = Field(10, ge=1, le=50, description="Antal e-post att hämta (1-50)")
    query: str = Field(None, description="Sökfilter (t.ex. 'is:unread', 'from:name@domain.com')")

class SearchEmailArgs(BaseModel):
    query: str = Field(description="Gmail-sökfråga (t.ex. 'subject:meeting', 'from:boss@company.com')")
    max_results: int = Field(20, ge=1, le=100, description="Max antal resultat (1-100)")

class CreateCalendarEventArgs(BaseModel):
    title: str = Field(description="Händelsens titel/ämne")
    start_time: str = Field(description="Starttid (t.ex. 'imorgon kl 14:00', '2024-01-15 09:00')")
    end_time: str = Field(None, description="Sluttid (valfritt, standard 1 timme)")
    description: str = Field(None, description="Beskrivning av händelsen (valfritt)")
    attendees: List[str] = Field(None, description="Lista med e-postadresser till deltagare (valfritt)")

class ListCalendarEventsArgs(BaseModel):
    max_results: int = Field(10, ge=1, le=50, description="Antal händelser att hämta (1-50)")
    time_min: str = Field(None, description="Tidigaste tid att visa händelser från (valfritt)")
    time_max: str = Field(None, description="Senaste tid att visa händelser till (valfritt)")

class SearchCalendarEventsArgs(BaseModel):
    query: str = Field(description="Söktext för att hitta händelser (t.ex. 'möte', 'Jonas')")
    max_results: int = Field(20, ge=1, le=100, description="Max antal resultat (1-100)")

class DeleteCalendarEventArgs(BaseModel):
    event_id: str = Field(description="ID för händelsen som ska tas bort")

class UpdateCalendarEventArgs(BaseModel):
    event_id: str = Field(description="ID för händelsen som ska uppdateras")
    title: str = Field(None, description="Ny titel (valfritt)")
    start_time: str = Field(None, description="Ny starttid (valfritt)")
    end_time: str = Field(None, description="Ny sluttid (valfritt)")
    description: str = Field(None, description="Ny beskrivning (valfritt)")

class NoArgs(BaseModel):
    """Inga argument behövs för detta verktyg"""
    pass

# ----- Canonical tools - EN sanningskälla -----
TOOL_SPECS: Dict[str, Dict[str, Any]] = {
    "PLAY": {
        "args_model": NoArgs,
        "desc": "Spela upp eller återuppta nuvarande låt.",
        "examples": ["spela upp", "starta musik", "fortsätt spela", "resume", "play"]
    },
    "PAUSE": {
        "args_model": NoArgs,
        "desc": "Pausa uppspelning av nuvarande låt.",
        "examples": ["pausa", "pausa musiken", "stoppa tillfälligt", "pause"]
    },
    "STOP": {
        "args_model": NoArgs,
        "desc": "Stoppa uppspelning helt.",
        "examples": ["stoppa", "stoppa musiken", "avsluta uppspelning", "stop"]
    },
    "NEXT": {
        "args_model": NoArgs,
        "desc": "Hoppa till nästa låt i spellistan.",
        "examples": ["nästa låt", "nästa", "hoppa framåt", "skip", "next"]
    },
    "PREV": {
        "args_model": NoArgs,
        "desc": "Gå till föregående låt i spellistan.",
        "examples": ["föregående låt", "föregående", "gå tillbaka", "tidigare", "prev", "previous"]
    },
    "SET_VOLUME": {
        "args_model": SetVolumeArgs,
        "desc": "Ställ in volym till absolut nivå eller justera relativt.",
        "examples": [
            "sätt volym till 80%",
            "höj volymen med 20%",
            "sänk volymen med 10%",
            "volym 50%"
        ]
    },
    "MUTE": {
        "args_model": NoArgs,
        "desc": "Stäng av ljudet (mute).",
        "examples": ["stäng av ljudet", "mute", "ljud av", "tyst"]
    },
    "UNMUTE": {
        "args_model": NoArgs,
        "desc": "Sätt på ljudet (unmute).",
        "examples": ["sätt på ljudet", "unmute", "ljud på", "ljud tillbaka"]
    },
    "REPEAT": {
        "args_model": RepeatArgs,
        "desc": "Ställ in upprepningsläge för spellistan.",
        "examples": [
            "upprepa låten",
            "upprepa spellistan", 
            "stäng av upprepning",
            "loop en låt"
        ]
    },
    "SHUFFLE": {
        "args_model": ShuffleArgs,
        "desc": "Slå på eller av blandad uppspelning (shuffle).",
        "examples": [
            "slå på shuffle",
            "stäng av shuffle",
            "blandad uppspelning",
            "random ordning"
        ]
    },
    "LIKE": {
        "args_model": NoArgs,
        "desc": "Gilla nuvarande låt (lägg till i favoriter).",
        "examples": ["gilla låten", "favorit", "like", "spara låt"]
    },
    "UNLIKE": {
        "args_model": NoArgs,
        "desc": "Ta bort gilla-markering från nuvarande låt.",
        "examples": ["ta bort favorit", "unlike", "ogilla", "ta bort från favoriter"]
    },
    "SEND_EMAIL": {
        "args_model": SendEmailArgs,
        "desc": "Skicka e-post via Gmail.",
        "examples": [
            "skicka mail till john@example.com med ämne 'möte imorgon'",
            "send email to boss@company.com",
            "skicka e-post om projektstatus"
        ]
    },
    "READ_EMAILS": {
        "args_model": ReadEmailArgs,
        "desc": "Läs och visa de senaste e-posten från Gmail.",
        "examples": [
            "visa nya mail",
            "läs de senaste e-posten",
            "check emails",
            "visa 5 senaste mail"
        ]
    },
    "SEARCH_EMAILS": {
        "args_model": SearchEmailArgs,
        "desc": "Sök e-post i Gmail med specifik fråga.",
        "examples": [
            "sök mail från chef",
            "hitta mail om projekt",
            "search emails from last week",
            "sök mail med ämne möte"
        ]
    },
    "CREATE_CALENDAR_EVENT": {
        "args_model": CreateCalendarEventArgs,
        "desc": "Skapa en ny kalenderhändelse/möte.",
        "examples": [
            "skapa möte imorgon kl 14:00",
            "boka tid för tandläkare på fredag kl 10:30",
            "lägg till lunch med Jonas imorgon 12:00",
            "skapa möte 'Projektstatus' nästa måndag kl 09:00"
        ]
    },
    "LIST_CALENDAR_EVENTS": {
        "args_model": ListCalendarEventsArgs,
        "desc": "Visa kommande kalenderhändelser.",
        "examples": [
            "visa mina möten denna vecka",
            "lista kalenderhändelser",
            "vad har jag för möten imorgon",
            "visa 5 kommande händelser"
        ]
    },
    "SEARCH_CALENDAR_EVENTS": {
        "args_model": SearchCalendarEventsArgs,
        "desc": "Sök efter specifika kalenderhändelser.",
        "examples": [
            "sök efter möte med Jonas",
            "hitta tandläkartid",
            "sök kalenderhändelse om projekt",
            "leta efter lunch möten"
        ]
    },
    "DELETE_CALENDAR_EVENT": {
        "args_model": DeleteCalendarEventArgs,
        "desc": "Ta bort en kalenderhändelse.",
        "examples": [
            "ta bort mötet på fredag",
            "radera kalenderhändelse",
            "avboka möte med event_id abc123"
        ]
    },
    "UPDATE_CALENDAR_EVENT": {
        "args_model": UpdateCalendarEventArgs,
        "desc": "Uppdatera en befintlig kalenderhändelse.",
        "examples": [
            "ändra mötet till kl 15:00",
            "uppdatera titel på möte",
            "flytta mötet till imorgon",
            "ändra beskrivning på kalenderhändelse"
        ]
    },
}

def enabled_tools() -> List[str]:
    """Hämta lista över aktiverade verktyg från miljövariabel"""
    env = os.getenv("ENABLED_TOOLS", "")
    if not env:
        # Default: aktivera enbart PLAY/PAUSE/SET_VOLUME i första steget
        return ["PLAY", "PAUSE", "SET_VOLUME"]
    
    tools = [t.strip().upper() for t in env.split(",") if t.strip()]
    return sorted(tools)

def build_harmony_tool_specs() -> List[Dict[str, Any]]:
    """Bygg Harmony-verktygsspecs för aktiverade verktyg"""
    specs = []
    for name in enabled_tools():
        if name not in TOOL_SPECS:
            continue
        spec = TOOL_SPECS[name]
        args_model = spec["args_model"]
        # Generera JSON-schema för Harmony
        schema = args_model.model_json_schema()
        specs.append({
            "name": name,
            "description": spec["desc"],
            "parameters": schema,
            "examples": spec.get("examples", [])
        })
    return specs

def get_tool_spec(name: str) -> Dict[str, Any]:
    """Hämta specifikation för ett verktyg"""
    return TOOL_SPECS.get(name.upper(), {})

def is_tool_enabled(name: str) -> bool:
    """Kontrollera om ett verktyg är aktiverat"""
    return name.upper() in enabled_tools()
