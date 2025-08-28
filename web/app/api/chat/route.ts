/**
 * Guardian-aware Chat API endpoint with fallback protection
 */
import { NextRequest, NextResponse } from 'next/server';
import OpenAI from 'openai';
import { INTAKE_BLOCKED } from '../guard/stop-intake/route';

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

    // 🛡️ GUARDIAN CHECK: Block requests if system overloaded
    if (INTAKE_BLOCKED) {
      console.log('[GUARDIAN] Request blocked - system overload protection active');
      return NextResponse.json({
        error: 'Alice system protection active - please try again later',
        blocked: true,
        guardian: true
      }, { status: 503 }); // Service Unavailable
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