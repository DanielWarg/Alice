"""
Agent Critic - Evaluerar och förbättrar resultat från AgentExecutor.
Analyserar framgång, identifierar problem och föreslår förbättringar.
"""

from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import json
from .agent_planner import AgentPlan, AgentAction
from .agent_executor import ExecutionPlan, ExecutionResult, ExecutionStatus

class CriticLevel(Enum):
    """Olika nivåer av kritik"""
    SUCCESS = "success"        # Allt gick bra
    WARNING = "warning"        # Mindre problem
    ERROR = "error"           # Allvarliga problem
    CRITICAL = "critical"     # Kritiska fel

class RecommendationType(Enum):
    """Typer av rekommendationer"""
    RETRY_ACTION = "retry_action"
    MODIFY_PARAMETERS = "modify_parameters"
    CHANGE_TOOL = "change_tool"
    ADD_DEPENDENCY = "add_dependency"
    REMOVE_STEP = "remove_step"
    OPTIMIZE_ORDER = "optimize_order"
    INCREASE_TIMEOUT = "increase_timeout"

@dataclass
class CriticInsight:
    """En enskild insikt från kritiken"""
    level: CriticLevel
    category: str
    message: str
    affected_steps: List[str] = None
    confidence: float = 0.0
    evidence: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.affected_steps is None:
            self.affected_steps = []
        if self.evidence is None:
            self.evidence = {}

@dataclass
class CriticRecommendation:
    """En rekommendation för förbättring"""
    type: RecommendationType
    priority: int  # 1-10, högre = viktigare
    description: str
    target_step_id: str = None
    suggested_changes: Dict[str, Any] = None
    expected_improvement: str = None
    confidence: float = 0.0
    
    def __post_init__(self):
        if self.suggested_changes is None:
            self.suggested_changes = {}

@dataclass
class CriticReport:
    """Komplett utvärderingsrapport från kritikern"""
    plan_id: str
    evaluation_timestamp: datetime
    overall_score: float  # 0.0-1.0
    overall_level: CriticLevel
    summary: str
    insights: List[CriticInsight] = None
    recommendations: List[CriticRecommendation] = None
    performance_metrics: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.insights is None:
            self.insights = []
        if self.recommendations is None:
            self.recommendations = []
        if self.performance_metrics is None:
            self.performance_metrics = {}

