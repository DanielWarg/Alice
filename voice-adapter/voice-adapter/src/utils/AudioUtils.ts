import {
  AudioChunk,
  AudioFormat,
  AudioUtilsInterface,
  DEFAULT_AUDIO_FORMAT
} from '../types';

/**
 * Audio utilities for format conversion and processing
 */
export class AudioUtils implements AudioUtilsInterface {
  private static instance: AudioUtils;

  private constructor() {}

  /**
   * Get singleton instance
   */
  static getInstance(): AudioUtils {
    if (!AudioUtils.instance) {
      AudioUtils.instance = new AudioUtils();
    }
    return AudioUtils.instance;
  }

  /**
   * Convert audio between formats
   */
  async convertFormat(input: AudioChunk, targetFormat: AudioFormat): Promise<AudioChunk> {
    // If formats are identical, return copy
    if (this.formatsEqual(input.format, targetFormat)) {
      return {
        ...input,
        data: Buffer.from(input.data)
      };
    }

    let processedData: any = Buffer.from(input.data);
    let currentFormat = { ...input.format };

    // Convert sample rate if needed
    if (currentFormat.sampleRate !== targetFormat.sampleRate) {
      processedData = await this.resampleAudio(processedData, currentFormat, targetFormat.sampleRate) as any;
      currentFormat.sampleRate = targetFormat.sampleRate;
    }

    // Convert channels if needed
    if (currentFormat.channels !== targetFormat.channels) {
      processedData = this.convertChannels(processedData, currentFormat, targetFormat.channels);
      currentFormat.channels = targetFormat.channels;
    }

    // Convert bit depth if needed
    if (currentFormat.bitDepth !== targetFormat.bitDepth) {
      processedData = this.convertBitDepth(processedData, currentFormat.bitDepth, targetFormat.bitDepth);
      currentFormat.bitDepth = targetFormat.bitDepth;
    }

    // Convert encoding if needed
    if (currentFormat.encoding !== targetFormat.encoding) {
      processedData = await this.convertEncoding(processedData, currentFormat, targetFormat.encoding) as any;
      currentFormat.encoding = targetFormat.encoding;
    }

    return {
      data: processedData,
      format: targetFormat,
      timestamp: input.timestamp,
      duration: this.calculateDuration({ data: processedData, format: targetFormat } as AudioChunk),
      sequenceId: input.sequenceId
    };
  }

  /**
   * Resample audio to different sample rate
   */
  async resample(input: AudioChunk, targetSampleRate: number): Promise<AudioChunk> {
    if (input.format.sampleRate === targetSampleRate) {
      return { ...input, data: Buffer.from(input.data) };
    }

    const resampledData: any = await this.resampleAudio(input.data, input.format, targetSampleRate);
    const newFormat = { ...input.format, sampleRate: targetSampleRate };

    return {
      data: resampledData,
      format: newFormat,
      timestamp: input.timestamp,
      duration: this.calculateDuration({ data: resampledData, format: newFormat } as AudioChunk),
      sequenceId: input.sequenceId || 0
    };
  }

  /**
   * Normalize audio volume
   */
  normalize(input: AudioChunk, targetLevel: number = 0.8): AudioChunk {
    if (input.format.encoding !== 'pcm') {
      console.warn('[AudioUtils] Normalization only supported for PCM format');
      return { ...input, data: Buffer.from(input.data) };
    }

    const samples = this.bufferToSamples(input.data, input.format.bitDepth);
    
    // Find peak amplitude
    let maxAmplitude = 0;
    for (const sample of samples) {
      maxAmplitude = Math.max(maxAmplitude, Math.abs(sample));
    }

    if (maxAmplitude === 0) {
      return { ...input, data: Buffer.from(input.data) };
    }

    // Calculate normalization factor
    const normalizationFactor = targetLevel / maxAmplitude;

    // Apply normalization
    const normalizedSamples = samples.map(sample => sample * normalizationFactor);
    const normalizedBuffer = this.samplesToBuffer(normalizedSamples, input.format.bitDepth);

    return {
      ...input,
      data: normalizedBuffer
    };
  }

