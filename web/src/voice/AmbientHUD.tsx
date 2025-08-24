import React, { useState, useEffect } from 'react';
import { Orchestrator, OrchestratorStatus } from './Orchestrator';

interface AmbientHUDProps {
  orchestrator: Orchestrator;
  className?: string;
}

export const AmbientHUD: React.FC<AmbientHUDProps> = ({ orchestrator, className = '' }) => {
  const [status, setStatus] = useState<OrchestratorStatus>(orchestrator.getStatus());
  const [isExpanded, setIsExpanded] = useState(false);

  useEffect(() => {
    const unsubscribe = orchestrator.on((event) => {
      if (event.type === 'status_change') {
        setStatus(event.status);
      }
    });

    return unsubscribe;
  }, [orchestrator]);

  const getStatusColor = () => {
    if (status.micPermission === 'denied') return 'bg-red-500';
    if (status.asrStatus === 'error') return 'bg-red-500';
    if (status.asrStatus === 'connecting') return 'bg-yellow-500';
    if (status.isListening && status.asrStatus === 'connected') return 'bg-green-500';
    return 'bg-gray-500';
  };

  const getStatusText = () => {
    if (status.micPermission === 'denied') return 'MIC BLOCKED';
    if (status.asrStatus === 'error') return 'ASR ERROR';
    if (status.asrStatus === 'connecting') return 'CONNECTING';
    if (status.isListening && status.asrStatus === 'connected') return 'LIVE';
    if (status.asrStatus === 'connected') return 'READY';
    return 'OFFLINE';
  };

  const handleToggle = async () => {
    try {
      await orchestrator.toggleListening();
    } catch (error) {
      console.error('Failed to toggle listening:', error);
    }
  };

  return (
    <div className={`fixed top-4 right-4 z-50 ${className}`}>
      {/* Main status badge */}
      <div className="flex items-center gap-2 bg-black/80 backdrop-blur border border-cyan-400/30 rounded-xl px-3 py-2">
        {/* Status indicator */}
        <div className="flex items-center gap-2">
          <div className="relative">
            <div className={`w-2 h-2 rounded-full ${getStatusColor()}`}>
              {status.isListening && (
                <div className={`absolute inset-0 rounded-full ${getStatusColor()} animate-ping opacity-75`} />
              )}
            </div>
          </div>
          <span className="text-xs font-mono text-cyan-100 uppercase tracking-wider">
            {getStatusText()}
          </span>
        </div>

        {/* Toggle button */}
        <button
          onClick={handleToggle}
          disabled={status.micPermission === 'denied' || status.asrStatus === 'error'}
          className="text-xs text-cyan-300 hover:text-cyan-100 disabled:text-gray-500 disabled:cursor-not-allowed"
        >
          {status.isListening ? '⏸' : '▶️'}
        </button>

        {/* Expand/collapse */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-xs text-cyan-300 hover:text-cyan-100"
        >
          {isExpanded ? '▼' : '▶️'}
        </button>
      </div>

      {/* Expanded panel */}
      {isExpanded && (
        <div className="mt-2 bg-black/90 backdrop-blur border border-cyan-400/30 rounded-xl p-4 min-w-80">
          {/* Last partial */}
          {status.lastPartial && (
            <div className="mb-3">
              <div className="text-xs text-cyan-400 mb-1">PARTIAL:</div>
              <div className="text-sm text-cyan-100 font-mono bg-cyan-950/30 rounded px-2 py-1 border border-cyan-400/20">
                "{status.lastPartial}"
              </div>
            </div>
          )}

          {/* Buffer stats */}
          {status.bufferStats && (
            <div className="mb-3">
              <div className="text-xs text-cyan-400 mb-1">BUFFER STATS:</div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="text-cyan-200">
                  Total: <span className="text-white font-mono">{status.bufferStats.totalChunks}</span>
                </div>
                <div className="text-cyan-200">
                  Important: <span className="text-white font-mono">{status.bufferStats.highScoreChunks}</span>
                </div>
              </div>
            </div>
          )}

          {/* System status */}
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="text-cyan-200">
              Mic: <span className={`font-mono ${
                status.micPermission === 'granted' ? 'text-green-400' : 
                status.micPermission === 'denied' ? 'text-red-400' : 'text-yellow-400'
              }`}>
                {status.micPermission.toUpperCase()}
              </span>
            </div>
            <div className="text-cyan-200">
              ASR: <span className={`font-mono ${
                status.asrStatus === 'connected' ? 'text-green-400' : 
                status.asrStatus === 'error' ? 'text-red-400' : 'text-yellow-400'
              }`}>
                {status.asrStatus.toUpperCase()}
              </span>
            </div>
          </div>

          {/* Config info */}
          <div className="mt-3 pt-2 border-t border-cyan-400/20">
            <div className="text-xs text-cyan-400 mb-1">CONFIG:</div>
            <div className="text-xs text-cyan-200 space-y-1">
              <div>Mode: <span className="text-white font-mono">{orchestrator.getConfig().voiceMode}</span></div>
              <div>Backend: <span className="text-white font-mono">{orchestrator.getConfig().asrBackend}</span></div>
              <div>Ambient: <span className="text-white font-mono">{orchestrator.getConfig().ambientEnabled ? 'ON' : 'OFF'}</span></div>
            </div>
          </div>

          {/* Permission request button */}
          {status.micPermission === 'denied' && (
            <button
              onClick={() => orchestrator.start()}
              className="mt-3 w-full bg-red-500/20 hover:bg-red-500/30 text-red-300 text-xs py-2 px-3 rounded border border-red-400/30"
            >
              Request Microphone Permission
            </button>
          )}
        </div>
      )}
    </div>
  );
};

// Hook för enkel integration i befintliga komponenter
export const useAmbientVoice = () => {
  const [orchestrator] = useState(() => new Orchestrator());
  const [status, setStatus] = useState<OrchestratorStatus>(orchestrator.getStatus());

  useEffect(() => {
    const unsubscribe = orchestrator.on((event) => {
      if (event.type === 'status_change') {
        setStatus(event.status);
      }
    });

    return () => {
      unsubscribe();
      orchestrator.stop();
    };
  }, [orchestrator]);

  return {
    orchestrator,
    status,
    isListening: status.isListening,
    lastPartial: status.lastPartial,
    toggleListening: () => orchestrator.toggleListening(),
  };
};