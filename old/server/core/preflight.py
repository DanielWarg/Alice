"""
Preflight-kontroller för att verifiera att alla delar av systemet är synkroniserade.
Körs innan servern startar och innan viktiga operationer.
"""

import logging
from typing import Dict, Any, List, Set, Tuple
from .tool_specs import enabled_tools, build_harmony_tool_specs
from .tool_registry import get_executor_names

logger = logging.getLogger(__name__)

def check_tool_surface_consistency() -> Tuple[bool, Dict[str, Any]]:
    """
    Kontrollera att verktygsytan är konsistent mellan alla delar.
    Returnerar (is_consistent, details).
    """
    try:
        # Hämta verktyg från alla källor
        enabled = set(enabled_tools())
        spec = set(t["name"] for t in build_harmony_tool_specs())
        reg = set(get_executor_names())
        
        # Kontrollera konsistens
        missing_enabled_spec = enabled - spec
        extra_enabled_spec = spec - enabled
        missing_spec_reg = spec - reg
        extra_spec_reg = reg - spec
        
        # Sammanställ resultat
        details = {
            "enabled": sorted(list(enabled)),
            "spec": sorted(list(spec)),
            "registry": sorted(list(reg)),
            "missing_enabled_spec": sorted(list(missing_enabled_spec)),
            "extra_enabled_spec": sorted(list(extra_enabled_spec)),
            "missing_spec_reg": sorted(list(missing_spec_reg)),
            "extra_spec_reg": sorted(list(extra_spec_reg)),
            "counts": {
                "enabled": len(enabled),
                "spec": len(spec),
                "registry": len(reg)
            }
        }
        
        # Kontrollera om allt matchar
        is_consistent = (
            len(missing_enabled_spec) == 0 and
            len(extra_enabled_spec) == 0 and
            len(missing_spec_reg) == 0 and
            len(extra_spec_reg) == 0
        )
        
        if not is_consistent:
            logger.error("Tool surface inconsistency detected:")
            if missing_enabled_spec:
                logger.error(f"  Tools in ENABLED_TOOLS but not in spec: {missing_enabled_spec}")
            if extra_enabled_spec:
                logger.error(f"  Tools in spec but not in ENABLED_TOOLS: {extra_enabled_spec}")
            if missing_spec_reg:
                logger.error(f"  Tools in spec but not in registry: {missing_spec_reg}")
            if extra_spec_reg:
                logger.error(f"  Tools in registry but not in spec: {extra_spec_reg}")
        else:
            logger.info(f"Tool surface consistency check passed: {len(enabled)} tools synchronized")
        
        return is_consistent, details
        
    except Exception as e:
        logger.error(f"Error during tool surface consistency check: {e}")
        return False, {"error": str(e)}

def check_environment_variables() -> Tuple[bool, Dict[str, Any]]:
    """
    Kontrollera att alla nödvändiga miljövariabler är satta.
    Returnerar (is_valid, details).
    """
    import os
    
    required_vars = [
        "USE_HARMONY",
        "USE_TOOLS", 
        "NLU_CONFIDENCE_THRESHOLD"
    ]
    
    optional_vars = [
        "ENABLED_TOOLS",
        "HARMONY_TEMPERATURE_COMMANDS",
        "HARMONY_REASONING_LEVEL"
    ]
    
    details = {
        "required": {},
        "optional": {},
        "missing_required": [],
        "warnings": []
    }
    
    # Kontrollera required
    for var in required_vars:
        value = os.getenv(var)
        details["required"][var] = value
        if value is None:
            details["missing_required"].append(var)
    
    # Kontrollera optional
    for var in optional_vars:
        value = os.getenv(var)
        details["optional"][var] = value
    
    # Kontrollera ENABLED_TOOLS om den finns
    enabled_tools_env = os.getenv("ENABLED_TOOLS")
    if enabled_tools_env:
        tools = [t.strip().upper() for t in enabled_tools_env.split(",") if t.strip()]
        details["enabled_tools_parsed"] = tools
        if len(tools) == 0:
            details["warnings"].append("ENABLED_TOOLS is empty or invalid")
    
    is_valid = len(details["missing_required"]) == 0
    
    if not is_valid:
        logger.error(f"Missing required environment variables: {details['missing_required']}")
    else:
        logger.info("Environment variables check passed")
    
    return is_valid, details

def run_preflight_checks() -> Tuple[bool, Dict[str, Any]]:
    """
    Kör alla preflight-kontroller.
    Returnerar (all_passed, results).
    """
    logger.info("Running preflight checks...")
    
    results = {}
    
    # Kontrollera miljövariabler
    env_ok, env_details = check_environment_variables()
    results["environment"] = {"passed": env_ok, "details": env_details}
    
    # Kontrollera verktygsytan (endast om miljövariablerna är OK)
    tool_ok = True
    tool_details = {}
    if env_ok:
        tool_ok, tool_details = check_tool_surface_consistency()
        results["tool_surface"] = {"passed": tool_ok, "details": tool_details}
    else:
        results["tool_surface"] = {"passed": False, "details": {"error": "Skipped due to environment issues"}}
    
    # Sammanställ resultat
    all_passed = env_ok and tool_ok
    
    if all_passed:
        logger.info("All preflight checks passed!")
    else:
        logger.error("Some preflight checks failed!")
    
    results["summary"] = {
        "all_passed": all_passed,
        "checks_run": len(results),
        "passed": sum(1 for r in results.values() if isinstance(r, dict) and r.get("passed")),
        "failed": sum(1 for r in results.values() if isinstance(r, dict) and not r.get("passed"))
    }
    
    return all_passed, results

def log_preflight_results(results: Dict[str, Any]) -> None:
    """Logga preflight-resultat i strukturerat format"""
    logger.info("Preflight check results:")
    logger.info(f"  Summary: {results.get('summary', {})}")
    
    for check_name, check_result in results.items():
        if check_name == "summary":
            continue
            
        if isinstance(check_result, dict):
            status = "PASSED" if check_result.get("passed") else "FAILED"
            logger.info(f"  {check_name}: {status}")
            
            details = check_result.get("details", {})
            if "error" in details:
                logger.error(f"    Error: {details['error']}")
            elif "warnings" in details and details["warnings"]:
                for warning in details["warnings"]:
                    logger.warning(f"    Warning: {warning}")
