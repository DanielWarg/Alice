"""
Unit tests för AgentPlanner.
Testar planning-logik, validation och error handling.
"""

import pytest
import json
from datetime import datetime
from unittest.mock import patch, AsyncMock

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.agent_planner import AgentPlanner, AgentPlan, AgentAction


class TestAgentAction:
    """Tester för AgentAction dataclass"""
    
    def test_agent_action_creation(self):
        """Test grundläggande skapande av AgentAction"""
        action = AgentAction(
            step_id="test_step",
            tool="TEST_TOOL",
            parameters={"param": "value"},
            description="Test action"
        )
        
        assert action.step_id == "test_step"
        assert action.tool == "TEST_TOOL"
        assert action.parameters == {"param": "value"}
        assert action.description == "Test action"
        assert action.depends_on == []
        assert action.retry_count == 0
        assert action.max_retries == 2
    
    def test_agent_action_with_dependencies(self):
        """Test AgentAction med dependencies"""
        action = AgentAction(
            step_id="step_2",
            tool="TEST_TOOL",
            parameters={},
            description="Dependent action",
            depends_on=["step_1"]
        )
        
        assert action.depends_on == ["step_1"]


class TestAgentPlan:
    """Tester för AgentPlan dataclass"""
    
    def test_agent_plan_creation(self):
        """Test grundläggande skapande av AgentPlan"""
        actions = [
            AgentAction("step_1", "TOOL_1", {}, "First step"),
            AgentAction("step_2", "TOOL_2", {}, "Second step", depends_on=["step_1"])
        ]
        
        plan = AgentPlan(
            plan_id="test_plan",
            goal="Test goal",
            actions=actions,
            created_at=datetime.now()
        )
        
        assert plan.plan_id == "test_plan"
        assert plan.goal == "Test goal"
        assert len(plan.actions) == 2
        assert plan.status == "created"
    
    def test_get_next_actions_no_dependencies(self):
        """Test hämta nästa actions utan dependencies"""
        actions = [
            AgentAction("step_1", "TOOL_1", {}, "First step"),
            AgentAction("step_2", "TOOL_2", {}, "Second step")
        ]
        
        plan = AgentPlan("test", "goal", actions, datetime.now())
        next_actions = plan.get_next_actions([])
        
        assert len(next_actions) == 2
        assert next_actions[0].step_id == "step_1"
        assert next_actions[1].step_id == "step_2"
    
    def test_get_next_actions_with_dependencies(self):
        """Test hämta nästa actions med dependencies"""
        actions = [
            AgentAction("step_1", "TOOL_1", {}, "First step"),
            AgentAction("step_2", "TOOL_2", {}, "Second step", depends_on=["step_1"]),
            AgentAction("step_3", "TOOL_3", {}, "Third step", depends_on=["step_1", "step_2"])
        ]
        
        plan = AgentPlan("test", "goal", actions, datetime.now())
        
        # Inga steg slutförda - endast step_1 kan köras
        next_actions = plan.get_next_actions([])
        assert len(next_actions) == 1
        assert next_actions[0].step_id == "step_1"
        
        # step_1 slutförd - step_2 kan köras
        next_actions = plan.get_next_actions(["step_1"])
        assert len(next_actions) == 1
        assert next_actions[0].step_id == "step_2"
        
        # step_1 och step_2 slutförda - step_3 kan köras
        next_actions = plan.get_next_actions(["step_1", "step_2"])
        assert len(next_actions) == 1
        assert next_actions[0].step_id == "step_3"


