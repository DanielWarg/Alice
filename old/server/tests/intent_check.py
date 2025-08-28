"""Intent check test suite.

Tests a series of natural language phrases against both router and Harmony paths,
verifying that they trigger the correct tools with expected meta.tool data.
"""
import sys
import os
import json
import asyncio
import httpx
from datetime import datetime
from typing import List, Dict, Any, Optional

# Test cases with expected outcomes
TEST_CASES = [
    {
        "prompt": "spela upp",
        "expect": {
            "tool": "PLAY",
            "source": "router",
            "args": {},
        }
    },
    {
        "prompt": "kan du spela lite musik",
        "expect": {
            "tool": "PLAY",
            "source": "harmony",
            "args": {},
        }
    },
    {
        "prompt": "pausa",
        "expect": {
            "tool": "PAUSE",
            "source": "router",
            "args": {},
        }
    },
    {
        "prompt": "skulle du kunna pausa i några minuter",
        "expect": {
            "tool": "PAUSE",
            "source": "harmony",
            "args": {},
        }
    },
    {
        "prompt": "höj volymen",
        "expect": {
            "tool": "SET_VOLUME",
            "source": "router",
            "args": {"delta": 10},
        }
    },
    {
        "prompt": "höj volymen till 80%",
        "expect": {
            "tool": "SET_VOLUME",
            "source": "harmony",
            "args": {"level": 80},
        }
    },
]

class IntentCheckResult:
    def __init__(
        self,
        prompt: str,
        expected_tool: str,
        expected_source: str,
        expected_args: Dict[str, Any],
    ):
        self.prompt = prompt
        self.expected_tool = expected_tool
        self.expected_source = expected_source
        self.expected_args = expected_args
        self.actual_tool: Optional[str] = None
        self.actual_source: Optional[str] = None
        self.actual_args: Optional[Dict[str, Any]] = None
        self.executed: Optional[bool] = None
        self.latency_ms: Optional[float] = None
        self.response_time_ms: float = 0
        self.passed = False
        self.error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prompt": self.prompt,
            "expected": {
                "tool": self.expected_tool,
                "source": self.expected_source,
                "args": self.expected_args,
            },
            "actual": {
                "tool": self.actual_tool,
                "source": self.actual_source,
                "args": self.actual_args,
                "executed": self.executed,
                "latency_ms": self.latency_ms,
            },
            "response_time_ms": self.response_time_ms,
            "passed": self.passed,
            "error": self.error,
        }

class IntentCheckReport:
    def __init__(self):
        self.results: List[IntentCheckResult] = []
        self.start_time = datetime.utcnow()
        self.end_time: Optional[datetime] = None

    def add_result(self, result: IntentCheckResult):
        self.results.append(result)

    def finalize(self):
        self.end_time = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)
        router_hits = sum(1 for r in self.results if r.actual_source == "router")
        harmony_hits = sum(1 for r in self.results if r.actual_source == "harmony")
        executed = sum(1 for r in self.results if r.executed)

        return {
            "summary": {
                "total": total,
                "passed": passed,
                "failed": total - passed,
                "pass_rate": round(100 * passed / max(1, total), 1),
                "router_hits": router_hits,
                "harmony_hits": harmony_hits,
                "executed_rate": round(100 * executed / max(1, total), 1),
                "avg_latency_ms": round(
                    sum(r.latency_ms or 0 for r in self.results) / max(1, total),
                    1,
                ),
                "avg_response_ms": round(
                    sum(r.response_time_ms for r in self.results) / max(1, total),
                    1,
                ),
            },
            "results": [r.to_dict() for r in self.results],
            "start_time": self.start_time.isoformat() + "Z",
            "end_time": self.end_time.isoformat() + "Z" if self.end_time else None,
        }

    def save_json(self, path: str):
        """Save report as JSON."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    def save_markdown(self, path: str):
        """Save report as Markdown with tables."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        d = self.to_dict()
        with open(path, "w") as f:
            f.write("# Intent Check Report\n\n")
            
            # Summary table
            f.write("## Summary\n\n")
            f.write("| Metric | Value |\n")
            f.write("|--------|-------|\n")
            s = d["summary"]
            f.write(f"| Total Tests | {s['total']} |\n")
            f.write(f"| Passed | {s['passed']} |\n")
            f.write(f"| Failed | {s['failed']} |\n")
            f.write(f"| Pass Rate | {s['pass_rate']}% |\n")
            f.write(f"| Router Hits | {s['router_hits']} |\n")
            f.write(f"| Harmony Hits | {s['harmony_hits']} |\n")
            f.write(f"| Tool Execution Rate | {s['executed_rate']}% |\n")
            f.write(f"| Avg Tool Latency | {s['avg_latency_ms']} ms |\n")
            f.write(f"| Avg Response Time | {s['avg_response_ms']} ms |\n")
            f.write("\n")

            # Results table
            f.write("## Detailed Results\n\n")
            f.write("| Prompt | Expected | Actual | Latency | Passed |\n")
            f.write("|--------|-----------|---------|----------|--------|\n")
            for r in d["results"]:
                exp = f"{r['expected']['tool']} via {r['expected']['source']}"
                act = f"{r['actual']['tool'] or '?'} via {r['actual']['source'] or '?'}"
                lat = f"{r['actual']['latency_ms']:.1f}ms" if r['actual']['latency_ms'] is not None else "?"
                passed = "✅" if r["passed"] else "❌"
                f.write(f"| `{r['prompt']}` | {exp} | {act} | {lat} | {passed} |\n")
            f.write("\n")

            # Timestamp
            f.write(f"\nTest run: {d['start_time']} → {d['end_time']}\n")

