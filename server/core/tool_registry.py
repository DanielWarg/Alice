"""
Tool-registry för validering och exekvering av verktyg.
Använder core.tool_specs som enda sanningskälla.
"""

from typing import Dict, Any, Optional
from .tool_specs import TOOL_SPECS, enabled_tools, is_tool_enabled

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