class TestAgentPlanner:
    """Tester för AgentPlanner klass"""
    
    @pytest.fixture
    def planner(self):
        """Skapa en AgentPlanner instans för tester"""
        return AgentPlanner()
    
    def test_planner_initialization(self, planner):
        """Test att planner initialiseras korrekt"""
        assert planner.available_tools is not None
        assert isinstance(planner.planning_prompts, dict)
        assert "swedish" in planner.planning_prompts
        assert "english" in planner.planning_prompts
    
    @pytest.mark.asyncio
    async def test_create_plan_music_goal(self, planner):
        """Test skapande av plan för musikmål"""
        plan = await planner.create_plan("spela musik")
        
        assert isinstance(plan, AgentPlan)
        assert "musik" in plan.goal.lower() or "spela" in plan.goal.lower()
        assert len(plan.actions) >= 1
        assert plan.actions[0].tool == "PLAY"
        assert plan.confidence_score > 0
    
    @pytest.mark.asyncio
    async def test_create_plan_calendar_goal(self, planner):
        """Test skapande av plan för kalendermål"""
        plan = await planner.create_plan("visa min kalender")
        
        assert isinstance(plan, AgentPlan)
        assert len(plan.actions) >= 1
        assert plan.actions[0].tool == "LIST_CALENDAR_EVENTS"
        assert plan.confidence_score > 0
    
    @pytest.mark.asyncio
    async def test_create_plan_email_goal(self, planner):
        """Test skapande av plan för e-postmål"""
        plan = await planner.create_plan("kolla min mail")
        
        assert isinstance(plan, AgentPlan)
        assert len(plan.actions) >= 1
        assert plan.actions[0].tool == "READ_EMAILS"
    
    @pytest.mark.asyncio
    async def test_create_plan_unknown_goal(self, planner):
        """Test skapande av plan för okänt mål"""
        plan = await planner.create_plan("gör något konstigt")
        
        assert isinstance(plan, AgentPlan)
        assert len(plan.actions) >= 1
        assert plan.actions[0].tool == "SIMPLE_RESPONSE"
    
    def test_parse_plan_response_valid_json(self, planner):
        """Test parsing av giltig JSON-respons"""
        json_response = """[
            {
                "step_id": "step_1",
                "tool": "TEST_TOOL",
                "parameters": {"test": "value"},
                "description": "Test step",
                "depends_on": [],
                "expected_outcome": "Success"
            }
        ]"""
        
        actions = planner._parse_plan_response(json_response)
        
        assert len(actions) == 1
        assert actions[0].step_id == "step_1"
        assert actions[0].tool == "TEST_TOOL"
        assert actions[0].parameters == {"test": "value"}
    
    def test_parse_plan_response_invalid_json(self, planner):
        """Test parsing av ogiltig JSON - ska skapa fallback"""
        invalid_response = "This is not JSON"
        
        actions = planner._parse_plan_response(invalid_response)
        
        assert len(actions) == 1
        assert actions[0].tool == "SIMPLE_RESPONSE"
        assert "parsing" in actions[0].description.lower()
    
    def test_parse_plan_response_single_object(self, planner):
        """Test parsing av enstaka objekt (inte array)"""
        json_response = """{
            "step_id": "step_1",
            "tool": "TEST_TOOL",
            "parameters": {},
            "description": "Single step"
        }"""
        
        actions = planner._parse_plan_response(json_response)
        
        assert len(actions) == 1
        assert actions[0].step_id == "step_1"
    
    @patch('core.agent_planner.enabled_tools')
    def test_validate_plan_valid_tools(self, mock_enabled_tools, planner):
        """Test validering av plan med giltiga verktyg"""
        mock_enabled_tools.return_value = ["TEST_TOOL", "ANOTHER_TOOL"]
        planner.available_tools = ["TEST_TOOL", "ANOTHER_TOOL"]
        
        actions = [
            AgentAction("step_1", "TEST_TOOL", {}, "Valid tool"),
            AgentAction("step_2", "ANOTHER_TOOL", {}, "Another valid tool")
        ]
        
        validated = planner._validate_plan(actions)
        
        assert len(validated) == 2
        assert validated[0].tool == "TEST_TOOL"
        assert validated[1].tool == "ANOTHER_TOOL"
    
    @patch('core.agent_planner.enabled_tools')
    def test_validate_plan_invalid_tools(self, mock_enabled_tools, planner):
        """Test validering av plan med ogiltiga verktyg"""
        mock_enabled_tools.return_value = ["VALID_TOOL"]
        planner.available_tools = ["VALID_TOOL"]
        
        actions = [
            AgentAction("step_1", "VALID_TOOL", {}, "Valid tool"),
            AgentAction("step_2", "INVALID_TOOL", {}, "Invalid tool")
        ]
        
        validated = planner._validate_plan(actions)
        
        assert len(validated) == 2
        assert validated[0].tool == "VALID_TOOL"
        assert validated[1].tool == "SIMPLE_RESPONSE"  # Fallback
        assert "inte tillgängligt" in validated[1].parameters["message"]
    
    def test_calculate_confidence_all_valid(self, planner):
        """Test confidence-beräkning med alla giltiga verktyg"""
        planner.available_tools = ["TOOL_1", "TOOL_2"]
        
        actions = [
            AgentAction("step_1", "TOOL_1", {}, "Step 1"),
            AgentAction("step_2", "TOOL_2", {}, "Step 2")
        ]
        
        confidence = planner._calculate_confidence(actions)
        assert confidence == 1.0
    
    def test_calculate_confidence_mixed_validity(self, planner):
        """Test confidence-beräkning med blandad giltighet"""
        planner.available_tools = ["TOOL_1"]
        
        actions = [
            AgentAction("step_1", "TOOL_1", {}, "Valid"),
            AgentAction("step_2", "INVALID_TOOL", {}, "Invalid")
        ]
        
        confidence = planner._calculate_confidence(actions)
        assert confidence == 0.5
    
    def test_calculate_confidence_empty_plan(self, planner):
        """Test confidence-beräkning med tom plan"""
        confidence = planner._calculate_confidence([])
        assert confidence == 0.0
    
    def test_estimate_duration(self, planner):
        """Test tidsuppskattning för plan"""
        actions = [
            AgentAction("step_1", "PLAY", {}, "Fast tool"),
            AgentAction("step_2", "GET_GMAIL_MESSAGES", {}, "API call"),
            AgentAction("step_3", "UNKNOWN_TOOL", {}, "Unknown tool")
        ]
        
        duration = planner._estimate_duration(actions)
        
        # PLAY = 2s, GET_GMAIL_MESSAGES = 5s, UNKNOWN = 10s
        assert duration == 17
    
    def test_optimize_plan(self, planner):
        """Test planoptimering"""
        actions = [
            AgentAction("step_1", "TOOL_1", {}, "Step 1"),
            AgentAction("step_2", "TOOL_2", {}, "Step 2")
        ]
        
        original_plan = AgentPlan("test", "goal", actions, datetime.now())
        optimized_plan = planner.optimize_plan(original_plan)
        
        # För tillfället ska ingen förändring ske
        assert len(optimized_plan.actions) == len(original_plan.actions)
        assert optimized_plan.confidence_score >= 0


