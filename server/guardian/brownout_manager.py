#!/usr/bin/env python3
"""
Brownout Manager - Intelligent Feature Degradation
==================================================

Hanterar intelligent nedtrappning av funktioner före hard kill:
1. Modellbyte: gpt-oss:20b → gpt-oss:7b för svar
2. Sänk context window & RAG top_k
3. Stäng av tunga toolkedjor temporärt
4. TTS fallback till snabbare röst/prosodi
5. Feature flags för gradvis degradation

Designprinciper:
- Behåll funktionalitet men reducera resurskrav
- Gradvis degradation istället för total avbrott
- Automatisk återställning vid recovery
- Spårning av brownout-effektivitet
"""

import os
import json
import time
import asyncio
import logging
import httpx
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

class BrownoutLevel(Enum):
    """Brownout degradation levels"""
    NONE = 0        # Normal operation
    LIGHT = 1       # Minimal degradation
    MODERATE = 2    # Significant degradation  
    HEAVY = 3       # Maximum degradation

@dataclass
class BrownoutConfig:
    """Brownout configuration från GuardianConfig"""
    # Model settings
    model_primary: str = "gpt-oss:20b"
    model_fallback: str = "gpt-oss:7b"
    
    # Context window settings
    context_window_normal: int = 8
    context_window_reduced: int = 3
    
    # RAG settings
    rag_top_k_normal: int = 8
    rag_top_k_reduced: int = 3
    
    # Service URLs
    alice_base_url: str = "http://localhost:8000"
    ollama_base_url: str = "http://localhost:11434"
    
    # Timeouts - Optimized för production stability
    request_timeout_s: float = 8.0         # Increased från 5.0
    model_switch_timeout_s: float = 15.0    # Increased från 10.0
    
    # Gradual degradation settings
    enable_gradual_degradation: bool = True
    degradation_steps: int = 3              # Number of degradation steps