  /**
   * Detect audio format from buffer
   */
  detectFormat(buffer: Buffer): AudioFormat | null {
    if (buffer.length < 44) {
      return null;
    }

    try {
      // Check for WAV header
      if (buffer.slice(0, 4).toString() === 'RIFF' && 
          buffer.slice(8, 12).toString() === 'WAVE') {
        return this.parseWAVHeader(buffer);
      }

      // Check for MP3 header
      if ((buffer[0] === 0xFF && (buffer[1]! & 0xE0) === 0xE0) || // MP3 frame sync
          (buffer.slice(0, 3).toString() === 'ID3')) { // ID3 tag
        return this.parseMpegHeader(buffer);
      }

      // Default to PCM if no header detected
      console.warn('[AudioUtils] Could not detect format, assuming PCM 16-bit 16kHz mono');
      return {
        sampleRate: 16000,
        channels: 1,
        bitDepth: 16,
        encoding: 'pcm'
      };

    } catch (error) {
      console.error('[AudioUtils] Error detecting audio format:', error);
      return null;
    }
  }

  /**
   * Calculate audio duration from buffer and format
   */
  getDuration(chunk: AudioChunk): number {
    return this.calculateDuration(chunk);
  }

  /**
   * Split audio into chunks
   */
  splitIntoChunks(input: AudioChunk, chunkDurationMs: number): AudioChunk[] {
    const chunks: AudioChunk[] = [];
    const bytesPerMs = this.calculateBytesPerMs(input.format);
    const chunkSizeBytes = Math.floor(bytesPerMs * chunkDurationMs);
    
    // Ensure chunk size is aligned to sample boundaries
    const bytesPerSample = (input.format.bitDepth / 8) * input.format.channels;
    const alignedChunkSize = Math.floor(chunkSizeBytes / bytesPerSample) * bytesPerSample;

    let offset = 0;
    let sequenceId = input.sequenceId || 0;

    while (offset < input.data.length) {
      const remainingBytes = input.data.length - offset;
      const currentChunkSize = Math.min(alignedChunkSize, remainingBytes);
      
      if (currentChunkSize === 0) break;

      const chunkData = input.data.slice(offset, offset + currentChunkSize);
      const chunkDuration = this.calculateDuration({
        data: chunkData,
        format: input.format
      } as AudioChunk);

      chunks.push({
        data: chunkData,
        format: input.format,
        timestamp: input.timestamp + (offset / bytesPerMs),
        duration: chunkDuration,
        sequenceId: sequenceId
      });

      offset += currentChunkSize;
    }

    return chunks;
  }

  /**
   * Merge multiple audio chunks
   */
  mergeChunks(chunks: AudioChunk[]): AudioChunk | null {
    if (chunks.length === 0) return null;

    // Validate all chunks have same format
    const baseFormat = chunks[0]!.format;
    const hasIncompatibleFormat = chunks.some(chunk => 
      !this.formatsEqual(chunk.format, baseFormat)
    );

    if (hasIncompatibleFormat) {
      throw new Error('Cannot merge chunks with different audio formats');
    }

    // Merge data buffers
    const mergedData = Buffer.concat(chunks.map(chunk => chunk.data));
    const totalDuration = chunks.reduce((sum, chunk) => sum + chunk.duration, 0);

    return {
      data: mergedData,
      format: baseFormat,
      timestamp: chunks[0]!.timestamp,
      duration: totalDuration,
      sequenceId: chunks[0]!.sequenceId || 0
    };
  }

  /**
   * Apply fade in/out effects
   */
  applyFade(
    input: AudioChunk, 
    fadeInMs: number = 0, 
    fadeOutMs: number = 0
  ): AudioChunk {
    if (input.format.encoding !== 'pcm') {
      console.warn('[AudioUtils] Fade effects only supported for PCM format');
      return { ...input, data: Buffer.from(input.data) };
    }

    const samples = this.bufferToSamples(input.data, input.format.bitDepth);
    const sampleRate = input.format.sampleRate;
    
    const fadeInSamples = Math.floor((fadeInMs / 1000) * sampleRate * input.format.channels);
    const fadeOutSamples = Math.floor((fadeOutMs / 1000) * sampleRate * input.format.channels);

    // Apply fade in
    for (let i = 0; i < Math.min(fadeInSamples, samples.length); i++) {
      const fadeRatio = i / fadeInSamples;
      samples[i] = samples[i]! * fadeRatio;
    }

    // Apply fade out
    const fadeOutStart = Math.max(0, samples.length - fadeOutSamples);
    for (let i = fadeOutStart; i < samples.length; i++) {
      const fadeRatio = (samples.length - i) / fadeOutSamples;
      samples[i] = samples[i]! * fadeRatio;
    }

    const fadedBuffer = this.samplesToBuffer(samples, input.format.bitDepth);

    return {
      ...input,
      data: fadedBuffer
    };
  }

