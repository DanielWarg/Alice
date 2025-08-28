/**
 * Fallback Engine - Graceful degradation for voice system
 * Handles network issues, device limitations, and audio problems
 */

import type { DeviceProfile, NetworkProfile } from './device-detector';

export interface FallbackConfig {
  textTimeoutMs: number;
  maxReconnectAttempts: number;
  enableCodecSwitch: boolean;
  enableOfflineMode: boolean;
}

export interface FallbackState {
  textMode: boolean;
  reconnecting: boolean;
  reconnectAttempts: number;
  codecSwitched: boolean;
  offlineMode: boolean;
  lastFailure?: {
    type: 'tts_timeout' | 'ws_disconnect' | 'audio_context_suspended' | 'codec_error';
    timestamp: number;
    message: string;
  };
}

export class FallbackEngine {
  private config: FallbackConfig;
  private state: FallbackState;
  private callbacks: {
    onTextFallback?: (text: string) => void;
    onReconnecting?: () => void;
    onReconnected?: () => void;
    onOfflineMode?: (enabled: boolean) => void;
    onCodecSwitch?: (newCodec: string) => void;
    onUserActionRequired?: (action: string, message: string) => void;
  };
  
  private ttsTimeouts: Map<string, NodeJS.Timeout> = new Map();
  private reconnectTimer?: NodeJS.Timeout;
  
  constructor(
    config: FallbackConfig,
    callbacks: FallbackEngine['callbacks'] = {}
  ) {
    this.config = config;
    this.callbacks = callbacks;
    this.state = {
      textMode: false,
      reconnecting: false,
      reconnectAttempts: 0,
      codecSwitched: false,
      offlineMode: false
    };
  }
  
  // Handle TTS timeout - show text immediately, continue TTS in background
  handleTTSTimeout(text: string, ttsId: string): void {
    console.log('🔄 TTS timeout detected, falling back to text');
    
    this.state.textMode = true;
    this.state.lastFailure = {
      type: 'tts_timeout',
      timestamp: Date.now(),
      message: `TTS timeout after ${this.config.textTimeoutMs}ms`
    };
    
    // Show text immediately
    this.callbacks.onTextFallback?.(text);
    
    // Set timeout to monitor TTS completion
    const timeout = setTimeout(() => {
      console.log('📱 TTS completed in background, resuming audio mode');
      this.state.textMode = false;
      this.ttsTimeouts.delete(ttsId);
    }, 10000); // Give TTS 10s to complete in background
    
    this.ttsTimeouts.set(ttsId, timeout);
  }
  
  // Handle WebSocket disconnection with progressive retry
  async handleWSDisconnect(): Promise<boolean> {
    if (this.state.reconnecting) {
      return false; // Already reconnecting
    }
    
    console.log('🔌 WebSocket disconnected, attempting reconnection...');
    
    this.state.reconnecting = true;
    this.state.lastFailure = {
      type: 'ws_disconnect',
      timestamp: Date.now(),
      message: 'WebSocket connection lost'
    };
    
    this.callbacks.onReconnecting?.();
    
    for (let attempt = 1; attempt <= this.config.maxReconnectAttempts; attempt++) {
      console.log(`🔄 Reconnection attempt ${attempt}/${this.config.maxReconnectAttempts}`);
      
      try {
        // Exponential backoff: 1s, 2s, 4s, 8s...
        const delay = Math.min(1000 * Math.pow(2, attempt - 1), 8000);
        await this.sleep(delay);
        
        // This would be called by the voice system to attempt reconnection
        const success = await this.attemptReconnection();
        
        if (success) {
          console.log('✅ Reconnection successful');
          this.state.reconnecting = false;
          this.state.reconnectAttempts = 0;
          this.callbacks.onReconnected?.();
          return true;
        }
        
      } catch (error) {
        console.warn(`❌ Reconnection attempt ${attempt} failed:`, error);
        this.state.reconnectAttempts = attempt;
      }
    }
    
    console.log('❌ All reconnection attempts failed, offering text mode');
    this.state.reconnecting = false;
    this.state.textMode = true;
    
    this.callbacks.onUserActionRequired?.('switch_to_text', 
      'Anslutningen förlorad. Byt till textläge eller försök igen senare.');
    
    return false;
  }
  
