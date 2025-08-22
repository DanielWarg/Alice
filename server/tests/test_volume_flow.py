"""Test script för att debugga volymkommandon.

Detta script testar hela flödet från input till output för volymrelaterade kommandon.
Det loggar varje steg i processen för att hjälpa oss hitta var saker går fel.
"""
import os
import json
import logging
import asyncio
import httpx
from typing import Dict, Any, Optional

# Sätt upp loggning
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('volume_test.log')
    ]
)
logger = logging.getLogger(__name__)

# Test cases med förväntade resultat
TEST_CASES = [
    {
        "input": "höj volymen",
        "expect": {
            "source": "router",
            "tool": "SET_VOLUME",
            "args": {"delta": 10}
        }
    },
    {
        "input": "höj volymen till 80%",
        "expect": {
            "source": "router",
            "tool": "SET_VOLUME",
            "args": {"level": 80}
        }
    },
    {
        "input": "sätt volymen till 50 procent",
        "expect": {
            "source": "router",
            "tool": "SET_VOLUME",
            "args": {"level": 50}
        }
    },
    {
        "input": "sänk volymen lite",
        "expect": {
            "source": "harmony",
            "tool": "SET_VOLUME",
            "args": {"delta": -10}
        }
    }
]

async def test_nlu_route(text: str) -> Dict[str, Any]:
    """Testa NLU-agentens route endpoint direkt."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            logger.info(f"Testing NLU route with: {text}")
            r = await client.post(
                "http://127.0.0.1:7071/agent/route",
                json={"text": text}
            )
            r.raise_for_status()
            data = r.json()
            logger.info(f"NLU response: {json.dumps(data, indent=2)}")
            return data
    except Exception as e:
        logger.error(f"NLU route error: {e}")
        return {}

async def test_chat_endpoint(text: str) -> Dict[str, Any]:
    """Testa backend chat endpoint."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            logger.info(f"Testing chat endpoint with: {text}")
            r = await client.post(
                "http://127.0.0.1:8000/api/chat",
                json={"prompt": text}
            )
            r.raise_for_status()
            data = r.json()
            logger.info(f"Chat response: {json.dumps(data, indent=2)}")
            return data
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        return {}

def check_result(case: Dict[str, Any], nlu_result: Dict[str, Any], chat_result: Dict[str, Any]) -> bool:
    """Kontrollera om resultatet matchar förväntningarna."""
    expect = case["expect"]
    
    # Kontrollera NLU resultat
    if nlu_result.get("ok"):
        plan = nlu_result.get("plan", {})
        confidence = nlu_result.get("confidence", 0)
        logger.info(f"NLU confidence: {confidence}")
        logger.info(f"NLU plan: {json.dumps(plan, indent=2)}")
        
        if expect["source"] == "router" and confidence < 0.9:
            logger.warning("Low confidence for router case")
            return False
    
    # Kontrollera chat resultat
    if chat_result.get("ok"):
        meta = chat_result.get("meta", {}).get("tool", {})
        logger.info(f"Chat meta.tool: {json.dumps(meta, indent=2)}")
        
        # Kontrollera source
        actual_source = meta.get("source")
        if actual_source != expect["source"]:
            logger.error(f"Source mismatch: expected {expect['source']}, got {actual_source}")
            return False
        
        # Kontrollera tool
        actual_tool = meta.get("name")
        if actual_tool != expect["tool"]:
            logger.error(f"Tool mismatch: expected {expect['tool']}, got {actual_tool}")
            return False
        
        # Kontrollera args
        actual_args = meta.get("args", {})
        for k, v in expect["args"].items():
            if k not in actual_args or actual_args[k] != v:
                logger.error(f"Args mismatch: expected {expect['args']}, got {actual_args}")
                return False
        
        return True
    
    return False

async def run_tests():
    """Kör alla testfall."""
    results = []
    for case in TEST_CASES:
        logger.info("=" * 80)
        logger.info(f"Testing case: {case['input']}")
        
        # Testa NLU först
        nlu_result = await test_nlu_route(case["input"])
        
        # Testa sedan hela flödet via chat
        chat_result = await test_chat_endpoint(case["input"])
        
        # Kontrollera resultat
        passed = check_result(case, nlu_result, chat_result)
        results.append(passed)
        
        logger.info(f"Test {'PASSED' if passed else 'FAILED'}")
        logger.info("=" * 80)
        logger.info("")  # Tom rad mellan tester
    
    # Summera resultat
    total = len(results)
    passed = sum(1 for r in results if r)
    logger.info(f"Test Summary: {passed}/{total} passed ({passed/total*100:.1f}%)")

if __name__ == "__main__":
    asyncio.run(run_tests())