class BrownoutManager:
    """
    Huvudklass för intelligent brownout management
    Koordinerar alla degradation-åtgärder
    """
    
    def __init__(self, guardian_config):
        self.config = BrownoutConfig(
            model_primary=guardian_config.brownout_model_primary,
            model_fallback=guardian_config.brownout_model_fallback,
            context_window_normal=guardian_config.brownout_context_window,
            context_window_reduced=guardian_config.brownout_context_reduced,
            rag_top_k_normal=guardian_config.brownout_rag_top_k,
            rag_top_k_reduced=guardian_config.brownout_rag_reduced,
            alice_base_url=guardian_config.alice_base_url,
            ollama_base_url=guardian_config.ollama_base_url
        )
        
        self.logger = logging.getLogger("guardian.brownout")
        
        # State tracking
        self.current_level = BrownoutLevel.NONE
        self.brownout_active = False
        self.activation_time: Optional[datetime] = None
        self.last_model_switch: Optional[datetime] = None
        
        # Backup of normal settings
        self.normal_settings = {}
        
        # Degradation statistics
        self.degradation_stats = {
            'activations': 0,
            'model_switches': 0,
            'context_reductions': 0,
            'toolchain_disables': 0,
            'total_brownout_time_s': 0.0
        }
        
        self.logger.info(f"BrownoutManager initialized: {self.config.model_primary} -> {self.config.model_fallback}")
    
    async def activate_brownout_mode(self, level: BrownoutLevel = BrownoutLevel.MODERATE) -> bool:
        """
        Aktivera brownout-läge med specificerad degradation level
        Returns: True om framgångsrik, False vid fel
        """
        if self.brownout_active:
            self.logger.info(f"Brownout already active at level {self.current_level.name}")
            return True
        
        self.logger.warning(f"🟡 ACTIVATING BROWNOUT MODE - Level {level.name}")
        self.activation_time = datetime.now()
        self.current_level = level
        self.degradation_stats['activations'] += 1
        
        success_count = 0
        total_actions = 4  # Model, context, RAG, toolchains
        
        # 1. Model degradation
        if await self._switch_to_fallback_model():
            success_count += 1
            self.degradation_stats['model_switches'] += 1
        
        # 2. Context window reduction
        if await self._reduce_context_window(level):
            success_count += 1
            self.degradation_stats['context_reductions'] += 1
        
        # 3. RAG reduction  
        if await self._reduce_rag_settings(level):
            success_count += 1
        
        # 4. Toolchain degradation
        if await self._disable_heavy_toolchains(level):
            success_count += 1
            self.degradation_stats['toolchain_disables'] += 1
        
        # Considera framgångsrik om minst hälften av åtgärderna lyckades
        if success_count >= total_actions / 2:
            self.brownout_active = True
            self.logger.info(f"✅ Brownout activated ({success_count}/{total_actions} actions successful)")
            
            # NDJSON logging för spårning
            brownout_event = {
                'timestamp': datetime.now().isoformat(),
                'event': 'brownout_activated',
                'level': level.name,
                'success_rate': success_count / total_actions,
                'actions_completed': success_count,
                'total_actions': total_actions
            }
            print(json.dumps(brownout_event, separators=(',', ':')))
            
            return True
        else:
            self.logger.error(f"❌ Brownout activation failed ({success_count}/{total_actions} actions successful)")
            self.current_level = BrownoutLevel.NONE
            return False
    
    async def restore_normal_operation(self) -> bool:
        """
        Återställ normal operation från brownout
        Returns: True om framgångsrik
        """
        if not self.brownout_active:
            self.logger.info("Not in brownout mode, nothing to restore")
            return True
        
        self.logger.info("🟢 RESTORING NORMAL OPERATION from brownout")
        
        # Uppdatera stats
        if self.activation_time:
            brownout_duration = (datetime.now() - self.activation_time).total_seconds()
            self.degradation_stats['total_brownout_time_s'] += brownout_duration
        
        success_count = 0
        total_actions = 4
        
        # 1. Återställ modell
        if await self._restore_primary_model():
            success_count += 1
        
        # 2. Återställ context window
        if await self._restore_context_window():
            success_count += 1
        
        # 3. Återställ RAG
        if await self._restore_rag_settings():
            success_count += 1
        
        # 4. Återställ toolchains
        if await self._restore_toolchains():
            success_count += 1
        
        # Uppdatera state
        self.brownout_active = False
        self.current_level = BrownoutLevel.NONE
        self.activation_time = None
        
        # NDJSON logging
        restore_event = {
            'timestamp': datetime.now().isoformat(),
            'event': 'brownout_restored',
            'success_rate': success_count / total_actions,
            'brownout_duration_s': brownout_duration if self.activation_time else 0
        }
        print(json.dumps(restore_event, separators=(',', ':')))
        
        return success_count >= total_actions / 2
    
    async def _switch_to_fallback_model(self) -> bool:
        """Byt till fallback-modell (gpt-oss:7b)"""
        try:
            url = f"{self.config.alice_base_url}/api/brain/model/switch"
            payload = {
                "model": self.config.model_fallback,
                "reason": "brownout_degradation"
            }
            
            async with httpx.AsyncClient(timeout=self.config.model_switch_timeout_s) as client:
                response = await client.post(url, json=payload)
                
                if response.status_code == 200:
                    self.last_model_switch = datetime.now()
                    self.logger.info(f"✅ Model switched to {self.config.model_fallback}")
                    return True
                else:
                    self.logger.error(f"❌ Model switch failed: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"❌ Model switch error: {e}")
            return False
    
    async def _restore_primary_model(self) -> bool:
        """Återställ primary modell (gpt-oss:20b)"""
        try:
            url = f"{self.config.alice_base_url}/api/brain/model/switch"
            payload = {
                "model": self.config.model_primary,
                "reason": "brownout_recovery"
            }
            
            async with httpx.AsyncClient(timeout=self.config.model_switch_timeout_s) as client:
                response = await client.post(url, json=payload)
                
                if response.status_code == 200:
                    self.logger.info(f"✅ Model restored to {self.config.model_primary}")
                    return True
                else:
                    self.logger.error(f"❌ Model restore failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"❌ Model restore error: {e}")
            return False
    
    async def _reduce_context_window(self, level: BrownoutLevel) -> bool:
        """Reducera context window baserat på degradation level"""
        try:
            # Bestäm context window baserat på level
            if level == BrownoutLevel.LIGHT:
                new_context = max(self.config.context_window_reduced, 
                                self.config.context_window_normal - 2)
            else:  # MODERATE eller HEAVY
                new_context = self.config.context_window_reduced
            
            url = f"{self.config.alice_base_url}/api/brain/context/set"
            payload = {"context_window": new_context}
            
            async with httpx.AsyncClient(timeout=self.config.request_timeout_s) as client:
                response = await client.post(url, json=payload)
                
                if response.status_code == 200:
                    self.logger.info(f"✅ Context window reduced to {new_context}")
                    return True
                else:
                    self.logger.warning(f"⚠️ Context window reduction failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"❌ Context window reduction error: {e}")
            return False
    
    async def _restore_context_window(self) -> bool:
        """Återställ normal context window"""
        try:
            url = f"{self.config.alice_base_url}/api/brain/context/set"
            payload = {"context_window": self.config.context_window_normal}
            
            async with httpx.AsyncClient(timeout=self.config.request_timeout_s) as client:
                response = await client.post(url, json=payload)
                
                if response.status_code == 200:
                    self.logger.info(f"✅ Context window restored to {self.config.context_window_normal}")
                    return True
                else:
                    self.logger.warning(f"⚠️ Context window restore failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"❌ Context window restore error: {e}")
            return False
    
    async def _reduce_rag_settings(self, level: BrownoutLevel) -> bool:
        """Reducera RAG top_k för mindre minnesanvändning"""
        try:
            # Bestäm RAG settings baserat på level
            if level == BrownoutLevel.LIGHT:
                new_top_k = max(self.config.rag_top_k_reduced,
                              self.config.rag_top_k_normal - 2)
            else:  # MODERATE eller HEAVY
                new_top_k = self.config.rag_top_k_reduced
            
            url = f"{self.config.alice_base_url}/api/brain/rag/set"
            payload = {"top_k": new_top_k}
            
            async with httpx.AsyncClient(timeout=self.config.request_timeout_s) as client:
                response = await client.post(url, json=payload)
                
                if response.status_code == 200:
                    self.logger.info(f"✅ RAG top_k reduced to {new_top_k}")
                    return True
                else:
                    self.logger.warning(f"⚠️ RAG reduction failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"❌ RAG reduction error: {e}")
            return False
    
    async def _restore_rag_settings(self) -> bool:
        """Återställ normal RAG settings"""
        try:
            url = f"{self.config.alice_base_url}/api/brain/rag/set"
            payload = {"top_k": self.config.rag_top_k_normal}
            
            async with httpx.AsyncClient(timeout=self.config.request_timeout_s) as client:
                response = await client.post(url, json=payload)
                
                if response.status_code == 200:
                    self.logger.info(f"✅ RAG top_k restored to {self.config.rag_top_k_normal}")
                    return True
                else:
                    self.logger.warning(f"⚠️ RAG restore failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"❌ RAG restore error: {e}")
            return False
    
    async def _disable_heavy_toolchains(self, level: BrownoutLevel) -> bool:
        """Stäng av tunga toolkedjor temporärt"""
        try:
            # Bestäm vilka tools som ska stängas av baserat på level
            disabled_tools = []
            
            if level == BrownoutLevel.LIGHT:
                disabled_tools = ["code_interpreter"]  # Bara kod-interpret
            elif level == BrownoutLevel.MODERATE:
                disabled_tools = ["code_interpreter", "file_search", "web_search"]
            else:  # HEAVY
                disabled_tools = ["code_interpreter", "file_search", "web_search", "calendar", "email"]
            
            url = f"{self.config.alice_base_url}/api/brain/tools/disable"
            payload = {"tools": disabled_tools, "reason": "brownout_degradation"}
            
            async with httpx.AsyncClient(timeout=self.config.request_timeout_s) as client:
                response = await client.post(url, json=payload)
                
                if response.status_code == 200:
                    self.logger.info(f"✅ Disabled tools: {', '.join(disabled_tools)}")
                    return True
                else:
                    self.logger.warning(f"⚠️ Tool disabling failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"❌ Tool disabling error: {e}")
            return False
    
    async def _restore_toolchains(self) -> bool:
        """Återställ alla toolchains"""
        try:
            url = f"{self.config.alice_base_url}/api/brain/tools/enable-all"
            payload = {"reason": "brownout_recovery"}
            
            async with httpx.AsyncClient(timeout=self.config.request_timeout_s) as client:
                response = await client.post(url, json=payload)
                
                if response.status_code == 200:
                    self.logger.info("✅ All tools re-enabled")
                    return True
                else:
                    self.logger.warning(f"⚠️ Tool restoration failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"❌ Tool restoration error: {e}")
            return False
    
    async def get_status(self) -> Dict[str, Any]:
        """Hämta brownout status"""
        brownout_duration = 0.0
        if self.brownout_active and self.activation_time:
            brownout_duration = (datetime.now() - self.activation_time).total_seconds()
        
        return {
            'active': self.brownout_active,
            'level': self.current_level.name,
            'activation_time': self.activation_time.isoformat() if self.activation_time else None,
            'duration_s': brownout_duration,
            'last_model_switch': self.last_model_switch.isoformat() if self.last_model_switch else None,
            'stats': self.degradation_stats.copy(),
            'config': {
                'model_primary': self.config.model_primary,
                'model_fallback': self.config.model_fallback,
                'context_normal': self.config.context_window_normal,
                'context_reduced': self.config.context_window_reduced,
                'rag_normal': self.config.rag_top_k_normal,
                'rag_reduced': self.config.rag_top_k_reduced
            }
        }
    
    def get_effectiveness_score(self) -> float:
        """
        Beräkna brownout effectiveness score baserat på användning
        Returns: 0.0-1.0 där högre är bättre
        """
        if self.degradation_stats['activations'] == 0:
            return 1.0  # Aldrig behövt aktivera = bra
        
        # Faktorer som påverkar effectiveness:
        # - Få activations = bättre
        # - Kort total brownout tid = bättre  
        # - Framgångsrika model switches = bättre
        
        activation_score = max(0, 1.0 - (self.degradation_stats['activations'] / 10.0))
        
        avg_brownout_duration = (self.degradation_stats['total_brownout_time_s'] / 
                               max(1, self.degradation_stats['activations']))
        duration_score = max(0, 1.0 - (avg_brownout_duration / 300.0))  # 5min = 0 score
        
        switch_success_rate = (self.degradation_stats['model_switches'] / 
                             max(1, self.degradation_stats['activations']))
        
        overall_score = (activation_score * 0.4 + 
                        duration_score * 0.4 + 
                        switch_success_rate * 0.2)
        
        return min(1.0, max(0.0, overall_score))

# Convenience functions för enkel användning
async def activate_brownout(config, level: BrownoutLevel = BrownoutLevel.MODERATE) -> bool:
    """Convenience function för brownout activation"""
    manager = BrownoutManager(config)
    return await manager.activate_brownout_mode(level)

async def restore_normal(config) -> bool:
    """Convenience function för brownout restoration"""  
    manager = BrownoutManager(config)
    return await manager.restore_normal_operation()

if __name__ == "__main__":
    # Test/demo
    import logging
    logging.basicConfig(level=logging.INFO)
    
    @dataclass
    class TestConfig:
        brownout_model_primary: str = "gpt-oss:20b"
        brownout_model_fallback: str = "gpt-oss:7b"
        brownout_context_window: int = 8
        brownout_context_reduced: int = 3
        brownout_rag_top_k: int = 8
        brownout_rag_reduced: int = 3
        alice_base_url: str = "http://localhost:8000"
        ollama_base_url: str = "http://localhost:11434"
    
    async def test_brownout():
        config = TestConfig()
        manager = BrownoutManager(config)
        
        print("Testing brownout activation...")
        success = await manager.activate_brownout_mode(BrownoutLevel.MODERATE)
        print(f"Activation: {'SUCCESS' if success else 'FAILED'}")
        
        await asyncio.sleep(2)
        
        print("Testing brownout restore...")
        success = await manager.restore_normal_operation()
        print(f"Restore: {'SUCCESS' if success else 'FAILED'}")
        
        status = await manager.get_status()
        print(f"Final status: {status}")
    
    asyncio.run(test_brownout())