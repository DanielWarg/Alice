"""
Harmony-compatible prompt formatting for tool-ready LLM interactions
"""

import json
from typing import Dict, List, Any, Optional

def harmonyWrap(
    system: str,
    user: str,
    developer: Optional[str] = None,
    history: Optional[List[Dict[str, str]]] = None,
    tool_responses: Optional[List[Dict[str, Any]]] = None
) -> List[Dict[str, Any]]:
    """
    Create Harmony-compatible message structure for LLM requests.
    
    Args:
        system: System prompt (core behavior)
        user: User input/query
        developer: Developer instructions (optional)
        history: Previous conversation turns (optional)
        tool_responses: Tool execution results (optional)
    
    Returns:
        List of messages in OpenAI format with Harmony channels
    """
    messages = []
    
    # System message - core behavior
    messages.append({"role": "system", "content": system})
    
    # Developer message - implementation guidance
    if developer:
        messages.append({"role": "developer", "content": developer})
    
    # History - previous conversation context
    if history:
        for msg in history:
            # Ensure valid roles
            role = msg.get("role", "user")
            if role not in ["user", "assistant"]:
                role = "user"
            messages.append({
                "role": role,
                "content": msg.get("content", "")
            })
    
    # Tool responses - results from previous tool calls
    if tool_responses:
        for tool_resp in tool_responses:
            tool_name = tool_resp.get("tool", "unknown_tool")
            content = tool_resp.get("content", {})
            
            # Format tool response as JSON string
            if isinstance(content, dict):
                content_str = json.dumps(content, ensure_ascii=False)
            else:
                content_str = str(content)
            
            messages.append({
                "role": "tool",
                "name": tool_name,
                "content": content_str
            })
    
    # User message - current request
    messages.append({"role": "user", "content": user})
    
    return messages

def create_system_prompt() -> str:
    """
    Create Harmony-compatible system prompt for Alice core planner.
    Encourages structured thinking and tool usage.
    """
    return """Du är Alice, en intelligent svensk AI-assistent med förmåga att använda verktyg för att hjälpa användare.

STRUKTURERAT TÄNKANDE:
- Använd `analysis` för att analysera användarens behov
- Använd `commentary` för att planera och anropa verktyg via tool_calls
- Använd `final` för att ge användaren ditt slutgiltiga svar

VERKTYGSANVÄNDNING:
- Använd verktyg när extern data eller handling krävs (kalender, e-post, musik, väder)
- Anropa verktyg i commentary-sektionen som tool_calls
- Vänta på verktygsresultat innan du ger final svar

KOMMUNIKATION:
- Svara alltid på svenska
- Var hjälpsam och proaktiv
- Ställ uppföljningsfrågor vid oklarheter
- Förklara vad du gör när du använder verktyg"""

def create_developer_prompt() -> str:
    """
    Create developer instructions for implementation guidance.
    """
    return """IMPLEMENTATION GUIDANCE:
- Föredra snabba kommandon via verktyg för HA/Gmail/Calendar/Spotify
- Längre resonemang och komplex analys hanteras av lokala modellen
- Var proaktiv: ställ uppföljningsfrågor vid oklarheter
- Använd svenska datum/tidsformat (YYYY-MM-DD HH:MM)
- Kontrollera verktygstillgänglighet innan användning"""

def extract_harmony_sections(text: str) -> Dict[str, str]:
    """
    Extract Harmony sections (analysis, commentary, final) from model output.
    
    Args:
        text: Model response text
        
    Returns:
        Dict with extracted sections
    """
    import re
    
    sections = {
        "analysis": "",
        "commentary": "",
        "final": "",
        "raw": text
    }
    
    # Pattern to match Harmony sections
    section_pattern = r'`([^`]+)`:\s*([^`]*?)(?=`[^`]+`:|$)'
    matches = re.findall(section_pattern, text, re.DOTALL | re.IGNORECASE)
    
    for section_name, content in matches:
        section_key = section_name.lower().strip()
        if section_key in sections:
            sections[section_key] = content.strip()
    
    # If no structured sections found, put everything in final
    if not any(sections[key] for key in ["analysis", "commentary", "final"]):
        sections["final"] = text.strip()
    
    return sections

def extract_tool_calls_from_commentary(commentary: str) -> List[Dict[str, Any]]:
    """
    Extract tool calls from commentary section.
    
    Args:
        commentary: Commentary section text
        
    Returns:
        List of tool calls
    """
    import re
    
    tool_calls = []
    
    # Look for tool_call patterns in commentary
    patterns = [
        r'tool_call\s*:\s*\{([^}]+)\}',
        r'"tool_calls":\s*\[([^\]]+)\]',
        r'tool:\s*"([^"]+)".*?args:\s*\{([^}]+)\}'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, commentary, re.DOTALL)
        for match in matches:
            try:
                if isinstance(match, tuple):
                    # Handle different match patterns
                    if len(match) == 2:
                        tool_name, args_str = match
                        tool_calls.append({
                            "type": "function",
                            "function": {
                                "name": tool_name.strip('"'),
                                "arguments": "{" + args_str + "}"
                            }
                        })
                else:
                    # Try to parse as JSON
                    import json
                    parsed = json.loads("{" + match + "}")
                    tool_calls.append(parsed)
            except:
                continue
    
    return tool_calls