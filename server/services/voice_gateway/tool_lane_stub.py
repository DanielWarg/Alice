"""
Tool Lane Stub - Local GPT-OSS Processing for Private Tools

This module implements local tool planning and execution with privacy-first design.
All processing is done locally without sending private data to cloud services.
"""

import json
import time
import logging
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import asyncio
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

class ToolType(Enum):
    EMAIL = "email"
    CALENDAR = "calendar"
    FILES = "files"

@dataclass
class ToolCall:
    tool_name: str
    args: Dict[str, Any]
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

@dataclass
class ToolResult:
    success: bool
    data: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    no_cloud: bool = True  # Always mark as private
    
@dataclass
class PerformanceMetrics:
    tool_planning_latency: float = 0.0
    tool_execution_latency: float = 0.0
    total_latency: float = 0.0
    llm_tokens_used: int = 0
    error_count: int = 0

class LocalToolPlanner:
    """
    Tool planner using local GPT-OSS for private tool orchestration
    """
    
    def __init__(self, local_llm_manager=None):
        self.local_llm_manager = local_llm_manager
        self.system_prompt = (
            "You plan and call local tools. Never send arguments or results to cloud. "
            "Prefer minimal scope. Output strictly: {tool_name, args}."
        )
        self.supported_tools = {
            ToolType.EMAIL.value: self._get_email_schema(),
            ToolType.CALENDAR.value: self._get_calendar_schema(),
            ToolType.FILES.value: self._get_files_schema()
        }
    
    def _get_email_schema(self) -> Dict:
        return {
            "name": "email",
            "description": "Handle email operations locally",
            "parameters": {
                "action": {"type": "string", "enum": ["read", "send", "search"]},
                "query": {"type": "string", "description": "Search query or recipient"},
                "content": {"type": "string", "description": "Email content for sending"},
                "subject": {"type": "string", "description": "Email subject"}
            },
            "required": ["action"]
        }
    
    def _get_calendar_schema(self) -> Dict:
        return {
            "name": "calendar",
            "description": "Handle calendar operations locally",
            "parameters": {
                "action": {"type": "string", "enum": ["read", "create", "update", "delete"]},
                "event_id": {"type": "string", "description": "Event identifier"},
                "title": {"type": "string", "description": "Event title"},
                "start_time": {"type": "string", "description": "Start time ISO format"},
                "end_time": {"type": "string", "description": "End time ISO format"},
                "description": {"type": "string", "description": "Event description"}
            },
            "required": ["action"]
        }
    
    def _get_files_schema(self) -> Dict:
        return {
            "name": "files",
            "description": "Handle file operations locally",
            "parameters": {
                "action": {"type": "string", "enum": ["read", "write", "search", "list"]},
                "path": {"type": "string", "description": "File or directory path"},
                "content": {"type": "string", "description": "File content for writing"},
                "query": {"type": "string", "description": "Search query"}
            },
            "required": ["action"]
        }
    
    async def plan_tools(self, user_input: str, context: Dict = None) -> List[ToolCall]:
        """
        Plan tool calls using local LLM processing
        """
        start_time = time.time()
        
        try:
            # Prepare planning prompt
            planning_prompt = self._create_planning_prompt(user_input, context)
            
            # Use local LLM for planning (force local provider)
            if self.local_llm_manager:
                response = await self._call_local_llm(planning_prompt)
            else:
                # Fallback to rule-based planning
                response = self._fallback_planning(user_input)
            
            # Parse tool calls from response
            tool_calls = self._parse_tool_calls(response)
            
            planning_latency = time.time() - start_time
            logger.info(f"Tool planning completed in {planning_latency:.3f}s")
            
            return tool_calls
            
        except Exception as e:
            logger.error(f"Tool planning failed: {e}")
            return self._emergency_fallback(user_input)
    
    def _create_planning_prompt(self, user_input: str, context: Dict = None) -> str:
        """Create planning prompt for local LLM"""
        tools_info = json.dumps(self.supported_tools, indent=2)
        
        prompt = f"""
{self.system_prompt}

Available tools:
{tools_info}

Context: {json.dumps(context or {}, indent=2)}

User request: {user_input}

Plan the minimal set of tool calls needed. Respond with JSON array of tool calls:
[{{"tool_name": "tool_name", "args": {{...}}}}]
"""
        return prompt
    
    async def _call_local_llm(self, prompt: str) -> str:
        """Call local LLM with privacy guarantees"""
        try:
            # Force local provider usage
            local_config = {
                "provider": "local",  # Force local processing
                "model": "gpt-oss",   # Use open source model
                "temperature": 0.1,   # Low temperature for consistency
                "max_tokens": 500,    # Limit response size
                "no_cloud": True      # Privacy flag
            }
            
            if hasattr(self.local_llm_manager, 'generate_with_config'):
                response = await self.local_llm_manager.generate_with_config(
                    prompt, local_config
                )
            else:
                # Fallback method
                response = await self.local_llm_manager.generate(prompt)
            
            return response
            
        except Exception as e:
            logger.error(f"Local LLM call failed: {e}")
            raise
    
    def _fallback_planning(self, user_input: str) -> str:
        """Rule-based fallback when LLM is unavailable"""
        user_lower = user_input.lower()
        
        if any(word in user_lower for word in ["email", "mail", "message"]):
            if any(word in user_lower for word in ["send", "write", "compose"]):
                return '[{"tool_name": "email", "args": {"action": "send"}}]'
            else:
                return '[{"tool_name": "email", "args": {"action": "read"}}]'
        
        elif any(word in user_lower for word in ["calendar", "meeting", "appointment", "schedule"]):
            if any(word in user_lower for word in ["create", "add", "schedule"]):
                return '[{"tool_name": "calendar", "args": {"action": "create"}}]'
            else:
                return '[{"tool_name": "calendar", "args": {"action": "read"}}]'
        
        elif any(word in user_lower for word in ["file", "document", "folder"]):
            if any(word in user_lower for word in ["search", "find"]):
                return '[{"tool_name": "files", "args": {"action": "search"}}]'
            else:
                return '[{"tool_name": "files", "args": {"action": "list"}}]'
        
        # Default fallback
        return '[{"tool_name": "files", "args": {"action": "list"}}]'
    
    def _parse_tool_calls(self, response: str) -> List[ToolCall]:
        """Parse tool calls from LLM response"""
        try:
            # Try to extract JSON from response
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:-3]
            elif response.startswith('```'):
                response = response[3:-3]
            
            # Parse JSON
            tool_data = json.loads(response)
            
            if not isinstance(tool_data, list):
                tool_data = [tool_data]
            
            tool_calls = []
            for item in tool_data:
                if isinstance(item, dict) and "tool_name" in item and "args" in item:
                    tool_calls.append(ToolCall(
                        tool_name=item["tool_name"],
                        args=item["args"]
                    ))
            
            return tool_calls
            
        except Exception as e:
            logger.error(f"Failed to parse tool calls: {e}")
            return []
    
    def _emergency_fallback(self, user_input: str) -> List[ToolCall]:
        """Emergency fallback when all planning fails"""
        return [ToolCall(
            tool_name="files",
            args={"action": "list", "path": "."}
        )]

