"""
Core-modul för Alice-systemet.
Innehåller verktygsspecifikationer, registry, router och preflight-kontroller.
"""

from .tool_specs import (
    TOOL_SPECS,
    enabled_tools,
    build_harmony_tool_specs,
    get_tool_spec,
    is_tool_enabled
)

from .tool_registry import (
    validate_and_execute_tool,
    list_tool_specs,
    get_executor_names
)

from .router import (
    classify,
    classify_volume,
    get_router_stats
)

from .preflight import (
    run_preflight_checks,
    check_tool_surface_consistency,
    check_environment_variables,
    log_preflight_results
)

from .agent_executor import (
    AgentExecutor,
    ExecutionStatus,
    ExecutionResult,
    ExecutionPlan
)

from .agent_critic import (
    AgentCritic,
    CriticLevel,
    RecommendationType,
    CriticInsight,
    CriticRecommendation,
    CriticReport
)

from .agent_orchestrator import (
    AgentOrchestrator,
    WorkflowStatus,
    ImprovementStrategy,
    WorkflowConfig,
    WorkflowIteration,
    WorkflowResult
)

__all__ = [
    # Tool specs
    "TOOL_SPECS",
    "enabled_tools", 
    "build_harmony_tool_specs",
    "get_tool_spec",
    "is_tool_enabled",
    
    # Tool registry
    "validate_and_execute_tool",
    "list_tool_specs",
    "get_executor_names",
    
    # Router
    "classify",
    "classify_volume", 
    "get_router_stats",
    
    # Preflight
    "run_preflight_checks",
    "check_tool_surface_consistency",
    "check_environment_variables",
    "log_preflight_results",
    
    # Agent Executor
    "AgentExecutor",
    "ExecutionStatus", 
    "ExecutionResult",
    "ExecutionPlan",
    
    # Agent Critic
    "AgentCritic",
    "CriticLevel",
    "RecommendationType",
    "CriticInsight",
    "CriticRecommendation",
    "CriticReport",
    
    # Agent Orchestrator
    "AgentOrchestrator",
    "WorkflowStatus",
    "ImprovementStrategy",
    "WorkflowConfig",
    "WorkflowIteration",
    "WorkflowResult"
]
