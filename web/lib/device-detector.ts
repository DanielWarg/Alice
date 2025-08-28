/**
 * Device Detector - Device and network profile detection
 * Optimizes voice experience for different device/network combinations
 */

export interface DeviceProfile {
  type: 'desktop' | 'mobile' | 'tablet';
  browser: 'chrome' | 'firefox' | 'safari' | 'edge' | 'unknown';
  os: 'windows' | 'macos' | 'linux' | 'ios' | 'android' | 'unknown';
  capabilities: {
    audioContext: boolean;
    userGestureRequired: boolean;
    webAudio: boolean;
    mediaDevices: boolean;
    webRTC: boolean;
  };
  recommendedSettings: {
    bufferSize: number;
    sampleRate: number;
    fallbackToWebAudio: boolean;
    requiresUserInteraction: boolean;
  };
}

export interface NetworkProfile {
  quality: 'good' | 'average' | 'poor';
  estimatedBandwidth: number; // kbps
  latency: number; // ms
  stability: 'stable' | 'unstable';
  offlineBlipSimulation?: boolean;
}

export class DeviceDetector {
  
  static getDeviceProfile(): DeviceProfile {
    const userAgent = navigator.userAgent.toLowerCase();
    const isIOS = /iphone|ipad|ipod/.test(userAgent);
    const isAndroid = /android/.test(userAgent);
    const isMobile = isIOS || isAndroid || /mobile/.test(userAgent);
    const isTablet = /ipad/.test(userAgent) || (isAndroid && !/mobile/.test(userAgent));
    
    // Browser detection
    let browser: DeviceProfile['browser'] = 'unknown';
    if (userAgent.includes('chrome') && !userAgent.includes('edg')) {
      browser = 'chrome';
    } else if (userAgent.includes('firefox')) {
      browser = 'firefox';
    } else if (userAgent.includes('safari') && !userAgent.includes('chrome')) {
      browser = 'safari';
    } else if (userAgent.includes('edg')) {
      browser = 'edge';
    }
    
    // OS detection
    let os: DeviceProfile['os'] = 'unknown';
    if (isIOS) {
      os = 'ios';
    } else if (isAndroid) {
      os = 'android';
    } else if (userAgent.includes('win')) {
      os = 'windows';
    } else if (userAgent.includes('mac')) {
      os = 'macos';
    } else if (userAgent.includes('linux')) {
      os = 'linux';
    }
    
    // Capability detection
    const capabilities = {
      audioContext: !!(window.AudioContext || (window as any).webkitAudioContext),
      userGestureRequired: isIOS || isMobile, // iOS and mobile require user gesture
      webAudio: !!(window.AudioContext || (window as any).webkitAudioContext),
      mediaDevices: !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia),
      webRTC: !!(window.RTCPeerConnection || (window as any).webkitRTCPeerConnection)
    };
    
    // Recommended settings based on device type
    let recommendedSettings = {
      bufferSize: 4096,
      sampleRate: 16000,
      fallbackToWebAudio: false,
      requiresUserInteraction: false
    };
    
    if (isIOS && browser === 'safari') {
      recommendedSettings = {
        bufferSize: 8192, // Larger buffer for iOS
        sampleRate: 16000,
        fallbackToWebAudio: true,
        requiresUserInteraction: true
      };
    } else if (isAndroid && browser === 'chrome') {
      recommendedSettings = {
        bufferSize: 4096,
        sampleRate: 16000,
        fallbackToWebAudio: false,
        requiresUserInteraction: false
      };
    } else if (browser === 'firefox') {
      recommendedSettings = {
        bufferSize: 4096,
        sampleRate: 16000,
        fallbackToWebAudio: true, // Firefox has WebAudio quirks
        requiresUserInteraction: false
      };
    }
    
