/**
 * Device Test Panel - Test different device/network combinations
 * Allows manual testing of fallback scenarios
 */
'use client';

import { useState, useEffect } from 'react';
import { DeviceDetector, type DeviceProfile, type NetworkProfile } from '../lib/device-detector';
import { FallbackEngine, type FallbackConfig } from '../lib/fallback-engine';

export interface DeviceTestPanelProps {
  voiceBinding?: any;
  onProfileChange?: (device: DeviceProfile, network: NetworkProfile) => void;
}

export default function DeviceTestPanel({ voiceBinding, onProfileChange }: DeviceTestPanelProps) {
  const [currentDevice, setCurrentDevice] = useState<DeviceProfile | null>(null);
  const [currentNetwork, setCurrentNetwork] = useState<NetworkProfile | null>(null);
  const [selectedDeviceProfile, setSelectedDeviceProfile] = useState<string>('auto');
  const [selectedNetworkProfile, setSelectedNetworkProfile] = useState<string>('good');
  const [fallbackEngine, setFallbackEngine] = useState<FallbackEngine | null>(null);
  const [fallbackStatus, setFallbackStatus] = useState<any>(null);
  const [testRunning, setTestRunning] = useState<string | null>(null);

  // Device profile options
  const deviceProfiles = [
    { id: 'auto', name: 'Auto-detect', description: 'Detect current device' },
    { id: 'desktop-chrome', name: 'Desktop Chrome', description: 'Windows/Mac Chrome' },
    { id: 'desktop-firefox', name: 'Desktop Firefox', description: 'Windows/Mac Firefox' },
    { id: 'desktop-edge', name: 'Desktop Edge', description: 'Windows Edge' },
    { id: 'ios-safari', name: 'iOS Safari', description: 'iPhone/iPad Safari' },
    { id: 'android-chrome', name: 'Android Chrome', description: 'Android Chrome' }
  ];

  // Network profile options
  const networkProfiles = [
    { id: 'good', name: 'Good', description: '4G/WiFi - Low latency' },
    { id: 'average', name: 'Average', description: '3G - Medium latency' },
    { id: 'poor', name: 'Poor', description: '2G - High latency' },
    { id: 'offline-blip', name: 'Offline Blip', description: '3-5s disconnect simulation' }
  ];

  useEffect(() => {
    // Initialize device detection
    const detectDevice = async () => {
      const device = DeviceDetector.getDeviceProfile();
      const network = await DeviceDetector.estimateNetworkProfile();
      
      setCurrentDevice(device);
      setCurrentNetwork(network);
      onProfileChange?.(device, network);
    };

    detectDevice();
  }, [onProfileChange]);

  useEffect(() => {
    // Initialize fallback engine
    if (currentDevice && currentNetwork) {
      const optimized = DeviceDetector.getOptimizedSettings(currentDevice, currentNetwork);
      
      const config: FallbackConfig = {
        textTimeoutMs: parseInt(process.env.NEXT_PUBLIC_VOICE_FALLBACK_TEXT_ON_TTS_TIMEOUT_MS || '2000'),
        maxReconnectAttempts: parseInt(process.env.NEXT_PUBLIC_VOICE_WS_MAX_RETRIES || '2'),
        enableCodecSwitch: process.env.NEXT_PUBLIC_VOICE_OUTPUT_CODEC === 'auto',
        enableOfflineMode: true
      };

      const engine = new FallbackEngine(config, {
        onTextFallback: (text) => {
          console.log('📱 Text fallback activated:', text);
        },
        onReconnecting: () => {
          console.log('🔄 Reconnecting...');
        },
        onReconnected: () => {
          console.log('✅ Reconnected successfully');
        },
        onUserActionRequired: (action, message) => {
          console.log('👆 User action required:', action, message);
        }
      });

      setFallbackEngine(engine);

      // Update status periodically
      const interval = setInterval(() => {
        setFallbackStatus(engine.getFallbackStatus());
      }, 1000);

      return () => {
        clearInterval(interval);
        engine.destroy();
      };
    }
  }, [currentDevice, currentNetwork]);

  const createMockDeviceProfile = (profileId: string): DeviceProfile => {
    const profiles: Record<string, Partial<DeviceProfile>> = {
      'desktop-chrome': {
        type: 'desktop',
        browser: 'chrome',
        os: 'windows',
        capabilities: {
          audioContext: true,
          userGestureRequired: false,
          webAudio: true,
          mediaDevices: true,
          webRTC: true
        },
        recommendedSettings: {
          bufferSize: 4096,
          sampleRate: 24000,
          fallbackToWebAudio: false,
          requiresUserInteraction: false
        }
      },
      'ios-safari': {
        type: 'mobile',
        browser: 'safari',
        os: 'ios',
        capabilities: {
          audioContext: true,
          userGestureRequired: true,
          webAudio: true,
          mediaDevices: true,
          webRTC: true
        },
        recommendedSettings: {
          bufferSize: 8192,
          sampleRate: 16000,
          fallbackToWebAudio: true,
          requiresUserInteraction: true
        }
      },
      'android-chrome': {
        type: 'mobile',
        browser: 'chrome',
        os: 'android',
        capabilities: {
          audioContext: true,
          userGestureRequired: false,
          webAudio: true,
          mediaDevices: true,
          webRTC: true
        },
        recommendedSettings: {
          bufferSize: 4096,
          sampleRate: 16000,
          fallbackToWebAudio: false,
          requiresUserInteraction: false
        }
      }
    };

    return {
      ...currentDevice,
      ...profiles[profileId]
    } as DeviceProfile;
  };

  const createMockNetworkProfile = (profileId: string): NetworkProfile => {
    const profiles: Record<string, NetworkProfile> = {
      'good': {
        quality: 'good',
        estimatedBandwidth: 10000,
        latency: 50,
        stability: 'stable'
      },
      'average': {
        quality: 'average',
        estimatedBandwidth: 700,
        latency: 200,
        stability: 'stable'
      },
      'poor': {
        quality: 'poor',
        estimatedBandwidth: 100,
        latency: 800,
        stability: 'unstable'
      },
      'offline-blip': {
        quality: 'good',
        estimatedBandwidth: 10000,
        latency: 50,
        stability: 'unstable',
        offlineBlipSimulation: true
      }
    };

    return profiles[profileId] || profiles['good'];
  };

  const handleDeviceProfileChange = (profileId: string) => {
    setSelectedDeviceProfile(profileId);
    
    if (profileId === 'auto' && currentDevice) {
      onProfileChange?.(currentDevice, currentNetwork!);
    } else {
      const mockDevice = createMockDeviceProfile(profileId);
      const mockNetwork = createMockNetworkProfile(selectedNetworkProfile);
      onProfileChange?.(mockDevice, mockNetwork);
    }
  };

  const handleNetworkProfileChange = (profileId: string) => {
    setSelectedNetworkProfile(profileId);
    
    const device = selectedDeviceProfile === 'auto' ? currentDevice! : createMockDeviceProfile(selectedDeviceProfile);
    const network = createMockNetworkProfile(profileId);
    
    onProfileChange?.(device, network);
  };

  const runFallbackTest = async (testType: string) => {
    if (!fallbackEngine || !voiceBinding) return;
    
    setTestRunning(testType);
    
    try {
      switch (testType) {
        case 'tts-timeout':
          fallbackEngine.handleTTSTimeout('Hej Alice, vad blir vädret i Göteborg idag?', 'test-tts-1');
          break;
          
        case 'ws-disconnect':
          await fallbackEngine.handleWSDisconnect();
          break;
          
        case 'audio-suspend':
          if (voiceBinding.audioContext) {
            await fallbackEngine.handleAudioContextSuspended(voiceBinding.audioContext);
          }
          break;
          
        case 'codec-switch':
          fallbackEngine.handleCodecIssues();
          break;
          
        case 'network-blip':
          await fallbackEngine.simulateNetworkBlip(3000);
          break;
      }
    } catch (error) {
      console.error('Test failed:', error);
    } finally {
      setTestRunning(null);
    }
  };

  if (!currentDevice || !currentNetwork) {
    return <div className="p-4">Detecting device and network...</div>;
  }

  return (
    <div className="bg-white p-6 rounded-lg shadow-lg max-w-4xl mx-auto">
      <h2 className="text-xl font-bold mb-4">🛠️ Device & Network Testing</h2>
      
      {/* Current Status */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <div className="bg-blue-50 p-4 rounded-lg">
          <h3 className="font-semibold mb-2">📱 Current Device</h3>
          <div className="text-sm space-y-1">
            <div><strong>Type:</strong> {DeviceDetector.getDeviceDisplayName(currentDevice)}</div>
            <div><strong>Audio Context:</strong> {currentDevice.capabilities.audioContext ? '✅' : '❌'}</div>
            <div><strong>User Gesture:</strong> {currentDevice.capabilities.userGestureRequired ? 'Required' : 'Not required'}</div>
            <div><strong>Buffer Size:</strong> {currentDevice.recommendedSettings.bufferSize}</div>
          </div>
        </div>

        <div className="bg-green-50 p-4 rounded-lg">
          <h3 className="font-semibold mb-2">🌐 Current Network</h3>
          <div className="text-sm space-y-1">
            <div><strong>Quality:</strong> <span className={`font-semibold ${
              currentNetwork.quality === 'good' ? 'text-green-600' : 
              currentNetwork.quality === 'average' ? 'text-yellow-600' : 'text-red-600'
            }`}>{currentNetwork.quality}</span></div>
            <div><strong>Bandwidth:</strong> {currentNetwork.estimatedBandwidth} kbps</div>
            <div><strong>Latency:</strong> {currentNetwork.latency} ms</div>
            <div><strong>Stability:</strong> {currentNetwork.stability}</div>
          </div>
        </div>
      </div>

      {/* Profile Selection */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        <div>
          <h3 className="font-semibold mb-3">Device Profile</h3>
          <select
            value={selectedDeviceProfile}
            onChange={(e) => handleDeviceProfileChange(e.target.value)}
            className="w-full p-2 border rounded-lg text-sm"
          >
            {deviceProfiles.map(profile => (
              <option key={profile.id} value={profile.id}>
                {profile.name} - {profile.description}
              </option>
            ))}
          </select>
        </div>

        <div>
          <h3 className="font-semibold mb-3">Network Profile</h3>
          <select
            value={selectedNetworkProfile}
            onChange={(e) => handleNetworkProfileChange(e.target.value)}
            className="w-full p-2 border rounded-lg text-sm"
          >
            {networkProfiles.map(profile => (
              <option key={profile.id} value={profile.id}>
                {profile.name} - {profile.description}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Fallback Status */}
      {fallbackStatus && fallbackStatus.active && (
        <div className="bg-orange-50 border border-orange-200 p-4 rounded-lg mb-6">
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 bg-orange-500 rounded-full animate-pulse"></div>
            <span className="font-semibold">Fallback Active: {fallbackStatus.mode}</span>
          </div>
          {fallbackStatus.message && (
            <p className="text-sm text-orange-700 mt-1">{fallbackStatus.message}</p>
          )}
        </div>
      )}

      {/* Test Controls */}
      <div>
        <h3 className="font-semibold mb-3">🧪 Fallback Tests</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
          <button
            onClick={() => runFallbackTest('tts-timeout')}
            disabled={testRunning === 'tts-timeout'}
            className="px-3 py-2 bg-yellow-500 text-white rounded text-sm hover:bg-yellow-600 disabled:bg-gray-400"
          >
            {testRunning === 'tts-timeout' ? '⏳' : '📱'} TTS Timeout
          </button>

          <button
            onClick={() => runFallbackTest('ws-disconnect')}
            disabled={testRunning === 'ws-disconnect'}
            className="px-3 py-2 bg-red-500 text-white rounded text-sm hover:bg-red-600 disabled:bg-gray-400"
          >
            {testRunning === 'ws-disconnect' ? '⏳' : '🔌'} WS Disconnect
          </button>

          <button
            onClick={() => runFallbackTest('audio-suspend')}
            disabled={testRunning === 'audio-suspend'}
            className="px-3 py-2 bg-purple-500 text-white rounded text-sm hover:bg-purple-600 disabled:bg-gray-400"
          >
            {testRunning === 'audio-suspend' ? '⏳' : '🎵'} Audio Suspend
          </button>

          <button
            onClick={() => runFallbackTest('codec-switch')}
            disabled={testRunning === 'codec-switch'}
            className="px-3 py-2 bg-blue-500 text-white rounded text-sm hover:bg-blue-600 disabled:bg-gray-400"
          >
            {testRunning === 'codec-switch' ? '⏳' : '🎚️'} Codec Switch
          </button>

          <button
            onClick={() => runFallbackTest('network-blip')}
            disabled={testRunning === 'network-blip'}
            className="px-3 py-2 bg-green-500 text-white rounded text-sm hover:bg-green-600 disabled:bg-gray-400"
          >
            {testRunning === 'network-blip' ? '⏳' : '🌐'} Network Blip
          </button>
        </div>
      </div>

      <div className="mt-4 text-xs text-gray-600">
        <p><strong>Tips:</strong> Tests simulate real-world issues. TTS Timeout shows text fallback, 
        WS Disconnect tests reconnection, Audio Suspend requires user interaction, 
        Codec Switch changes audio format, Network Blip simulates connection loss.</p>
      </div>
    </div>
  );
}