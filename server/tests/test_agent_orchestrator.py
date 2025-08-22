"""
Unit tests för AgentOrchestrator.
Testar workflow management, planning-execution-criticism cycles och förbättringar.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock, MagicMock

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.agent_orchestrator import (
    AgentOrchestrator, WorkflowStatus, ImprovementStrategy,
    WorkflowConfig, WorkflowIteration, WorkflowResult
)
from core.agent_planner import AgentPlanner, AgentPlan, AgentAction
from core.agent_executor import AgentExecutor, ExecutionPlan, ExecutionResult, ExecutionStatus
from core.agent_critic import AgentCritic, CriticReport, CriticLevel, CriticInsight, CriticRecommendation, RecommendationType


class TestWorkflowConfig:
    """Tester för WorkflowConfig dataclass"""
    
    def test_workflow_config_creation(self):
        """Test grundläggande skapande av WorkflowConfig"""
        config = WorkflowConfig()
        
        assert config.max_iterations == 3
        assert config.improvement_strategy == ImprovementStrategy.ADAPTIVE
        assert config.auto_improve == True
        assert config.min_success_score == 0.8
        assert config.enable_ai_planning == False
        assert config.execution_timeout_seconds == 300
    
    def test_workflow_config_custom(self):
        """Test anpassad WorkflowConfig"""
        config = WorkflowConfig(
            max_iterations=5,
            improvement_strategy=ImprovementStrategy.RETRY_FAILED,
            auto_improve=False,
            min_success_score=0.9
        )
        
        assert config.max_iterations == 5
        assert config.improvement_strategy == ImprovementStrategy.RETRY_FAILED
        assert config.auto_improve == False
        assert config.min_success_score == 0.9


class TestWorkflowResult:
    """Tester för WorkflowResult dataclass"""
    
    def test_workflow_result_creation(self):
        """Test skapande av WorkflowResult"""
        result = WorkflowResult(
            workflow_id="test_workflow",
            original_goal="Test goal",
            status=WorkflowStatus.PLANNING,
            iterations=[]
        )
        
        assert result.workflow_id == "test_workflow"
        assert result.original_goal == "Test goal"
        assert result.status == WorkflowStatus.PLANNING
        assert result.iterations == []
        assert result.total_improvements == 0
        assert result.started_at is not None
    
    def test_workflow_success_property(self):
        """Test success property"""
        # Successful workflow
        successful_execution = MagicMock()
        successful_execution.status = ExecutionStatus.COMPLETED
        
        result = WorkflowResult(
            workflow_id="test",
            original_goal="goal",
            status=WorkflowStatus.COMPLETED,
            iterations=[],
            final_execution=successful_execution
        )
        
        assert result.success == True
        
        # Failed workflow
        failed_result = WorkflowResult(
            workflow_id="test",
            original_goal="goal", 
            status=WorkflowStatus.FAILED,
            iterations=[]
        )
        
        assert failed_result.success == False
    
    def test_final_score_property(self):
        """Test final_score property"""
        # With critic report
        mock_report = MagicMock()
        mock_report.overall_score = 0.85
        
        result = WorkflowResult(
            workflow_id="test",
            original_goal="goal",
            status=WorkflowStatus.COMPLETED,
            iterations=[],
            final_report=mock_report
        )
        
        assert result.final_score == 0.85
        
        # Without critic report
        result_no_report = WorkflowResult(
            workflow_id="test",
            original_goal="goal",
            status=WorkflowStatus.COMPLETED,
            iterations=[]
        )
        
        assert result_no_report.final_score == 0.0


class TestAgentOrchestrator:
    """Tester för AgentOrchestrator klass"""
    
    @pytest.fixture
    def orchestrator(self):
        """Skapa en AgentOrchestrator instans för tester"""
        return AgentOrchestrator()
    
    @pytest.fixture
    def mock_components(self):
        """Mock av alla Agent Core komponenter"""
        planner = MagicMock(spec=AgentPlanner)
        executor = MagicMock(spec=AgentExecutor)
        critic = MagicMock(spec=AgentCritic)
        
        return planner, executor, critic
    
    def test_orchestrator_initialization(self, orchestrator):
        """Test att orchestrator initialiseras korrekt"""
        assert isinstance(orchestrator.planner, AgentPlanner)
        assert isinstance(orchestrator.executor, AgentExecutor)
        assert isinstance(orchestrator.critic, AgentCritic)
        assert isinstance(orchestrator.config, WorkflowConfig)
        assert orchestrator.active_workflows == {}
        assert len(orchestrator.workflow_hooks) == 10
    
    def test_orchestrator_with_custom_components(self, mock_components):
        """Test orchestrator med anpassade komponenter"""
        planner, executor, critic = mock_components
        config = WorkflowConfig(max_iterations=5)
        
        orchestrator = AgentOrchestrator(
            planner=planner,
            executor=executor,
            critic=critic,
            config=config
        )
        
        assert orchestrator.planner == planner
        assert orchestrator.executor == executor
        assert orchestrator.critic == critic
        assert orchestrator.config.max_iterations == 5
    
    @pytest.mark.asyncio
    async def test_execute_workflow_successful_single_iteration(self, orchestrator):
        """Test framgångsrikt workflow på första försöket"""
        goal = "spela musik"
        
        # Mock successful plan
        mock_plan = AgentPlan(
            plan_id="test_plan",
            goal=goal,
            actions=[AgentAction("step_1", "PLAY", {}, "Play music")],
            created_at=datetime.now()
        )
        
        # Mock successful execution
        mock_execution = ExecutionPlan(
            plan_id="test_plan",
            goal=goal,
            status=ExecutionStatus.COMPLETED,
            started_at=datetime.now() - timedelta(seconds=1),
            completed_at=datetime.now(),
            total_actions=1,
            completed_actions=1,
            failed_actions=0
        )
        
        # Mock positive criticism
        mock_criticism = CriticReport(
            plan_id="test_plan",
            evaluation_timestamp=datetime.now(),
            overall_score=0.9,  # High score
            overall_level=CriticLevel.SUCCESS,
            summary="Excellent execution"
        )
        
        # Setup mocks
        orchestrator.planner.create_plan = AsyncMock(return_value=mock_plan)
        orchestrator.executor.execute_plan = AsyncMock(return_value=mock_execution)
        orchestrator.critic.evaluate_execution = AsyncMock(return_value=mock_criticism)
        
        # Execute workflow
        result = await orchestrator.execute_workflow(goal)
        
        # Validate results
        assert isinstance(result, WorkflowResult)
        assert result.original_goal == goal
        assert result.status == WorkflowStatus.COMPLETED
        assert result.success == True
        assert len(result.iterations) == 1
        assert result.total_improvements == 0
        assert result.final_score == 0.9
        
        # Validate that all components were called
        orchestrator.planner.create_plan.assert_called_once()
        orchestrator.executor.execute_plan.assert_called_once()
        orchestrator.critic.evaluate_execution.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_workflow_with_improvement(self, orchestrator):
        """Test workflow med förbättring"""
        goal = "komplex uppgift"
        config = WorkflowConfig(max_iterations=2, min_success_score=0.8)
        
        # First iteration - low score
        mock_plan1 = AgentPlan("plan_1", goal, [AgentAction("step_1", "TOOL_1", {}, "Step 1")], datetime.now())
        mock_execution1 = ExecutionPlan(
            plan_id="plan_1", goal=goal, status=ExecutionStatus.COMPLETED,
            started_at=datetime.now(), total_actions=1, completed_actions=1, failed_actions=0
        )
        mock_criticism1 = CriticReport(
            plan_id="plan_1", evaluation_timestamp=datetime.now(),
            overall_score=0.5, overall_level=CriticLevel.WARNING, summary="Needs improvement",
            recommendations=[CriticRecommendation(RecommendationType.OPTIMIZE_ORDER, 8, "Optimize plan")]
        )
        
        # Second iteration - high score
        mock_plan2 = AgentPlan("plan_1_improved", goal, [AgentAction("step_1", "TOOL_2", {}, "Improved step")], datetime.now())
        mock_execution2 = ExecutionPlan(
            plan_id="plan_1_improved", goal=goal, status=ExecutionStatus.COMPLETED,
            started_at=datetime.now(), total_actions=1, completed_actions=1, failed_actions=0
        )
        mock_criticism2 = CriticReport(
            plan_id="plan_1_improved", evaluation_timestamp=datetime.now(),
            overall_score=0.9, overall_level=CriticLevel.SUCCESS, summary="Much better!"
        )
        
        # Setup mocks to return different values on different calls
        orchestrator.planner.create_plan = AsyncMock(return_value=mock_plan1)
        orchestrator.planner.optimize_plan = MagicMock(return_value=mock_plan2)
        orchestrator.executor.execute_plan = AsyncMock(side_effect=[mock_execution1, mock_execution2])
        orchestrator.critic.evaluate_execution = AsyncMock(side_effect=[mock_criticism1, mock_criticism2])
        
        # Execute workflow with improvement
        result = await orchestrator.execute_workflow(goal, config_override=config)
        
        # Validate improvement occurred
        assert result.status == WorkflowStatus.COMPLETED
        assert len(result.iterations) == 2
        assert result.total_improvements == 1
        assert result.final_score == 0.9
        # First iteration should have improvement applied (triggering second iteration)
        assert result.iterations[0].improvement_applied == True
    
    @pytest.mark.asyncio
    async def test_execute_workflow_max_iterations_reached(self, orchestrator):
        """Test workflow som når max iterations"""
        goal = "svår uppgift"
        config = WorkflowConfig(max_iterations=2, min_success_score=0.9)
        
        # Always return low score
        mock_plan = MagicMock()
        mock_execution = MagicMock()
        mock_execution.status = ExecutionStatus.COMPLETED
        mock_criticism = MagicMock()
        mock_criticism.overall_score = 0.6  # Always below threshold
        mock_criticism.recommendations = [MagicMock(priority=9)]
        
        orchestrator.planner.create_plan = AsyncMock(return_value=mock_plan)
        orchestrator.planner.optimize_plan = MagicMock(return_value=mock_plan)
        orchestrator.executor.execute_plan = AsyncMock(return_value=mock_execution)
        orchestrator.critic.evaluate_execution = AsyncMock(return_value=mock_criticism)
        
        result = await orchestrator.execute_workflow(goal, config_override=config)
        
        # Should complete after max iterations even with low score
        assert result.status == WorkflowStatus.COMPLETED
        assert len(result.iterations) == 2
        assert result.total_improvements == 1  # One improvement attempted
    
    @pytest.mark.asyncio
    async def test_execute_workflow_with_failure(self, orchestrator):
        """Test workflow med execution failure"""
        goal = "misslyckad uppgift"
        
        mock_plan = MagicMock()
        mock_execution = MagicMock()
        mock_execution.status = ExecutionStatus.FAILED
        mock_criticism = MagicMock()
        mock_criticism.overall_score = 0.2
        mock_criticism.recommendations = []
        
        orchestrator.planner.create_plan = AsyncMock(return_value=mock_plan)
        orchestrator.executor.execute_plan = AsyncMock(return_value=mock_execution)
        orchestrator.critic.evaluate_execution = AsyncMock(return_value=mock_criticism)
        
        result = await orchestrator.execute_workflow(goal)
        
        assert result.status == WorkflowStatus.FAILED
        assert result.success == False
        assert result.final_score == 0.2
    
    @pytest.mark.asyncio
    async def test_execute_workflow_with_progress_callback(self, orchestrator):
        """Test workflow med progress callback"""
        goal = "test progress"
        progress_updates = []
        
        def progress_callback(info):
            progress_updates.append(info["message"])
        
        # Mock components
        mock_plan = MagicMock()
        mock_execution = MagicMock()
        mock_execution.status = ExecutionStatus.COMPLETED
        mock_criticism = MagicMock()
        mock_criticism.overall_score = 0.9
        
        orchestrator.planner.create_plan = AsyncMock(return_value=mock_plan)
        orchestrator.executor.execute_plan = AsyncMock(return_value=mock_execution)
        orchestrator.critic.evaluate_execution = AsyncMock(return_value=mock_criticism)
        
        result = await orchestrator.execute_workflow(goal, progress_callback=progress_callback)
        
        assert result.success == True
        assert len(progress_updates) > 0
        assert any("Planning completed" in msg for msg in progress_updates)
        assert any("Execution completed" in msg for msg in progress_updates)
    
    @pytest.mark.asyncio
    async def test_improve_plan_adaptive_strategy(self, orchestrator):
        """Test plan improvement med adaptiv strategi"""
        original_plan = AgentPlan(
            plan_id="original",
            goal="test",
            actions=[
                AgentAction("step_1", "TOOL_1", {"param": "old"}, "Old step"),
                AgentAction("step_2", "BAD_TOOL", {}, "Bad step")
            ],
            created_at=datetime.now()
        )
        
        # Critic report med recommendations
        recommendations = [
            CriticRecommendation(RecommendationType.REMOVE_STEP, 9, "Remove bad step", target_step_id="step_2"),
            CriticRecommendation(RecommendationType.MODIFY_PARAMETERS, 8, "Update params", 
                               target_step_id="step_1", suggested_changes={"param": "new"})
        ]
        
        critic_report = CriticReport(
            plan_id="original", evaluation_timestamp=datetime.now(),
            overall_score=0.5, overall_level=CriticLevel.WARNING,
            summary="Needs improvement", recommendations=recommendations
        )
        
        improved_plan = await orchestrator._improve_plan(
            original_plan, critic_report, ImprovementStrategy.ADAPTIVE
        )
        
        # Validate improvements
        assert improved_plan.plan_id == "original_improved"
        assert len(improved_plan.actions) == 1  # step_2 removed
        assert improved_plan.actions[0].step_id == "step_1"
        assert improved_plan.actions[0].parameters["param"] == "new"  # parameter updated
    
    def test_should_improve_logic(self, orchestrator):
        """Test should_improve decision logic"""
        config = WorkflowConfig(min_success_score=0.8)
        
        # Low score - should improve
        low_score_report = MagicMock()
        low_score_report.overall_score = 0.6
        low_score_report.recommendations = []
        
        assert orchestrator._should_improve(low_score_report, config) == True
        
        # High score but high priority recommendations - should improve
        high_score_report = MagicMock()
        high_score_report.overall_score = 0.9
        high_rec = MagicMock()
        high_rec.priority = 9
        high_score_report.recommendations = [high_rec]
        
        assert orchestrator._should_improve(high_score_report, config) == True
        
        # High score, no high priority recommendations - don't improve
        good_report = MagicMock()
        good_report.overall_score = 0.9
        low_rec = MagicMock()
        low_rec.priority = 5
        good_report.recommendations = [low_rec]
        
        assert orchestrator._should_improve(good_report, config) == False
        
        # No report - don't improve
        assert orchestrator._should_improve(None, config) == False
    
    @pytest.mark.asyncio
    async def test_workflow_hooks(self, orchestrator):
        """Test workflow hooks"""
        hook_calls = []
        
        def test_hook(*args):
            hook_calls.append("hook_called")
        
        async def async_test_hook(*args):
            hook_calls.append("async_hook_called")
        
        # Add hooks
        orchestrator.add_workflow_hook("before_planning", test_hook)
        orchestrator.add_workflow_hook("workflow_complete", async_test_hook)
        
        # Mock successful workflow
        mock_plan = MagicMock()
        mock_execution = MagicMock()
        mock_execution.status = ExecutionStatus.COMPLETED
        mock_criticism = MagicMock()
        mock_criticism.overall_score = 0.9
        
        orchestrator.planner.create_plan = AsyncMock(return_value=mock_plan)
        orchestrator.executor.execute_plan = AsyncMock(return_value=mock_execution)
        orchestrator.critic.evaluate_execution = AsyncMock(return_value=mock_criticism)
        
        result = await orchestrator.execute_workflow("test hooks")
        
        assert result.success == True
        assert "hook_called" in hook_calls
        assert "async_hook_called" in hook_calls
    
    def test_add_remove_workflow_hooks(self, orchestrator):
        """Test att lägga till och ta bort workflow hooks"""
        def test_hook():
            pass
        
        # Add hook
        orchestrator.add_workflow_hook("before_planning", test_hook)
        assert test_hook in orchestrator.workflow_hooks["before_planning"]
        
        # Remove hook
        orchestrator.remove_workflow_hook("before_planning", test_hook)
        assert test_hook not in orchestrator.workflow_hooks["before_planning"]
    
    @pytest.mark.asyncio
    async def test_cancel_workflow(self, orchestrator):
        """Test avbrytning av workflow"""
        # Add mock active workflow
        mock_result = MagicMock()
        mock_result.status = WorkflowStatus.EXECUTING
        mock_execution = MagicMock()
        mock_execution.status = ExecutionStatus.IN_PROGRESS
        mock_execution.plan_id = "test_plan"
        mock_result.final_execution = mock_execution
        
        orchestrator.active_workflows["test_workflow"] = mock_result
        orchestrator.executor.cancel_execution = AsyncMock(return_value=True)
        
        cancelled = await orchestrator.cancel_workflow("test_workflow")
        
        assert cancelled == True
        assert mock_result.status == WorkflowStatus.CANCELLED
        assert mock_result.completed_at is not None
        orchestrator.executor.cancel_execution.assert_called_once_with("test_plan")
        
        # Test cancel non-existent workflow
        cancelled_fake = await orchestrator.cancel_workflow("fake_workflow")
        assert cancelled_fake == False
    
    def test_get_workflow_status(self, orchestrator):
        """Test hämta workflow status"""
        mock_result = MagicMock()
        orchestrator.active_workflows["test_workflow"] = mock_result
        
        status = orchestrator.get_workflow_status("test_workflow")
        assert status == mock_result
        
        # Non-existent workflow
        no_status = orchestrator.get_workflow_status("fake_workflow")
        assert no_status is None
    
    def test_get_active_workflows(self, orchestrator):
        """Test hämta aktiva workflows"""
        assert orchestrator.get_active_workflows() == []
        
        orchestrator.active_workflows["workflow_1"] = MagicMock()
        orchestrator.active_workflows["workflow_2"] = MagicMock()
        
        active = orchestrator.get_active_workflows()
        assert set(active) == {"workflow_1", "workflow_2"}
    
    def test_get_workflow_statistics(self, orchestrator):
        """Test hämta workflow statistik"""
        stats = orchestrator.get_workflow_statistics()
        
        assert "total_workflows" in stats
        assert "successful_workflows" in stats
        assert "failed_workflows" in stats
        assert "average_iterations" in stats
        assert "average_success_score" in stats
    
    @pytest.mark.asyncio
    async def test_execute_simple_goal(self, orchestrator):
        """Test enkel goal execution"""
        goal = "enkel uppgift"
        
        # Mock successful workflow
        mock_plan = MagicMock()
        mock_execution = MagicMock()
        mock_execution.status = ExecutionStatus.COMPLETED
        mock_execution.completed_actions = 2
        mock_execution.failed_actions = 0
        mock_criticism = MagicMock()
        mock_criticism.overall_score = 0.85
        mock_criticism.insights = ["insight1", "insight2"]
        mock_criticism.recommendations = ["rec1"]
        mock_criticism.summary = "Good execution"
        
        orchestrator.planner.create_plan = AsyncMock(return_value=mock_plan)
        orchestrator.executor.execute_plan = AsyncMock(return_value=mock_execution)
        orchestrator.critic.evaluate_execution = AsyncMock(return_value=mock_criticism)
        
        success, summary = await orchestrator.execute_simple_goal(goal)
        
        assert success == True
        assert isinstance(summary, dict)
        assert summary["goal"] == goal
        assert summary["success"] == True
        assert summary["final_score"] == 0.85
        assert summary["actions_completed"] == 2
        assert summary["actions_failed"] == 0
        assert summary["insights"] == 2
        assert summary["recommendations"] == 1
    
    @pytest.mark.asyncio
    async def test_workflow_error_handling(self, orchestrator):
        """Test felhantering i workflow"""
        goal = "error prone task"
        
        # Mock planner to throw exception
        orchestrator.planner.create_plan = AsyncMock(side_effect=Exception("Planning failed"))
        
        result = await orchestrator.execute_workflow(goal)
        
        assert result.status == WorkflowStatus.FAILED
        assert result.success == False
        assert result.completed_at is not None


class TestAgentOrchestratorIntegration:
    """Integration tests för AgentOrchestrator"""
    
    @pytest.fixture
    def orchestrator(self):
        return AgentOrchestrator()
    
    @pytest.mark.asyncio
    async def test_complete_workflow_integration(self, orchestrator):
        """Test komplett workflow integration med riktiga komponenter"""
        goal = "spela musik och sätt volym"
        
        # Mock tool execution för alla komponenter
        with patch('core.agent_executor.validate_and_execute_tool') as mock_tool:
            mock_tool.return_value = {"ok": True, "message": "Tool executed successfully"}
            
            result = await orchestrator.execute_workflow(goal)
        
        # Validate complete workflow
        assert isinstance(result, WorkflowResult)
        assert result.original_goal == goal
        assert result.status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED]
        assert len(result.iterations) >= 1
        
        # First iteration should have all phases
        first_iteration = result.iterations[0]
        assert first_iteration.plan is not None
        assert first_iteration.execution_result is not None
        assert first_iteration.critic_report is not None
        
        print(f"Integration test completed:")
        print(f"  Status: {result.status}")
        print(f"  Success: {result.success}")
        print(f"  Iterations: {len(result.iterations)}")
        print(f"  Final Score: {result.final_score}")
        print(f"  Improvements: {result.total_improvements}")


if __name__ == "__main__":
    # Kör tester med pytest
    pytest.main([__file__, "-v", "--tb=short"])