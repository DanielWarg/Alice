#!/usr/bin/env python3
"""
🎙️ Create Test Audio File
Generate a simple spoken phrase for ASR testing
"""

import numpy as np
import wave
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_spoken_phrase(phrase: str = "hello alice", duration: float = 2.0, sample_rate: int = 16000) -> np.ndarray:
    """Create a simple spoken phrase simulation"""
    
    # Convert phrase to phonetic patterns
    phonetic_map = {
        'hello': [(200, 0.3), (800, 0.2), (400, 0.15), (600, 0.2), (300, 0.15)],
        'alice': [(500, 0.2), (1200, 0.15), (300, 0.1), (900, 0.2), (400, 0.15)],
        'test': [(800, 0.15), (400, 0.1), (1000, 0.15), (300, 0.1)],
        'one': [(400, 0.2), (600, 0.15), (300, 0.15)],
        'two': [(300, 0.15), (800, 0.2), (400, 0.15)],
        'three': [(600, 0.15), (1000, 0.15), (500, 0.15), (400, 0.1)]
    }
    
    words = phrase.lower().split()
    total_samples = int(duration * sample_rate)
    audio = np.zeros(total_samples, dtype=np.float32)
    
    # Time per word
    word_duration = duration / len(words)
    
    for i, word in enumerate(words):
        if word not in phonetic_map:
            continue
            
        word_start = int(i * word_duration * sample_rate)
        word_samples = int(word_duration * sample_rate * 0.8)  # 80% of word time is speech
        
        if word_start + word_samples > total_samples:
            word_samples = total_samples - word_start
            
        # Get phonetic pattern
        phonemes = phonetic_map[word]
        phoneme_duration = word_samples / len(phonemes)
        
        for j, (freq, amp) in enumerate(phonemes):
            phoneme_start = word_start + int(j * phoneme_duration)
            phoneme_samples = int(phoneme_duration)
            
            if phoneme_start + phoneme_samples > total_samples:
                phoneme_samples = total_samples - phoneme_start
                
            # Generate phoneme
            t = np.arange(phoneme_samples) / sample_rate
            
            # Fundamental frequency with slight vibrato
            f0 = freq * (1 + 0.05 * np.sin(2 * np.pi * 6 * t))
            
            # Add harmonics for more realistic voice
            phoneme_audio = (
                amp * np.sin(2 * np.pi * f0 * t) +  # Fundamental
                amp * 0.5 * np.sin(2 * np.pi * f0 * 2 * t) +  # 2nd harmonic
                amp * 0.3 * np.sin(2 * np.pi * f0 * 3 * t) +  # 3rd harmonic
                amp * 0.1 * np.random.normal(0, 1, phoneme_samples)  # Noise
            )
            
            # Apply envelope
            envelope = np.exp(-3 * ((t - t[len(t)//2]) ** 2) / (phoneme_duration ** 2))
            phoneme_audio = phoneme_audio * envelope
            
            # Add to main audio
            audio[phoneme_start:phoneme_start + phoneme_samples] += phoneme_audio
    
    # Normalize and add breath noise
    audio = audio * 0.8
    audio += 0.02 * np.random.normal(0, 1, total_samples).astype(np.float32)
    
    # Final normalization
    audio = np.clip(audio, -1.0, 1.0)
    
    return audio

def save_wav(audio: np.ndarray, filename: str, sample_rate: int = 16000):
    """Save audio as WAV file"""
    # Convert to 16-bit PCM
    audio_int16 = (audio * 32767).astype(np.int16)
    
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_int16.tobytes())

def create_test_files():
    """Create various test audio files"""
    
    phrases = [
        ("hello alice", "test_hello_alice.wav"),
        ("test one two three", "test_counting.wav"), 
        ("this is a test", "test_sentence.wav")
    ]
    
    for phrase, filename in phrases:
        logger.info(f"Creating {filename}: '{phrase}'")
        audio = create_spoken_phrase(phrase, duration=2.5)
        save_wav(audio, filename)
        logger.info(f"✅ Saved {filename}")

if __name__ == "__main__":
    create_test_files()
    logger.info("🎉 Test audio files created!")