"""
Agent Executor - Exekverar handlingsplaner från AgentPlanner.
Hanterar stegvis utförande, felhantering och progress tracking.
"""

from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import asyncio
import json
from .agent_planner import AgentPlan, AgentAction
from .tool_registry import validate_and_execute_tool

class ExecutionStatus(Enum):
    """Status för en execution"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"

@dataclass
class ExecutionResult:
    """Resultat från en utförd action"""
    action_id: str
    status: ExecutionStatus
    result: Dict[str, Any] = None
    error_message: str = None
    execution_time_ms: int = 0
    started_at: datetime = None
    completed_at: datetime = None
    retry_count: int = 0
    
    def __post_init__(self):
        if self.result is None:
            self.result = {}

@dataclass
class ExecutionPlan:
    """Plan execution state tracking"""
    plan_id: str
    goal: str
    status: ExecutionStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_actions: int = 0
    completed_actions: int = 0
    failed_actions: int = 0
    results: Dict[str, ExecutionResult] = None
    current_step: str = None
    
    def __post_init__(self):
        if self.results is None:
            self.results = {}
    
    @property
    def progress_percent(self) -> float:
        """Beräkna progress i procent"""
        if self.total_actions == 0:
            return 0.0
        return (self.completed_actions / self.total_actions) * 100

class AgentExecutor:
    """
    Executor som utför AgentPlaner steg för steg.
    Hanterar dependencies, retries, parallellisering och error recovery.
    """
    
    def __init__(self, max_parallel_actions: int = 3, default_timeout_ms: int = 30000):
        self.max_parallel_actions = max_parallel_actions
        self.default_timeout_ms = default_timeout_ms
        self.active_executions: Dict[str, ExecutionPlan] = {}
        self.execution_hooks: Dict[str, List[Callable]] = {
            "before_action": [],
            "after_action": [],
            "on_error": [],
            "on_plan_complete": []
        }
    
    async def execute_plan(
        self,
        plan: AgentPlan,
        context: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable] = None
    ) -> ExecutionPlan:
        """
        Exekvera en komplett handlingsplan.
        
        Args:
            plan: AgentPlan att exekvera
            context: Extra kontext för execution
            progress_callback: Callback för progress updates
            
        Returns:
            ExecutionPlan med resultat och status
        """
        execution_plan = ExecutionPlan(
            plan_id=plan.plan_id,
            goal=plan.goal,
            status=ExecutionStatus.IN_PROGRESS,
            started_at=datetime.now(),
            total_actions=len(plan.actions)
        )
        
        self.active_executions[plan.plan_id] = execution_plan
        
        try:
            # Kör alla actions enligt dependencies
            completed_steps = []
            
            while len(completed_steps) < len(plan.actions):
                # Hämta nästa actions som kan köras
                next_actions = plan.get_next_actions(completed_steps)
                
                if not next_actions:
                    # Kolla om vi är fast i en deadlock
                    remaining_actions = [a for a in plan.actions if a.step_id not in completed_steps]
                    if remaining_actions:
                        # Det finns actions kvar men inga kan köras - dependency problem
                        for action in remaining_actions:
                            result = ExecutionResult(
                                action_id=action.step_id,
                                status=ExecutionStatus.FAILED,
                                error_message="Dependency deadlock - required dependencies not satisfied",
                                started_at=datetime.now(),
                                completed_at=datetime.now()
                            )
                            execution_plan.results[action.step_id] = result
                            execution_plan.failed_actions += 1
                    break
                
                # Exekvera actions (parallellt om möjligt)
                if len(next_actions) == 1:
                    # En action - kör synkront
                    result = await self._execute_single_action(
                        next_actions[0], context, execution_plan
                    )
                    self._process_action_result(result, completed_steps, execution_plan)
                else:
                    # Flera actions - kör parallellt
                    results = await self._execute_parallel_actions(
                        next_actions[:self.max_parallel_actions], context, execution_plan
                    )
                    for result in results:
                        self._process_action_result(result, completed_steps, execution_plan)
                
                # Uppdatera progress
                if progress_callback:
                    await self._call_progress_callback(progress_callback, execution_plan)
            
            # Slutförd execution
            execution_plan.status = ExecutionStatus.COMPLETED if execution_plan.failed_actions == 0 else ExecutionStatus.FAILED
            execution_plan.completed_at = datetime.now()
            
            # Kör completion hooks
            await self._run_hooks("on_plan_complete", execution_plan)
            
            return execution_plan
            
        except Exception as e:
            execution_plan.status = ExecutionStatus.FAILED
            execution_plan.completed_at = datetime.now()
            
            # Lägg till fel som resultat för nuvarande steg
            if execution_plan.current_step:
                error_result = ExecutionResult(
                    action_id=execution_plan.current_step,
                    status=ExecutionStatus.FAILED,
                    error_message=f"Plan execution failed: {str(e)}",
                    started_at=datetime.now(),
                    completed_at=datetime.now()
                )
                execution_plan.results[execution_plan.current_step] = error_result
            
            return execution_plan
        finally:
            # Rensa från active executions
            if plan.plan_id in self.active_executions:
                del self.active_executions[plan.plan_id]
    
    async def _execute_single_action(
        self,
        action: AgentAction,
        context: Optional[Dict[str, Any]],
        execution_plan: ExecutionPlan
    ) -> ExecutionResult:
        """Exekvera en enskild action"""
        execution_plan.current_step = action.step_id
        
        result = ExecutionResult(
            action_id=action.step_id,
            status=ExecutionStatus.IN_PROGRESS,
            started_at=datetime.now()
        )
        
        try:
            # Kör before_action hooks
            await self._run_hooks("before_action", action, context)
            
            # Utför verktygsanrop
            start_time = datetime.now()
            tool_result = validate_and_execute_tool(action.tool, action.parameters)
            end_time = datetime.now()
            
            result.execution_time_ms = int((end_time - start_time).total_seconds() * 1000)
            result.completed_at = end_time
            
            if tool_result.get("ok", False):
                result.status = ExecutionStatus.COMPLETED
                result.result = {
                    "success": True,
                    "message": tool_result.get("message", ""),
                    "tool": action.tool,
                    "parameters": action.parameters
                }
            else:
                result.status = ExecutionStatus.FAILED
                result.error_message = tool_result.get("message", "Tool execution failed")
                result.result = {"success": False, "tool": action.tool}
            
            # Kör after_action hooks
            await self._run_hooks("after_action", action, result, context)
            
            return result
            
        except Exception as e:
            result.status = ExecutionStatus.FAILED
            result.error_message = str(e)
            result.completed_at = datetime.now()
            result.execution_time_ms = int((datetime.now() - result.started_at).total_seconds() * 1000)
            
            # Kör error hooks
            await self._run_hooks("on_error", action, e, context)
            
            return result
    
    async def _execute_parallel_actions(
        self,
        actions: List[AgentAction],
        context: Optional[Dict[str, Any]],
        execution_plan: ExecutionPlan
    ) -> List[ExecutionResult]:
        """Exekvera flera actions parallellt"""
        tasks = []
        for action in actions:
            task = asyncio.create_task(
                self._execute_single_action(action, context, execution_plan)
            )
            tasks.append(task)
        
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    def _process_action_result(
        self,
        result: ExecutionResult,
        completed_steps: List[str],
        execution_plan: ExecutionPlan
    ):
        """Bearbeta resultat från en action"""
        execution_plan.results[result.action_id] = result
        
        # Lägg till i completed_steps oavsett status för att undvika infinite loops
        completed_steps.append(result.action_id)
        
        if result.status == ExecutionStatus.COMPLETED:
            execution_plan.completed_actions += 1
        elif result.status == ExecutionStatus.FAILED:
            execution_plan.failed_actions += 1
    
    async def _call_progress_callback(self, callback: Callable, execution_plan: ExecutionPlan):
        """Anropa progress callback säkert"""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(execution_plan)
            else:
                callback(execution_plan)
        except Exception:
            # Ignore callback errors
            pass
    
    async def _run_hooks(self, hook_type: str, *args):
        """Kör registrerade hooks av given typ"""
        if hook_type in self.execution_hooks:
            for hook in self.execution_hooks[hook_type]:
                try:
                    if asyncio.iscoroutinefunction(hook):
                        await hook(*args)
                    else:
                        hook(*args)
                except Exception:
                    # Ignore hook errors to not break execution
                    pass
    
    def add_execution_hook(self, hook_type: str, callback: Callable):
        """Lägg till execution hook"""
        if hook_type in self.execution_hooks:
            self.execution_hooks[hook_type].append(callback)
    
    def remove_execution_hook(self, hook_type: str, callback: Callable):
        """Ta bort execution hook"""
        if hook_type in self.execution_hooks and callback in self.execution_hooks[hook_type]:
            self.execution_hooks[hook_type].remove(callback)
    
    async def cancel_execution(self, plan_id: str) -> bool:
        """Avbryt en pågående execution"""
        if plan_id in self.active_executions:
            execution_plan = self.active_executions[plan_id]
            execution_plan.status = ExecutionStatus.CANCELLED
            execution_plan.completed_at = datetime.now()
            return True
        return False
    
    def get_execution_status(self, plan_id: str) -> Optional[ExecutionPlan]:
        """Hämta status för en execution"""
        return self.active_executions.get(plan_id)
    
    def get_active_executions(self) -> List[str]:
        """Hämta lista över aktiva execution-IDs"""
        return list(self.active_executions.keys())
    
    async def retry_failed_action(
        self,
        plan_id: str,
        action_id: str,
        max_retries: int = 3
    ) -> Optional[ExecutionResult]:
        """Retry en misslyckad action"""
        execution_plan = self.active_executions.get(plan_id)
        if not execution_plan or action_id not in execution_plan.results:
            return None
        
        previous_result = execution_plan.results[action_id]
        if previous_result.status != ExecutionStatus.FAILED:
            return previous_result
        
        if previous_result.retry_count >= max_retries:
            return previous_result
        
        # Hitta original action (skulle behöva referens till ursprungsplanen)
        # För nu, returnera bara previous_result
        # TODO: Implementera retry-logik med original action data
        
        return previous_result