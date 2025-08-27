/**
 * Voice Activity Detection - minimal implementation
 */
import type { VADResult } from '../types/index.js';

export class SimpleVAD {
  process(audioData: Float32Array): VADResult {
    return {
      state: 'silence',
      confidence: 0.5,
      energy: 0,
      timestamp_ms: Date.now()
    };
  }
}