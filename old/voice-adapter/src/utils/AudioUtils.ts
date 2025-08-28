/**
 * Audio Utilities - minimal implementation
 */
export class AudioUtils {
  static convertSampleRate(input: Float32Array, from: number, to: number): Float32Array {
    return input; // Stub implementation
  }
  
  static normalize(input: Float32Array): Float32Array {
    return input; // Stub implementation
  }
  
  static toInt16Array(input: Float32Array): Int16Array {
    const output = new Int16Array(input.length);
    for (let i = 0; i < input.length; i++) {
      output[i] = Math.round(input[i] * 32767);
    }
    return output;
  }
  
  static toFloat32Array(input: Int16Array): Float32Array {
    const output = new Float32Array(input.length);
    for (let i = 0; i < input.length; i++) {
      output[i] = input[i] / 32767;
    }
    return output;
  }
}