class AgentCritic:
    """
    Critic som analyserar execution-resultat och ger feedback.
    Identifierar problem, mäter prestanda och föreslår förbättringar.
    """
    
    def __init__(self, enable_ai_analysis: bool = False):
        self.enable_ai_analysis = enable_ai_analysis
        self.evaluation_rules = self._initialize_evaluation_rules()
        self.performance_thresholds = {
            "execution_time_warning_ms": 5000,    # Varna om steg tar >5s
            "execution_time_critical_ms": 15000,   # Kritisk om steg tar >15s
            "retry_count_warning": 2,              # Varna om >2 retries
            "failure_rate_warning": 0.2,          # Varna om >20% failure rate
            "failure_rate_critical": 0.5          # Kritisk om >50% failure rate
        }
        
    def _initialize_evaluation_rules(self) -> Dict[str, Callable]:
        """Initialisera regelbaserade utvärderingar"""
        return {
            "execution_success": self._evaluate_execution_success,
            "performance_analysis": self._evaluate_performance,
            "dependency_analysis": self._evaluate_dependencies,
            "tool_usage_analysis": self._evaluate_tool_usage,
            "error_pattern_analysis": self._evaluate_error_patterns,
            "optimization_opportunities": self._identify_optimizations
        }
    
    async def evaluate_execution(
        self,
        plan: AgentPlan,
        execution_result: ExecutionPlan,
        context: Optional[Dict[str, Any]] = None
    ) -> CriticReport:
        """
        Huvudmetod för att utvärdera en execution.
        
        Args:
            plan: Original plan som exekverades
            execution_result: Resultat från AgentExecutor
            context: Extra kontext för utvärdering
            
        Returns:
            CriticReport med detaljerad analys
        """
        report = CriticReport(
            plan_id=plan.plan_id,
            evaluation_timestamp=datetime.now(),
            overall_score=0.0,
            overall_level=CriticLevel.SUCCESS,
            summary=""
        )
        
        try:
            # Kör alla utvärderingsregler
            all_insights = []
            all_recommendations = []
            
            for rule_name, rule_func in self.evaluation_rules.items():
                try:
                    insights, recommendations = rule_func(plan, execution_result, context)
                    all_insights.extend(insights)
                    all_recommendations.extend(recommendations)
                except Exception as e:
                    # Logga fel men fortsätt med andra regler
                    error_insight = CriticInsight(
                        level=CriticLevel.WARNING,
                        category="evaluation_error",
                        message=f"Evalueringsregel '{rule_name}' misslyckades: {str(e)}",
                        confidence=0.8
                    )
                    all_insights.append(error_insight)
            
            # Sammanställ rapport
            report.insights = all_insights
            report.recommendations = sorted(all_recommendations, key=lambda r: r.priority, reverse=True)
            report.overall_score = self._calculate_overall_score(execution_result, all_insights)
            report.overall_level = self._determine_overall_level(all_insights)
            report.summary = self._generate_summary(execution_result, all_insights, all_recommendations)
            report.performance_metrics = self._calculate_performance_metrics(execution_result)
            
            # AI-baserad analys (om aktiverad)
            if self.enable_ai_analysis:
                ai_insights = await self._perform_ai_analysis(plan, execution_result, context)
                report.insights.extend(ai_insights)
            
            return report
            
        except Exception as e:
            # Fallback-rapport vid fel
            fallback_insight = CriticInsight(
                level=CriticLevel.ERROR,
                category="critical_error",
                message=f"Kritisk fel i utvärdering: {str(e)}",
                confidence=1.0
            )
            
            report.insights = [fallback_insight]
            report.overall_score = 0.1
            report.overall_level = CriticLevel.CRITICAL
            report.summary = "Utvärdering kunde inte genomföras på grund av kritiskt fel"
            
            return report
    
    def _evaluate_execution_success(
        self, 
        plan: AgentPlan, 
        execution_result: ExecutionPlan, 
        context: Optional[Dict[str, Any]]
    ) -> tuple[List[CriticInsight], List[CriticRecommendation]]:
        """Utvärdera grundläggande framgång för execution"""
        insights = []
        recommendations = []
        
        total_actions = execution_result.total_actions
        completed_actions = execution_result.completed_actions
        failed_actions = execution_result.failed_actions
        
        if execution_result.status == ExecutionStatus.COMPLETED and failed_actions == 0:
            insights.append(CriticInsight(
                level=CriticLevel.SUCCESS,
                category="execution_success",
                message=f"All {total_actions} actions slutfördes framgångsrikt",
                confidence=1.0,
                evidence={"completed_actions": completed_actions, "failed_actions": failed_actions}
            ))
        elif execution_result.status == ExecutionStatus.FAILED:
            failure_rate = failed_actions / total_actions if total_actions > 0 else 0
            
            level = CriticLevel.CRITICAL if failure_rate >= self.performance_thresholds["failure_rate_critical"] else CriticLevel.ERROR
            
            insights.append(CriticInsight(
                level=level,
                category="execution_failure",
                message=f"Execution misslyckades: {failed_actions}/{total_actions} actions failed ({failure_rate:.1%})",
                confidence=1.0,
                evidence={"failure_rate": failure_rate, "failed_actions": failed_actions}
            ))
            
            # Rekommendera retry för misslyckade actions
            for step_id, result in execution_result.results.items():
                if result.status == ExecutionStatus.FAILED and result.retry_count < 3:
                    recommendations.append(CriticRecommendation(
                        type=RecommendationType.RETRY_ACTION,
                        priority=8,
                        description=f"Retry misslyckad action: {result.error_message}",
                        target_step_id=step_id,
                        expected_improvement="Högre chans för framgång vid retry",
                        confidence=0.7
                    ))
        
        return insights, recommendations
    
    def _evaluate_performance(
        self, 
        plan: AgentPlan, 
        execution_result: ExecutionPlan, 
        context: Optional[Dict[str, Any]]
    ) -> tuple[List[CriticInsight], List[CriticRecommendation]]:
        """Utvärdera prestanda-aspekter"""
        insights = []
        recommendations = []
        
        # Analysera execution-tider
        slow_steps = []
        very_slow_steps = []
        
        for step_id, result in execution_result.results.items():
            if result.execution_time_ms > self.performance_thresholds["execution_time_critical_ms"]:
                very_slow_steps.append((step_id, result.execution_time_ms))
            elif result.execution_time_ms > self.performance_thresholds["execution_time_warning_ms"]:
                slow_steps.append((step_id, result.execution_time_ms))
        
        if very_slow_steps:
            insights.append(CriticInsight(
                level=CriticLevel.CRITICAL,
                category="performance",
                message=f"{len(very_slow_steps)} steg tog extremt lång tid att exekvera",
                affected_steps=[step for step, _ in very_slow_steps],
                confidence=0.9,
                evidence={"slow_steps": dict(very_slow_steps)}
            ))
            
            for step_id, time_ms in very_slow_steps:
                recommendations.append(CriticRecommendation(
                    type=RecommendationType.INCREASE_TIMEOUT,
                    priority=6,
                    description=f"Öka timeout för långsamt steg {step_id} ({time_ms}ms)",
                    target_step_id=step_id,
                    expected_improvement="Undvik timeouts för långsamma operationer",
                    confidence=0.8
                ))
        
        elif slow_steps:
            insights.append(CriticInsight(
                level=CriticLevel.WARNING,
                category="performance",
                message=f"{len(slow_steps)} steg tog längre tid än förväntat",
                affected_steps=[step for step, _ in slow_steps],
                confidence=0.8,
                evidence={"slow_steps": dict(slow_steps)}
            ))
        
        return insights, recommendations
    
    def _evaluate_dependencies(
        self, 
        plan: AgentPlan, 
        execution_result: ExecutionPlan, 
        context: Optional[Dict[str, Any]]
    ) -> tuple[List[CriticInsight], List[CriticRecommendation]]:
        """Analysera dependency-hantering"""
        insights = []
        recommendations = []
        
        # Kolla efter dependency-problem
        deadlock_actions = []
        for step_id, result in execution_result.results.items():
            if "deadlock" in (result.error_message or "").lower():
                deadlock_actions.append(step_id)
        
        if deadlock_actions:
            insights.append(CriticInsight(
                level=CriticLevel.ERROR,
                category="dependencies",
                message="Dependency deadlock upptäckt - cirkulära dependencies",
                affected_steps=deadlock_actions,
                confidence=1.0
            ))
            
            recommendations.append(CriticRecommendation(
                type=RecommendationType.REMOVE_STEP,
                priority=9,
                description="Ta bort cirkulära dependencies genom att omstrukturera plan",
                expected_improvement="Eliminera deadlock-risk",
                confidence=0.9
            ))
        
        # Analysera dependency-effektivitet
        sequential_steps = 0
        for action in plan.actions:
            if len(action.depends_on) > 0:
                sequential_steps += 1
        
        if sequential_steps == len(plan.actions) - 1:  # Alla steg beroende av föregående
            insights.append(CriticInsight(
                level=CriticLevel.WARNING,
                category="dependencies",
                message="Planen är helt sekventiell - inga möjligheter för parallellisering",
                confidence=0.7
            ))
            
            recommendations.append(CriticRecommendation(
                type=RecommendationType.OPTIMIZE_ORDER,
                priority=5,
                description="Identifiera steg som kan köras parallellt",
                expected_improvement="Snabbare execution genom parallellisering",
                confidence=0.6
            ))
        
        return insights, recommendations
    
    def _evaluate_tool_usage(
        self, 
        plan: AgentPlan, 
        execution_result: ExecutionPlan, 
        context: Optional[Dict[str, Any]]
    ) -> tuple[List[CriticInsight], List[CriticRecommendation]]:
        """Analysera verktygsanvändning"""
        insights = []
        recommendations = []
        
        # Räkna verktygsanvändning
        tool_usage = {}
        tool_failures = {}
        
        for action in plan.actions:
            tool = action.tool
            tool_usage[tool] = tool_usage.get(tool, 0) + 1
            
            result = execution_result.results.get(action.step_id)
            if result and result.status == ExecutionStatus.FAILED:
                tool_failures[tool] = tool_failures.get(tool, 0) + 1
        
        # Identifiera problematiska verktyg
        for tool, failure_count in tool_failures.items():
            total_usage = tool_usage[tool]
            failure_rate = failure_count / total_usage
            
            if failure_rate >= 0.5:
                insights.append(CriticInsight(
                    level=CriticLevel.ERROR,
                    category="tool_usage",
                    message=f"Verktyg '{tool}' har hög failure rate: {failure_rate:.1%}",
                    confidence=0.9,
                    evidence={"tool": tool, "failure_rate": failure_rate, "failures": failure_count}
                ))
                
                recommendations.append(CriticRecommendation(
                    type=RecommendationType.CHANGE_TOOL,
                    priority=7,
                    description=f"Överväg alternativ till verktyg '{tool}' som ofta misslyckas",
                    expected_improvement="Högre success rate",
                    confidence=0.7
                ))
        
        return insights, recommendations
    
    def _evaluate_error_patterns(
        self, 
        plan: AgentPlan, 
        execution_result: ExecutionPlan, 
        context: Optional[Dict[str, Any]]
    ) -> tuple[List[CriticInsight], List[CriticRecommendation]]:
        """Analysera fel-mönster"""
        insights = []
        recommendations = []
        
        # Samla fel-meddelanden
        error_messages = []
        for result in execution_result.results.values():
            if result.error_message:
                error_messages.append(result.error_message.lower())
        
        if not error_messages:
            return insights, recommendations
        
        # Analysera vanliga fel-mönster
        common_patterns = {
            "timeout": ["timeout", "timed out", "time exceeded"],
            "permission": ["permission", "denied", "unauthorized", "forbidden"],
            "network": ["connection", "network", "unreachable", "dns"],
            "parameter": ["parameter", "argument", "invalid", "missing"]
        }
        
        for pattern_name, keywords in common_patterns.items():
            matching_errors = sum(1 for msg in error_messages if any(kw in msg for kw in keywords))
            
            if matching_errors > 0:
                insights.append(CriticInsight(
                    level=CriticLevel.WARNING,
                    category="error_patterns",
                    message=f"Upptäckte {matching_errors} fel relaterade till {pattern_name}",
                    confidence=0.8,
                    evidence={"pattern": pattern_name, "count": matching_errors}
                ))
                
                # Specifika rekommendationer baserat på fel-typ
                if pattern_name == "parameter":
                    recommendations.append(CriticRecommendation(
                        type=RecommendationType.MODIFY_PARAMETERS,
                        priority=8,
                        description="Validera och korrigera parameters innan execution",
                        expected_improvement="Färre parameter-relaterade fel",
                        confidence=0.8
                    ))
        
        return insights, recommendations
    
    def _identify_optimizations(
        self, 
        plan: AgentPlan, 
        execution_result: ExecutionPlan, 
        context: Optional[Dict[str, Any]]
    ) -> tuple[List[CriticInsight], List[CriticRecommendation]]:
        """Identifiera optimeringsmöjligheter"""
        insights = []
        recommendations = []
        
        # Kolla efter redundanta steg
        tool_sequences = []
        for action in plan.actions:
            tool_sequences.append(action.tool)
        
        # Hitta upprepade verktyg i rad
        redundant_sequences = []
        for i in range(len(tool_sequences) - 1):
            if tool_sequences[i] == tool_sequences[i + 1]:
                redundant_sequences.append((i, tool_sequences[i]))
        
        if redundant_sequences:
            insights.append(CriticInsight(
                level=CriticLevel.WARNING,
                category="optimization",
                message=f"Upptäckte {len(redundant_sequences)} potentiellt redundanta steg-sekvenser",
                confidence=0.6
            ))
            
            recommendations.append(CriticRecommendation(
                type=RecommendationType.OPTIMIZE_ORDER,
                priority=4,
                description="Kombinera eller eliminera redundanta steg",
                expected_improvement="Snabbare execution och färre steg",
                confidence=0.6
            ))
        
        # Kolla efter förbättringsmöjligheter i success rate
        if execution_result.completed_actions > 0 and execution_result.failed_actions == 0:
            insights.append(CriticInsight(
                level=CriticLevel.SUCCESS,
                category="optimization",
                message="Execution var 100% framgångsrik - bra planering!",
                confidence=1.0
            ))
        
        return insights, recommendations
    
    def _calculate_overall_score(
        self, 
        execution_result: ExecutionPlan, 
        insights: List[CriticInsight]
    ) -> float:
        """Beräkna övergripande score 0.0-1.0"""
        base_score = 0.5
        
        # Success rate påverkan
        if execution_result.total_actions > 0:
            success_rate = execution_result.completed_actions / execution_result.total_actions
            base_score = success_rate
        
        # Justera baserat på insight-levels
        critical_count = sum(1 for i in insights if i.level == CriticLevel.CRITICAL)
        error_count = sum(1 for i in insights if i.level == CriticLevel.ERROR)
        warning_count = sum(1 for i in insights if i.level == CriticLevel.WARNING)
        success_count = sum(1 for i in insights if i.level == CriticLevel.SUCCESS)
        
        # Penalty för fel
        score_penalty = (critical_count * 0.3) + (error_count * 0.2) + (warning_count * 0.1)
        # Bonus för framgångar
        score_bonus = success_count * 0.05
        
        final_score = max(0.0, min(1.0, base_score - score_penalty + score_bonus))
        return final_score
    
    def _determine_overall_level(self, insights: List[CriticInsight]) -> CriticLevel:
        """Bestäm övergripande nivå baserat på insights"""
        if any(i.level == CriticLevel.CRITICAL for i in insights):
            return CriticLevel.CRITICAL
        elif any(i.level == CriticLevel.ERROR for i in insights):
            return CriticLevel.ERROR
        elif any(i.level == CriticLevel.WARNING for i in insights):
            return CriticLevel.WARNING
        else:
            return CriticLevel.SUCCESS
    
    def _generate_summary(
        self, 
        execution_result: ExecutionPlan, 
        insights: List[CriticInsight], 
        recommendations: List[CriticRecommendation]
    ) -> str:
        """Generera sammanfattning av utvärderingen"""
        total = execution_result.total_actions
        completed = execution_result.completed_actions
        failed = execution_result.failed_actions
        
        summary_parts = [
            f"Execution av {total} steg: {completed} lyckades, {failed} misslyckades."
        ]
        
        if insights:
            critical_count = sum(1 for i in insights if i.level == CriticLevel.CRITICAL)
            error_count = sum(1 for i in insights if i.level == CriticLevel.ERROR)
            warning_count = sum(1 for i in insights if i.level == CriticLevel.WARNING)
            
            if critical_count > 0:
                summary_parts.append(f"{critical_count} kritiska problem identifierade.")
            if error_count > 0:
                summary_parts.append(f"{error_count} fel upptäckta.")
            if warning_count > 0:
                summary_parts.append(f"{warning_count} varningar noterade.")
        
        if recommendations:
            high_priority_recs = sum(1 for r in recommendations if r.priority >= 8)
            if high_priority_recs > 0:
                summary_parts.append(f"{high_priority_recs} högt prioriterade förbättringar rekommenderas.")
        
        return " ".join(summary_parts)
    
    def _calculate_performance_metrics(self, execution_result: ExecutionPlan) -> Dict[str, Any]:
        """Beräkna prestanda-metrics"""
        metrics = {}
        
        if execution_result.total_actions > 0:
            metrics["success_rate"] = execution_result.completed_actions / execution_result.total_actions
            metrics["failure_rate"] = execution_result.failed_actions / execution_result.total_actions
        
        if execution_result.completed_at and execution_result.started_at:
            total_time = (execution_result.completed_at - execution_result.started_at).total_seconds()
            metrics["total_execution_time_seconds"] = total_time
            if execution_result.total_actions > 0:
                metrics["average_time_per_action_seconds"] = total_time / execution_result.total_actions
        
        # Execution time distribution
        execution_times = [r.execution_time_ms for r in execution_result.results.values()]
        if execution_times:
            metrics["min_execution_time_ms"] = min(execution_times)
            metrics["max_execution_time_ms"] = max(execution_times)
            metrics["avg_execution_time_ms"] = sum(execution_times) / len(execution_times)
        
        return metrics
    
    async def _perform_ai_analysis(
        self, 
        plan: AgentPlan, 
        execution_result: ExecutionPlan, 
        context: Optional[Dict[str, Any]]
    ) -> List[CriticInsight]:
        """Utför AI-baserad analys (placeholder för framtida implementation)"""
        # TODO: Implementera AI-baserad analys med Ollama/OpenAI
        return []
    
    def create_improvement_plan(self, report: CriticReport) -> List[CriticRecommendation]:
        """Skapa prioriterad förbättringsplan baserat på rapport"""
        # Returnera recommendations sorterat efter prioritet
        return sorted(report.recommendations, key=lambda r: r.priority, reverse=True)
    
    def compare_executions(
        self, 
        reports: List[CriticReport]
    ) -> Dict[str, Any]:
        """Jämför flera execution-rapporter för att identifiera trender"""
        if len(reports) < 2:
            return {"error": "Minst 2 rapporter behövs för jämförelse"}
        
        comparison = {
            "report_count": len(reports),
            "score_trend": [],
            "common_issues": {},
            "performance_trend": {}
        }
        
        # Score trend
        for report in reports:
            comparison["score_trend"].append({
                "plan_id": report.plan_id,
                "score": report.overall_score,
                "timestamp": report.evaluation_timestamp.isoformat()
            })
        
        # Vanliga problem
        all_categories = {}
        for report in reports:
            for insight in report.insights:
                category = insight.category
                all_categories[category] = all_categories.get(category, 0) + 1
        
        comparison["common_issues"] = dict(sorted(all_categories.items(), key=lambda x: x[1], reverse=True))
        
        return comparison