  /**
   * Calculate audio power/energy
   */
  calculatePower(input: AudioChunk): number {
    if (input.format.encoding !== 'pcm') {
      return 0;
    }

    const samples = this.bufferToSamples(input.data, input.format.bitDepth);
    const sumSquares = samples.reduce((sum, sample) => sum + sample * sample, 0);
    return Math.sqrt(sumSquares / samples.length);
  }

  /**
   * Detect silence in audio
   */
  detectSilence(input: AudioChunk, threshold: number = 0.01): boolean {
    const power = this.calculatePower(input);
    return power < threshold;
  }

  /**
   * Apply gain to audio
   */
  applyGain(input: AudioChunk, gainDb: number): AudioChunk {
    if (input.format.encoding !== 'pcm') {
      console.warn('[AudioUtils] Gain only supported for PCM format');
      return { ...input, data: Buffer.from(input.data) };
    }

    const gainLinear = Math.pow(10, gainDb / 20);
    const samples = this.bufferToSamples(input.data, input.format.bitDepth);
    const gainedSamples = samples.map(sample => {
      const gained = sample * gainLinear;
      // Clamp to prevent clipping
      return Math.max(-1, Math.min(1, gained));
    });

    const gainedBuffer = this.samplesToBuffer(gainedSamples, input.format.bitDepth);

    return {
      ...input,
      data: gainedBuffer
    };
  }

  // Private helper methods

  private formatsEqual(format1: AudioFormat, format2: AudioFormat): boolean {
    return format1.sampleRate === format2.sampleRate &&
           format1.channels === format2.channels &&
           format1.bitDepth === format2.bitDepth &&
           format1.encoding === format2.encoding;
  }

  private calculateDuration(chunk: AudioChunk): number {
    const bytesPerSample = (chunk.format.bitDepth / 8) * chunk.format.channels;
    const totalSamples = chunk.data.length / bytesPerSample;
    return (totalSamples / chunk.format.sampleRate) * 1000;
  }

  private calculateBytesPerMs(format: AudioFormat): number {
    const bytesPerSample = (format.bitDepth / 8) * format.channels;
    return (format.sampleRate * bytesPerSample) / 1000;
  }

  private bufferToSamples(buffer: Buffer, bitDepth: number): number[] {
    const samples: number[] = [];

    switch (bitDepth) {
      case 16:
        for (let i = 0; i < buffer.length; i += 2) {
          const sample = buffer.readInt16LE(i) / 32768;
          samples.push(sample);
        }
        break;
      
      case 24:
        for (let i = 0; i < buffer.length; i += 3) {
          let sample = buffer.readUIntLE(i, 3);
          if (sample > 0x7FFFFF) sample -= 0x1000000;
          samples.push(sample / 8388608);
        }
        break;
      
      case 32:
        for (let i = 0; i < buffer.length; i += 4) {
          const sample = buffer.readInt32LE(i) / 2147483648;
          samples.push(sample);
        }
        break;
      
      default:
        throw new Error(`Unsupported bit depth: ${bitDepth}`);
    }

    return samples;
  }

