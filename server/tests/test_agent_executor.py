"""
Unit tests för AgentExecutor.
Testar execution-logik, error handling, parallellisering och hooks.
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import patch, AsyncMock, MagicMock

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.agent_executor import AgentExecutor, ExecutionStatus, ExecutionResult, ExecutionPlan
from core.agent_planner import AgentPlan, AgentAction


class TestExecutionResult:
    """Tester för ExecutionResult dataclass"""
    
    def test_execution_result_creation(self):
        """Test grundläggande skapande av ExecutionResult"""
        result = ExecutionResult(
            action_id="test_action",
            status=ExecutionStatus.COMPLETED,
            result={"success": True},
            execution_time_ms=150
        )
        
        assert result.action_id == "test_action"
        assert result.status == ExecutionStatus.COMPLETED
        assert result.result == {"success": True}
        assert result.execution_time_ms == 150
        assert result.error_message is None
        assert result.retry_count == 0
    
    def test_execution_result_default_values(self):
        """Test ExecutionResult med default-värden"""
        result = ExecutionResult(
            action_id="test_action",
            status=ExecutionStatus.PENDING
        )
        
        assert result.result == {}
        assert result.error_message is None
        assert result.execution_time_ms == 0
        assert result.retry_count == 0


class TestExecutionPlan:
    """Tester för ExecutionPlan dataclass"""
    
    def test_execution_plan_creation(self):
        """Test grundläggande skapande av ExecutionPlan"""
        plan = ExecutionPlan(
            plan_id="test_plan",
            goal="Test goal",
            status=ExecutionStatus.IN_PROGRESS,
            started_at=datetime.now(),
            total_actions=5
        )
        
        assert plan.plan_id == "test_plan"
        assert plan.goal == "Test goal"
        assert plan.status == ExecutionStatus.IN_PROGRESS
        assert plan.total_actions == 5
        assert plan.completed_actions == 0
        assert plan.failed_actions == 0
        assert plan.results == {}
    
    def test_progress_percent_calculation(self):
        """Test progress-beräkning"""
        plan = ExecutionPlan(
            plan_id="test",
            goal="goal",
            status=ExecutionStatus.IN_PROGRESS,
            started_at=datetime.now(),
            total_actions=4,
            completed_actions=2
        )
        
        assert plan.progress_percent == 50.0
    
    def test_progress_percent_zero_actions(self):
        """Test progress med inga actions"""
        plan = ExecutionPlan(
            plan_id="test",
            goal="goal",
            status=ExecutionStatus.IN_PROGRESS,
            started_at=datetime.now(),
            total_actions=0
        )
        
        assert plan.progress_percent == 0.0


class TestAgentExecutor:
    """Tester för AgentExecutor klass"""
    
    @pytest.fixture
    def executor(self):
        """Skapa en AgentExecutor instans för tester"""
        return AgentExecutor(max_parallel_actions=2)
    
    @pytest.fixture
    def simple_plan(self):
        """Skapa en enkel plan för tester"""
        actions = [
            AgentAction("step_1", "PLAY", {}, "Start music"),
            AgentAction("step_2", "PAUSE", {}, "Pause music", depends_on=["step_1"])
        ]
        
        return AgentPlan(
            plan_id="test_plan",
            goal="Test music control",
            actions=actions,
            created_at=datetime.now()
        )
    
    @pytest.fixture
    def parallel_plan(self):
        """Skapa en plan med parallella steg"""
        actions = [
            AgentAction("step_1", "PLAY", {}, "Start music"),
            AgentAction("step_2", "SET_VOLUME", {"level": 50}, "Set volume"),
            AgentAction("step_3", "STOP", {}, "Stop music", depends_on=["step_1", "step_2"])
        ]
        
        return AgentPlan(
            plan_id="parallel_plan",
            goal="Test parallel execution",
            actions=actions,
            created_at=datetime.now()
        )
    
    def test_executor_initialization(self, executor):
        """Test att executor initialiseras korrekt"""
        assert executor.max_parallel_actions == 2
        assert executor.default_timeout_ms == 30000
        assert executor.active_executions == {}
        assert len(executor.execution_hooks) == 4
    
    @pytest.mark.asyncio
    @patch('core.agent_executor.validate_and_execute_tool')
    async def test_execute_simple_plan_success(self, mock_tool_exec, executor, simple_plan):
        """Test exekvering av enkel plan med framgång"""
        mock_tool_exec.return_value = {"ok": True, "message": "Success"}
        
        result = await executor.execute_plan(simple_plan)
        
        assert result.status == ExecutionStatus.COMPLETED
        assert result.completed_actions == 2
        assert result.failed_actions == 0
        assert len(result.results) == 2
        assert result.progress_percent == 100.0
        
        # Kontrollera att båda stegen kördes
        assert "step_1" in result.results
        assert "step_2" in result.results
        assert result.results["step_1"].status == ExecutionStatus.COMPLETED
        assert result.results["step_2"].status == ExecutionStatus.COMPLETED
    
    @pytest.mark.asyncio
    @patch('core.agent_executor.validate_and_execute_tool')
    async def test_execute_plan_with_failure(self, mock_tool_exec, executor, simple_plan):
        """Test exekvering med misslyckad action"""
        # Första anropet lyckas, andra misslyckas
        mock_tool_exec.side_effect = [
            {"ok": True, "message": "Success"},
            {"ok": False, "message": "Tool failed"}
        ]
        
        result = await executor.execute_plan(simple_plan)
        
        assert result.status == ExecutionStatus.FAILED
        assert result.completed_actions == 1
        assert result.failed_actions == 1
        assert result.results["step_1"].status == ExecutionStatus.COMPLETED
        assert result.results["step_2"].status == ExecutionStatus.FAILED
        assert "Tool failed" in result.results["step_2"].error_message
    
    @pytest.mark.asyncio
    @patch('core.agent_executor.validate_and_execute_tool')
    async def test_execute_parallel_actions(self, mock_tool_exec, executor, parallel_plan):
        """Test parallell exekvering av actions"""
        mock_tool_exec.return_value = {"ok": True, "message": "Success"}
        
        result = await executor.execute_plan(parallel_plan)
        
        assert result.status == ExecutionStatus.COMPLETED
        assert result.completed_actions == 3
        assert result.failed_actions == 0
        
        # step_1 och step_2 ska ha körts först (parallellt)
        # sedan step_3 som är beroende av både
        step1_result = result.results["step_1"]
        step2_result = result.results["step_2"] 
        step3_result = result.results["step_3"]
        
        assert step1_result.status == ExecutionStatus.COMPLETED
        assert step2_result.status == ExecutionStatus.COMPLETED
        assert step3_result.status == ExecutionStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_execute_plan_with_progress_callback(self, executor, simple_plan):
        """Test exekvering med progress callback"""
        progress_updates = []
        
        def progress_callback(execution_plan):
            progress_updates.append(execution_plan.progress_percent)
        
        with patch('core.agent_executor.validate_and_execute_tool') as mock_tool:
            mock_tool.return_value = {"ok": True, "message": "Success"}
            
            result = await executor.execute_plan(simple_plan, progress_callback=progress_callback)
        
        assert result.status == ExecutionStatus.COMPLETED
        # Progress callback ska ha anropats
        assert len(progress_updates) > 0
    
    @pytest.mark.asyncio
    async def test_execute_plan_with_context(self, executor, simple_plan):
        """Test exekvering med kontext"""
        context = {"user_id": "123", "session": "test"}
        
        with patch('core.agent_executor.validate_and_execute_tool') as mock_tool:
            mock_tool.return_value = {"ok": True, "message": "Success"}
            
            result = await executor.execute_plan(simple_plan, context=context)
        
        assert result.status == ExecutionStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_dependency_deadlock_handling(self, executor):
        """Test hantering av dependency deadlock"""
        # Skapa en plan med circular dependencies
        actions = [
            AgentAction("step_1", "PLAY", {}, "Step 1", depends_on=["step_2"]),
            AgentAction("step_2", "PAUSE", {}, "Step 2", depends_on=["step_1"])
        ]
        
        deadlock_plan = AgentPlan(
            plan_id="deadlock_plan",
            goal="Test deadlock",
            actions=actions,
            created_at=datetime.now()
        )
        
        result = await executor.execute_plan(deadlock_plan)
        
        assert result.status == ExecutionStatus.FAILED
        assert result.failed_actions == 2
        
        # Båda actions ska ha failed med deadlock-meddelande
        for action_result in result.results.values():
            assert action_result.status == ExecutionStatus.FAILED
            assert "deadlock" in action_result.error_message.lower()
    
    @pytest.mark.asyncio
    async def test_execution_hooks(self, executor, simple_plan):
        """Test execution hooks"""
        hook_calls = []
        
        def before_action_hook(action, context):
            hook_calls.append(f"before_{action.step_id}")
        
        def after_action_hook(action, result, context):
            hook_calls.append(f"after_{action.step_id}")
        
        def on_complete_hook(execution_plan):
            hook_calls.append("plan_complete")
        
        executor.add_execution_hook("before_action", before_action_hook)
        executor.add_execution_hook("after_action", after_action_hook)
        executor.add_execution_hook("on_plan_complete", on_complete_hook)
        
        with patch('core.agent_executor.validate_and_execute_tool') as mock_tool:
            mock_tool.return_value = {"ok": True, "message": "Success"}
            
            result = await executor.execute_plan(simple_plan)
        
        assert result.status == ExecutionStatus.COMPLETED
        
        # Kontrollera att hooks anropades i rätt ordning
        expected_calls = [
            "before_step_1", "after_step_1",
            "before_step_2", "after_step_2", 
            "plan_complete"
        ]
        assert hook_calls == expected_calls
    
    @pytest.mark.asyncio
    async def test_error_hook(self, executor, simple_plan):
        """Test error hook vid fel"""
        error_calls = []
        
        def error_hook(action, error, context):
            error_calls.append(f"error_{action.step_id}")
        
        executor.add_execution_hook("on_error", error_hook)
        
        with patch('core.agent_executor.validate_and_execute_tool') as mock_tool:
            # Första lyckas, andra ger exception
            mock_tool.side_effect = [
                {"ok": True, "message": "Success"},
                Exception("Test error")
            ]
            
            result = await executor.execute_plan(simple_plan)
        
        assert result.status == ExecutionStatus.FAILED
        assert len(error_calls) == 1
        assert "error_step_2" in error_calls
    
    def test_add_remove_execution_hooks(self, executor):
        """Test att lägga till och ta bort hooks"""
        def test_hook():
            pass
        
        # Lägg till
        executor.add_execution_hook("before_action", test_hook)
        assert test_hook in executor.execution_hooks["before_action"]
        
        # Ta bort
        executor.remove_execution_hook("before_action", test_hook)
        assert test_hook not in executor.execution_hooks["before_action"]
    
    @pytest.mark.asyncio
    async def test_cancel_execution(self, executor):
        """Test avbrytning av execution"""
        # Skapa mock execution plan
        execution_plan = ExecutionPlan(
            plan_id="test_plan",
            goal="Test goal",
            status=ExecutionStatus.IN_PROGRESS,
            started_at=datetime.now()
        )
        executor.active_executions["test_plan"] = execution_plan
        
        # Testa cancellation
        cancelled = await executor.cancel_execution("test_plan")
        
        assert cancelled == True
        assert execution_plan.status == ExecutionStatus.CANCELLED
        assert execution_plan.completed_at is not None
        
        # Test med icke-existerande plan
        not_cancelled = await executor.cancel_execution("nonexistent")
        assert not_cancelled == False
    
    def test_get_execution_status(self, executor):
        """Test hämta execution status"""
        # Lägg till mock execution
        execution_plan = ExecutionPlan(
            plan_id="test_plan",
            goal="Test goal",
            status=ExecutionStatus.IN_PROGRESS,
            started_at=datetime.now()
        )
        executor.active_executions["test_plan"] = execution_plan
        
        status = executor.get_execution_status("test_plan")
        assert status == execution_plan
        
        # Test med icke-existerande plan
        status = executor.get_execution_status("nonexistent")
        assert status is None
    
    def test_get_active_executions(self, executor):
        """Test hämta aktiva executions"""
        # Tomt från början
        assert executor.get_active_executions() == []
        
        # Lägg till mock executions
        executor.active_executions["plan1"] = MagicMock()
        executor.active_executions["plan2"] = MagicMock()
        
        active = executor.get_active_executions()
        assert set(active) == {"plan1", "plan2"}
    
    @pytest.mark.asyncio
    async def test_retry_failed_action(self, executor):
        """Test retry av misslyckad action"""
        # Skapa mock execution plan med failed action
        execution_plan = ExecutionPlan(
            plan_id="test_plan",
            goal="Test goal", 
            status=ExecutionStatus.IN_PROGRESS,
            started_at=datetime.now()
        )
        
        failed_result = ExecutionResult(
            action_id="failed_step",
            status=ExecutionStatus.FAILED,
            error_message="Original failure",
            retry_count=0
        )
        execution_plan.results["failed_step"] = failed_result
        executor.active_executions["test_plan"] = execution_plan
        
        # Testa retry
        retry_result = await executor.retry_failed_action("test_plan", "failed_step")
        
        # För tillfället returnerar implementationen bara original result
        assert retry_result == failed_result


class TestAgentExecutorIntegration:
    """Integration tests för AgentExecutor med verkliga verktyg"""
    
    @pytest.fixture
    def executor(self):
        return AgentExecutor()
    
    @pytest.mark.asyncio
    async def test_execute_plan_with_real_tools(self, executor):
        """Test exekvering med riktiga verktyg (mocked)"""
        actions = [
            AgentAction("music_1", "PLAY", {}, "Play music"),
            AgentAction("music_2", "SET_VOLUME", {"level": 75}, "Set volume")
        ]
        
        plan = AgentPlan(
            plan_id="real_tools_plan",
            goal="Control music",
            actions=actions,
            created_at=datetime.now()
        )
        
        with patch('core.agent_executor.validate_and_execute_tool') as mock_tool:
            mock_tool.return_value = {"ok": True, "message": "Tool executed successfully"}
            
            result = await executor.execute_plan(plan)
        
        assert result.status == ExecutionStatus.COMPLETED
        assert result.completed_actions == 2
        assert len(result.results) == 2
        
        # Kontrollera att rätt verktyg anropades
        assert mock_tool.call_count == 2
        mock_tool.assert_any_call("PLAY", {})
        mock_tool.assert_any_call("SET_VOLUME", {"level": 75})
    
    @pytest.mark.asyncio
    async def test_complex_workflow_execution(self, executor):
        """Test exekvering av komplex workflow"""
        # Komplex plan med flera steg och dependencies
        actions = [
            AgentAction("init", "PLAY", {}, "Start playback"),
            AgentAction("setup_vol", "SET_VOLUME", {"level": 50}, "Set initial volume"),
            AgentAction("check", "PAUSE", {}, "Pause for check", depends_on=["init", "setup_vol"]),
            AgentAction("resume", "PLAY", {}, "Resume", depends_on=["check"]),
            AgentAction("final_vol", "SET_VOLUME", {"level": 80}, "Final volume", depends_on=["resume"])
        ]
        
        complex_plan = AgentPlan(
            plan_id="complex_workflow",
            goal="Complex music workflow",
            actions=actions,
            created_at=datetime.now()
        )
        
        with patch('core.agent_executor.validate_and_execute_tool') as mock_tool:
            mock_tool.return_value = {"ok": True, "message": "Success"}
            
            result = await executor.execute_plan(complex_plan)
        
        assert result.status == ExecutionStatus.COMPLETED
        assert result.completed_actions == 5
        assert result.failed_actions == 0
        
        # Kontrollera att alla steg kördes
        for action in actions:
            assert action.step_id in result.results
            assert result.results[action.step_id].status == ExecutionStatus.COMPLETED


if __name__ == "__main__":
    # Kör tester med pytest
    pytest.main([__file__, "-v", "--tb=short"])