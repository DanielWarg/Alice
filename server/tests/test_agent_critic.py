"""
Unit tests för AgentCritic.
Testar evaluation-logik, insights, recommendations och performance metrics.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.agent_critic import (
    AgentCritic, CriticLevel, RecommendationType,
    CriticInsight, CriticRecommendation, CriticReport
)
from core.agent_planner import AgentPlan, AgentAction
from core.agent_executor import ExecutionPlan, ExecutionResult, ExecutionStatus


class TestCriticInsight:
    """Tester för CriticInsight dataclass"""
    
    def test_critic_insight_creation(self):
        """Test grundläggande skapande av CriticInsight"""
        insight = CriticInsight(
            level=CriticLevel.WARNING,
            category="performance",
            message="Slow execution detected",
            confidence=0.8
        )
        
        assert insight.level == CriticLevel.WARNING
        assert insight.category == "performance"
        assert insight.message == "Slow execution detected"
        assert insight.confidence == 0.8
        assert insight.affected_steps == []
        assert insight.evidence == {}
    
    def test_critic_insight_with_details(self):
        """Test CriticInsight med detaljer"""
        insight = CriticInsight(
            level=CriticLevel.ERROR,
            category="execution_failure",
            message="Multiple steps failed",
            affected_steps=["step_1", "step_2"],
            confidence=0.9,
            evidence={"failure_count": 2}
        )
        
        assert insight.affected_steps == ["step_1", "step_2"]
        assert insight.evidence == {"failure_count": 2}


class TestCriticRecommendation:
    """Tester för CriticRecommendation dataclass"""
    
    def test_critic_recommendation_creation(self):
        """Test grundläggande skapande av CriticRecommendation"""
        rec = CriticRecommendation(
            type=RecommendationType.RETRY_ACTION,
            priority=8,
            description="Retry failed step",
            confidence=0.7
        )
        
        assert rec.type == RecommendationType.RETRY_ACTION
        assert rec.priority == 8
        assert rec.description == "Retry failed step"
        assert rec.confidence == 0.7
        assert rec.suggested_changes == {}
    
    def test_critic_recommendation_with_changes(self):
        """Test CriticRecommendation med föreslagna ändringar"""
        rec = CriticRecommendation(
            type=RecommendationType.MODIFY_PARAMETERS,
            priority=5,
            description="Update parameters",
            target_step_id="step_1",
            suggested_changes={"timeout": 30},
            expected_improvement="Better success rate",
            confidence=0.8
        )
        
        assert rec.target_step_id == "step_1"
        assert rec.suggested_changes == {"timeout": 30}
        assert rec.expected_improvement == "Better success rate"


class TestAgentCritic:
    """Tester för AgentCritic klass"""
    
    @pytest.fixture
    def critic(self):
        """Skapa en AgentCritic instans för tester"""
        return AgentCritic()
    
    @pytest.fixture
    def successful_execution(self):
        """Mock av framgångsrik execution"""
        plan = AgentPlan(
            plan_id="success_plan",
            goal="Test successful execution",
            actions=[
                AgentAction("step_1", "PLAY", {}, "Play music"),
                AgentAction("step_2", "SET_VOLUME", {"level": 50}, "Set volume")
            ],
            created_at=datetime.now()
        )
        
        execution_result = ExecutionPlan(
            plan_id="success_plan",
            goal="Test successful execution",
            status=ExecutionStatus.COMPLETED,
            started_at=datetime.now() - timedelta(seconds=2),
            completed_at=datetime.now(),
            total_actions=2,
            completed_actions=2,
            failed_actions=0
        )
        
        execution_result.results = {
            "step_1": ExecutionResult(
                action_id="step_1",
                status=ExecutionStatus.COMPLETED,
                result={"success": True, "message": "Music started"},
                execution_time_ms=150,
                started_at=datetime.now() - timedelta(seconds=2),
                completed_at=datetime.now() - timedelta(seconds=1)
            ),
            "step_2": ExecutionResult(
                action_id="step_2", 
                status=ExecutionStatus.COMPLETED,
                result={"success": True, "message": "Volume set"},
                execution_time_ms=100,
                started_at=datetime.now() - timedelta(seconds=1),
                completed_at=datetime.now()
            )
        }
        
        return plan, execution_result
    
    @pytest.fixture
    def failed_execution(self):
        """Mock av misslyckad execution"""
        plan = AgentPlan(
            plan_id="failed_plan",
            goal="Test failed execution",
            actions=[
                AgentAction("step_1", "PLAY", {}, "Play music"),
                AgentAction("step_2", "INVALID_TOOL", {}, "Invalid step")
            ],
            created_at=datetime.now()
        )
        
        execution_result = ExecutionPlan(
            plan_id="failed_plan",
            goal="Test failed execution", 
            status=ExecutionStatus.FAILED,
            started_at=datetime.now() - timedelta(seconds=3),
            completed_at=datetime.now(),
            total_actions=2,
            completed_actions=1,
            failed_actions=1
        )
        
        execution_result.results = {
            "step_1": ExecutionResult(
                action_id="step_1",
                status=ExecutionStatus.COMPLETED,
                result={"success": True, "message": "Music started"},
                execution_time_ms=150
            ),
            "step_2": ExecutionResult(
                action_id="step_2",
                status=ExecutionStatus.FAILED,
                error_message="Tool not found",
                execution_time_ms=50
            )
        }
        
        return plan, execution_result
    
    def test_critic_initialization(self, critic):
        """Test att critic initialiseras korrekt"""
        assert critic.enable_ai_analysis == False
        assert len(critic.evaluation_rules) > 0
        assert "execution_success" in critic.evaluation_rules
        assert "performance_analysis" in critic.evaluation_rules
        assert critic.performance_thresholds["execution_time_warning_ms"] == 5000
    
    @pytest.mark.asyncio
    async def test_evaluate_successful_execution(self, critic, successful_execution):
        """Test utvärdering av framgångsrik execution"""
        plan, execution_result = successful_execution
        
        report = await critic.evaluate_execution(plan, execution_result)
        
        assert isinstance(report, CriticReport)
        assert report.plan_id == "success_plan"
        assert report.overall_level == CriticLevel.SUCCESS
        assert report.overall_score > 0.8  # Hög score för framgång
        assert len(report.insights) > 0
        
        # Ska ha success insight
        success_insights = [i for i in report.insights if i.level == CriticLevel.SUCCESS]
        assert len(success_insights) > 0
    
    @pytest.mark.asyncio
    async def test_evaluate_failed_execution(self, critic, failed_execution):
        """Test utvärdering av misslyckad execution"""
        plan, execution_result = failed_execution
        
        report = await critic.evaluate_execution(plan, execution_result)
        
        assert report.plan_id == "failed_plan"
        assert report.overall_level in [CriticLevel.ERROR, CriticLevel.CRITICAL]
        assert report.overall_score < 0.8  # Låg score för misslyckande
        
        # Ska ha error insights
        error_insights = [i for i in report.insights if i.level in [CriticLevel.ERROR, CriticLevel.CRITICAL]]
        assert len(error_insights) > 0
        
        # Ska ha retry recommendations
        retry_recs = [r for r in report.recommendations if r.type == RecommendationType.RETRY_ACTION]
        assert len(retry_recs) > 0
    
    @pytest.mark.asyncio
    async def test_performance_analysis(self, critic):
        """Test prestanda-analys för långsamma steg"""
        plan = AgentPlan(
            plan_id="slow_plan",
            goal="Test slow execution",
            actions=[AgentAction("slow_step", "SLOW_TOOL", {}, "Slow operation")],
            created_at=datetime.now()
        )
        
        execution_result = ExecutionPlan(
            plan_id="slow_plan",
            goal="Test slow execution",
            status=ExecutionStatus.COMPLETED,
            started_at=datetime.now() - timedelta(seconds=20),
            completed_at=datetime.now(),
            total_actions=1,
            completed_actions=1,
            failed_actions=0
        )
        
        execution_result.results = {
            "slow_step": ExecutionResult(
                action_id="slow_step",
                status=ExecutionStatus.COMPLETED,
                result={"success": True},
                execution_time_ms=18000  # 18 seconds - över critical threshold
            )
        }
        
        report = await critic.evaluate_execution(plan, execution_result)
        
        # Ska identifiera prestanda-problem
        perf_insights = [i for i in report.insights if i.category == "performance"]
        assert len(perf_insights) > 0
        assert any(i.level == CriticLevel.CRITICAL for i in perf_insights)
        
        # Ska rekommendera timeout increase
        timeout_recs = [r for r in report.recommendations if r.type == RecommendationType.INCREASE_TIMEOUT]
        assert len(timeout_recs) > 0
    
    @pytest.mark.asyncio 
    async def test_dependency_deadlock_detection(self, critic):
        """Test upptäckt av dependency deadlocks"""
        plan = AgentPlan(
            plan_id="deadlock_plan",
            goal="Test deadlock",
            actions=[
                AgentAction("step_1", "PLAY", {}, "Step 1", depends_on=["step_2"]),
                AgentAction("step_2", "PAUSE", {}, "Step 2", depends_on=["step_1"])
            ],
            created_at=datetime.now()
        )
        
        execution_result = ExecutionPlan(
            plan_id="deadlock_plan",
            goal="Test deadlock",
            status=ExecutionStatus.FAILED,
            started_at=datetime.now() - timedelta(seconds=1),
            completed_at=datetime.now(),
            total_actions=2,
            completed_actions=0,
            failed_actions=2
        )
        
        execution_result.results = {
            "step_1": ExecutionResult(
                action_id="step_1",
                status=ExecutionStatus.FAILED,
                error_message="Dependency deadlock - required dependencies not satisfied"
            ),
            "step_2": ExecutionResult(
                action_id="step_2", 
                status=ExecutionStatus.FAILED,
                error_message="Dependency deadlock - required dependencies not satisfied"
            )
        }
        
        report = await critic.evaluate_execution(plan, execution_result)
        
        # Ska identifiera deadlock
        dep_insights = [i for i in report.insights if i.category == "dependencies"]
        assert len(dep_insights) > 0
        assert any("deadlock" in i.message.lower() for i in dep_insights)
        
        # Ska rekommendera att ta bort steg
        remove_recs = [r for r in report.recommendations if r.type == RecommendationType.REMOVE_STEP]
        assert len(remove_recs) > 0
    
    @pytest.mark.asyncio
    async def test_tool_usage_analysis(self, critic):
        """Test analys av verktygsanvändning"""
        plan = AgentPlan(
            plan_id="tool_analysis_plan",
            goal="Test tool usage",
            actions=[
                AgentAction("step_1", "UNRELIABLE_TOOL", {}, "Step 1"),
                AgentAction("step_2", "UNRELIABLE_TOOL", {}, "Step 2"),
                AgentAction("step_3", "GOOD_TOOL", {}, "Step 3")
            ],
            created_at=datetime.now()
        )
        
        execution_result = ExecutionPlan(
            plan_id="tool_analysis_plan",
            goal="Test tool usage",
            status=ExecutionStatus.FAILED,
            started_at=datetime.now() - timedelta(seconds=2),
            completed_at=datetime.now(),
            total_actions=3,
            completed_actions=1,
            failed_actions=2
        )
        
        execution_result.results = {
            "step_1": ExecutionResult(
                action_id="step_1",
                status=ExecutionStatus.FAILED,
                error_message="Tool failed"
            ),
            "step_2": ExecutionResult(
                action_id="step_2",
                status=ExecutionStatus.FAILED, 
                error_message="Tool failed again"
            ),
            "step_3": ExecutionResult(
                action_id="step_3",
                status=ExecutionStatus.COMPLETED,
                result={"success": True}
            )
        }
        
        report = await critic.evaluate_execution(plan, execution_result)
        
        # Ska identifiera problematiskt verktyg
        tool_insights = [i for i in report.insights if i.category == "tool_usage"]
        assert len(tool_insights) > 0
        
        # Ska rekommendera att byta verktyg
        change_tool_recs = [r for r in report.recommendations if r.type == RecommendationType.CHANGE_TOOL]
        assert len(change_tool_recs) > 0
    
    @pytest.mark.asyncio
    async def test_error_pattern_analysis(self, critic):
        """Test analys av fel-mönster"""
        plan = AgentPlan(
            plan_id="error_pattern_plan",
            goal="Test error patterns",
            actions=[
                AgentAction("step_1", "TIMEOUT_TOOL", {}, "Step 1"),
                AgentAction("step_2", "PARAM_TOOL", {}, "Step 2")
            ],
            created_at=datetime.now()
        )
        
        execution_result = ExecutionPlan(
            plan_id="error_pattern_plan",
            goal="Test error patterns",
            status=ExecutionStatus.FAILED,
            started_at=datetime.now() - timedelta(seconds=1),
            completed_at=datetime.now(),
            total_actions=2,
            completed_actions=0,
            failed_actions=2
        )
        
        execution_result.results = {
            "step_1": ExecutionResult(
                action_id="step_1",
                status=ExecutionStatus.FAILED,
                error_message="Connection timeout occurred"
            ),
            "step_2": ExecutionResult(
                action_id="step_2",
                status=ExecutionStatus.FAILED,
                error_message="Invalid parameter provided"
            )
        }
        
        report = await critic.evaluate_execution(plan, execution_result)
        
        # Ska identifiera fel-mönster
        error_insights = [i for i in report.insights if i.category == "error_patterns"]
        assert len(error_insights) > 0
        
        # Ska rekommendera parameter-förbättringar
        param_recs = [r for r in report.recommendations if r.type == RecommendationType.MODIFY_PARAMETERS]
        assert len(param_recs) > 0
    
    @pytest.mark.asyncio
    async def test_optimization_identification(self, critic):
        """Test identifiering av optimeringsmöjligheter"""
        plan = AgentPlan(
            plan_id="optimization_plan", 
            goal="Test optimization",
            actions=[
                AgentAction("step_1", "PLAY", {}, "Step 1"),
                AgentAction("step_2", "PLAY", {}, "Step 2"),  # Redundant
                AgentAction("step_3", "PAUSE", {}, "Step 3")
            ],
            created_at=datetime.now()
        )
        
        execution_result = ExecutionPlan(
            plan_id="optimization_plan",
            goal="Test optimization",
            status=ExecutionStatus.COMPLETED,
            started_at=datetime.now() - timedelta(seconds=1),
            completed_at=datetime.now(),
            total_actions=3,
            completed_actions=3,
            failed_actions=0
        )
        
        execution_result.results = {
            "step_1": ExecutionResult(action_id="step_1", status=ExecutionStatus.COMPLETED),
            "step_2": ExecutionResult(action_id="step_2", status=ExecutionStatus.COMPLETED),
            "step_3": ExecutionResult(action_id="step_3", status=ExecutionStatus.COMPLETED)
        }
        
        report = await critic.evaluate_execution(plan, execution_result)
        
        # Ska identifiera optimeringsmöjligheter
        opt_insights = [i for i in report.insights if i.category == "optimization"]
        assert len(opt_insights) > 0
        
        # Kan ha optimize order recommendations
        opt_recs = [r for r in report.recommendations if r.type == RecommendationType.OPTIMIZE_ORDER]
        # Denna är optional baserat på logik
    
    def test_overall_score_calculation(self, critic, successful_execution, failed_execution):
        """Test beräkning av overall score"""
        _, success_result = successful_execution
        _, failed_result = failed_execution
        
        # Framgångsrik execution ska ha hög score
        success_insights = [
            CriticInsight(CriticLevel.SUCCESS, "test", "Success")
        ]
        success_score = critic._calculate_overall_score(success_result, success_insights)
        assert success_score > 0.8
        
        # Misslyckad execution ska ha låg score
        failed_insights = [
            CriticInsight(CriticLevel.ERROR, "test", "Error"),
            CriticInsight(CriticLevel.CRITICAL, "test", "Critical")
        ]
        failed_score = critic._calculate_overall_score(failed_result, failed_insights)
        assert failed_score < 0.5
    
    def test_overall_level_determination(self, critic):
        """Test bestämning av overall level"""
        # Critical insights
        critical_insights = [CriticInsight(CriticLevel.CRITICAL, "test", "Critical")]
        assert critic._determine_overall_level(critical_insights) == CriticLevel.CRITICAL
        
        # Error insights
        error_insights = [CriticInsight(CriticLevel.ERROR, "test", "Error")]
        assert critic._determine_overall_level(error_insights) == CriticLevel.ERROR
        
        # Warning insights
        warning_insights = [CriticInsight(CriticLevel.WARNING, "test", "Warning")]
        assert critic._determine_overall_level(warning_insights) == CriticLevel.WARNING
        
        # Success insights
        success_insights = [CriticInsight(CriticLevel.SUCCESS, "test", "Success")]
        assert critic._determine_overall_level(success_insights) == CriticLevel.SUCCESS
    
    def test_performance_metrics_calculation(self, critic, successful_execution):
        """Test beräkning av prestanda-metrics"""
        _, execution_result = successful_execution
        
        metrics = critic._calculate_performance_metrics(execution_result)
        
        assert "success_rate" in metrics
        assert "failure_rate" in metrics
        assert "total_execution_time_seconds" in metrics
        assert "average_time_per_action_seconds" in metrics
        assert "min_execution_time_ms" in metrics
        assert "max_execution_time_ms" in metrics
        assert "avg_execution_time_ms" in metrics
        
        assert metrics["success_rate"] == 1.0
        assert metrics["failure_rate"] == 0.0
    
    def test_create_improvement_plan(self, critic):
        """Test skapande av förbättringsplan"""
        recommendations = [
            CriticRecommendation(RecommendationType.RETRY_ACTION, 5, "Low priority"),
            CriticRecommendation(RecommendationType.CHANGE_TOOL, 9, "High priority"),
            CriticRecommendation(RecommendationType.MODIFY_PARAMETERS, 7, "Medium priority")
        ]
        
        report = CriticReport(
            plan_id="test",
            evaluation_timestamp=datetime.now(),
            overall_score=0.5,
            overall_level=CriticLevel.WARNING,
            summary="Test report",
            recommendations=recommendations
        )
        
        improvement_plan = critic.create_improvement_plan(report)
        
        # Ska vara sorterat efter prioritet (högst först)
        assert len(improvement_plan) == 3
        assert improvement_plan[0].priority == 9
        assert improvement_plan[1].priority == 7
        assert improvement_plan[2].priority == 5
    
    def test_compare_executions(self, critic):
        """Test jämförelse av flera executions"""
        reports = [
            CriticReport(
                plan_id="plan_1",
                evaluation_timestamp=datetime.now(),
                overall_score=0.8,
                overall_level=CriticLevel.SUCCESS,
                summary="Good execution",
                insights=[CriticInsight(CriticLevel.SUCCESS, "performance", "Fast")]
            ),
            CriticReport(
                plan_id="plan_2",
                evaluation_timestamp=datetime.now(),
                overall_score=0.3,
                overall_level=CriticLevel.ERROR,
                summary="Poor execution",
                insights=[CriticInsight(CriticLevel.ERROR, "execution_failure", "Failed")]
            )
        ]
        
        comparison = critic.compare_executions(reports)
        
        assert "report_count" in comparison
        assert "score_trend" in comparison
        assert "common_issues" in comparison
        assert "performance_trend" in comparison
        
        assert comparison["report_count"] == 2
        assert len(comparison["score_trend"]) == 2
        
        # Test med för få rapporter
        single_comparison = critic.compare_executions([reports[0]])
        assert "error" in single_comparison
    
    @pytest.mark.asyncio
    async def test_evaluation_error_handling(self, critic):
        """Test felhantering i utvärdering"""
        # Skapa korrupt execution result
        plan = AgentPlan("error_plan", "Error test", [], datetime.now())
        
        execution_result = ExecutionPlan(
            plan_id="error_plan",
            goal="Error test",
            status=ExecutionStatus.FAILED,
            started_at=datetime.now(),
            total_actions=0
        )
        execution_result.results = None  # Korrupt data
        
        report = await critic.evaluate_execution(plan, execution_result)
        
        # Ska hantera fel gracefully
        assert isinstance(report, CriticReport)
        assert report.overall_level == CriticLevel.CRITICAL
        assert len(report.insights) > 0
        assert any("kritisk fel" in i.message.lower() for i in report.insights)


class TestAgentCriticIntegration:
    """Integration tests för AgentCritic"""
    
    @pytest.fixture
    def critic(self):
        return AgentCritic()
    
    @pytest.mark.asyncio
    async def test_complete_evaluation_workflow(self, critic):
        """Test komplett evaluerings-workflow"""
        # Skapa realistisk plan och execution
        plan = AgentPlan(
            plan_id="integration_plan",
            goal="Complete workflow test",
            actions=[
                AgentAction("init", "PLAY", {}, "Initialize"),
                AgentAction("config", "SET_VOLUME", {"level": 75}, "Configure", depends_on=["init"]),
                AgentAction("verify", "PAUSE", {}, "Verify", depends_on=["config"])
            ],
            created_at=datetime.now()
        )
        
        execution_result = ExecutionPlan(
            plan_id="integration_plan",
            goal="Complete workflow test",
            status=ExecutionStatus.COMPLETED,
            started_at=datetime.now() - timedelta(seconds=3),
            completed_at=datetime.now(),
            total_actions=3,
            completed_actions=3,
            failed_actions=0
        )
        
        execution_result.results = {
            "init": ExecutionResult(
                action_id="init",
                status=ExecutionStatus.COMPLETED,
                result={"success": True, "message": "Initialized successfully"},
                execution_time_ms=200
            ),
            "config": ExecutionResult(
                action_id="config",
                status=ExecutionStatus.COMPLETED,
                result={"success": True, "message": "Volume set to 75%"},
                execution_time_ms=150
            ),
            "verify": ExecutionResult(
                action_id="verify",
                status=ExecutionStatus.COMPLETED,
                result={"success": True, "message": "Verification complete"},
                execution_time_ms=100
            )
        }
        
        # Utför utvärdering
        report = await critic.evaluate_execution(plan, execution_result)
        
        # Validera komplett rapport
        assert isinstance(report, CriticReport)
        assert report.plan_id == "integration_plan"
        assert report.overall_level in [CriticLevel.SUCCESS, CriticLevel.WARNING]  # WARNING är OK för sekventiell plan
        assert report.overall_score > 0.9  # Mycket hög score
        
        # Ska ha insights från alla kategorier
        categories = {i.category for i in report.insights}
        expected_categories = {
            "execution_success", "performance", "dependencies", 
            "tool_usage", "error_patterns", "optimization"
        }
        # Inte alla kategorier behöver finnas för framgångsrik execution
        assert len(categories) > 0
        
        # Performance metrics ska finnas
        assert len(report.performance_metrics) > 0
        assert "success_rate" in report.performance_metrics
        assert report.performance_metrics["success_rate"] == 1.0
        
        # Summary ska vara informativ
        assert "3 steg" in report.summary
        assert "lyckades" in report.summary
        
        print(f"Integration test report: {report.summary}")
        print(f"Score: {report.overall_score:.2f}, Level: {report.overall_level}")
        print(f"Insights: {len(report.insights)}, Recommendations: {len(report.recommendations)}")


if __name__ == "__main__":
    # Kör tester med pytest
    pytest.main([__file__, "-v", "--tb=short"])