async def run_intent_check(base_url: str = "http://127.0.0.1:8000") -> IntentCheckReport:
    """Run all test cases and generate report."""
    report = IntentCheckReport()
    
    async with httpx.AsyncClient() as client:
        for case in TEST_CASES:
            result = IntentCheckResult(
                prompt=case["prompt"],
                expected_tool=case["expect"]["tool"],
                expected_source=case["expect"]["source"],
                expected_args=case["expect"]["args"],
            )

            try:
                t0 = datetime.utcnow()
                r = await client.post(
                    f"{base_url}/api/chat",
                    json={"prompt": case["prompt"]},
                    timeout=10.0,
                )
                result.response_time_ms = (datetime.utcnow() - t0).total_seconds() * 1000

                if r.status_code != 200:
                    result.error = f"HTTP {r.status_code}"
                    report.add_result(result)
                    continue

                data = r.json()
                meta_tool = (data.get("meta") or {}).get("tool")
                if not meta_tool:
                    result.error = "No meta.tool in response"
                    report.add_result(result)
                    continue

                # Record actual values
                result.actual_tool = meta_tool.get("name")
                result.actual_source = meta_tool.get("source")
                result.actual_args = meta_tool.get("args")
                result.executed = meta_tool.get("executed")
                result.latency_ms = meta_tool.get("latency_ms")

                # Check expectations
                result.passed = (
                    result.actual_tool == result.expected_tool
                    and result.actual_source == result.expected_source
                    # Loose args check - expected must be subset of actual
                    and all(
                        result.actual_args.get(k) == v
                        for k, v in result.expected_args.items()
                    )
                )

            except Exception as e:
                result.error = str(e)

            report.add_result(result)

    report.finalize()
    return report

async def main():
    """Run intent check and save reports."""
    base_url = os.getenv("SERVER_URL", "http://127.0.0.1:8000")
    report_dir = os.getenv("REPORT_DIR", "tests/reports")
    
    # Run tests
    report = await run_intent_check(base_url)
    
    # Save reports
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    report.save_json(f"{report_dir}/intent_check_{ts}.json")
    report.save_markdown(f"{report_dir}/intent_check_{ts}.md")
    
    # Print summary
    d = report.to_dict()
    print("\nIntent Check Summary:")
    print(f"Total: {d['summary']['total']}")
    print(f"Passed: {d['summary']['passed']}")
    print(f"Pass Rate: {d['summary']['pass_rate']}%")
    print(f"Router Hits: {d['summary']['router_hits']}")
    print(f"Harmony Hits: {d['summary']['harmony_hits']}")
    print(f"\nReports saved to {report_dir}/")

    # Exit with status
    sys.exit(0 if d["summary"]["pass_rate"] > 95 else 1)

if __name__ == "__main__":
    asyncio.run(main())
