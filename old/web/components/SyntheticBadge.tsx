/**
 * SyntheticBadge - Transparent disclosure of synthetic speech
 * Always visible when TTS is active for compliance and trust
 */
'use client';

import { useState, useEffect } from 'react';

export interface SyntheticBadgeProps {
  isActive: boolean;
  provider?: string;
  model?: string;
  sessionId?: string;
}

export default function SyntheticBadge({ 
  isActive, 
  provider = 'AI', 
  model, 
  sessionId 
}: SyntheticBadgeProps) {
  const [fadeOut, setFadeOut] = useState(false);
  const [showDetails, setShowDetails] = useState(false);

  useEffect(() => {
    if (!isActive && fadeOut) {
      // Fade out after 300ms delay when TTS stops
      const timer = setTimeout(() => {
        setFadeOut(false);
      }, 300);
      return () => clearTimeout(timer);
    } else if (isActive) {
      setFadeOut(false);
    } else if (!isActive) {
      setFadeOut(true);
    }
  }, [isActive, fadeOut]);

  // Don't render if not active and fully faded out
  if (!isActive && !fadeOut) return null;

  return (
    <div 
      className={`fixed top-4 right-4 z-40 transition-all duration-300 ${
        isActive 
          ? 'opacity-100 translate-y-0' 
          : 'opacity-0 translate-y-[-10px]'
      }`}
    >
      <div 
        className="bg-purple-600 text-white px-3 py-2 rounded-lg shadow-lg flex items-center space-x-2 text-sm cursor-pointer hover:bg-purple-700 transition-colors"
        onClick={() => setShowDetails(!showDetails)}
      >
        <div className="flex items-center space-x-2">
          <div className="w-2 h-2 bg-white rounded-full animate-pulse"></div>
          <span className="font-medium">Syntetiskt tal aktivt</span>
        </div>
        
        <svg 
          className={`w-4 h-4 transition-transform ${showDetails ? 'rotate-180' : ''}`} 
          fill="none" 
          stroke="currentColor" 
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </div>

      {/* Expandable details */}
      {showDetails && (
        <div className="absolute top-full right-0 mt-2 bg-white border border-gray-200 rounded-lg shadow-xl p-3 text-xs min-w-[200px]">
          <div className="space-y-2 text-gray-700">
            <div className="flex justify-between">
              <span className="font-medium">Provider:</span>
              <span className="text-purple-600">{provider}</span>
            </div>
            
            {model && (
              <div className="flex justify-between">
                <span className="font-medium">Model:</span>
                <span className="text-gray-600">{model}</span>
              </div>
            )}
            
            {sessionId && (
              <div className="flex justify-between">
                <span className="font-medium">Session:</span>
                <span className="text-gray-400 font-mono text-xs">{sessionId.slice(-8)}</span>
              </div>
            )}
            
            <div className="border-t pt-2 mt-2">
              <div className="flex items-center space-x-1 text-purple-600">
                <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                </svg>
                <span className="font-medium">AI-genererat tal</span>
              </div>
              <p className="text-gray-600 mt-1 leading-tight">
                Detta röstmeddelande är syntetiskt genererat av AI, inte inspelat av en människa.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}