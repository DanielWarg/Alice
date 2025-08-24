// Audio State Management för Alice B2
// Hanterar conversation flow states och state transitions

export type AudioState = 'listening' | 'speaking' | 'interrupted' | 'processing' | 'calibrating' | 'error';

export interface StateTransition {
  from: AudioState;
  to: AudioState;
  timestamp: number;
  trigger: string;
  context?: any;
}

export interface StateMetrics {
  totalTransitions: number;
  timeInStates: Record<AudioState, number>;
  averageStateTime: Record<AudioState, number>;
  lastTransition: StateTransition | null;
  stateHistory: StateTransition[];
}

export interface StateContext {
  interruptedContent?: string;
  resumePosition?: number;
  userInput?: string;
  confidence?: number;
  error?: string;
}

export class AudioStateManager {
  private currentState: AudioState = 'listening';
  private previousState: AudioState = 'listening';
  private stateStartTime: number = Date.now();
  
  // State transition tracking
  private transitions: StateTransition[] = [];
  private maxHistoryLength = 100;
  
  // State timing metrics
  private stateTimings: Record<AudioState, number[]> = {
    listening: [],
    speaking: [],
    interrupted: [],
    processing: [],
    calibrating: [],
    error: []
  };
  
  // Valid state transitions
  private validTransitions: Record<AudioState, AudioState[]> = {
    listening: ['speaking', 'processing', 'calibrating', 'error'],
    speaking: ['interrupted', 'listening', 'error'],
    interrupted: ['processing', 'listening', 'error'],
    processing: ['speaking', 'listening', 'error'],
    calibrating: ['listening', 'error'],
    error: ['listening', 'calibrating']
  };
  
  // Context data för current state
  private stateContext: StateContext = {};
  
  // Event handlers
  public onStateChange: (oldState: AudioState, newState: AudioState, context?: StateContext) => void = () => {};
  public onInvalidTransition: (from: AudioState, to: AudioState) => void = () => {};
  public onStateTimeout: (state: AudioState, duration: number) => void = () => {};
  public onError: (error: string, state: AudioState) => void = () => {};
  
  // State timeouts (in milliseconds)
  private stateTimeouts: Record<AudioState, number> = {
    listening: 0, // No timeout
    speaking: 30000, // 30 seconds max speaking time
    interrupted: 5000, // 5 seconds to handle interruption
    processing: 10000, // 10 seconds max processing time
    calibrating: 5000, // 5 seconds max calibration
    error: 0 // Manual recovery only
  };
  
  private timeoutHandle: NodeJS.Timeout | null = null;

  constructor() {
    console.log('🎛️ AudioStateManager initialized');
    this.startStateTimer();
  }

  // Get current state
  getCurrentState(): AudioState {
    return this.currentState;
  }

  // Get previous state
  getPreviousState(): AudioState {
    return this.previousState;
  }

  // Get current state context
  getStateContext(): StateContext {
    return { ...this.stateContext };
  }

  // Check if transition is valid
  isValidTransition(from: AudioState, to: AudioState): boolean {
    return this.validTransitions[from]?.includes(to) || false;
  }

  // Transition to new state
  transitionTo(newState: AudioState, trigger: string, context: StateContext = {}): boolean {
    const oldState = this.currentState;
    
    // Validate transition
    if (!this.isValidTransition(oldState, newState)) {
      console.warn(`⚠️ Invalid state transition: ${oldState} -> ${newState}`);
      this.onInvalidTransition(oldState, newState);
      return false;
    }
    
    // Clear existing timeout
    if (this.timeoutHandle) {
      clearTimeout(this.timeoutHandle);
      this.timeoutHandle = null;
    }
    
    // Record timing för previous state
    const stateTime = Date.now() - this.stateStartTime;
    this.stateTimings[oldState].push(stateTime);
    
    // Limit history size
    if (this.stateTimings[oldState].length > 50) {
      this.stateTimings[oldState] = this.stateTimings[oldState].slice(-25);
    }
    
    // Create transition record
    const transition: StateTransition = {
      from: oldState,
      to: newState,
      timestamp: Date.now(),
      trigger,
      context
    };
    
    // Update state
    this.previousState = oldState;
    this.currentState = newState;
    this.stateStartTime = Date.now();
    this.stateContext = { ...context };
    
    // Record transition
    this.transitions.push(transition);
    if (this.transitions.length > this.maxHistoryLength) {
      this.transitions = this.transitions.slice(-this.maxHistoryLength / 2);
    }
    
    // Set up new state timeout
    this.startStateTimer();
    
    // Log transition
    console.log(`🔄 State transition: ${oldState} -> ${newState} (${trigger})`, context);
    
    // Trigger event handler
    this.onStateChange(oldState, newState, context);
    
    return true;
  }