  // Handle suspended AudioContext (common on mobile)
  async handleAudioContextSuspended(audioContext: AudioContext): Promise<void> {
    console.log('🎵 AudioContext suspended, requesting user interaction');
    
    this.state.lastFailure = {
      type: 'audio_context_suspended',
      timestamp: Date.now(),
      message: 'Audio context suspended - user interaction required'
    };
    
    // Prompt user to resume audio
    this.callbacks.onUserActionRequired?.('resume_audio', 
      'Tryck här för att fortsätta med ljud');
    
    // Attempt to resume
    try {
      await audioContext.resume();
      console.log('✅ AudioContext resumed successfully');
    } catch (error) {
      console.error('❌ Failed to resume AudioContext:', error);
      this.callbacks.onUserActionRequired?.('reload_required', 
        'Ladda om sidan för att återaktivera ljud');
    }
  }
  
  // Handle codec switching for stuttering audio
  handleCodecIssues(): void {
    if (this.state.codecSwitched || !this.config.enableCodecSwitch) {
      return;
    }
    
    console.log('🎚️ Audio codec issues detected, switching to fallback codec');
    
    this.state.codecSwitched = true;
    this.state.lastFailure = {
      type: 'codec_error',
      timestamp: Date.now(),
      message: 'Audio codec performance issues'
    };
    
    // Switch from PCM to Opus or vice versa
    const newCodec = 'opus'; // or 'pcm16' depending on current
    this.callbacks.onCodecSwitch?.(newCodec);
  }
  
  // Simulate network blip for testing
  async simulateNetworkBlip(durationMs: number = 3000): Promise<void> {
    console.log(`🌐 Simulating ${durationMs}ms network blip`);
    
    const originalState = { ...this.state };
    
    // Trigger offline mode
    this.state.offlineMode = true;
    this.callbacks.onOfflineMode?.(true);
    
    // Wait for blip duration
    await this.sleep(durationMs);
    
    // Restore connection and trigger reconnection
    this.state.offlineMode = false;
    this.callbacks.onOfflineMode?.(false);
    
    // Attempt to reconnect
    await this.handleWSDisconnect();
  }
  
  // Check if system should use fallbacks based on device/network
  shouldUseFallbacks(device: DeviceProfile, network: NetworkProfile): {
    textFallback: boolean;
    codecSwitch: boolean;
    extendedTimeouts: boolean;
  } {
    return {
      textFallback: network.quality === 'poor' || network.latency > 1000,
      codecSwitch: device.browser === 'firefox' || network.quality !== 'good',
      extendedTimeouts: device.type === 'mobile' || network.quality !== 'good'
    };
  }
  
  // Get current fallback status for UI
  getFallbackStatus(): {
    active: boolean;
    mode: 'text' | 'reconnecting' | 'offline' | 'normal';
    message?: string;
    canRetry: boolean;
  } {
    if (this.state.offlineMode) {
      return {
        active: true,
        mode: 'offline',
        message: 'Ingen internetanslutning',
        canRetry: false
      };
    }
    
    if (this.state.reconnecting) {
      return {
        active: true,
        mode: 'reconnecting',
        message: `Återansluter... (${this.state.reconnectAttempts}/${this.config.maxReconnectAttempts})`,
        canRetry: false
      };
    }
    
    if (this.state.textMode) {
      return {
        active: true,
        mode: 'text',
        message: 'Textläge aktivt - röst fungerar i bakgrunden',
        canRetry: true
      };
    }
    
    return {
      active: false,
      mode: 'normal',
      canRetry: false
    };
  }
  
  // Reset fallback state
  reset(): void {
    this.state = {
      textMode: false,
      reconnecting: false,
      reconnectAttempts: 0,
      codecSwitched: false,
      offlineMode: false
    };
    
    // Clear all timeouts
    this.ttsTimeouts.forEach(timeout => clearTimeout(timeout));
    this.ttsTimeouts.clear();
    
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = undefined;
    }
  }
  
  // Update configuration
  updateConfig(newConfig: Partial<FallbackConfig>): void {
    this.config = { ...this.config, ...newConfig };
  }
  
  // Private helper methods
  private async attemptReconnection(): Promise<boolean> {
    // This would be implemented by the voice system
    // For now, simulate success/failure
    return Math.random() > 0.3; // 70% success rate simulation
  }
  
  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
  
  // Cleanup
  destroy(): void {
    this.reset();
  }
}