/**
 * Agent API - Main conversation endpoint with toolcalling support
 * Maps ASR.final → agent processing → TTS.speak(reply)
 */
import { NextRequest, NextResponse } from 'next/server';
import OpenAI from 'openai';

// Initialize OpenAI client
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

interface Message {
  role: 'system' | 'user' | 'assistant' | 'tool';
  content: string | null;
  tool_calls?: ToolCall[];
  name?: string;
  tool_call_id?: string;
}

interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, any>;
}

interface AgentRequest {
  session_id: string;
  request_id?: string;
  user_id?: string;
  locale?: string;
  mode?: 'single' | 'stream';
  allow_tool_calls?: boolean;
  tools_capabilities?: any[];
  messages: Message[];
  limits?: {
    max_tokens?: number;
    temperature?: number;
    tool_max_depth?: number;
  };
  timeout_ms?: number;
}

interface AgentResponse {
  session_id: string;
  request_id?: string;
  next_action: 'final' | 'tool_call';
  assistant: {
    content: string | null;
    tool_calls?: ToolCall[];
    speech_hint?: {
      ssml?: string;
      voice_id?: string;
      rate?: number;
      pitch?: number;
    };
  };
  metrics: {
    llm_latency_ms: number;
  };
}

// Available tools configuration
const AVAILABLE_TOOLS = [
  {
    type: "function" as const,
    function: {
      name: "timer.set",
      description: "Starta en timer med specificerad tid",
      parameters: {
        type: "object",
        properties: {
          minutes: {
            type: "integer",
            minimum: 0,
            maximum: 24 * 60,
            description: "Antal minuter"
          },
          seconds: {
            type: "integer",
            minimum: 0,
            maximum: 59,
            default: 0,
            description: "Antal sekunder"
          },
          label: {
            type: "string",
            maxLength: 64,
            description: "Valfri etikett för timern"
          }
        },
        required: ["minutes"]
      }
    }
  },
  {
    type: "function" as const,
    function: {
      name: "weather.get",
      description: "Hämta aktuellt väder och prognos för en plats",
      parameters: {
        type: "object",
        properties: {
          location: {
            type: "string",
            minLength: 2,
            description: "Platsnamn, t.ex. 'Göteborg, SE'"
          },
          units: {
            type: "string",
            enum: ["metric", "imperial"],
            default: "metric",
            description: "Temperaturenheter"
          },
          include_forecast: {
            type: "boolean",
            default: true,
            description: "Inkludera väderprognos"
          },
          days: {
            type: "integer",
            minimum: 1,
            maximum: 7,
            default: 1,
            description: "Antal dagar för prognos"
          }
        },
        required: ["location"]
      }
    }
  }
];

export async function POST(request: NextRequest) {
  const startTime = Date.now();
  
  try {
    const body: AgentRequest = await request.json();
    
    // Validate required fields
    if (!body.session_id || !body.messages) {
      return NextResponse.json({
        error: {
          code: 'INVALID_INPUT',
          message: 'session_id och messages krävs',
          fallback_action: 'abort'
        }
      }, { status: 400 });
    }

    // Prepare system message
    const systemMessage = {
      role: 'system' as const,
      content: `Du är Alice, en hjälpsam AI-assistent som talar svenska. Du kan hjälpa till med:
- Väderinformation (weather.get)
- Timers och påminnelser (timer.set)
- Allmänna frågor och konversation

Svara kort och naturligt på svenska. När du använder verktyg, förklara vad du gör.
Dagens datum: ${new Date().toLocaleDateString('sv-SE')}`
    };

    // Prepare messages for OpenAI API
    const messages = [systemMessage, ...body.messages.filter(m => m.role !== 'system')];

    // Check if we should use tools
    const shouldUseTools = body.allow_tool_calls !== false;
    
    const openaiRequest: any = {
      model: 'gpt-4o',
      messages: messages,
      max_tokens: body.limits?.max_tokens || 300,
      temperature: body.limits?.temperature || 0.3,
      timeout: body.timeout_ms || 20000
    };

    if (shouldUseTools) {
      openaiRequest.tools = AVAILABLE_TOOLS;
      openaiRequest.tool_choice = 'auto';
    }

    // Call OpenAI API
    console.log('🤖 Sending request to OpenAI...');
    const completion = await openai.chat.completions.create(openaiRequest);

    const llmLatency = Date.now() - startTime;
    const choice = completion.choices[0];
    
    if (!choice) {
      throw new Error('No response from OpenAI');
    }

    // Check if response contains tool calls
    if (choice.message.tool_calls && choice.message.tool_calls.length > 0) {
      // Return tool calls for client to execute
      const response: AgentResponse = {
        session_id: body.session_id,
        request_id: body.request_id,
        next_action: 'tool_call',
        assistant: {
          content: null,
          tool_calls: choice.message.tool_calls.map(tc => ({
            id: tc.id,
            name: tc.function.name,
            arguments: JSON.parse(tc.function.arguments)
          }))
        },
        metrics: {
          llm_latency_ms: llmLatency
        }
      };

      console.log(`🔧 Returning ${choice.message.tool_calls.length} tool calls in ${llmLatency}ms`);
      return NextResponse.json(response);
    }

    // Return final response
    const response: AgentResponse = {
      session_id: body.session_id,
      request_id: body.request_id,
      next_action: 'final',
      assistant: {
        content: choice.message.content || 'Jag förstod inte riktigt vad du menade.',
        speech_hint: {
          voice_id: 'sv_female_1',
          rate: 1.0,
          pitch: 0
        }
      },
      metrics: {
        llm_latency_ms: llmLatency
      }
    };

    console.log(`💬 Final response in ${llmLatency}ms: "${response.assistant.content?.substring(0, 50)}..."`);
    return NextResponse.json(response);

  } catch (error: any) {
    const llmLatency = Date.now() - startTime;
    console.error('❌ Agent error:', error);

    // Handle specific error types
    if (error.code === 'insufficient_quota' || error.status === 429) {
      return NextResponse.json({
        error: {
          code: 'TOO_MANY_REQUESTS',
          message: 'För många förfrågningar. Försök igen senare.',
          retry_after_ms: 5000,
          fallback_action: 'text_only'
        }
      }, { status: 429 });
    }

    if (error.code === 'context_length_exceeded') {
      return NextResponse.json({
        error: {
          code: 'INVALID_INPUT',
          message: 'Konversationen är för lång. Starta om för att fortsätta.',
          fallback_action: 'abort'
        }
      }, { status: 400 });
    }

    // Generic error
    return NextResponse.json({
      error: {
        code: 'INTERNAL',
        message: 'Ett tekniskt fel uppstod. Försök igen.',
        fallback_action: 'retry'
      }
    }, { status: 500 });
  }
}

// Health check endpoint
export async function GET() {
  try {
    // Quick health check - just verify OpenAI client is configured
    if (!process.env.OPENAI_API_KEY) {
      return NextResponse.json({
        status: 'error',
        message: 'OpenAI API key not configured'
      }, { status: 503 });
    }

    return NextResponse.json({
      status: 'ok',
      timestamp: new Date().toISOString(),
      version: '1.0'
    });
  } catch (error) {
    return NextResponse.json({
      status: 'error',
      message: 'Agent service unavailable'
    }, { status: 503 });
  }
}