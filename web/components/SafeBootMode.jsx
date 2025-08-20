"use client";
import React, { useState, useEffect } from "react";
import { ErrorBoundary } from "./ErrorBoundary";

/**
 * SafeBootMode - Privacy controls and emergency disable for Alice HUD
 * 
 * Provides secure fallback mode when full features cannot be safely loaded.
 * Critical for Alice's reliability and user privacy.
 * 
 * Features:
 * - Emergency disable toggle
 * - Privacy mode controls
 * - Safe fallback rendering
 * - Feature isolation
 */

// Safe boot state management
const SAFE_BOOT_KEY = 'alice_safe_boot_mode';
const PRIVACY_SETTINGS_KEY = 'alice_privacy_settings';

const DEFAULT_PRIVACY_SETTINGS = {
  disableCamera: false,
  disableMicrophone: false,
  disableLocation: false,
  disableWebGL: false,
  disableExternalAPIs: false,
  offlineMode: false
};

export function SafeBootMode({ children, forceSafeMode = false }) {
  const [safeBootEnabled, setSafeBootEnabled] = useState(forceSafeMode);
  const [privacySettings, setPrivacySettings] = useState(DEFAULT_PRIVACY_SETTINGS);
  const [showControls, setShowControls] = useState(false);
  const [systemChecks, setSystemChecks] = useState({
    webgl: null,
    camera: null,
    microphone: null,
    speechRecognition: null
  });

  // Initialize safe boot state
  useEffect(() => {
    if (typeof window === 'undefined') return;
    
    // Check for safe boot flag
    const savedSafeBoot = localStorage.getItem(SAFE_BOOT_KEY);
    const savedPrivacy = localStorage.getItem(PRIVACY_SETTINGS_KEY);
    
    if (savedSafeBoot === 'true' || forceSafeMode) {
      setSafeBootEnabled(true);
    }
    
    if (savedPrivacy) {
      try {
        setPrivacySettings({ ...DEFAULT_PRIVACY_SETTINGS, ...JSON.parse(savedPrivacy) });
      } catch (e) {
        console.warn('Failed to parse privacy settings:', e);
      }
    }
    
    // Run system capability checks
    runSystemChecks();
  }, [forceSafeMode]);

  // System capability detection
  const runSystemChecks = async () => {
    const checks = { ...systemChecks };
    
    // WebGL check
    try {
      const canvas = document.createElement('canvas');
      const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
      checks.webgl = !!gl;
    } catch (e) {
      checks.webgl = false;
    }
    
    // Camera access check
    try {
      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
        checks.camera = true;
      } else {
        checks.camera = false;
      }
    } catch (e) {
      checks.camera = false;
    }
    
    // Microphone check
    try {
      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
        checks.microphone = true;
      } else {
        checks.microphone = false;
      }
    } catch (e) {
      checks.microphone = false;
    }
    
    // Speech recognition check
    checks.speechRecognition = !!(window.webkitSpeechRecognition || window.SpeechRecognition);
    
    setSystemChecks(checks);
  };

  // Toggle safe boot mode
  const toggleSafeMode = () => {
    const newState = !safeBootEnabled;
    setSafeBootEnabled(newState);
    localStorage.setItem(SAFE_BOOT_KEY, newState.toString());
  };

  // Update privacy settings
  const updatePrivacySetting = (key, value) => {
    const newSettings = { ...privacySettings, [key]: value };
    setPrivacySettings(newSettings);
    localStorage.setItem(PRIVACY_SETTINGS_KEY, JSON.stringify(newSettings));
  };

  // Clear all data and reset
  const emergencyReset = () => {
    if (confirm('This will clear all Alice data and reload the page. Continue?')) {
      localStorage.clear();
      sessionStorage.clear();
      window.location.reload();
    }
  };

  // Safe boot indicator component
  const SafeBootIndicator = () => (
    <div className="fixed top-4 right-4 z-50">
      <div className="flex items-center gap-2 rounded-lg border border-orange-500/30 bg-orange-950/20 px-3 py-2 text-sm backdrop-blur">
        <div className="h-2 w-2 rounded-full bg-orange-400 animate-pulse" />
        <span className="text-orange-200">Safe Boot</span>
        <button
          onClick={() => setShowControls(!showControls)}
          className="ml-2 rounded-md border border-orange-400/30 px-2 py-1 text-xs text-orange-200 hover:bg-orange-400/10"
        >
          Settings
        </button>
      </div>
    </div>
  );

  // Privacy controls panel
  const PrivacyControls = () => (
    <div className="fixed top-16 right-4 z-50 w-80 rounded-lg border border-cyan-500/20 bg-cyan-950/90 backdrop-blur p-4">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-cyan-200">Alice Privacy Controls</h3>
        <p className="text-sm text-cyan-300/80">Manage system access and privacy settings</p>
      </div>
      
      {/* Safe Mode Toggle */}
      <div className="mb-4 flex items-center justify-between">
        <span className="text-sm text-cyan-200">Safe Boot Mode</span>
        <button
          onClick={toggleSafeMode}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
            safeBootEnabled ? 'bg-orange-500' : 'bg-gray-600'
          }`}
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              safeBootEnabled ? 'translate-x-6' : 'translate-x-1'
            }`}
          />
        </button>
      </div>

      {/* Privacy Settings */}
      <div className="space-y-3">
        {Object.entries(privacySettings).map(([key, value]) => (
          <div key={key} className="flex items-center justify-between">
            <span className="text-sm text-cyan-300">
              {key.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase())}
            </span>
            <button
              onClick={() => updatePrivacySetting(key, !value)}
              className={`relative inline-flex h-5 w-9 items-center rounded-full text-xs transition-colors ${
                value ? 'bg-red-500' : 'bg-gray-600'
              }`}
            >
              <span
                className={`inline-block h-3 w-3 transform rounded-full bg-white transition-transform ${
                  value ? 'translate-x-5' : 'translate-x-1'
                }`}
              />
            </button>
          </div>
        ))}
      </div>

      {/* System Status */}
      <div className="mt-4 pt-4 border-t border-cyan-500/20">
        <h4 className="text-sm font-semibold text-cyan-200 mb-2">System Status</h4>
        <div className="space-y-1 text-xs">
          {Object.entries(systemChecks).map(([key, status]) => (
            <div key={key} className="flex items-center justify-between">
              <span className="text-cyan-300">{key}</span>
              <span className={`${status === true ? 'text-green-400' : status === false ? 'text-red-400' : 'text-yellow-400'}`}>
                {status === null ? 'Checking...' : status ? 'Available' : 'Unavailable'}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Emergency Controls */}
      <div className="mt-4 pt-4 border-t border-cyan-500/20">
        <div className="flex gap-2">
          <button
            onClick={() => setShowControls(false)}
            className="flex-1 rounded-lg border border-cyan-400/30 px-3 py-2 text-sm text-cyan-200 hover:bg-cyan-400/10"
          >
            Close
          </button>
          <button
            onClick={emergencyReset}
            className="flex-1 rounded-lg border border-red-400/30 px-3 py-2 text-sm text-red-200 hover:bg-red-400/10"
          >
            Emergency Reset
          </button>
        </div>
      </div>
    </div>
  );

  // Safe fallback renderer
  const SafeFallback = ({ children }) => (
    <div className="min-h-screen bg-gray-900 text-gray-100">
      <SafeBootIndicator />
      {showControls && <PrivacyControls />}
      
      <div className="container mx-auto px-6 py-8">
        <div className="mb-8 text-center">
          <div className="inline-flex h-16 w-16 items-center justify-center rounded-full bg-orange-500/20 mb-4">
            <svg className="h-8 w-8 text-orange-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-orange-200">Alice Safe Mode</h1>
          <p className="text-orange-300/80 mt-2">
            Some features are disabled for enhanced privacy and safety
          </p>
        </div>
        
        {children}
      </div>
    </div>
  );

  // Apply privacy restrictions to children
  const getRestrictedChildren = () => {
    if (!children) return null;
    
    // Clone children and pass privacy settings as props
    return React.Children.map(children, child => {
      if (React.isValidElement(child)) {
        return React.cloneElement(child, {
          safeBootMode: safeBootEnabled,
          privacySettings: privacySettings,
          systemChecks: systemChecks,
          ...child.props
        });
      }
      return child;
    });
  };

  // Render safe mode or normal mode
  if (safeBootEnabled) {
    return (
      <ErrorBoundary componentName="SafeBootMode">
        <SafeFallback>
          {getRestrictedChildren()}
        </SafeFallback>
      </ErrorBoundary>
    );
  }

  return (
    <ErrorBoundary componentName="SafeBootMode">
      {showControls && <PrivacyControls />}
      {getRestrictedChildren()}
    </ErrorBoundary>
  );
}

