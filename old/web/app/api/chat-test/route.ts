/**
 * Simple chat endpoint for voice testing with mock AI responses
 * Will be replaced with real OpenAI when API key is configured
 */
import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const { message } = await request.json();
    
    if (!message) {
      return NextResponse.json({
        error: 'Message required'
      }, { status: 400 });
    }

    // Mock AI responses based on input
    const mockResponses: Record<string, string> = {
      'hej alice': 'Hej! Vad kul att höra från dig! Hur kan jag hjälpa dig idag?',
      'hej': 'Hej där! Jag är Alice, din AI-assistent. Vad kan jag göra för dig?',
      'vad är klockan': `Klockan är ${new Date().toLocaleTimeString('sv-SE', { 
        hour: '2-digit', 
        minute: '2-digit' 
      })} just nu.`,
      'hur är vädret': 'Jag kan tyvärr inte kolla vädret just nu eftersom mina verktyg inte är konfigurerade. Men jag hoppas det är fint väder där du är!',
      'vad heter du': 'Jag heter Alice och jag är din AI-assistent. Jag kan hjälpa dig med olika uppgifter genom röstkommandon.',
      'default': 'Tack för ditt meddelande! Jag förstod att du sa: "{message}". Jag är Alice och även om mina avancerade funktioner inte är aktiverade just nu, så fungerar röstfunktionen perfekt!'
    };

    // Find appropriate response
    const key = message.toLowerCase().trim();
    let response = mockResponses[key];
    
    if (!response) {
      // Check for partial matches
      for (const [pattern, resp] of Object.entries(mockResponses)) {
        if (pattern !== 'default' && key.includes(pattern)) {
          response = resp;
          break;
        }
      }
    }
    
    if (!response) {
      response = mockResponses.default.replace('{message}', message);
    }

    // Add a small delay to simulate API processing
    await new Promise(resolve => setTimeout(resolve, 800));

    return NextResponse.json({
      message: response,
      timestamp: new Date().toISOString(),
      mock: true
    });

  } catch (error) {
    console.error('Chat test error:', error);
    return NextResponse.json({
      error: 'Failed to process message'
    }, { status: 500 });
  }
}