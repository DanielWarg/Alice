/**
 * Real OpenAI Chat API endpoint for live AI responses
 */
import { NextRequest, NextResponse } from 'next/server';
import OpenAI from 'openai';

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

export async function POST(request: NextRequest) {
  try {
    const { message } = await request.json();
    
    if (!message) {
      return NextResponse.json({
        error: 'Message required'
      }, { status: 400 });
    }

    if (!process.env.OPENAI_API_KEY) {
      return NextResponse.json({
        error: 'OpenAI API key not configured'
      }, { status: 500 });
    }

    // Call OpenAI with Swedish context
    const completion = await openai.chat.completions.create({
      model: 'gpt-4o-mini',
      messages: [
        {
          role: 'system',
          content: `Du är Alice, en hjälpsam AI-assistent som pratar svenska. Du ska svara på ett naturligt och vänligt sätt på svenska. Håll svaren korta och koncisa (max 2-3 meningar) eftersom detta är en röstkonversation. Du kan hjälpa med frågor, ge information och ha vanliga samtal.`
        },
        {
          role: 'user',
          content: message
        }
      ],
      max_tokens: 150,
      temperature: 0.7
    });

    const response = completion.choices[0]?.message?.content;
    
    if (!response) {
      return NextResponse.json({
        error: 'No response from OpenAI'
      }, { status: 500 });
    }

    return NextResponse.json({
      message: response.trim(),
      timestamp: new Date().toISOString(),
      model: 'gpt-4o-mini',
      live: true
    });

  } catch (error) {
    console.error('OpenAI Chat error:', error);
    return NextResponse.json({
      error: 'Failed to get AI response'
    }, { status: 500 });
  }
}