/**
 * Voice Realtime Interface - React Component for OpenAI Realtime Voice
 * Provides visual states: "Lyssnar" → "Tänker" → "Svarar"
 * Now with Barge-in & Interrupt functionality
 */
'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { VoiceUIBinding, type VoiceState, type VoiceUICallbacks } from '../lib/voice-binding';
import { ConsentStore } from '../lib/consent-store';
import ConsentModal from './ConsentModal';
import SyntheticBadge from './SyntheticBadge';
import type { VoiceMetrics } from '@alice/voice-adapter';

interface VoiceMetricsDisplay {
  asr_partial_latency_ms?: number;
  asr_final_latency_ms?: number;
  llm_latency_ms?: number;
  tts_ttfa_ms?: number;
  e2e_roundtrip_ms?: number;
}

export default function VoiceRealtimeInterface({ onVoiceBindingReady }: { 
  onVoiceBindingReady?: (binding: VoiceUIBinding) => void 
} = {}) {
  const [voiceState, setVoiceState] = useState<VoiceState>('idle');
  const [partialText, setPartialText] = useState('');
  const [finalText, setFinalText] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [metrics, setMetrics] = useState<VoiceMetricsDisplay>({});
  const [isInitialized, setIsInitialized] = useState(false);
  const [conversationHistory, setConversationHistory] = useState<Array<{
    type: 'user' | 'assistant';
    text: string;
    timestamp: number;
  }>>([]);
  const [bargeInEnabled, setBargeInEnabled] = useState(true);
  const [vadThreshold, setVadThreshold] = useState(0.01);
  const [vadGracePeriod, setVadGracePeriod] = useState(300);
  const [showConsentModal, setShowConsentModal] = useState(false);
  const [hasConsent, setHasConsent] = useState(false);
  const [sessionId, setSessionId] = useState('');
  const [showConsentSuccess, setShowConsentSuccess] = useState(false);
  
  const voiceBindingRef = useRef<VoiceUIBinding | null>(null);
  const initializationRef = useRef(false);
  
  // Voice UI callbacks
  const callbacks: VoiceUICallbacks = useCallback({
    onStateChange: (state: VoiceState) => {
      console.log('Voice state changed:', state);
      setVoiceState(state);
      
      if (state === 'idle') {
        setPartialText('');
        setError(null);
      }
    },
    
    onPartialTranscript: (text: string, confidence: number) => {
      console.log('Partial transcript:', text, 'confidence:', confidence);
      setPartialText(text);
    },
    
    onFinalTranscript: (text: string, confidence: number) => {
      console.log('Final transcript:', text, 'confidence:', confidence);
      setFinalText(text);
      setPartialText('');
      
      // Add to conversation history
      setConversationHistory(prev => [...prev, {
        type: 'user',
        text,
        timestamp: Date.now()
      }]);
    },
    
    onSpeakingStart: () => {
      console.log('Started speaking');
    },
    
    onSpeakingEnd: () => {
      console.log('Finished speaking');
      
      if (finalText) {
        // Add assistant response to history
        setConversationHistory(prev => [...prev, {
          type: 'assistant',
          text: `Du sa: ${finalText}`,
          timestamp: Date.now()
        }]);
        setFinalText('');
      }
    },
    
    onError: (errorMessage: string) => {
      console.error('Voice error:', errorMessage);
      setError(errorMessage);
    },
    
    onMetrics: (voiceMetrics: VoiceMetrics) => {
      console.log('Voice metrics:', voiceMetrics);
      setMetrics({
        asr_partial_latency_ms: voiceMetrics.asr_partial_latency_ms,
        asr_final_latency_ms: voiceMetrics.asr_final_latency_ms,
        llm_latency_ms: voiceMetrics.llm_latency_ms,
        tts_ttfa_ms: voiceMetrics.tts_ttfa_ms,
        e2e_roundtrip_ms: voiceMetrics.e2e_roundtrip_ms
      });
    }
  }, [finalText]);
  
  // Initialize voice binding with consent checking
  useEffect(() => {
    if (initializationRef.current) return;
    initializationRef.current = true;
    
    const checkConsentAndInitialize = async () => {
      // Generate session ID
      setSessionId('session_' + Date.now().toString(36));
      
      // Check if consent is required and valid
      if (ConsentStore.isConsentRequired()) {
        const hasValidConsent = ConsentStore.hasValidConsent();
        setHasConsent(hasValidConsent);
        
        if (!hasValidConsent) {
          setShowConsentModal(true);
          return; // Don't initialize until consent is granted
        }
      } else {
        setHasConsent(true);
      }
      
      // Initialize if we have consent
      await initializeVoice();
    };
    
    const initializeVoice = async () => {
      try {
        console.log('Initializing voice binding...');
        const binding = new VoiceUIBinding(callbacks);
        await binding.initialize();
        
        voiceBindingRef.current = binding;
        setIsInitialized(true);
        console.log('Voice binding initialized successfully');
        
        // Notify parent component that voice binding is ready
        onVoiceBindingReady?.(binding);
        
      } catch (err) {
        console.error('Voice initialization failed:', err);
        
        if ((err as Error).message === 'CONSENT_REQUIRED') {
          setShowConsentModal(true);
        } else {
          setError(`Initialization failed: ${err}`);
        }
      }
    };
    
    checkConsentAndInitialize();
    
    // Cleanup on unmount
    return () => {
      if (voiceBindingRef.current) {
        voiceBindingRef.current.destroy().catch(console.error);
      }
    };
  }, [callbacks]);
  
  const startListening = async () => {
    if (!voiceBindingRef.current || !isInitialized) {
      setError('Voice system not initialized');
      return;
    }
    
    try {
      await voiceBindingRef.current.startListening();
    } catch (err) {
      setError(`Failed to start listening: ${err}`);
    }
  };
  
  const stopListening = async () => {
    if (!voiceBindingRef.current) return;
    
    try {
      await voiceBindingRef.current.stopListening();
    } catch (err) {
      setError(`Failed to stop listening: ${err}`);
    }
  };
  
  const cancelSpeaking = async () => {
    if (!voiceBindingRef.current) return;
    
    try {
      await voiceBindingRef.current.cancel();
    } catch (err) {
      setError(`Failed to cancel speaking: ${err}`);
    }
  };
  
  const updateBargeInSettings = () => {
    if (!voiceBindingRef.current) return;
    
    voiceBindingRef.current.setVADEnabled(bargeInEnabled);
    voiceBindingRef.current.setVADThreshold(vadThreshold);
    voiceBindingRef.current.setVADGracePeriod(vadGracePeriod);
  };
  
  // Apply barge-in settings when they change
  useEffect(() => {
    updateBargeInSettings();
  }, [bargeInEnabled, vadThreshold, vadGracePeriod]);
  
  // Test barge-in function
  const testBargeIn = async () => {
    if (!voiceBindingRef.current) return;
    
    // Start a long TTS message for testing
    await voiceBindingRef.current.speakText(
      "Detta är ett långt test meddelande för att testa barge-in funktionaliteten. Du bör kunna avbryta mig när som helst genom att börja prata."
    );
  };
  
  // Consent handlers
  const handleConsentGranted = async (scopes: ('asr' | 'tts' | 'voice_clone')[]) => {
    try {
      await ConsentStore.grantConsent(scopes);
      setHasConsent(true);
      setShowConsentModal(false);
      
      // Show confirmation snackbar
      setShowConsentSuccess(true);
      setTimeout(() => setShowConsentSuccess(false), 4000);
      
      // Now initialize voice system
      const binding = new VoiceUIBinding(callbacks);
      await binding.initialize();
      
      voiceBindingRef.current = binding;
      setIsInitialized(true);
      console.log('Voice binding initialized after consent');
      
      onVoiceBindingReady?.(binding);
      
    } catch (error) {
      console.error('Failed to initialize after consent:', error);
      setError(`Failed to initialize: ${error}`);
    }
  };
  
  const handleConsentDeclined = () => {
    setShowConsentModal(false);
    setError('Röstfunktioner kräver samtycke för att fungera');
  };
  
  const revokeConsent = async () => {
    await ConsentStore.revokeConsent();
    setHasConsent(false);
    setIsInitialized(false);
    
    // Destroy current voice binding
    if (voiceBindingRef.current) {
      await voiceBindingRef.current.destroy();
      voiceBindingRef.current = null;
    }
    
    setError('Samtycke återkallat - röstfunktioner inaktiverade');
  };
  
  const getStateText = (state: VoiceState): string => {
    switch (state) {
      case 'idle': return 'Redo att lyssna';
      case 'listening': return 'Lyssnar...';
      case 'thinking': return 'Tänker...';
      case 'thinking_tools': return 'Tänker (kör verktyg)...';
      case 'speaking': return 'Svarar...';
      case 'error': return 'Fel uppstod';
      default: return 'Okänt tillstånd';
    }
  };
  
  const getStateColor = (state: VoiceState): string => {
    switch (state) {
      case 'idle': return 'bg-gray-500';
      case 'listening': return 'bg-blue-500 animate-pulse';
      case 'thinking': return 'bg-yellow-500 animate-pulse';
      case 'thinking_tools': return 'bg-purple-500 animate-bounce';
      case 'speaking': return 'bg-green-500 animate-pulse';
      case 'error': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };
  
  return (
    <>
      {/* Consent Modal */}
      <ConsentModal 
        isOpen={showConsentModal}
        onConsent={handleConsentGranted}
        onDecline={handleConsentDeclined}
      />
      
      {/* Synthetic Speech Badge */}
      <SyntheticBadge 
        isActive={ConsentStore.showSyntheticBadge() && voiceState === 'speaking'}
        provider={process.env.NEXT_PUBLIC_VOICE_PROVIDER || 'OpenAI'}
        model={process.env.NEXT_PUBLIC_OPENAI_REALTIME_MODEL}
        sessionId={sessionId}
      />
      
      {/* Consent Success Snackbar */}
      {showConsentSuccess && (
        <div className="fixed top-4 left-1/2 transform -translate-x-1/2 z-50 bg-green-600 text-white px-6 py-3 rounded-lg shadow-lg animate-fade-in">
          <div className="flex items-center space-x-2">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            <div>
              <div className="font-medium">Tack! Röst är aktiverat.</div>
              <div className="text-sm opacity-90">Du kan när som helst ändra dina val under Inställningar → Integritet.</div>
            </div>
          </div>
        </div>
      )}
      
      <div className="bg-white rounded-lg shadow-lg p-6 max-w-2xl mx-auto">
        <h2 className="text-2xl font-bold mb-6 text-center">Alice Voice Interface</h2>
      
      {/* Voice State Indicator */}
      <div className="flex items-center justify-center mb-6">
        <div className={`w-4 h-4 rounded-full ${getStateColor(voiceState)} mr-3`}></div>
        <span className="text-lg font-medium">{getStateText(voiceState)}</span>
      </div>
      
      {/* Controls */}
      <div className="flex justify-center gap-4 mb-6 flex-wrap">
        <button
          onClick={startListening}
          disabled={!isInitialized || voiceState === 'listening' || voiceState === 'speaking'}
          className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed"
        >
          🎤 Starta
        </button>
        
        <button
          onClick={stopListening}
          disabled={voiceState !== 'listening'}
          className="px-6 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 disabled:bg-gray-300 disabled:cursor-not-allowed"
        >
          ⏹️ Stoppa
        </button>
        
        <button
          onClick={cancelSpeaking}
          disabled={voiceState !== 'speaking'}
          className="px-6 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 disabled:bg-gray-300 disabled:cursor-not-allowed"
        >
          ❌ Avbryt
        </button>
        
        <button
          onClick={testBargeIn}
          disabled={!isInitialized}
          className="px-4 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600 disabled:bg-gray-300 disabled:cursor-not-allowed text-sm"
        >
          🎯 Test Barge-in
        </button>
      </div>
      
      {/* Barge-in Settings */}
      <div className="bg-purple-50 p-4 rounded-lg mb-6">
        <h3 className="text-lg font-semibold mb-3">🎯 Barge-in Settings</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="flex items-center space-x-2">
            <input
              type="checkbox"
              id="barge-in-enabled"
              checked={bargeInEnabled}
              onChange={(e) => setBargeInEnabled(e.target.checked)}
              className="rounded"
            />
            <label htmlFor="barge-in-enabled" className="text-sm font-medium">
              Enable Barge-in
            </label>
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-1">
              VAD Threshold: {(vadThreshold * 1000).toFixed(0)}μ
            </label>
            <input
              type="range"
              min="0.001"
              max="0.1"
              step="0.001"
              value={vadThreshold}
              onChange={(e) => setVadThreshold(parseFloat(e.target.value))}
              className="w-full"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-1">
              Grace Period: {vadGracePeriod}ms
            </label>
            <input
              type="range"
              min="100"
              max="1000"
              step="50"
              value={vadGracePeriod}
              onChange={(e) => setVadGracePeriod(parseInt(e.target.value))}
              className="w-full"
            />
          </div>
        </div>
        
        <div className="mt-3 text-xs text-gray-600">
          <p>💡 <strong>Barge-in</strong> låter dig avbryta TTS genom att börja prata. 
          Höj threshold för att minska false positives, justera grace period för reaktionstid.</p>
        </div>
      </div>
      
      {/* Current Transcription */}
      <div className="mb-6">
        {partialText && (
          <div className="bg-blue-50 p-3 rounded-lg mb-2">
            <span className="text-sm text-blue-600 font-medium">Transkriberar...</span>
            <p className="text-blue-800">{partialText}</p>
          </div>
        )}
        
        {voiceState === 'thinking' && finalText && (
          <div className="bg-yellow-50 p-3 rounded-lg mb-2">
            <span className="text-sm text-yellow-600 font-medium">Tänker på:</span>
            <p className="text-yellow-800">{finalText}</p>
          </div>
        )}
      </div>
      
      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 p-3 rounded-lg mb-6">
          <span className="text-sm text-red-600 font-medium">Fel:</span>
          <p className="text-red-800">{error}</p>
        </div>
      )}
      
      {/* Compliance & Privacy Status */}
      <div className="bg-green-50 p-4 rounded-lg mb-6">
        <div className="flex justify-between items-center">
          <div>
            <h3 className="text-sm font-semibold mb-1">🛡️ Integritet & Samtycke</h3>
            <div className="text-xs space-y-1">
              <div>Status: {hasConsent ? '✅ Samtycke beviljat' : '❌ Ingen samtycke'}</div>
              <div>Filter: {ConsentStore.getContentFilter()}</div>
              <div>Audio-lagring: {ConsentStore.persistAudio() ? 'Aktiverad' : 'Inaktiverad ✅'}</div>
            </div>
          </div>
          {hasConsent && (
            <button
              onClick={revokeConsent}
              className="px-3 py-1 bg-red-500 text-white rounded text-xs hover:bg-red-600"
            >
              Återkalla samtycke
            </button>
          )}
        </div>
      </div>
      
      {/* Conversation History */}
      {conversationHistory.length > 0 && (
        <div className="mb-6">
          <h3 className="text-lg font-semibold mb-3">Konversation</h3>
          <div className="space-y-2 max-h-40 overflow-y-auto">
            {conversationHistory.slice(-6).map((item, index) => (
              <div
                key={index}
                className={`p-2 rounded-lg ${
                  item.type === 'user' 
                    ? 'bg-blue-50 border-l-4 border-blue-500' 
                    : 'bg-green-50 border-l-4 border-green-500'
                }`}
              >
                <span className="text-xs text-gray-500">
                  {item.type === 'user' ? 'Du:' : 'Alice:'}
                </span>
                <p className="text-sm">{item.text}</p>
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* Performance Metrics */}
      {Object.keys(metrics).length > 0 && (
        <div className="bg-gray-50 p-4 rounded-lg">
          <h3 className="text-sm font-semibold mb-2">Prestanda (ms)</h3>
          <div className="grid grid-cols-2 gap-2 text-xs">
            {metrics.asr_partial_latency_ms && (
              <div>ASR Partial: {Math.round(metrics.asr_partial_latency_ms)}ms</div>
            )}
            {metrics.asr_final_latency_ms && (
              <div>ASR Final: {Math.round(metrics.asr_final_latency_ms)}ms</div>
            )}
            {metrics.llm_latency_ms && (
              <div>LLM: {Math.round(metrics.llm_latency_ms)}ms</div>
            )}
            {metrics.tts_ttfa_ms && (
              <div>TTS TTFA: {Math.round(metrics.tts_ttfa_ms)}ms</div>
            )}
            {metrics.e2e_roundtrip_ms && (
              <div className="col-span-2 font-semibold">
                E2E Total: {Math.round(metrics.e2e_roundtrip_ms)}ms
              </div>
            )}
          </div>
        </div>
      )}
    </div>
    </>
  );
}