  private samplesToBuffer(samples: number[], bitDepth: number): Buffer {
    let buffer: Buffer;

    switch (bitDepth) {
      case 16:
        buffer = Buffer.alloc(samples.length * 2);
        for (let i = 0; i < samples.length; i++) {
          const sample = Math.round(samples[i]! * 32767);
          const clamped = Math.max(-32768, Math.min(32767, sample));
          buffer.writeInt16LE(clamped, i * 2);
        }
        break;
      
      case 24:
        buffer = Buffer.alloc(samples.length * 3);
        for (let i = 0; i < samples.length; i++) {
          const sample = Math.round(samples[i]! * 8388607);
          const clamped = Math.max(-8388608, Math.min(8388607, sample));
          buffer.writeUIntLE(clamped < 0 ? clamped + 0x1000000 : clamped, i * 3, 3);
        }
        break;
      
      case 32:
        buffer = Buffer.alloc(samples.length * 4);
        for (let i = 0; i < samples.length; i++) {
          const sample = Math.round(samples[i]! * 2147483647);
          const clamped = Math.max(-2147483648, Math.min(2147483647, sample));
          buffer.writeInt32LE(clamped, i * 4);
        }
        break;
      
      default:
        throw new Error(`Unsupported bit depth: ${bitDepth}`);
    }

    return buffer;
  }

  private async resampleAudio(
    data: Buffer, 
    currentFormat: AudioFormat, 
    targetSampleRate: number
  ): Promise<Buffer> {
    // Simple linear interpolation resampling
    // For production use, consider implementing proper anti-aliasing filters
    
    const samples = this.bufferToSamples(data, currentFormat.bitDepth);
    const ratio = targetSampleRate / currentFormat.sampleRate;
    const newLength = Math.floor(samples.length * ratio);
    const resampledSamples: number[] = [];

    for (let i = 0; i < newLength; i++) {
      const sourceIndex = i / ratio;
      const lowerIndex = Math.floor(sourceIndex);
      const upperIndex = Math.ceil(sourceIndex);
      const fraction = sourceIndex - lowerIndex;

      if (upperIndex >= samples.length) {
        resampledSamples.push(samples[lowerIndex] || 0);
      } else {
        const lowerSample = samples[lowerIndex] || 0;
        const upperSample = samples[upperIndex] || 0;
        const interpolated = lowerSample + (upperSample - lowerSample) * fraction;
        resampledSamples.push(interpolated);
      }
    }

    return this.samplesToBuffer(resampledSamples, currentFormat.bitDepth);
  }

  private convertChannels(
    data: Buffer, 
    currentFormat: AudioFormat, 
    targetChannels: number
  ): Buffer {
    if (currentFormat.channels === targetChannels) {
      return data;
    }

    const samples = this.bufferToSamples(data, currentFormat.bitDepth);
    const samplesPerChannel = samples.length / currentFormat.channels;
    const newSamples: number[] = [];

    if (currentFormat.channels === 1 && targetChannels === 2) {
      // Mono to stereo: duplicate mono channel
      for (let i = 0; i < samples.length; i++) {
        newSamples.push(samples[i]!, samples[i]!);
      }
    } else if (currentFormat.channels === 2 && targetChannels === 1) {
      // Stereo to mono: average left and right channels
      for (let i = 0; i < samples.length; i += 2) {
        const left = samples[i] || 0;
        const right = samples[i + 1] || 0;
        newSamples.push((left + right) / 2);
      }
    } else {
      throw new Error(`Unsupported channel conversion: ${currentFormat.channels} to ${targetChannels}`);
    }

    return this.samplesToBuffer(newSamples, currentFormat.bitDepth);
  }

  private convertBitDepth(data: Buffer, fromBitDepth: number, toBitDepth: number): Buffer {
    if (fromBitDepth === toBitDepth) {
      return data;
    }

    const samples = this.bufferToSamples(data, fromBitDepth);
    return this.samplesToBuffer(samples, toBitDepth);
  }

  private async convertEncoding(
    data: Buffer, 
    currentFormat: AudioFormat, 
    targetEncoding: AudioFormat['encoding']
  ): Promise<Buffer> {
    if (currentFormat.encoding === targetEncoding) {
      return data;
    }

    // Basic encoding conversions
    switch (`${currentFormat.encoding}->${targetEncoding}`) {
      case 'pcm->wav':
        return this.addWAVHeader(data, currentFormat);
      
      case 'wav->pcm':
        return this.removeWAVHeader(data);
      
      default:
        console.warn(`[AudioUtils] Unsupported encoding conversion: ${currentFormat.encoding} to ${targetEncoding}`);
        return data;
    }
  }

