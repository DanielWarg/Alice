/**
 * OpenAI Text-to-Speech API endpoint
 */
import { NextRequest, NextResponse } from 'next/server';
import OpenAI from 'openai';

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

export async function POST(request: NextRequest) {
  try {
    const { text, voice = 'nova' } = await request.json();

    if (!text) {
      return NextResponse.json({
        error: 'Text is required'
      }, { status: 400 });
    }

    if (!process.env.OPENAI_API_KEY) {
      return NextResponse.json({
        error: 'OpenAI API key not configured'
      }, { status: 500 });
    }

    const mp3Response = await openai.audio.speech.create({
      model: 'tts-1',
      voice: voice as 'alloy' | 'echo' | 'fable' | 'onyx' | 'nova' | 'shimmer',
      input: text,
    });

    const arrayBuffer = await mp3Response.arrayBuffer();
    
    return new NextResponse(arrayBuffer, {
      headers: {
        'Content-Type': 'audio/mpeg',
        'Content-Length': arrayBuffer.byteLength.toString(),
      },
    });

  } catch (error) {
    console.error('TTS Error:', error);
    return NextResponse.json({
      error: 'TTS generation failed'
    }, { status: 500 });
  }
}