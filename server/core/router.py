"""
Router för snabba intents - klassificerar text och returnerar verktygsanrop.
Använder core.tool_specs som enda sanningskälla.
"""

import re
from typing import Dict, Any, Optional, List
from difflib import SequenceMatcher
from .tool_specs import TOOL_SPECS, enabled_tools, is_tool_enabled

# Router-regler för varje verktyg - synonymer och vanliga uttryck
ROUTER_RULES: Dict[str, List[str]] = {
    "PLAY": [
        "spela", "spela upp", "starta", "starta musik", "fortsätt", "fortsätt spela",
        "play", "resume", "start", "continue"
    ],
    "PAUSE": [
        "pausa", "pausa musiken", "stoppa tillfälligt", "paus", "pausa uppspelning",
        "pause", "stop temporarily", "halt"
    ],
    "STOP": [
        "stoppa", "stoppa musiken", "avsluta", "avsluta uppspelning", "stopp",
        "stop", "end", "terminate"
    ],
    "NEXT": [
        "nästa", "nästa låt", "hoppa framåt", "hoppa över", "nästa spår",
        "next", "skip", "forward", "next track"
    ],
    "PREV": [
        "föregående", "föregående låt", "gå tillbaka", "tidigare", "föregående spår",
        "prev", "previous", "back", "previous track"
    ],
    "MUTE": [
        "stäng av ljudet", "mute", "ljud av", "tyst", "stäng av ljud",
        "mute audio", "silence", "quiet"
    ],
    "UNMUTE": [
        "sätt på ljudet", "unmute", "ljud på", "ljud tillbaka", "aktivera ljud",
        "unmute audio", "enable sound", "restore audio"
    ],
    "REPEAT": [
        "upprepa", "upprepa låten", "upprepa spellistan", "loop", "repetera",
        "repeat", "loop track", "loop playlist"
    ],
    "SHUFFLE": [
        "shuffle", "blanda", "blanda låtar", "slumpvis", "random ordning",
        "randomize", "mix", "random order"
    ],
    "LIKE": [
        "gilla", "gilla låten", "favorit", "like", "spara låt", "lägg till i favoriter",
        "like track", "favorite", "save track"
    ],
    "UNLIKE": [
        "ogilla", "ta bort favorit", "unlike", "ta bort från favoriter", "ta bort gilla",
        "unlike track", "remove favorite", "unfavorite"
    ],
}

# Volym-specifika regler för SET_VOLUME
VOLUME_PATTERNS = [
    # Absoluta värden
    (r"sätt volym(?:en)? (?:till )?(\d+)%?", "level"),
    (r"volym(?:en)? (?:på )?(\d+)%?", "level"),
    (r"volym (\d+)", "level"),
    # Relativa värden
    (r"höj volym(?:en)? (?:med )?(\d+)%?", "delta"),
    (r"sänk volym(?:en)? (?:med )?(\d+)%?", "delta"),
    (r"höj(?: volym)? (\d+)%?", "delta"),
    (r"sänk(?: volym)? (\d+)%?", "delta"),
    # Generella volymkommandon
    (r"volym(?:en)? (?:höj|sänk)", "delta"),
    (r"justera volym", "delta"),
]

def similarity(a: str, b: str) -> float:
    """Beräkna likhet mellan två strängar (0-1)"""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def classify_volume(text: str) -> Optional[Dict[str, Any]]:
    """Klassificera volymkommandon med regex"""
    text_lower = text.lower()
    
    for pattern, arg_type in VOLUME_PATTERNS:
        match = re.search(pattern, text_lower)
        if match:
            if arg_type == "level":
                try:
                    level = int(match.group(1))
                    if 0 <= level <= 100:
                        return {
                            "tool": "SET_VOLUME",
                            "args": {"level": level},
                            "confidence": 0.95
                        }
                except ValueError:
                    continue
            elif arg_type == "delta":
                # För generella volymkommandon, gissa delta
                if "höj" in text_lower or "hög" in text_lower:
                    return {
                        "tool": "SET_VOLUME", 
                        "args": {"delta": 10},
                        "confidence": 0.8
                    }
                elif "sänk" in text_lower or "låg" in text_lower:
                    return {
                        "tool": "SET_VOLUME",
                        "args": {"delta": -10}, 
                        "confidence": 0.8
                    }
    
    return None

def classify(text: str) -> Optional[Dict[str, Any]]:
    """
    Klassificera text och returnera verktygsanrop med confidence.
    Returnerar None vid osäkerhet (Harmony tar över).
    """
    if not text or not text.strip():
        return None
    
    text_lower = text.strip().lower()
    
    # Först, kontrollera volymkommandon (kräver regex)
    volume_result = classify_volume(text)
    if volume_result:
        return volume_result
    
    # Sedan, kontrollera alla andra verktyg med fuzzy matching
    best_match = None
    best_confidence = 0.0
    
    for tool_name, synonyms in ROUTER_RULES.items():
        # Kontrollera att verktyget är aktiverat
        if not is_tool_enabled(tool_name):
            continue
            
        # Exakt match på synonym
        if text_lower in synonyms:
            return {
                "tool": tool_name,
                "args": {},
                "confidence": 1.0
            }
        
        # Fuzzy match på synonym
        for synonym in synonyms:
            sim = similarity(text_lower, synonym)
            if sim > best_confidence and sim >= 0.8:  # Mycket försiktig fuzzy
                best_confidence = sim
                best_match = {
                    "tool": tool_name,
                    "args": {},
                    "confidence": sim
                }
    
    # Returnera bästa match om confidence är tillräckligt hög
    if best_match and best_match["confidence"] >= 0.85:
        return best_match
    
    # Ingen säker match - låt Harmony hantera
    return None

def get_router_stats() -> Dict[str, Any]:
    """Hämta statistik om router-reglerna"""
    total_rules = sum(len(synonyms) for synonyms in ROUTER_RULES.values())
    enabled_count = len([tool for tool in ROUTER_RULES.keys() if is_tool_enabled(tool)])
    
    return {
        "total_tools": len(ROUTER_RULES),
        "enabled_tools": enabled_count,
        "total_synonyms": total_rules,
        "enabled_tools_list": [tool for tool in ROUTER_RULES.keys() if is_tool_enabled(tool)]
    }