  private addWAVHeader(data: Buffer, format: AudioFormat): Buffer {
    const header = Buffer.alloc(44);
    const dataSize = data.length;
    const fileSize = dataSize + 36;
    const byteRate = format.sampleRate * format.channels * (format.bitDepth / 8);
    const blockAlign = format.channels * (format.bitDepth / 8);

    // WAV header
    header.write('RIFF', 0);
    header.writeUInt32LE(fileSize, 4);
    header.write('WAVE', 8);
    header.write('fmt ', 12);
    header.writeUInt32LE(16, 16); // Subchunk1Size
    header.writeUInt16LE(1, 20); // AudioFormat (PCM)
    header.writeUInt16LE(format.channels, 22);
    header.writeUInt32LE(format.sampleRate, 24);
    header.writeUInt32LE(byteRate, 28);
    header.writeUInt16LE(blockAlign, 32);
    header.writeUInt16LE(format.bitDepth, 34);
    header.write('data', 36);
    header.writeUInt32LE(dataSize, 40);

    return Buffer.concat([header, data]);
  }

  private removeWAVHeader(data: Buffer): Buffer {
    // Skip WAV header (typically 44 bytes)
    const headerSize = this.findDataChunkOffset(data);
    return data.slice(headerSize);
  }

  private findDataChunkOffset(buffer: Buffer): number {
    // Look for 'data' chunk
    for (let i = 12; i < buffer.length - 4; i++) {
      if (buffer.slice(i, i + 4).toString() === 'data') {
        return i + 8; // Skip 'data' and size field
      }
    }
    return 44; // Default WAV header size
  }

  private parseWAVHeader(buffer: Buffer): AudioFormat {
    const channels = buffer.readUInt16LE(22);
    const sampleRate = buffer.readUInt32LE(24);
    const bitDepth = buffer.readUInt16LE(34);

    return {
      sampleRate,
      channels,
      bitDepth: bitDepth as any,
      encoding: 'wav' as any
    };
  }

  private parseMpegHeader(buffer: Buffer): AudioFormat {
    // Simplified MP3 header parsing
    // For production use, implement full MPEG header parsing
    return {
      sampleRate: 44100, // Common MP3 sample rate
      channels: 2, // Assume stereo
      bitDepth: 16, // MP3 is typically decoded to 16-bit
      encoding: 'mp3'
    };
  }
}

/**
 * Singleton instance getter
 */
export const audioUtils = AudioUtils.getInstance();

/**
 * Convenience functions
 */
export function createAudioChunk(
  data: Buffer,
  format: AudioFormat,
  timestamp?: number
): AudioChunk {
  const utils = AudioUtils.getInstance();
  return {
    data,
    format,
    timestamp: timestamp || Date.now(),
    duration: utils.getDuration({ data, format } as AudioChunk)
  };
}

export function isAudioFormatSupported(format: AudioFormat): boolean {
  const supportedEncodings = ['pcm', 'wav', 'mp3', 'opus'];
  const supportedBitDepths = [16, 24, 32];
  const supportedChannels = [1, 2];

  return supportedEncodings.includes(format.encoding) &&
         supportedBitDepths.includes(format.bitDepth) &&
         supportedChannels.includes(format.channels) &&
         format.sampleRate > 0;
}

export function getOptimalAudioFormat(
  inputFormat: AudioFormat,
  requirements?: {
    maxSampleRate?: number;
    preferredChannels?: number;
    preferredBitDepth?: number;
    preferredEncoding?: AudioFormat['encoding'];
  }
): AudioFormat {
  const optimal: AudioFormat = { ...inputFormat };

  if (requirements?.maxSampleRate && optimal.sampleRate > requirements.maxSampleRate) {
    optimal.sampleRate = requirements.maxSampleRate;
  }

  if (requirements?.preferredChannels) {
    optimal.channels = requirements.preferredChannels;
  }

  if (requirements?.preferredBitDepth) {
    optimal.bitDepth = requirements.preferredBitDepth as any;
  }

  if (requirements?.preferredEncoding) {
    optimal.encoding = requirements.preferredEncoding;
  }

  return optimal;
}