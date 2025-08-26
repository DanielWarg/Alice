#!/usr/bin/env python3
"""
🎯 Streaming Voice Metrics - Accept Loggers
Production-ready metrics for talk-latency and barge-in performance tracking
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

class Route(Enum):
    REALTIME = "realtime"
    LOCAL = "local"

@dataclass
class TalkLatencyThresholds:
    """SLO thresholds for talk latency metrics"""
    first_partial_ms: float = 300.0
    ttft_ms: float = 300.0  # Time to first token
    tts_first_chunk_ms: float = 150.0
    total_latency_ms: float = 500.0

@dataclass
class BargeInThresholds:
    """SLO thresholds for barge-in performance"""
    barge_in_cut_ms: float = 120.0

class TalkLatencyLogger:
    """
    Accept-logger for talk-lane latency metrics
    
    Tracks complete conversation turn timing:
    - first_partial: STT partial transcript time
    - ttft: Time to first token from LLM
    - tts_first_chunk: First audio chunk from TTS  
    - total_latency: End-to-end response time
    
    Logs NDJSON to logs/talk_latency.ndjson with pass/fail against SLOs
    """
    
    def __init__(self, logfile: str = "logs/talk_latency.ndjson", thresholds: Optional[TalkLatencyThresholds] = None):
        self.logfile = Path(logfile)
        self.thresholds = thresholds or TalkLatencyThresholds()
        self.turns: Dict[str, Dict[str, Any]] = {}
        
        # Ensure log directory exists
        self.logfile.parent.mkdir(parents=True, exist_ok=True)
    
    def start_turn(self, turn_id: str, route: Route):
        """Start tracking a new conversation turn"""
        self.turns[turn_id] = {
            "route": route.value,
            "timestamps": {
                "mic_open": time.time() * 1000  # milliseconds
            },
            "metrics": {}
        }
    
    def mark_event(self, turn_id: str, event: str):
        """Mark a timing event in the conversation turn"""
        if turn_id not in self.turns:
            return
        
        self.turns[turn_id]["timestamps"][event] = time.time() * 1000
    
    async def finalize_turn(self, turn_id: str) -> Dict[str, Any]:
        """Calculate metrics and log results with pass/fail"""
        if turn_id not in self.turns:
            return {"error": "Turn not found"}
        
        turn = self.turns[turn_id]
        t = turn["timestamps"]
        
        # Calculate metrics
        metrics = {}
        
        if "stt_partial" in t and "mic_open" in t:
            metrics["first_partial_ms"] = t["stt_partial"] - t["mic_open"]
        
        if "llm_first_token" in t:
            base_time = t.get("stt_final", t.get("stt_partial", t["mic_open"]))
            metrics["ttft_ms"] = t["llm_first_token"] - base_time
        
        if "tts_first_chunk" in t and "llm_first_token" in t:
            metrics["tts_first_chunk_ms"] = t["tts_first_chunk"] - t["llm_first_token"]
        
        if "playback_start" in t and "mic_open" in t:
            metrics["total_latency_ms"] = t["playback_start"] - t["mic_open"]
        
        # Check SLO compliance
        slo_pass = True
        slo_results = {}
        
        for metric_name, threshold in {
            "first_partial_ms": self.thresholds.first_partial_ms,
            "ttft_ms": self.thresholds.ttft_ms,
            "tts_first_chunk_ms": self.thresholds.tts_first_chunk_ms,
            "total_latency_ms": self.thresholds.total_latency_ms
        }.items():
            if metric_name in metrics:
                passed = metrics[metric_name] <= threshold
                slo_results[metric_name] = {
                    "value": metrics[metric_name],
                    "threshold": threshold,
                    "pass": passed
                }
                if not passed:
                    slo_pass = False
        
        # Create log entry
        log_entry = {
            "timestamp": int(time.time() * 1000),
            "turn_id": turn_id,
            "route": turn["route"],
            "metrics": metrics,
            "slo_results": slo_results,
            "slo_pass": slo_pass,
            "thresholds": {
                "first_partial_ms": self.thresholds.first_partial_ms,
                "ttft_ms": self.thresholds.ttft_ms,
                "tts_first_chunk_ms": self.thresholds.tts_first_chunk_ms,
                "total_latency_ms": self.thresholds.total_latency_ms
            }
        }
        
        # Write to log file
        await self._write_log_entry(log_entry)
        
        # Cleanup
        del self.turns[turn_id]
        
        return log_entry
    
    async def _write_log_entry(self, entry: Dict[str, Any]):
        """Write NDJSON log entry"""
        try:
            with open(self.logfile, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry) + '\n')
        except Exception as e:
            print(f"Error writing talk latency log: {e}")

class BargeInLogger:
    """
    Accept-logger for barge-in performance metrics
    
    Tracks how quickly TTS playback is interrupted when user starts speaking:
    - user_voice_detected: VAD detects user speech during TTS
    - tts_cut_complete: TTS generation cancelled and playback stopped
    - barge_in_cut_ms: Time between detection and cutoff
    
    Logs NDJSON to logs/barge_in.ndjson with pass/fail against SLOs
    """
    
    def __init__(self, logfile: str = "logs/barge_in.ndjson", thresholds: Optional[BargeInThresholds] = None):
        self.logfile = Path(logfile)
        self.thresholds = thresholds or BargeInThresholds()
        self.sessions: Dict[str, Dict[str, Any]] = {}
        
        # Ensure log directory exists  
        self.logfile.parent.mkdir(parents=True, exist_ok=True)
    
    def start_playback(self, session_id: str, route: Route):
        """Start tracking a TTS playback session"""
        self.sessions[session_id] = {
            "route": route.value,
            "timestamps": {
                "playback_start": time.time() * 1000
            }
        }
    
    def mark_user_voice_detected(self, session_id: str):
        """Mark when VAD detects user speech during TTS"""
        if session_id not in self.sessions:
            return
        
        if "user_voice_detected" not in self.sessions[session_id]["timestamps"]:
            self.sessions[session_id]["timestamps"]["user_voice_detected"] = time.time() * 1000
    
    async def mark_tts_cut_complete(self, session_id: str) -> Dict[str, Any]:
        """Mark when TTS is fully stopped and calculate metrics"""
        if session_id not in self.sessions:
            return {"error": "Session not found"}
        
        session = self.sessions[session_id]
        t = session["timestamps"]
        t["tts_cut_complete"] = time.time() * 1000
        
        # Calculate barge-in metrics
        metrics = {}
        if "user_voice_detected" in t and "tts_cut_complete" in t:
            metrics["barge_in_cut_ms"] = t["tts_cut_complete"] - t["user_voice_detected"]
        
        # Check SLO compliance
        slo_pass = True
        if "barge_in_cut_ms" in metrics:
            slo_pass = metrics["barge_in_cut_ms"] <= self.thresholds.barge_in_cut_ms
        
        # Create log entry
        log_entry = {
            "timestamp": int(time.time() * 1000),
            "session_id": session_id,
            "route": session["route"],
            "metrics": metrics,
            "slo_pass": slo_pass,
            "thresholds": {
                "barge_in_cut_ms": self.thresholds.barge_in_cut_ms
            }
        }
        
        # Write to log file
        await self._write_log_entry(log_entry)
        
        # Cleanup
        del self.sessions[session_id]
        
        return log_entry
    
    async def _write_log_entry(self, entry: Dict[str, Any]):
        """Write NDJSON log entry"""
        try:
            with open(self.logfile, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry) + '\n')
        except Exception as e:
            print(f"Error writing barge-in log: {e}")

# Usage example and testing
async def main():
    """Example usage of the streaming metrics loggers"""
    
    # Talk latency logger test
    talk_logger = TalkLatencyLogger()
    
    turn_id = f"turn_{int(time.time())}"
    talk_logger.start_turn(turn_id, Route.REALTIME)
    
    # Simulate conversation timing
    await asyncio.sleep(0.1)  # Simulate processing time
    talk_logger.mark_event(turn_id, "stt_partial")
    
    await asyncio.sleep(0.05)
    talk_logger.mark_event(turn_id, "stt_final")
    
    await asyncio.sleep(0.2)
    talk_logger.mark_event(turn_id, "llm_first_token")
    
    await asyncio.sleep(0.1)
    talk_logger.mark_event(turn_id, "tts_first_chunk")
    
    await asyncio.sleep(0.05)
    talk_logger.mark_event(turn_id, "playback_start")
    
    result = await talk_logger.finalize_turn(turn_id)
    print(f"Talk latency result: {result}")
    
    # Barge-in logger test
    barge_logger = BargeInLogger()
    
    session_id = f"session_{int(time.time())}"
    barge_logger.start_playback(session_id, Route.REALTIME)
    
    await asyncio.sleep(0.5)  # TTS playing
    barge_logger.mark_user_voice_detected(session_id)
    
    await asyncio.sleep(0.08)  # Quick barge-in response
    result = await barge_logger.mark_tts_cut_complete(session_id)
    print(f"Barge-in result: {result}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())