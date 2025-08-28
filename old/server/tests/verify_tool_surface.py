#!/usr/bin/env python3
"""
Verifiera att verktygsytan är konsistent mellan alla delar av systemet.
Kör detta före E2E-tester för att fånga ytfel tidigt.
"""

import requests
import sys
import os
from typing import Set, Tuple

def get_tool_surface(base_url: str = "http://127.0.0.1:8000") -> Tuple[Set[str], Set[str], Set[str]]:
    """Hämta verktygsytan från alla endpoints"""
    try:
        # Hämta aktiverade verktyg från miljövariabel
        env_response = requests.get(f"{base_url}/tools/enabled", timeout=5)
        env_response.raise_for_status()
        env = set(env_response.json()["enabled"])
        
        # Hämta Harmony-specs
        spec_response = requests.get(f"{base_url}/tools/spec", timeout=5)
        spec_response.raise_for_status()
        spec = set(t["name"] for t in spec_response.json())
        
        # Hämta registry-executors
        reg_response = requests.get(f"{base_url}/tools/registry", timeout=5)
        reg_response.raise_for_status()
        reg = set(reg_response.json()["executors"])
        
        return env, spec, reg
        
    except requests.RequestException as e:
        print(f"[ERROR] Kunde inte ansluta till {base_url}: {e}")
        print("Kontrollera att servern körs på rätt port")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Oväntat fel: {e}")
        sys.exit(1)

def verify_consistency(env: Set[str], spec: Set[str], reg: Set[str]) -> bool:
    """Verifiera att alla verktygsytor matchar varandra"""
    ok = True
    
    # Kontrollera env vs spec
    missing_env_spec = env - spec
    extra_env_spec = spec - env
    if missing_env_spec or extra_env_spec:
        ok = False
        print(f"[FAIL] env vs spec:")
        if missing_env_spec:
            print(f"  Saknas i spec: {sorted(missing_env_spec)}")
        if extra_env_spec:
            print(f"  Extra i spec: {sorted(extra_env_spec)}")
    else:
        print(f"[OK] env vs spec: {len(env)} verktyg matchar")
    
    # Kontrollera spec vs registry
    missing_spec_reg = spec - reg
    extra_spec_reg = reg - spec
    if missing_spec_reg or extra_spec_reg:
        ok = False
        print(f"[FAIL] spec vs registry:")
        if missing_spec_reg:
            print(f"  Saknas i registry: {sorted(missing_spec_reg)}")
        if extra_spec_reg:
            print(f"  Extra i registry: {sorted(extra_spec_reg)}")
    else:
        print(f"[OK] spec vs registry: {len(spec)} verktyg matchar")
    
    # Kontrollera env vs registry
    missing_env_reg = env - reg
    extra_env_reg = reg - env
    if missing_env_reg or extra_env_reg:
        ok = False
        print(f"[FAIL] env vs registry:")
        if missing_env_reg:
            print(f"  Saknas i registry: {sorted(missing_env_reg)}")
        if extra_env_reg:
            print(f"  Extra i registry: {sorted(extra_env_reg)}")
    else:
        print(f"[OK] env vs registry: {len(env)} verktyg matchar")
    
    return ok

def print_summary(env: Set[str], spec: Set[str], reg: Set[str]):
    """Skriv ut sammanfattning av verktygsytan"""
    print("\n" + "="*50)
    print("VERKTYGSYTA SAMMANFATTNING")
    print("="*50)
    print(f"Miljövariabel (ENABLED_TOOLS): {len(env)} verktyg")
    print(f"  {sorted(env)}")
    print(f"\nHarmony-specs: {len(spec)} verktyg")
    print(f"  {sorted(spec)}")
    print(f"\nRegistry-executors: {len(reg)} verktyg")
    print(f"  {sorted(reg)}")
    print("="*50)

def main():
    """Huvudfunktion"""
    print("🔍 Verifierar verktygsytan...")
    
    # Hämta verktygsytan från alla endpoints
    env, spec, reg = get_tool_surface()
    
    # Skriv ut sammanfattning
    print_summary(env, spec, reg)
    
    # Verifiera konsistens
    print("\n📋 KONSISTENSKONTROLL:")
    print("-" * 30)
    is_consistent = verify_consistency(env, spec, reg)
    
    # Sammanfattning
    print("\n" + "="*50)
    if is_consistent:
        print("✅ ALLA VERKTYGSYTOR MATCHAR!")
        print("Systemet är redo för E2E-tester.")
        sys.exit(0)
    else:
        print("❌ VERKTYGSYTORNA MATCHAR INTE!")
        print("Fixa inkonsistenserna innan du kör E2E-tester.")
        print("\nVanliga orsaker:")
        print("- Olika namn i spec.py vs registry.py")
        print("- ENABLED_TOOLS innehåller verktyg som inte finns i spec")
        print("- Registry har verktyg som inte finns i spec")
        sys.exit(1)

if __name__ == "__main__":
    main()