class TestAgentPlannerIntegration:
    """Integration tests för AgentPlanner med mock AI"""
    
    @pytest.fixture
    def planner(self):
        return AgentPlanner()
    
    @pytest.mark.asyncio
    async def test_create_plan_with_context(self, planner):
        """Test skapande av plan med kontext"""
        context = {
            "current_time": "14:30",
            "location": "office",
            "previous_action": "checked_calendar"
        }
        
        plan = await planner.create_plan(
            "spela lugn musik för fokus", 
            context=context
        )
        
        assert isinstance(plan, AgentPlan)
        assert len(plan.actions) >= 1
        assert plan.confidence_score > 0
    
    @pytest.mark.asyncio
    async def test_create_plan_english(self, planner):
        """Test skapande av plan på engelska"""
        plan = await planner.create_plan(
            "play music",
            language="english"
        )
        
        assert isinstance(plan, AgentPlan)
        assert len(plan.actions) >= 1
    
    @pytest.mark.asyncio
    async def test_create_plan_with_mock_ai(self, planner):
        """Test skapande av plan med mock AI-klient"""
        mock_ai = AsyncMock()
        mock_ai.generate.return_value = """[{
            "step_id": "ai_step_1",
            "tool": "PLAY",
            "parameters": {},
            "description": "AI generated step",
            "depends_on": [],
            "expected_outcome": "Music playing"
        }]"""
        
        plan = await planner.create_plan(
            "spela musik",
            ai_client=mock_ai
        )
        
        assert isinstance(plan, AgentPlan)
        # AI-genererad plan ska användas om tillgänglig
        assert len(plan.actions) >= 1
    
    @pytest.mark.asyncio
    async def test_create_plan_error_handling(self, planner):
        """Test error handling vid plan creation"""
        # Simulera fel genom att ändra available_tools till None
        original_tools = planner.available_tools
        planner.available_tools = None
        
        try:
            plan = await planner.create_plan("test goal")
            
            # Även vid fel ska en plan skapas (fallback)
            assert isinstance(plan, AgentPlan)
            assert len(plan.actions) >= 1
            assert plan.actions[0].tool == "SIMPLE_RESPONSE"
            assert plan.confidence_score < 0.5
        finally:
            # Återställ
            planner.available_tools = original_tools


if __name__ == "__main__":
    # Kör tester med pytest
    pytest.main([__file__, "-v", "--tb=short"])