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
