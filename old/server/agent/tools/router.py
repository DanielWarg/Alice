"""
Tool-call extraction and execution with Harmony support
"""

import json
import re
import logging
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass

logger = logging.getLogger("alice.agent.tools")

@dataclass
class ToolExecutionResult:
    """Result from tool execution"""
    tool: str
    success: bool
    content: Any
    error: Optional[str] = None

def extractToolCalls(model_output: Union[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extract tool calls from model output - supports both Harmony and OpenAI formats.
    
    Args:
        model_output: String response or dict with tool_calls
        
    Returns:
        List of tool calls in OpenAI format
    """
    tool_calls = []
    
    # Handle direct dict format (OpenAI response format)
    if isinstance(model_output, dict):
        if "tool_calls" in model_output:
            return model_output["tool_calls"]
        return []
    
    # Handle string format - extract from various patterns
    text = str(model_output)
    
    # 1. Look for OpenAI-style tool_calls JSON
    openai_pattern = r'"tool_calls":\s*(\[[^\]]*\])'
    matches = re.findall(openai_pattern, text, re.DOTALL)
    
    for match in matches:
        try:
            calls = json.loads(match)
            tool_calls.extend(calls)
        except json.JSONDecodeError:
            continue
    
    # 2. Look for Harmony commentary with tool calls
    commentary_pattern = r'`commentary`:\s*(.*?)(?=`[^`]+`:|$)'
    commentary_matches = re.findall(commentary_pattern, text, re.DOTALL | re.IGNORECASE)
    
    for commentary in commentary_matches:
        # Extract tool calls from commentary
        harmony_calls = _extract_harmony_tool_calls(commentary)
        tool_calls.extend(harmony_calls)
    
    # 3. Look for legacy Alice format { tool: "...", args: {...} }
    legacy_pattern = r'\{\s*"?tool"?\s*:\s*"([^"]+)"[^}]*"?args"?\s*:\s*(\{[^}]*\})\s*\}'
    legacy_matches = re.findall(legacy_pattern, text)
    
    for tool_name, args_str in legacy_matches:
        try:
            args = json.loads(args_str)
            tool_calls.append({
                "type": "function",
                "function": {
                    "name": tool_name,
                    "arguments": json.dumps(args)
                }
            })
        except json.JSONDecodeError:
            continue
    
    # 4. Look for simple function call patterns
    function_pattern = r'(\w+)\s*\(\s*([^)]*)\s*\)'
    function_matches = re.findall(function_pattern, text)
    
    # Only include if it looks like a tool call (not regular text)
    tool_names = ["turn_on_light", "get_weather", "play_music", "send_email", 
                 "create_calendar_event", "search_gmail"]
    
    for func_name, args_str in function_matches:
        if func_name in tool_names:
            try:
                # Try to parse args as JSON-like
                args = _parse_function_args(args_str)
                tool_calls.append({
                    "type": "function", 
                    "function": {
                        "name": func_name,
                        "arguments": json.dumps(args)
                    }
                })
            except:
                continue
    
    logger.debug(f"Extracted {len(tool_calls)} tool calls from model output")
    return tool_calls

def _extract_harmony_tool_calls(commentary: str) -> List[Dict[str, Any]]:
    """Extract tool calls from Harmony commentary section"""
    tool_calls = []
    
    patterns = [
        r'tool_call\s*:\s*\{([^}]+)\}',
        r'"function":\s*\{[^}]*"name":\s*"([^"]+)"[^}]*"arguments":\s*"([^"]*)"',
        r'call\s*:\s*([^,\n]+)\s*\([^)]*\)'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, commentary, re.DOTALL)
        for match in matches:
            try:
                if isinstance(match, tuple) and len(match) >= 2:
                    name, args = match[0], match[1]
                    tool_calls.append({
                        "type": "function",
                        "function": {
                            "name": name.strip('"'),
                            "arguments": args
                        }
                    })
                else:
                    # Try to parse as full tool call
                    parsed = json.loads("{" + str(match) + "}")
                    if "function" in parsed:
                        tool_calls.append(parsed)
            except:
                continue
    
    return tool_calls

def _parse_function_args(args_str: str) -> Dict[str, Any]:
    """Parse function arguments from string"""
    if not args_str.strip():
        return {}
    
    # Try JSON first
    try:
        return json.loads(args_str)
    except:
        pass
    
    # Try simple key=value parsing
    args = {}
    parts = args_str.split(',')
    for part in parts:
        if '=' in part:
            key, value = part.split('=', 1)
            key = key.strip().strip('"\'')
            value = value.strip().strip('"\'')
            args[key] = value
    
    return args

async def executeToolCall(tool_call: Dict[str, Any]) -> ToolExecutionResult:
    """
    Execute a single tool call and return result.
    
    Args:
        tool_call: Tool call in OpenAI format
        
    Returns:
        ToolExecutionResult with execution outcome
    """
    try:
        # Extract function details
        if "function" not in tool_call:
            return ToolExecutionResult(
                tool="unknown",
                success=False,
                content=None,
                error="No function specified in tool call"
            )
        
        function = tool_call["function"]
        tool_name = function.get("name", "unknown")
        
        # Parse arguments
        try:
            args_str = function.get("arguments", "{}")
            if isinstance(args_str, str):
                args = json.loads(args_str)
            else:
                args = args_str
        except json.JSONDecodeError as e:
            return ToolExecutionResult(
                tool=tool_name,
                success=False,
                content=None,
                error=f"Invalid arguments JSON: {e}"
            )
        
        # Route to appropriate tool handler
        result = await _route_tool_execution(tool_name, args)
        
        return ToolExecutionResult(
            tool=tool_name,
            success=True,
            content=result
        )
        
    except Exception as e:
        logger.error(f"Tool execution failed: {e}")
        return ToolExecutionResult(
            tool=tool_call.get("function", {}).get("name", "unknown"),
            success=False,
            content=None,
            error=str(e)
        )

async def _route_tool_execution(tool_name: str, args: Dict[str, Any]) -> Any:
    """Route tool execution to appropriate handler"""
    
    # Import existing tool system
    try:
        from ...core import validate_and_execute_tool
        
        # Convert to legacy format for existing tool system
        tool_request = {
            "tool": tool_name,
            "args": args
        }
        
        result = validate_and_execute_tool(tool_request)
        return result
        
    except ImportError:
        logger.warning("Core tool system not available, using mock")
        return _mock_tool_execution(tool_name, args)

def _mock_tool_execution(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Mock tool execution for testing"""
    
    mock_responses = {
        "turn_on_light": {"status": "success", "device": args.get("device", "unknown"), "action": "turned_on"},
        "get_weather": {"temperature": 22, "condition": "sunny", "location": args.get("location", "Stockholm")},
        "play_music": {"status": "playing", "track": args.get("query", "unknown song")},
        "send_email": {"status": "sent", "to": args.get("to", "unknown")},
        "create_calendar_event": {"status": "created", "event_id": "mock_123", "title": args.get("title", "New Event")},
        "search_gmail": {"count": 3, "results": ["Email 1", "Email 2", "Email 3"]}
    }
    
    return mock_responses.get(tool_name, {"status": "unknown_tool", "tool": tool_name})