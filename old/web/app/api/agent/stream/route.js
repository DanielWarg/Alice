import { NextResponse } from 'next/server';

export async function POST(request) {
  try {
    const body = await request.json();
    const { prompt, model, provider, use_rag, use_tools, language, context } = body;

    // Forward the request to the Alice backend server
    const backendUrl = 'http://127.0.0.1:8000/api/chat';
    
    const chatPayload = {
      prompt,
      model: model || 'gpt-oss:20b',
      stream: false,
      provider: provider || 'local',
      context: context || {}
    };

    console.log('Forwarding to Alice backend:', { prompt, provider });

    const response = await fetch(backendUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(chatPayload)
    });

    if (!response.ok) {
      throw new Error(`Backend request failed: ${response.status}`);
    }

    const result = await response.json();
    
    // Convert to agent response format expected by VoiceClient
    return NextResponse.json({
      type: 'chunk',
      content: result.text || 'No response from Alice',
      metadata: {
        memory_id: result.memory_id,
        provider: result.provider || provider
      }
    });

  } catch (error) {
    console.error('Agent stream error:', error);
    return NextResponse.json({
      type: 'error',
      content: `Agent error: ${error.message}`,
      metadata: {}
    }, { status: 500 });
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