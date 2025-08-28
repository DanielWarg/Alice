"""
Agent Orchestrator - Koordinerar hela Agent Core workflow.
Hanterar Planning → Execution → Criticism → Improvement cycles.
"""

from typing import Dict, Any, Optional, List, Callable, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import asyncio
import json
from .agent_planner import AgentPlanner, AgentPlan
from .agent_executor import AgentExecutor, ExecutionPlan, ExecutionStatus
from .agent_critic import AgentCritic, CriticReport, CriticLevel, RecommendationType

class WorkflowStatus(Enum):
    """Status för workflow execution"""
    PLANNING = "planning"
    EXECUTING = "executing" 
    EVALUATING = "evaluating"
    IMPROVING = "improving"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ImprovementStrategy(Enum):
    """Strategier för förbättring"""
    NONE = "none"                    # Ingen förbättring
    RETRY_FAILED = "retry_failed"    # Retry bara misslyckade steg
    OPTIMIZE_PLAN = "optimize_plan"  # Optimera hela planen
    ADAPTIVE = "adaptive"            # Adaptiv strategi baserat på kritik

@dataclass
class WorkflowConfig:
    """Konfiguration för workflow"""
    max_iterations: int = 3           # Max antal förbättrings-iterationer
    improvement_strategy: ImprovementStrategy = ImprovementStrategy.ADAPTIVE
    auto_improve: bool = True         # Automatisk förbättring
    min_success_score: float = 0.8    # Minsta score för att acceptera resultat
    enable_ai_planning: bool = False  # AI-baserad planering
    enable_ai_criticism: bool = False # AI-baserad kritik
    execution_timeout_seconds: int = 300  # Timeout för execution
    
@dataclass
class WorkflowIteration:
    """En iteration i workflow"""
    iteration_number: int
    plan: AgentPlan
    execution_result: Optional[ExecutionPlan] = None
    critic_report: Optional[CriticReport] = None
    improvement_applied: bool = False
    started_at: datetime = None
    completed_at: datetime = None
    
    def __post_init__(self):
        if self.started_at is None:
            self.started_at = datetime.now()

@dataclass
class WorkflowResult:
    """Slutresultat från workflow"""
    workflow_id: str
    original_goal: str
    status: WorkflowStatus
    iterations: List[WorkflowIteration]
    final_plan: Optional[AgentPlan] = None
    final_execution: Optional[ExecutionPlan] = None
    final_report: Optional[CriticReport] = None
    total_improvements: int = 0
    started_at: datetime = None
    completed_at: datetime = None
    
    def __post_init__(self):
        if self.started_at is None:
            self.started_at = datetime.now()
    
    @property
    def success(self) -> bool:
        """Om workflowet lyckades"""
        return (self.status == WorkflowStatus.COMPLETED and 
                self.final_execution and 
                self.final_execution.status == ExecutionStatus.COMPLETED)
    
    @property
    def final_score(self) -> float:
        """Final score från kritikern"""
        return self.final_report.overall_score if self.final_report else 0.0