  // Start state timeout timer
  private startStateTimer(): void {
    const timeout = this.stateTimeouts[this.currentState];
    
    if (timeout > 0) {
      this.timeoutHandle = setTimeout(() => {
        const duration = Date.now() - this.stateStartTime;
        console.warn(`⏰ State timeout: ${this.currentState} (${duration}ms)`);
        
        this.onStateTimeout(this.currentState, duration);
        
        // Auto-transition to appropriate state on timeout
        this.handleStateTimeout();
      }, timeout);
    }
  }

  // Handle state timeout
  private handleStateTimeout(): void {
    switch (this.currentState) {
      case 'speaking':
        // Speaking too long - force stop
        this.transitionTo('listening', 'speaking_timeout');
        break;
        
      case 'interrupted':
        // Interruption not handled - resume listening
        this.transitionTo('listening', 'interruption_timeout');
        break;
        
      case 'processing':
        // Processing taking too long - error state
        this.transitionTo('error', 'processing_timeout', {
          error: 'Processing timeout - system may be overloaded'
        });
        break;
        
      case 'calibrating':
        // Calibration timeout - assume failed, go to listening
        this.transitionTo('listening', 'calibration_timeout');
        break;
        
      default:
        // Unexpected timeout
        console.warn(`⚠️ Unexpected timeout in state: ${this.currentState}`);
    }
  }

  // State-specific helper methods

  startListening(context: StateContext = {}): boolean {
    return this.transitionTo('listening', 'start_listening', context);
  }

  startSpeaking(content?: string): boolean {
    return this.transitionTo('speaking', 'start_speaking', { 
      interruptedContent: content 
    });
  }

  handleInterruption(userInput?: string, confidence?: number): boolean {
    // Store context för potential resume
    const currentContext = this.getStateContext();
    
    return this.transitionTo('interrupted', 'user_barge_in', {
      ...currentContext,
      userInput,
      confidence
    });
  }

  startProcessing(userInput?: string): boolean {
    return this.transitionTo('processing', 'start_processing', { 
      userInput 
    });
  }

  startCalibration(): boolean {
    return this.transitionTo('calibrating', 'start_calibration');
  }

  enterErrorState(error: string): boolean {
    return this.transitionTo('error', 'error_occurred', { error });
  }

  recoverFromError(): boolean {
    if (this.currentState !== 'error') {
      console.warn('⚠️ Not in error state - cannot recover');
      return false;
    }
    
    return this.transitionTo('listening', 'error_recovery');
  }

  // Resume from interrupted state
  resumeAfterInterruption(newContent?: string): boolean {
    if (this.currentState !== 'interrupted') {
      console.warn('⚠️ Not in interrupted state - cannot resume');
      return false;
    }
    
    const context = this.getStateContext();
    
    if (newContent) {
      // Start speaking with new content
      return this.transitionTo('speaking', 'resume_with_new_content', {
        interruptedContent: newContent
      });
    } else if (context.interruptedContent) {
      // Resume original content
      return this.transitionTo('speaking', 'resume_original_content', context);
    } else {
      // No content to resume - go back to listening
      return this.transitionTo('listening', 'no_content_to_resume');
    }
  }

  // Update state context without changing state
  updateContext(newContext: Partial<StateContext>): void {
    this.stateContext = { ...this.stateContext, ...newContext };
    console.log('📝 State context updated:', newContext);
  }

  // Get state metrics
  getMetrics(): StateMetrics {
    const now = Date.now();
    const currentStateTime = now - this.stateStartTime;
    
    // Calculate total time in each state
    const timeInStates: Record<AudioState, number> = {
      listening: 0,
      speaking: 0,
      interrupted: 0,
      processing: 0,
      calibrating: 0,
      error: 0
    };
    
    // Add recorded timings
    for (const state of Object.keys(this.stateTimings) as AudioState[]) {
      const timings = this.stateTimings[state];
      timeInStates[state] = timings.reduce((sum, time) => sum + time, 0);
    }
    
    // Add current state time
    timeInStates[this.currentState] += currentStateTime;
    
    // Calculate averages
    const averageStateTime: Record<AudioState, number> = {
      listening: 0,
      speaking: 0,
      interrupted: 0,
      processing: 0,
      calibrating: 0,
      error: 0
    };
    
    for (const state of Object.keys(this.stateTimings) as AudioState[]) {
      const timings = this.stateTimings[state];
      if (timings.length > 0) {
        averageStateTime[state] = timings.reduce((sum, time) => sum + time, 0) / timings.length;
      }
    }
    
    return {
      totalTransitions: this.transitions.length,
      timeInStates,
      averageStateTime,
      lastTransition: this.transitions[this.transitions.length - 1] || null,
      stateHistory: [...this.transitions]
    };
  }

  // Get state history
  getStateHistory(maxEntries?: number): StateTransition[] {
    const history = [...this.transitions];
    
    if (maxEntries && maxEntries > 0) {
      return history.slice(-maxEntries);
    }
    
    return history;
  }

  // Check how long in current state
  getTimeInCurrentState(): number {
    return Date.now() - this.stateStartTime;
  }

