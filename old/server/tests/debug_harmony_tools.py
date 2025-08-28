#!/usr/bin/env python3
import os
import json
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import aiohttp
from rich.console import Console
from rich.table import Table
from rich.progress import Progress

# Test cases med förväntade verktyg och argument
TEST_CASES = {
    "PLAY": [
        ("spela", {}),
        ("spela musik", {}),
        ("fortsätt spela", {}),
        ("kör låten", {}),
        ("play", {})
    ],
    "PAUSE": [
        ("pausa", {}),
        ("paus", {}),
        ("pausa musiken", {}),
        ("stoppa låten", {}),
        ("pause", {})
    ],
    "NEXT": [
        ("nästa", {}),
        ("nästa låt", {}),
        ("hoppa över", {}),
        ("byt låt", {}),
        ("next", {})
    ],
    "PREV": [
        ("föregående", {}),
        ("förra låten", {}),
        ("gå tillbaka", {}),
        ("previous", {}),
        ("back", {})
    ],
    "SET_VOLUME": [
        ("sätt volymen till 50 procent", {"level": 50}),
        ("höj volymen till 80%", {"level": 80}),
        ("sänk volymen till 20%", {"level": 20}),
        ("volym 75", {"level": 75}),
        ("ställ volymen på 60", {"level": 60})
    ],
    "MUTE": [
        ("mute", {}),
        ("stäng av ljudet", {}),
        ("tysta", {}),
        ("ljud av", {}),
        ("tyst läge", {})
    ],
    "UNMUTE": [
        ("unmute", {}),
        ("sätt på ljudet", {}),
        ("ljud på", {}),
        ("avmuta", {}),
        ("aktivera ljud", {})
    ],
    "REPEAT": [
        ("repetera", {}),
        ("upprepa låten", {}),
        ("spela om", {}),
        ("repeat", {}),
        ("loop", {})
    ],
    "SHUFFLE": [
        ("shuffle", {}),
        ("blanda låtar", {}),
        ("spela blandat", {}),
        ("random", {}),
        ("slumpvis", {})
    ],
    "LIKE": [
        ("gilla", {}),
        ("like", {}),
        ("tumme upp", {}),
        ("spara låt", {}),
        ("lägg till i favoriter", {})
    ],
    "UNLIKE": [
        ("ogilla", {}),
        ("unlike", {}),
        ("tumme ner", {}),
        ("ta bort från favoriter", {}),
        ("sluta gilla", {})
    ]
}

@dataclass
class TestResult:
    timestamp: str
    prompt: str
    expected_tool: str
    expected_args: Dict
    raw_response: Dict
    actual_tool: Optional[str] = None
    actual_args: Optional[Dict] = None
    success: bool = False
    error: Optional[str] = None

class HarmonyTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results: List[TestResult] = []
        self.console = Console()
        self.results_file = os.path.join(
            os.path.dirname(__file__),
            "results",
            f"harmony_debug_{datetime.now().strftime('%Y%m%d_%H%M')}.jsonl"
        )
        os.makedirs(os.path.dirname(self.results_file), exist_ok=True)
        
    def log_result(self, result: TestResult):
        """Logga ett testresultat till JSONL-filen"""
        with open(self.results_file, "a") as f:
            f.write(json.dumps(asdict(result)) + "\n")
    
    async def test_prompt(self, prompt: str, expected_tool: str, expected_args: Dict) -> TestResult:
        """Testa en specifik prompt mot Harmony"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/chat",
                    json={"prompt": prompt}
                ) as resp:
                    response_data = await resp.json()
                    
                    result = TestResult(
                        timestamp=datetime.now().isoformat(),
                        prompt=prompt,
                        expected_tool=expected_tool,
                        expected_args=expected_args,
                        raw_response=response_data
                    )
                    
                    # Extrahera tool metadata om det finns
                    if "meta" in response_data and "tool" in response_data["meta"]:
                        tool_data = response_data["meta"]["tool"]
                        result.actual_tool = tool_data.get("name")
                        result.actual_args = tool_data.get("args", {})
                        
                        # Validera verktyg och argument
                        if result.actual_tool == expected_tool:
                            # För SET_VOLUME, validera level/delta
                            if expected_tool == "SET_VOLUME":
                                if "level" in expected_args:
                                    result.success = result.actual_args.get("level") == expected_args["level"]
                                elif "delta" in expected_args:
                                    result.success = result.actual_args.get("delta") == expected_args["delta"]
                            # För andra verktyg, bara kolla att verktyget är rätt
                            else:
                                result.success = True
                        
                        if not result.success:
                            result.error = f"Tool mismatch: expected {expected_tool}, got {result.actual_tool}"
                    else:
                        result.error = "No tool metadata in response"
                    
                    # Logga resultatet
                    self.log_result(result)
                    
                    # Skriv ut status
                    status = "[green]PASS" if result.success else "[red]FAIL"
                    details = f"-> {result.actual_tool}" if result.actual_tool else "-> no tool"
                    if not result.success and result.error:
                        details += f" ({result.error})"
                    self.console.print(f"[{status}] \"{prompt}\" {details}")
                    
                    return result
                    
        except Exception as e:
            result = TestResult(
                timestamp=datetime.now().isoformat(),
                prompt=prompt,
                expected_tool=expected_tool,
                expected_args=expected_args,
                raw_response={},
                success=False,
                error=str(e)
            )
            self.log_result(result)
            self.console.print(f"[red]ERROR[/red] Testing \"{prompt}\": {str(e)}")
            return result

    def print_results(self):
        """Skriv ut en sammanfattning av testresultaten"""
        # Skapa resultatstabell
        table = Table(title="Harmony Tool Test Results")
        table.add_column("Tool", style="cyan")
        table.add_column("Total", justify="right")
        table.add_column("Passed", style="green", justify="right")
        table.add_column("Failed", style="red", justify="right")
        
        # Gruppera resultat per verktyg
        tool_results = {}
        for result in self.results:
            if result.expected_tool not in tool_results:
                tool_results[result.expected_tool] = []
            tool_results[result.expected_tool].append(result)
        
        # Beräkna statistik per verktyg
        total_tests = 0
        total_passed = 0
        
        for tool, results in sorted(tool_results.items()):
            passed = sum(1 for r in results if r.success)
            failed = len(results) - passed
            
            total_tests += len(results)
            total_passed += passed
            
            table.add_row(
                tool,
                str(len(results)),
                str(passed),
                str(failed)
            )
        
        # Lägg till totalsumma
        table.add_row(
            "TOTAL",
            str(total_tests),
            str(total_passed),
            str(total_tests - total_passed),
            style="bold"
        )
        
        # Skriv ut tabellen
        self.console.print("\n")
        self.console.print(table)
        self.console.print(f"\nPass rate: {(total_passed/total_tests)*100:.1f}%")
        self.console.print(f"Results saved to: {self.results_file}\n")
        
        # Skriv ut alla fel
        failed_results = [r for r in self.results if not r.success]
        if failed_results:
            self.console.print("\nFailed tests:", style="red bold")
            for result in failed_results:
                self.console.print(f"  • {result.prompt}")
                if result.actual_tool:
                    self.console.print(f"    Expected: {result.expected_tool}, Got: {result.actual_tool}")
                if result.error:
                    self.console.print(f"    {result.error}", style="red")

async def main():
    # Skapa testaren
    tester = HarmonyTester()
    
    # Testa alla fraser
    with Progress() as progress:
        task = progress.add_task("[cyan]Testing commands...", total=sum(len(phrases) for phrases in TEST_CASES.values()))
        
        for tool, test_cases in TEST_CASES.items():
            for prompt, expected_args in test_cases:
                result = await tester.test_prompt(prompt, tool, expected_args)
                tester.results.append(result)
                progress.update(task, advance=1)
                await asyncio.sleep(0.1)  # Liten paus mellan tester
    
    # Skriv ut resultaten
    tester.print_results()

if __name__ == "__main__":
    asyncio.run(main())