class LocalToolExecutor:
    """
    Local tool executor with stubbed implementations
    """
    
    def __init__(self):
        self.executors = {
            ToolType.EMAIL.value: EmailExecutorStub(),
            ToolType.CALENDAR.value: CalendarExecutorStub(),
            ToolType.FILES.value: FilesExecutorStub()
        }
    
    async def execute_tool(self, tool_call: ToolCall) -> ToolResult:
        """Execute a tool call locally"""
        start_time = time.time()
        
        try:
            executor = self.executors.get(tool_call.tool_name)
            if not executor:
                return ToolResult(
                    success=False,
                    error=f"Unknown tool: {tool_call.tool_name}",
                    execution_time=time.time() - start_time
                )
            
            result = await executor.execute(tool_call.args)
            result.execution_time = time.time() - start_time
            result.no_cloud = True  # Always mark as private
            
            return result
            
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                execution_time=time.time() - start_time
            )

class EmailExecutorStub:
    """Stubbed email operations for local processing"""
    
    async def execute(self, args: Dict) -> ToolResult:
        action = args.get("action", "read")
        
        if action == "read":
            return ToolResult(
                success=True,
                data={
                    "emails": [
                        {
                            "id": "stub_001",
                            "subject": "[STUB] Sample email",
                            "from": "stub@example.com",
                            "preview": "This is a stubbed email response"
                        }
                    ],
                    "count": 1
                }
            )
        
        elif action == "send":
            return ToolResult(
                success=True,
                data={
                    "message": "Email would be sent (stub mode)",
                    "recipient": args.get("query", "unknown"),
                    "subject": args.get("subject", "No subject")
                }
            )
        
        elif action == "search":
            return ToolResult(
                success=True,
                data={
                    "results": [
                        {
                            "id": "search_001",
                            "subject": f"[STUB] Found: {args.get('query', 'N/A')}",
                            "relevance": 0.8
                        }
                    ]
                }
            )
        
        return ToolResult(success=False, error=f"Unknown email action: {action}")

class CalendarExecutorStub:
    """Stubbed calendar operations for local processing"""
    
    async def execute(self, args: Dict) -> ToolResult:
        action = args.get("action", "read")
        
        if action == "read":
            return ToolResult(
                success=True,
                data={
                    "events": [
                        {
                            "id": "cal_001",
                            "title": "[STUB] Sample meeting",
                            "start": "2025-08-26T10:00:00Z",
                            "end": "2025-08-26T11:00:00Z"
                        }
                    ],
                    "count": 1
                }
            )
        
        elif action == "create":
            return ToolResult(
                success=True,
                data={
                    "message": "Event would be created (stub mode)",
                    "title": args.get("title", "Untitled"),
                    "start": args.get("start_time", "TBD")
                }
            )
        
        elif action == "update":
            return ToolResult(
                success=True,
                data={
                    "message": "Event would be updated (stub mode)",
                    "event_id": args.get("event_id", "unknown")
                }
            )
        
        elif action == "delete":
            return ToolResult(
                success=True,
                data={
                    "message": "Event would be deleted (stub mode)",
                    "event_id": args.get("event_id", "unknown")
                }
            )
        
        return ToolResult(success=False, error=f"Unknown calendar action: {action}")

