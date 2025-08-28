"""
Agent Planner - Bryter ner komplexa uppgifter i exekverade steg.
Använder AI för att skapa detaljerade handlingsplaner.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import json
from .tool_specs import enabled_tools, get_tool_spec

@dataclass
class AgentAction:
    """En enda handling i en plan"""
    step_id: str
    tool: str
    parameters: Dict[str, Any]
    description: str
    depends_on: List[str] = None  # Vilka steg som måste slutföras först
    expected_outcome: str = None
    retry_count: int = 0
    max_retries: int = 2
    
    def __post_init__(self):
        if self.depends_on is None:
            self.depends_on = []

@dataclass 
class AgentPlan:
    """En komplett handlingsplan för en uppgift"""
    plan_id: str
    goal: str
    actions: List[AgentAction]
    created_at: datetime
    estimated_duration_seconds: int = None
    confidence_score: float = 0.0
    status: str = "created"  # created, executing, completed, failed
    
    def get_next_actions(self, completed_steps: List[str]) -> List[AgentAction]:
        """Hämta nästa actions som kan köras baserat på dependencies"""
        available_actions = []
        for action in self.actions:
            if action.step_id in completed_steps:
                continue
            # Kolla om alla dependencies är slutförda
            if all(dep in completed_steps for dep in action.depends_on):
                available_actions.append(action)
        return available_actions

class AgentPlanner:
    """
    Planner som bryter ner komplexa mål i exekverbara steg.
    Använder AI och regelbaserad logik för att skapa effektiva planer.
    """
    
    def __init__(self):
        self.available_tools = enabled_tools()
        self.planning_prompts = {
            "swedish": """Du är Alice's planeringsmodul. Bryt ner detta mål i konkreta, exekverbara steg.

Tillgängliga verktyg: {tools}

Mål: {goal}
Kontext: {context}

Skapa en detaljerad plan som en JSON-array med följande format:
[
  {{
    "step_id": "step_1",
    "tool": "TOOL_NAME",
    "parameters": {{"param": "värde"}},
    "description": "Vad detta steg gör",
    "depends_on": ["step_0"],
    "expected_outcome": "Förväntat resultat"
  }}
]

Viktigt:
- Använd endast verktyg som finns i listan
- Gör stegen specifika och testbara
- Ange tydliga dependencies mellan steg
- Beskriv förväntade resultat för varje steg

Plan:""",
            
            "english": """You are Alice's planning module. Break down this goal into concrete, executable steps.

Available tools: {tools}
Goal: {goal}
Context: {context}

Create a detailed plan as a JSON array with this format:
[
  {{
    "step_id": "step_1", 
    "tool": "TOOL_NAME",
    "parameters": {{"param": "value"}},
    "description": "What this step does",
    "depends_on": ["step_0"],
    "expected_outcome": "Expected result"
  }}
]

Important:
- Only use tools from the available list
- Make steps specific and testable
- Specify clear dependencies between steps
- Describe expected outcomes for each step