  // Force transition (bypass validation) - use carefully!
  forceTransition(newState: AudioState, trigger: string, context: StateContext = {}): void {
    const oldState = this.currentState;
    
    console.warn(`🚨 Force transition: ${oldState} -> ${newState} (${trigger})`);
    
    // Clear timeout
    if (this.timeoutHandle) {
      clearTimeout(this.timeoutHandle);
      this.timeoutHandle = null;
    }
    
    // Update state without validation
    this.previousState = oldState;
    this.currentState = newState;
    this.stateStartTime = Date.now();
    this.stateContext = { ...context };
    
    // Record forced transition
    this.transitions.push({
      from: oldState,
      to: newState,
      timestamp: Date.now(),
      trigger: `FORCED: ${trigger}`,
      context
    });
    
    this.startStateTimer();
    this.onStateChange(oldState, newState, context);
  }

  // Reset state manager
  reset(): void {
    console.log('🔄 Resetting AudioStateManager');
    
    if (this.timeoutHandle) {
      clearTimeout(this.timeoutHandle);
      this.timeoutHandle = null;
    }
    
    this.currentState = 'listening';
    this.previousState = 'listening';
    this.stateStartTime = Date.now();
    this.stateContext = {};
    
    // Keep some history för analysis
    if (this.transitions.length > 10) {
      this.transitions = this.transitions.slice(-5);
    }
    
    this.startStateTimer();
  }

  // Configure state timeouts
  setStateTimeout(state: AudioState, timeoutMs: number): void {
    this.stateTimeouts[state] = timeoutMs;
    console.log(`⏰ Timeout för ${state} set to ${timeoutMs}ms`);
    
    // If we're currently in this state, restart timer
    if (this.currentState === state) {
      this.startStateTimer();
    }
  }

  // Validate state transitions configuration
  validateConfiguration(): boolean {
    let isValid = true;
    
    for (const fromState of Object.keys(this.validTransitions) as AudioState[]) {
      const toStates = this.validTransitions[fromState];
      
      for (const toState of toStates) {
        if (!(toState in this.validTransitions)) {
          console.error(`❌ Invalid transition target: ${fromState} -> ${toState}`);
          isValid = false;
        }
      }
    }
    
    if (isValid) {
      console.log('✅ State transition configuration is valid');
    }
    
    return isValid;
  }

  // Cleanup resources
  cleanup(): void {
    if (this.timeoutHandle) {
      clearTimeout(this.timeoutHandle);
      this.timeoutHandle = null;
    }
    
    console.log('🧹 AudioStateManager cleanup complete');
  }
}

// State machine testing utilities
export class StateManagerTester {
  static testAllTransitions(manager: AudioStateManager): void {
    console.log('🧪 Testing all state transitions...');
    
    const states: AudioState[] = ['listening', 'speaking', 'interrupted', 'processing', 'calibrating', 'error'];
    let passedTransitions = 0;
    let totalTransitions = 0;
    
    for (const fromState of states) {
      for (const toState of states) {
        if (fromState !== toState) {
          totalTransitions++;
          
          // Force to fromState first
          manager.forceTransition(fromState, 'test_setup');
          
          // Try transition
          const success = manager.transitionTo(toState, 'test_transition');
          
          if (success) {
            passedTransitions++;
            console.log(`✅ ${fromState} -> ${toState}: PASS`);
          } else {
            console.log(`❌ ${fromState} -> ${toState}: BLOCKED`);
          }
        }
      }
    }
    
    console.log(`📊 Transition test results: ${passedTransitions}/${totalTransitions} allowed`);
    
    // Reset to clean state
    manager.reset();
  }

  static async testStateTimeouts(manager: AudioStateManager): Promise<void> {
    console.log('🧪 Testing state timeouts...');
    
    return new Promise((resolve) => {
      let timeoutsDetected = 0;
      
      const originalHandler = manager.onStateTimeout;
      manager.onStateTimeout = (state: AudioState, duration: number) => {
        timeoutsDetected++;
        console.log(`⏰ Timeout detected: ${state} (${duration}ms)`);
        originalHandler(state, duration);
        
        if (timeoutsDetected >= 2) {
          manager.onStateTimeout = originalHandler;
          resolve();
        }
      };
      
      // Test speaking timeout (set to 1 second för quick test)
      manager.setStateTimeout('speaking', 1000);
      manager.startSpeaking('Test content');
      
      // Test processing timeout after 2 seconds
      setTimeout(() => {
        manager.setStateTimeout('processing', 1000);
        manager.startProcessing('Test input');
      }, 1500);
      
      // Safety timeout
      setTimeout(() => {
        manager.onStateTimeout = originalHandler;
        resolve();
      }, 5000);
    });
  }

  static measureStateTransitionLatency(manager: AudioStateManager): number {
    const start = performance.now();
    
    manager.transitionTo('speaking', 'latency_test');
    manager.transitionTo('listening', 'latency_test');
    
    const end = performance.now();
    const latency = end - start;
    
    console.log(`⚡ State transition latency: ${latency.toFixed(2)}ms`);
    return latency;
  }
}

export default AudioStateManager;