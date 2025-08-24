import React, { useEffect, useState } from 'react';
import { HealthMonitor, Orchestrator, LaptopClient, ProbeClient } from './index';

interface VoiceStatusBadgeProps {
  className?: string;
}

export const VoiceStatusBadge: React.FC<VoiceStatusBadgeProps> = ({ className = "" }) => {
  const [source, setSource] = useState<'PROBE' | 'LAPTOP' | 'OFFLINE'>('LAPTOP');
  const [state, setState] = useState<'IDLE' | 'LISTENING' | 'REPLYING'>('IDLE');

  useEffect(() => {
    // Initialize voice system
    const healthMonitor = new HealthMonitor('http://127.0.0.1:8000/api/probe/health');
    const probeClient = new ProbeClient();
    const laptopClient = new LaptopClient();
    const orchestrator = new Orchestrator(probeClient, laptopClient);

    // Listen for status changes
    healthMonitor.on((status) => {
      orchestrator.setProbeStatus(status);
    });

    orchestrator.on((event) => {
      if (event.type === 'source') {
        setSource(event.source);
      }
      if (event.type === 'state') {
        setState(event.state);
      }
    });

    // Start monitoring
    healthMonitor.start();

    return () => {
      healthMonitor.stop();
      probeClient.stop();
      laptopClient.stop();
    };
  }, []);

  const getBadgeColor = () => {
    if (state === 'LISTENING') return 'bg-green-500';
    if (state === 'REPLYING') return 'bg-blue-500';
    if (source === 'OFFLINE') return 'bg-red-500';
    if (source === 'PROBE') return 'bg-purple-500';
    return 'bg-gray-500'; // LAPTOP
  };

  const getBadgeText = () => {
    if (state === 'LISTENING') return `🎤 ${source}`;
    if (state === 'REPLYING') return `🗣️ ${source}`;
    return source;
  };

  return (
    <div className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium text-white ${getBadgeColor()} ${className}`}>
      {getBadgeText()}
    </div>
  );
};