/**
 * ConsentModal - GDPR/EU AI-Act compliant consent interface
 * Compact, clear, and user-friendly consent flow
 */
'use client';

import { useState } from 'react';

export interface ConsentModalProps {
  isOpen: boolean;
  onConsent: (scopes: ('asr' | 'tts' | 'voice_clone')[]) => void;
  onDecline: () => void;
}

export default function ConsentModal({ isOpen, onConsent, onDecline }: ConsentModalProps) {
  const [allowVoiceCloning, setAllowVoiceCloning] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  
  // Compact consent version for compliance logging (v1.0)
  const CONSENT_VERSION = "v1.0: Samtycke till ASR/TTS via vald leverantör, tekniska mätvärden lagras, rå-audio 0 dagar standard, återkallbart via inställningar.";

  if (!isOpen) return null;

  const handleConsent = () => {
    const scopes: ('asr' | 'tts' | 'voice_clone')[] = ['asr', 'tts'];
    if (allowVoiceCloning) {
      scopes.push('voice_clone');
    }
    onConsent(scopes);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
        <div className="flex items-center mb-4">
          <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mr-3">
            <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
            </svg>
          </div>
          <div>
            <h2 className="text-xl font-bold text-gray-900">Samtycke till röstinteraktion</h2>
            <p className="text-sm text-gray-500">För att använda röst i Alice</p>
          </div>
        </div>

        <div className="mb-4">
          <p className="text-sm text-gray-700 leading-relaxed">
            För att använda röst i Alice behöver vi ditt samtycke. Vi behandlar ljud lokalt och via vald leverantör för transkribering och syntetiskt tal. Vi sparar inte rå-audio som standard.
          </p>
        </div>

        {/* Advanced options */}
        <div className="mb-4 p-3 bg-gray-50 rounded-lg">
          <div className="flex items-start space-x-2">
            <input
              type="checkbox"
              id="voice-cloning"
              checked={allowVoiceCloning}
              onChange={(e) => setAllowVoiceCloning(e.target.checked)}
              className="mt-1 rounded"
            />
            <label htmlFor="voice-cloning" className="text-sm">
              <span className="font-medium">Röstkloning (valfritt, av som standard)</span>
              <span className="text-gray-600 block">
                Jag samtycker till röstkloning av MIN EGEN röst för personlig användning.
              </span>
            </label>
          </div>
        </div>

        {/* Expandable details */}
        <button
          onClick={() => setShowDetails(!showDetails)}
          className="text-xs text-blue-600 hover:text-blue-800 mb-4 flex items-center"
        >
          {showDetails ? '▼' : '▶'} Mer information om datahantering
        </button>

        {showDetails && (
          <div className="mb-4 p-3 bg-blue-50 rounded-lg text-xs space-y-2">
            <div><strong>• Vad används:</strong> röst till text (ASR), svar från modellen, syntetiskt tal (TTS).</div>
            <div><strong>• Vad lagras:</strong> tekniska mätvärden (latens, felkoder), sessions-ID och tidsstämplar. Rå-audio sparas inte om du inte uttryckligen tillåter det.</div>
            <div><strong>• Lagringstid:</strong> standard 0 dagar för rå-audio (avstängt), övrig telemetri enligt vår policy.</div>
            <div><strong>• Rättigheter:</strong> du kan när som helst återkalla samtycke och be oss radera metadata.</div>
            <div><strong>• Kontakt:</strong> <a href="mailto:support@postboxen.se" className="text-blue-600 underline">support@postboxen.se</a></div>
            <div><strong>Policy:</strong> <a href="/privacy" className="text-blue-600 underline">Läs Integritet & säkerhet</a> | <a href="/consent" className="text-blue-600 underline">Hantera samtycken</a></div>
          </div>
        )}

        {/* Actions */}
        <div className="flex space-x-3">
          <button
            onClick={onDecline}
            className="flex-1 px-4 py-2 text-gray-700 bg-gray-200 rounded-lg hover:bg-gray-300 text-sm font-medium"
          >
            Avbryt
          </button>
          <button
            onClick={handleConsent}
            className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium"
          >
            Godkänn och fortsätt
          </button>
        </div>

        <div className="mt-3 text-center">
          <p className="text-xs text-gray-500">
            🇪🇺 GDPR & EU AI Act compliant • {CONSENT_VERSION.split(':')[0]}
          </p>
        </div>
      </div>
    </div>
  );
}