// Hook for accessing safe boot context in child components
export function useSafeBootMode() {
  const [safeBootEnabled, setSafeBootEnabled] = useState(false);
  const [privacySettings, setPrivacySettings] = useState(DEFAULT_PRIVACY_SETTINGS);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    
    const savedSafeBoot = localStorage.getItem(SAFE_BOOT_KEY);
    const savedPrivacy = localStorage.getItem(PRIVACY_SETTINGS_KEY);
    
    setSafeBootEnabled(savedSafeBoot === 'true');
    
    if (savedPrivacy) {
      try {
        setPrivacySettings({ ...DEFAULT_PRIVACY_SETTINGS, ...JSON.parse(savedPrivacy) });
      } catch (e) {
        console.warn('Failed to parse privacy settings:', e);
      }
    }
  }, []);

  return {
    safeBootEnabled,
    privacySettings,
    isCameraDisabled: privacySettings.disableCamera,
    isMicrophoneDisabled: privacySettings.disableMicrophone,
    isLocationDisabled: privacySettings.disableLocation,
    isWebGLDisabled: privacySettings.disableWebGL,
    isExternalAPIsDisabled: privacySettings.disableExternalAPIs,
    isOfflineModeEnabled: privacySettings.offlineMode
  };
}

export default SafeBootMode;