    return {
      type: isMobile ? 'mobile' : isTablet ? 'tablet' : 'desktop',
      browser,
      os,
      capabilities,
      recommendedSettings
    };
  }
  
  static async estimateNetworkProfile(): Promise<NetworkProfile> {
    let quality: NetworkProfile['quality'] = 'good';
    let estimatedBandwidth = 1000; // kbps
    let latency = 50; // ms
    let stability: NetworkProfile['stability'] = 'stable';
    
    // Use Network Information API if available
    if ('connection' in navigator) {
      const connection = (navigator as any).connection;
      
      if (connection) {
        // Estimate bandwidth from connection type
        const effectiveType = connection.effectiveType;
        switch (effectiveType) {
          case 'slow-2g':
            quality = 'poor';
            estimatedBandwidth = 50;
            latency = 2000;
            break;
          case '2g':
            quality = 'poor';
            estimatedBandwidth = 250;
            latency = 1400;
            break;
          case '3g':
            quality = 'average';
            estimatedBandwidth = 700;
            latency = 400;
            break;
          case '4g':
            quality = 'good';
            estimatedBandwidth = 10000;
            latency = 100;
            break;
        }
        
        // Check for instability
        if (connection.saveData || connection.rtt > 500) {
          stability = 'unstable';
        }
      }
    }
    
    // Fallback: perform a simple latency test
    try {
      const start = Date.now();
      await fetch('/api/ping', { method: 'HEAD' }).catch(() => {});
      latency = Date.now() - start;
      
      if (latency > 500) {
        quality = 'poor';
      } else if (latency > 200) {
        quality = 'average';
      }
    } catch {
      // Ignore ping test failures
    }
    
    return {
      quality,
      estimatedBandwidth,
      latency,
      stability
    };
  }
  
  static getOptimizedSettings(device: DeviceProfile, network: NetworkProfile): {
    audioSettings: {
      bufferSize: number;
      sampleRate: number;
      enableEchoCancellation: boolean;
      enableNoiseSuppression: boolean;
    };
    fallbackSettings: {
      enableTextFallback: boolean;
      textTimeoutMs: number;
      maxReconnectAttempts: number;
      enableCodecSwitch: boolean;
    };
  } {
    const audioSettings = {
      bufferSize: device.recommendedSettings.bufferSize,
      sampleRate: device.recommendedSettings.sampleRate,
      enableEchoCancellation: device.type === 'mobile',
      enableNoiseSuppression: device.type === 'mobile'
    };
    
    // Adjust for network quality
    if (network.quality === 'poor') {
      audioSettings.bufferSize *= 2; // Larger buffer for poor connections
      audioSettings.sampleRate = 8000; // Lower sample rate
    }
    
    const fallbackSettings = {
      enableTextFallback: network.quality !== 'good',
      textTimeoutMs: network.quality === 'poor' ? 1500 : 2000,
      maxReconnectAttempts: network.stability === 'unstable' ? 3 : 2,
      enableCodecSwitch: device.browser === 'firefox' || network.quality === 'poor'
    };
    
    return {
      audioSettings,
      fallbackSettings
    };
  }
  
  static getDeviceDisplayName(profile: DeviceProfile): string {
    const browserNames = {
      chrome: 'Chrome',
      firefox: 'Firefox',
      safari: 'Safari',
      edge: 'Edge',
      unknown: 'Browser'
    };
    
    const osNames = {
      windows: 'Windows',
      macos: 'macOS',
      linux: 'Linux',
      ios: 'iOS',
      android: 'Android',
      unknown: 'OS'
    };
    
    const deviceType = profile.type.charAt(0).toUpperCase() + profile.type.slice(1);
    return `${deviceType} ${browserNames[profile.browser]} (${osNames[profile.os]})`;
  }
  
  static simulateOfflineBlip(durationMs: number = 3000): Promise<void> {
    console.log(`🌐 Simulating ${durationMs}ms offline blip`);
    
    // Override fetch to simulate network failure
    const originalFetch = window.fetch;
    window.fetch = (...args) => {
      return Promise.reject(new Error('Simulated network failure'));
    };
    
    return new Promise(resolve => {
      setTimeout(() => {
        window.fetch = originalFetch;
        console.log('🌐 Network restored');
        resolve();
      }, durationMs);
    });
  }
}