class FilesExecutorStub:
    """Stubbed file operations for local processing"""
    
    async def execute(self, args: Dict) -> ToolResult:
        action = args.get("action", "list")
        
        if action == "list":
            return ToolResult(
                success=True,
                data={
                    "files": [
                        {"name": "stub_file1.txt", "type": "file", "size": 1024},
                        {"name": "stub_folder", "type": "directory", "size": 0}
                    ],
                    "path": args.get("path", "."),
                    "count": 2
                }
            )
        
        elif action == "read":
            return ToolResult(
                success=True,
                data={
                    "content": f"[STUB] Content of {args.get('path', 'unknown file')}",
                    "path": args.get("path"),
                    "size": 42
                }
            )
        
        elif action == "write":
            return ToolResult(
                success=True,
                data={
                    "message": "File would be written (stub mode)",
                    "path": args.get("path", "unknown"),
                    "bytes_written": len(args.get("content", ""))
                }
            )
        
        elif action == "search":
            return ToolResult(
                success=True,
                data={
                    "results": [
                        {
                            "path": "/stub/path/found_file.txt",
                            "matches": 3,
                            "query": args.get("query", "N/A")
                        }
                    ],
                    "total_matches": 3
                }
            )
        
        return ToolResult(success=False, error=f"Unknown files action: {action}")

class ToolLane:
    """
    Main tool lane coordinator for local private tool processing
    """
    
    def __init__(self, local_llm_manager=None):
        self.planner = LocalToolPlanner(local_llm_manager)
        self.executor = LocalToolExecutor()
        self.metrics = PerformanceMetrics()
    
    async def process_request(self, user_input: str, context: Dict = None) -> Dict[str, Any]:
        """
        Process a user request through the local tool lane
        """
        start_time = time.time()
        
        try:
            # Step 1: Plan tools locally
            planning_start = time.time()
            tool_calls = await self.planner.plan_tools(user_input, context)
            self.metrics.tool_planning_latency = time.time() - planning_start
            
            if not tool_calls:
                return {
                    "success": False,
                    "error": "No valid tools could be planned",
                    "no_cloud": True,
                    "metrics": asdict(self.metrics)
                }
            
            # Step 2: Execute tools
            execution_start = time.time()
            results = []
            
            for tool_call in tool_calls:
                result = await self.executor.execute_tool(tool_call)
                results.append({
                    "tool": tool_call.tool_name,
                    "args": tool_call.args,
                    "result": asdict(result)
                })
                
                if not result.success:
                    self.metrics.error_count += 1
            
            self.metrics.tool_execution_latency = time.time() - execution_start
            self.metrics.total_latency = time.time() - start_time
            
            # Step 3: Structure response for privacy filter
            response = {
                "success": True,
                "tool_results": results,
                "no_cloud": True,  # Always mark as private
                "processed_locally": True,
                "timestamp": datetime.now().isoformat(),
                "metrics": asdict(self.metrics)
            }
            
            logger.info(f"Tool lane processing completed in {self.metrics.total_latency:.3f}s")
            
            return response
            
        except Exception as e:
            logger.error(f"Tool lane processing failed: {e}")
            self.metrics.error_count += 1
            self.metrics.total_latency = time.time() - start_time
            
            return {
                "success": False,
                "error": str(e),
                "no_cloud": True,
                "metrics": asdict(self.metrics)
            }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        return asdict(self.metrics)
    
    def reset_metrics(self):
        """Reset performance metrics"""
        self.metrics = PerformanceMetrics()

# Factory function for integration
def create_tool_lane(local_llm_manager=None) -> ToolLane:
    """
    Create and configure a tool lane instance
    """
    return ToolLane(local_llm_manager)

# Health check function
async def health_check() -> Dict[str, Any]:
    """
    Check tool lane health and capabilities
    """
    try:
        tool_lane = create_tool_lane()
        
        # Test basic functionality
        test_result = await tool_lane.process_request(
            "test request",
            {"test": True}
        )
        
        return {
            "status": "healthy",
            "local_processing": True,
            "supported_tools": list(tool_lane.executor.executors.keys()),
            "test_successful": test_result.get("success", False),
            "privacy_enabled": True
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "privacy_enabled": True
        }

if __name__ == "__main__":
    # Basic test/demo
    import asyncio
    
    async def demo():
        tool_lane = create_tool_lane()
        
        test_requests = [
            "Check my recent emails",
            "Create a meeting for tomorrow at 2pm",
            "Search for files containing 'budget'",
        ]
        
        for request in test_requests:
            print(f"\nProcessing: {request}")
            result = await tool_lane.process_request(request)
            print(f"Result: {json.dumps(result, indent=2)}")
    
    asyncio.run(demo())