class AgentOrchestrator:
    """
    Orchestrator som koordinerar hela Agent Core workflow.
    Hanterar Planning → Execution → Criticism → Improvement cycles.
    """
    
    def __init__(
        self,
        planner: Optional[AgentPlanner] = None,
        executor: Optional[AgentExecutor] = None,
        critic: Optional[AgentCritic] = None,
        config: Optional[WorkflowConfig] = None
    ):
        self.planner = planner or AgentPlanner()
        self.executor = executor or AgentExecutor()
        self.critic = critic or AgentCritic()
        self.config = config or WorkflowConfig()
        
        self.active_workflows: Dict[str, WorkflowResult] = {}
        self.workflow_hooks: Dict[str, List[Callable]] = {
            "before_planning": [],
            "after_planning": [],
            "before_execution": [],
            "after_execution": [],
            "before_criticism": [],
            "after_criticism": [],
            "before_improvement": [],
            "after_improvement": [],
            "workflow_complete": [],
            "workflow_failed": []
        }
    
    async def execute_workflow(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None,
        config_override: Optional[WorkflowConfig] = None,
        progress_callback: Optional[Callable] = None
    ) -> WorkflowResult:
        """
        Huvudmetod för att exekvera ett komplett agent workflow.
        
        Args:
            goal: Målet som ska uppnås
            context: Extra kontext för planeringen
            config_override: Override av standard-konfiguration  
            progress_callback: Callback för progress updates
            
        Returns:
            WorkflowResult med komplett historik och resultat
        """
        config = config_override or self.config
        workflow_id = f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        result = WorkflowResult(
            workflow_id=workflow_id,
            original_goal=goal,
            status=WorkflowStatus.PLANNING,
            iterations=[]
        )
        
        self.active_workflows[workflow_id] = result
        
        try:
            print(f"🎯 Starting workflow for goal: {goal}")
            iteration_count = 0
            current_plan = None
            
            while iteration_count < config.max_iterations:
                iteration_count += 1
                iteration = WorkflowIteration(
                    iteration_number=iteration_count,
                    plan=current_plan  # Will be set in planning phase
                )
                
                result.iterations.append(iteration)
                result.status = WorkflowStatus.PLANNING
                
                # === PLANNING PHASE ===
                print(f"🎯 Starting planning phase for iteration {iteration_count}")
                await self._run_hooks("before_planning", goal, context, iteration)
                
                if iteration_count == 1:
                    # First iteration - create new plan
                    print(f"🎯 Creating new plan...")
                    plan = await self.planner.create_plan(
                        goal=goal,
                        context=context,
                        language="swedish" if context and context.get("language") == "svenska" else "swedish"
                    )
                else:
                    # Improvement iteration - improve existing plan
                    plan = await self._improve_plan(
                        result.iterations[-2].plan,
                        result.iterations[-2].critic_report,
                        config.improvement_strategy
                    )
                
                iteration.plan = plan
                current_plan = plan
                
                await self._run_hooks("after_planning", plan, iteration)
                await self._notify_progress(progress_callback, result, "Planning completed")
                
                # === EXECUTION PHASE ===
                result.status = WorkflowStatus.EXECUTING
                await self._run_hooks("before_execution", plan, iteration)
                
                execution_result = await self.executor.execute_plan(
                    plan=plan,
                    context=context,
                    progress_callback=lambda ep: self._notify_progress(progress_callback, result, f"Executing: {ep.progress_percent:.1f}%")
                )
                
                iteration.execution_result = execution_result
                
                await self._run_hooks("after_execution", execution_result, iteration)
                await self._notify_progress(progress_callback, result, "Execution completed")
                
                # === CRITICISM PHASE ===
                result.status = WorkflowStatus.EVALUATING
                await self._run_hooks("before_criticism", plan, execution_result, iteration)
                
                critic_report = await self.critic.evaluate_execution(
                    plan=plan,
                    execution_result=execution_result,
                    context=context
                )
                
                iteration.critic_report = critic_report
                iteration.completed_at = datetime.now()
                
                await self._run_hooks("after_criticism", critic_report, iteration)
                await self._notify_progress(progress_callback, result, f"Evaluation completed (Score: {critic_report.overall_score:.2f})")
                
                # === DECISION PHASE ===
                # Kolla om resultatet är tillräckligt bra
                if (execution_result.status == ExecutionStatus.COMPLETED and 
                    critic_report.overall_score >= config.min_success_score):
                    # Success! Vi är klara
                    result.status = WorkflowStatus.COMPLETED
                    result.final_plan = plan
                    result.final_execution = execution_result
                    result.final_report = critic_report
                    break
                
                # Kolla om vi ska förbättra eller avbryta
                if not config.auto_improve or iteration_count >= config.max_iterations:
                    # Inga fler förbättringsförsök
                    if execution_result.status == ExecutionStatus.COMPLETED:
                        result.status = WorkflowStatus.COMPLETED
                    else:
                        result.status = WorkflowStatus.FAILED
                    
                    result.final_plan = plan
                    result.final_execution = execution_result 
                    result.final_report = critic_report
                    break
                
                # === IMPROVEMENT PHASE ===
                if config.auto_improve and self._should_improve(critic_report, config):
                    result.status = WorkflowStatus.IMPROVING
                    await self._run_hooks("before_improvement", critic_report, iteration)
                    
                    iteration.improvement_applied = True
                    result.total_improvements += 1
                    
                    await self._run_hooks("after_improvement", iteration)
                    await self._notify_progress(progress_callback, result, f"Improvement applied (Iteration {iteration_count + 1})")
                    
                    # Continue to next iteration
                else:
                    # No improvement needed/possible
                    result.status = WorkflowStatus.COMPLETED if execution_result.status == ExecutionStatus.COMPLETED else WorkflowStatus.FAILED
                    result.final_plan = plan
                    result.final_execution = execution_result
                    result.final_report = critic_report
                    break
            
            # Set final timestamps
            result.completed_at = datetime.now()
            
            # Run completion hooks
            if result.success:
                await self._run_hooks("workflow_complete", result)
            else:
                await self._run_hooks("workflow_failed", result)
            
            await self._notify_progress(progress_callback, result, f"Workflow completed: {result.status.value}")
            
            return result
            
        except Exception as e:
            # Handle workflow errors
            print(f"🚨 Workflow failed with exception: {e}")
            import traceback
            traceback.print_exc()
            result.status = WorkflowStatus.FAILED
            result.completed_at = datetime.now()
            
            await self._run_hooks("workflow_failed", result, str(e))
            await self._notify_progress(progress_callback, result, f"Workflow failed: {str(e)}")
            
            return result
        finally:
            # Cleanup
            if workflow_id in self.active_workflows:
                del self.active_workflows[workflow_id]
    
    async def _improve_plan(
        self,
        original_plan: AgentPlan, 
        critic_report: CriticReport,
        strategy: ImprovementStrategy
    ) -> AgentPlan:
        """Förbättra en plan baserat på kritik"""
        if not critic_report or not critic_report.recommendations:
            return original_plan
        
        improved_plan = AgentPlan(
            plan_id=f"{original_plan.plan_id}_improved",
            goal=original_plan.goal,
            actions=original_plan.actions.copy(),
            created_at=datetime.now(),
            confidence_score=original_plan.confidence_score
        )
        
        if strategy == ImprovementStrategy.RETRY_FAILED:
            # Retry bara misslyckade actions - basic strategy
            pass  # ExecutionResult redan hanterar retries
            
        elif strategy == ImprovementStrategy.OPTIMIZE_PLAN:
            # Optimera hela planen
            improved_plan = self.planner.optimize_plan(improved_plan)
            
        elif strategy == ImprovementStrategy.ADAPTIVE:
            # Adaptiv strategi baserat på recommendations
            high_priority_recs = [r for r in critic_report.recommendations if r.priority >= 7]
            
            for rec in high_priority_recs:
                if rec.type == RecommendationType.REMOVE_STEP and rec.target_step_id:
                    # Ta bort problematiskt steg
                    improved_plan.actions = [a for a in improved_plan.actions if a.step_id != rec.target_step_id]
                
                elif rec.type == RecommendationType.MODIFY_PARAMETERS and rec.target_step_id:
                    # Modifiera parameters
                    for action in improved_plan.actions:
                        if action.step_id == rec.target_step_id and rec.suggested_changes:
                            action.parameters.update(rec.suggested_changes)
                
                elif rec.type == RecommendationType.OPTIMIZE_ORDER:
                    # Optimera ordningen
                    improved_plan = self.planner.optimize_plan(improved_plan)
        
        return improved_plan
    
    def _should_improve(self, critic_report: CriticReport, config: WorkflowConfig) -> bool:
        """Avgör om vi ska försöka förbättra planen"""
        if not critic_report:
            return False
        
        # Förbättra om score är under threshold
        if critic_report.overall_score < config.min_success_score:
            return True
        
        # Förbättra om det finns högt prioriterade recommendations
        high_priority_recs = [r for r in critic_report.recommendations if r.priority >= 8]
        return len(high_priority_recs) > 0
    
    async def _run_hooks(self, hook_type: str, *args):
        """Kör registrerade hooks"""
        if hook_type in self.workflow_hooks:
            for hook in self.workflow_hooks[hook_type]:
                try:
                    if asyncio.iscoroutinefunction(hook):
                        await hook(*args)
                    else:
                        hook(*args)
                except Exception:
                    # Ignore hook errors to not break workflow
                    pass
    
    async def _notify_progress(
        self, 
        callback: Optional[Callable], 
        result: WorkflowResult, 
        message: str
    ):
        """Notify progress callback"""
        if callback:
            try:
                progress_info = {
                    "workflow_id": result.workflow_id,
                    "status": result.status.value,
                    "iteration": len(result.iterations),
                    "message": message,
                    "timestamp": datetime.now().isoformat()
                }
                
                if asyncio.iscoroutinefunction(callback):
                    await callback(progress_info)
                else:
                    callback(progress_info)
            except Exception:
                # Ignore callback errors
                pass
    
    def add_workflow_hook(self, hook_type: str, callback: Callable):
        """Lägg till workflow hook"""
        if hook_type in self.workflow_hooks:
            self.workflow_hooks[hook_type].append(callback)
    
    def remove_workflow_hook(self, hook_type: str, callback: Callable):
        """Ta bort workflow hook"""
        if hook_type in self.workflow_hooks and callback in self.workflow_hooks[hook_type]:
            self.workflow_hooks[hook_type].remove(callback)
    
    async def cancel_workflow(self, workflow_id: str) -> bool:
        """Avbryt ett pågående workflow"""
        if workflow_id in self.active_workflows:
            result = self.active_workflows[workflow_id]
            result.status = WorkflowStatus.CANCELLED
            result.completed_at = datetime.now()
            
            # Try to cancel execution if running
            if result.final_execution and result.final_execution.status == ExecutionStatus.IN_PROGRESS:
                await self.executor.cancel_execution(result.final_execution.plan_id)
            
            return True
        return False
    
    def get_workflow_status(self, workflow_id: str) -> Optional[WorkflowResult]:
        """Hämta status för ett workflow"""
        return self.active_workflows.get(workflow_id)
    
    def get_active_workflows(self) -> List[str]:
        """Hämta lista över aktiva workflows"""
        return list(self.active_workflows.keys())
    
    def get_workflow_statistics(self) -> Dict[str, Any]:
        """Hämta statistik över workflows"""
        # This would be implemented with persistent storage
        return {
            "total_workflows": 0,
            "successful_workflows": 0, 
            "failed_workflows": 0,
            "average_iterations": 0.0,
            "average_success_score": 0.0
        }
    
    async def execute_simple_goal(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Enkel metod för att exekvera ett mål och returnera success/failure.
        
        Returns:
            Tuple av (success: bool, result_summary: Dict)
        """
        result = await self.execute_workflow(goal, context)
        
        summary = {
            "workflow_id": result.workflow_id,
            "goal": result.original_goal,
            "success": result.success,
            "status": result.status.value,
            "iterations": len(result.iterations),
            "improvements": result.total_improvements,
            "final_score": result.final_score,
            "execution_time_seconds": (result.completed_at - result.started_at).total_seconds() if result.completed_at else 0
        }
        
        if result.final_execution and result.final_execution.results:
            summary["actions_completed"] = result.final_execution.completed_actions
            summary["actions_failed"] = result.final_execution.failed_actions
            summary["execution_results"] = result.final_execution.results
            
        if result.final_report:
            summary["insights"] = len(result.final_report.insights)
            summary["recommendations"] = len(result.final_report.recommendations)
            summary["critic_summary"] = result.final_report.summary
        
        return result.success, summary