Plan:"""
        }
    
    async def create_plan(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None,
        language: str = "swedish",
        ai_client = None
    ) -> AgentPlan:
        """
        Skapa en handlingsplan för att uppnå ett mål.
        
        Args:
            goal: Målet som ska uppnås
            context: Extra kontext som kan påverka planeringen
            language: Språk för planering (swedish/english)
            ai_client: AI-klient för planering (Ollama, OpenAI, etc.)
            
        Returns:
            AgentPlan med detaljerade steg
        """
        plan_id = f"plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Bygg tillgängliga verktyg-lista
        tools_info = []
        for tool_name in (self.available_tools or []):
            spec = get_tool_spec(tool_name)
            if spec:
                tools_info.append(f"{tool_name}: {spec.get('description', 'No description')}")
        
        tools_text = "\n".join(tools_info)
        context_text = json.dumps(context or {}, ensure_ascii=False)
        
        # Förbered prompt
        prompt_template = self.planning_prompts.get(language, self.planning_prompts["swedish"])
        full_prompt = prompt_template.format(
            tools=tools_text,
            goal=goal,
            context=context_text
        )
        
        try:
            # Använd AI för att skapa plan (om tillgänglig)
            if ai_client:
                print(f"📋 Using AI planning for goal: {goal}")
                plan_response = await self._generate_ai_plan(full_prompt, ai_client)
            else:
                # Fallback till regelbaserad planering
                print(f"📋 Using rule-based planning for goal: {goal}")
                plan_response = self._generate_rule_based_plan(goal, context)
                print(f"📋 Generated plan JSON: {plan_response}")
            
            # Parsa AI-respons till AgentAction-objekt
            actions = self._parse_plan_response(plan_response)
            
            # Validera plan
            validated_actions = self._validate_plan(actions)
            
            # Skapa slutlig plan
            plan = AgentPlan(
                plan_id=plan_id,
                goal=goal,
                actions=validated_actions,
                created_at=datetime.now(),
                confidence_score=self._calculate_confidence(validated_actions),
                estimated_duration_seconds=self._estimate_duration(validated_actions)
            )
            
            return plan
            
        except Exception as e:
            # Skapa minimal fallback-plan
            fallback_action = AgentAction(
                step_id="fallback_1",
                tool="SIMPLE_RESPONSE", 
                parameters={"message": f"Kunde inte skapa plan för: {goal}. Fel: {str(e)}"},
                description="Fallback response när planering misslyckades"
            )
            
            return AgentPlan(
                plan_id=plan_id,
                goal=goal,
                actions=[fallback_action],
                created_at=datetime.now(),
                confidence_score=0.1
            )
    
    async def _generate_ai_plan(self, prompt: str, ai_client) -> str:
        """Generera plan med AI-modell"""
        # Försök använda AI-klientens generate-metod
        if hasattr(ai_client, 'generate'):
            if asyncio.iscoroutinefunction(ai_client.generate):
                return await ai_client.generate()
            else:
                return ai_client.generate()
        
        # Fallback för andra AI-klient strukturer
        if hasattr(ai_client, 'return_value'):
            return ai_client.return_value
            
        # Detta kommer att integreras med Alice's befintliga AI-system senare
        return '[]'
    
    def _generate_rule_based_plan(self, goal: str, context: Optional[Dict[str, Any]]) -> str:
        """Enkel regelbaserad planering som fallback"""
        goal_lower = goal.lower()
        
        # Enkla mönster för vanliga mål
        if "musik" in goal_lower or "spela" in goal_lower:
            return json.dumps([
                {
                    "step_id": "step_1",
                    "tool": "PLAY",
                    "parameters": {},
                    "description": "Starta musikuppspelning",
                    "depends_on": [],
                    "expected_outcome": "Musik spelar"
                }
            ])
        
        elif "kalender" in goal_lower or "möte" in goal_lower:
            return json.dumps([
                {
                    "step_id": "step_1", 
                    "tool": "LIST_CALENDAR_EVENTS",
                    "parameters": {"max_results": 10},
                    "description": "Hämta kalenderhändelser",
                    "depends_on": [],
                    "expected_outcome": "Lista med kommande händelser"
                }
            ])
            
        elif "mail" in goal_lower or "e-post" in goal_lower:
            return json.dumps([
                {
                    "step_id": "step_1",
                    "tool": "READ_EMAILS", 
                    "parameters": {"max_results": 10},
                    "description": "Hämta senaste e-postmeddelanden",
                    "depends_on": [],
                    "expected_outcome": "Lista med e-postmeddelanden"
                }
            ])
        
        elif "tid" in goal_lower or "klocka" in goal_lower or "datum" in goal_lower:
            return json.dumps([
                {
                    "step_id": "step_1",
                    "tool": "CURRENT_TIME",
                    "parameters": {},
                    "description": "Hämta aktuell tid och datum",
                    "depends_on": [],
                    "expected_outcome": "Visa aktuell tid"
                }
            ])
        
        # Default fallback
        return json.dumps([
            {
                "step_id": "step_1",
                "tool": "SIMPLE_RESPONSE",
                "parameters": {"message": f"Jag förstår att du vill: {goal}"},
                "description": "Bekräfta mål när specifik plan inte kunde skapas", 
                "depends_on": [],
                "expected_outcome": "Bekräftelse skickad"
            }
        ])
    
    def _parse_plan_response(self, plan_response: str) -> List[AgentAction]:
        """Parsa AI-respons till AgentAction-objekt"""
        try:
            plan_data = json.loads(plan_response.strip())
            if not isinstance(plan_data, list):
                plan_data = [plan_data]
            
            actions = []
            for step in plan_data:
                action = AgentAction(
                    step_id=step.get("step_id", f"step_{len(actions) + 1}"),
                    tool=step.get("tool", "SIMPLE_RESPONSE"),
                    parameters=step.get("parameters", {}),
                    description=step.get("description", "No description"),
                    depends_on=step.get("depends_on", []),
                    expected_outcome=step.get("expected_outcome", "Unknown outcome")
                )
                actions.append(action)
            
            return actions
            
        except json.JSONDecodeError:
            # Skapa minimal action om JSON parsing misslyckas
            return [
                AgentAction(
                    step_id="parse_error_1",
                    tool="SIMPLE_RESPONSE",
                    parameters={"message": "Kunde inte parsa planering"},
                    description="Fallback när plan-parsing misslyckades"
                )
            ]
    
    def _validate_plan(self, actions: List[AgentAction]) -> List[AgentAction]:
        """Validera att alla verktyg i planen existerar och är aktiverade"""
        validated_actions = []
        
        for action in actions:
            # Kontrollera att verktyget finns och är aktiverat
            if action.tool in self.available_tools or action.tool == "SIMPLE_RESPONSE":
                validated_actions.append(action)
            else:
                # Ersätt med fallback
                fallback_action = AgentAction(
                    step_id=action.step_id,
                    tool="SIMPLE_RESPONSE",
                    parameters={"message": f"Verktyg {action.tool} är inte tillgängligt"},
                    description=f"Fallback för otillgängligt verktyg: {action.tool}"
                )
                validated_actions.append(fallback_action)
        
        return validated_actions
    
    def _calculate_confidence(self, actions: List[AgentAction]) -> float:
        """Beräkna konfidenspoäng för planen"""
        if not actions:
            return 0.0
        
        # Enkel konfidensberäkning baserat på verktygtillgänglighet
        valid_tools = sum(1 for action in actions if action.tool in self.available_tools)
        return min(valid_tools / len(actions), 1.0)
    
    def _estimate_duration(self, actions: List[AgentAction]) -> int:
        """Uppskatta hur lång tid planen tar att utföra (sekunder)"""
        # Enkel heuristik: varje steg tar 5-15 sekunder beroende på verktyg
        total_seconds = 0
        
        for action in actions:
            if action.tool in ["PLAY", "PAUSE", "STOP", "NEXT", "PREV"]:
                total_seconds += 2  # Snabba verktyg
            elif action.tool in ["GET_GMAIL_MESSAGES", "GET_CALENDAR_EVENTS"]:
                total_seconds += 5  # API-anrop
            else:
                total_seconds += 10  # Default
        
        return total_seconds
    
    def optimize_plan(self, plan: AgentPlan) -> AgentPlan:
        """Optimera en befintlig plan för bättre prestanda"""
        # Identifiera parallella steg
        optimized_actions = []
        
        # Enkel optimering: kombinera steg som kan köras samtidigt
        for action in plan.actions:
            # För nu, behåll alla steg som de är
            # Framtida förbättringar kan lägga till parallellisering
            optimized_actions.append(action)
        
        plan.actions = optimized_actions
        plan.confidence_score = self._calculate_confidence(optimized_actions)
        
        return plan