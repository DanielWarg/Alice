import { NextResponse } from 'next/server';

export async function POST(request) {
  try {
    const body = await request.json();
    const { text, model, voice, speed, response_format, stream } = body;

    // Forward to Alice backend TTS endpoint
    const backendUrl = 'http://127.0.0.1:8000/api/tts/synthesize';
    
    const ttsPayload = {
      text,
      personality: 'alice', // Default personality
      emotion: 'friendly',   // Default emotion
      voice: voice || 'sv_SE-nst-medium',
      cache: true
    };

    console.log('Forwarding TTS to Alice backend:', { text: text?.substring(0, 50) + '...', voice });

    const response = await fetch(backendUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(ttsPayload)
    });

    if (!response.ok) {
      // Fallback to mock response if backend is unavailable
      console.warn('Alice TTS backend unavailable, using mock response');
      
      // Return a minimal mock audio stream
      const mockAudioData = new Uint8Array(1024).fill(0);
      return new NextResponse(mockAudioData, {
        headers: {
          'Content-Type': response_format === 'mp3' ? 'audio/mpeg' : 'audio/wav',
          'Transfer-Encoding': 'chunked'
        }
      });
    }

    const result = await response.json();
    
    if (result.success && result.audio_data) {
      // Convert base64 audio data to binary
      const audioBuffer = Uint8Array.from(atob(result.audio_data), c => c.charCodeAt(0));
      
      return new NextResponse(audioBuffer, {
        headers: {
          'Content-Type': response_format === 'mp3' ? 'audio/mpeg' : 'audio/wav',
          'Transfer-Encoding': 'chunked'
        }
      });
    } else {
      throw new Error('TTS synthesis failed');
    }

  } catch (error) {
    console.error('TTS OpenAI stream error:', error);
    
    // Return empty audio as fallback
    const emptyAudio = new Uint8Array(1024).fill(0);
    return new NextResponse(emptyAudio, {
      status: 200, // Don't fail - just return silence
      headers: {
        'Content-Type': 'audio/wav'
      }
    });
  }
}

// Handle preflight OPTIONS request for CORS
export async function OPTIONS() {
  return new NextResponse(null, {
    status: 200,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    },
  });
}