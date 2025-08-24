'use client';

import React, { useState, useEffect } from 'react';
import { AmbientHUD, useAmbientVoice } from '@/src/voice/AmbientHUD';
import { Orchestrator } from '@/src/voice/Orchestrator';

export default function AmbientDemoPage() {
  const { orchestrator, status, isListening, lastPartial, toggleListening } = useAmbientVoice();
  const [logs, setLogs] = useState<string[]>([]);
  const [stats, setStats] = useState<any>(null);
  
  // Lägg till event logging
  useEffect(() => {
    const unsubscribe = orchestrator.on((event) => {
      const timestamp = new Date().toLocaleTimeString();
      setLogs(prev => [...prev.slice(-49), `[${timestamp}] ${event.type}: ${JSON.stringify(event, null, 2)}`]);
    });
    
    return unsubscribe;
  }, [orchestrator]);

  // Hämta stats regelbundet
  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await fetch('/api/memory/ambient/stats');
        if (response.ok) {
          const data = await response.json();
          setStats(data);
        }
      } catch (error) {
        console.error('Failed to fetch stats:', error);
      }
    };

    fetchStats();
    const interval = setInterval(fetchStats, 10000); // var 10:e sekund
    return () => clearInterval(interval);
  }, []);

  const handleTestSummary = async () => {
    try {
      // Skicka test-highlights för att trigga en summary
      const testHighlights = [
        {
          text: "jag ska handla mjölk och bröd imorgon",
          score: 2,
          ts: new Date().toISOString()
        },
        {
          text: "påminn mig om mötet klockan tre",
          score: 3,
          ts: new Date().toISOString()
        }
      ];

      const response = await fetch('/api/memory/ambient/summary', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          windowSec: 60,
          highlights: testHighlights,
          rawRef: `test:${Date.now()}`,
          windowStart: new Date(Date.now() - 60000).toISOString(),
          windowEnd: new Date().toISOString(),
          chunkCount: 2
        })
      });

      const result = await response.json();
      setLogs(prev => [...prev, `[TEST] Created summary: ${JSON.stringify(result)}`]);
    } catch (error) {
      setLogs(prev => [...prev, `[ERROR] Test summary failed: ${error}`]);
    }
  };

  const handleCleanup = async () => {
    try {
      const response = await fetch('/api/memory/ambient/clean', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ olderThanMinutes: 0 })
      });

      const result = await response.json();
      setLogs(prev => [...prev, `[CLEANUP] ${JSON.stringify(result)}`]);
    } catch (error) {
      setLogs(prev => [...prev, `[ERROR] Cleanup failed: ${error}`]);
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      {/* HUD Component */}
      <AmbientHUD orchestrator={orchestrator} />
      
      <div className="max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold mb-8">Alice Ambient Memory Demo</h1>
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Status Panel */}
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">System Status</h2>
            
            <div className="space-y-2 text-sm">
              <div>Voice Mode: <span className="text-green-400">{orchestrator.getConfig().voiceMode}</span></div>
              <div>ASR Backend: <span className="text-blue-400">{orchestrator.getConfig().asrBackend}</span></div>
              <div>Ambient Enabled: <span className="text-purple-400">{orchestrator.getConfig().ambientEnabled ? 'YES' : 'NO'}</span></div>
              <div>Mic Permission: <span className={status.micPermission === 'granted' ? 'text-green-400' : 'text-red-400'}>{status.micPermission}</span></div>
              <div>ASR Status: <span className={status.asrStatus === 'connected' ? 'text-green-400' : 'text-yellow-400'}>{status.asrStatus}</span></div>
              <div>Listening: <span className={isListening ? 'text-green-400' : 'text-gray-400'}>{isListening ? 'YES' : 'NO'}</span></div>
            </div>
            
            {lastPartial && (
              <div className="mt-4 p-3 bg-gray-700 rounded border-l-4 border-cyan-400">
                <div className="text-xs text-cyan-300">LAST PARTIAL:</div>
                <div className="font-mono text-sm">"{lastPartial}"</div>
              </div>
            )}
            
            {status.bufferStats && (
              <div className="mt-4 p-3 bg-gray-700 rounded">
                <div className="text-xs text-gray-300 mb-2">BUFFER STATS:</div>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div>Total: {status.bufferStats.totalChunks}</div>
                  <div>Important: {status.bufferStats.highScoreChunks}</div>
                </div>
              </div>
            )}
            
            <div className="mt-4 flex gap-2">
              <button
                onClick={toggleListening}
                className={`px-4 py-2 rounded text-sm font-medium ${
                  isListening 
                    ? 'bg-red-600 hover:bg-red-700' 
                    : 'bg-green-600 hover:bg-green-700'
                }`}
                disabled={status.micPermission === 'denied'}
              >
                {isListening ? '⏸ Stop' : '▶️ Start'}
              </button>
              
              <button
                onClick={handleTestSummary}
                className="px-4 py-2 rounded text-sm font-medium bg-blue-600 hover:bg-blue-700"
              >
                🧪 Test Summary
              </button>
              
              <button
                onClick={handleCleanup}
                className="px-4 py-2 rounded text-sm font-medium bg-yellow-600 hover:bg-yellow-700"
              >
                🧹 Cleanup
              </button>
            </div>
          </div>
          
          {/* Database Stats */}
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Database Stats</h2>
            
            {stats ? (
              <div className="space-y-4">
                <div>
                  <h3 className="text-lg font-medium text-cyan-400">Raw Chunks</h3>
                  <div className="text-sm space-y-1">
                    <div>Total: {stats.ambient_raw.total}</div>
                    <div>Active: {stats.ambient_raw.active}</div>
                    <div>Expired: {stats.ambient_raw.expired}</div>
                  </div>
                </div>
                
                <div>
                  <h3 className="text-lg font-medium text-purple-400">Summaries</h3>
                  <div className="text-sm space-y-1">
                    <div>Total: {stats.summaries.total}</div>
                    {stats.summaries.latest && (
                      <>
                        <div>Latest: {new Date(stats.summaries.latest.created_at).toLocaleString()}</div>
                        <div className="text-xs text-gray-400 mt-2">{stats.summaries.latest.preview}</div>
                      </>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-gray-400">Loading stats...</div>
            )}
          </div>
        </div>
        
        {/* Event Log */}
        <div className="mt-6 bg-gray-800 rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">Event Log</h2>
          <div className="bg-black rounded p-4 h-96 overflow-y-auto font-mono text-xs">
            {logs.length === 0 ? (
              <div className="text-gray-500">No events yet...</div>
            ) : (
              logs.map((log, index) => (
                <div key={index} className="mb-1 whitespace-pre-wrap">
                  {log}
                </div>
              ))
            )}
          </div>
          <button
            onClick={() => setLogs([])}
            className="mt-2 px-3 py-1 rounded text-xs bg-gray-700 hover:bg-gray-600"
          >
            Clear Log
          </button>
        </div>
        
        {/* Instructions */}
        <div className="mt-6 bg-gray-800 rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">How to Test</h2>
          <div className="text-sm space-y-2">
            <div>1. Click "Start" to begin always-on listening</div>
            <div>2. Speak into your microphone - you should see partials in real-time</div>
            <div>3. After ~90 seconds, summaries should be created automatically</div>
            <div>4. Use "Test Summary" to manually trigger the summary process</div>
            <div>5. Check the database stats to see data accumulating</div>
            <div>6. Use "Cleanup" to remove old data for testing</div>
          </div>
          
          <div className="mt-4 p-3 bg-yellow-900/20 border border-yellow-600/30 rounded">
            <div className="text-yellow-300 font-medium">Note:</div>
            <div className="text-sm text-yellow-200">
              This demo uses a mock Realtime ASR endpoint. In production, you would connect to OpenAI Realtime API.
              The importance scoring and summarization use real LLM calls if OPENAI_API_KEY is configured.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}